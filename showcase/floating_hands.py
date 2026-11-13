# SPDX-License-Identifier: Apache-2.0
"""Generic dual floating-hand embodiment for FlashCHORD (multi-embodiment showcase, 2026-11-06).

Same mounting as FlashCHORD's SharpaHands (3 prismatic wrist joints + a ball wrist, then the URDF fingers; wrist by
joint PD + effort PD, fingers by position PD), but for ANY hand URDF prepared by showcase/prep_robots.py:
  - robot name "<side>_<robot>", every link and joint name starts with "<side>_";
  - semantic links "<side>_palm" (the URDF root), "<side>_<digit>_DP" and "<side>_<digit>_fingertip" per digit;
  - no <mimic> tags (coupled joints are driven independently: a showcase simplification).
Finger joints may be revolute or prismatic (parallel grippers): wrist joints are told apart by name, not by type.
Self-collisions inside one hand are off (no hand-specific exclusion list is needed); hand-hand and hand-object contacts
stay on. Every hand link that owns a shape is an object-contact link (the contact reward is object-side in FlashCHORD,
so it needs no hand-part mapping).

Install: copy this file to flash_chord/embodiments/floating_hands.py (showcase/install_fc.sh does it), so a checkpoint's
saved config (_target_ flash_chord.embodiments.floating_hands.FloatingHands) rebuilds in the evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import newton
import numpy as np

from flash_chord.data.reference import HandPoseReference
from flash_chord.embodiments.base import (
    BodyFrame,
    Embodiment,
    EmbodimentLayout,
    HandLayout,
    HandLinkGeometry,
    JointControlSpec,
    finger_joint_order,
    register_embodiment,
    resolve_joint_controls,
)
from flash_chord.embodiments.binding import RobotReferenceBinding, build_robot_reference_binding
from flash_chord.embodiments.frames import capture_body_ids, resolve_body_frames
from flash_chord.utils.quat import wxyz_to_rotvec, wxyz_to_xyzw

_WRIST_POS = ("wrist_x", "wrist_y", "wrist_z")


def _default_overrides() -> dict[str, dict]:
    return {
        r"wrist_[xyz]$": dict(kp=400.0, kd=20.0, effort_limit=150.0),  # mid-stiffness wrist (our sharpa_hands_mid)
        r"right_wrist_y$": dict(default_pos=0.25),
        r"left_wrist_y$": dict(default_pos=-0.25),
        r"wrist_z$": dict(default_pos=0.5),
        r"wrist_rotvec$": dict(mode="effort", kp=25.0, kd=6.0, effort_limit=45.0),
    }


@dataclass
class FloatingHandsConfig:
    robot: str = "hand"
    left_urdf_path: Path | None = None
    right_urdf_path: Path | None = None
    digits: tuple[str, ...] = ("thumb", "index")
    left_base_pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    right_base_pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    gravity_compensation: bool = True
    self_collisions: bool = False
    default_joint: JointControlSpec = field(default_factory=JointControlSpec)
    joint_overrides: dict[str, dict] = field(default_factory=_default_overrides)
    finger_overrides: dict[str, dict] = field(default_factory=dict)  # merged after joint_overrides
    # soft-pad contact model for the hand's shapes (2026-11-06, Panda fix): MuJoCo condim 4 adds torsional friction, so a
    # two-finger pinch resists the object twisting about the pinch axis, as rubber pads do; None keeps the defaults
    pad_condim: int | None = None
    pad_torsional: float | None = None   # m (MuJoCo torsional friction coefficient, ~ contact patch radius x mu)
    pad_mu: float | None = None

    def __post_init__(self) -> None:
        self.digits = tuple(self.digits)
        if self.left_urdf_path is None or self.right_urdf_path is None:
            raise ValueError("FloatingHandsConfig needs left_urdf_path and right_urdf_path")
        self.left_urdf_path = Path(self.left_urdf_path)
        self.right_urdf_path = Path(self.right_urdf_path)
        if not self.digits:
            raise ValueError("FloatingHandsConfig needs at least one digit")


def _semantic_frame_names(side: str, digits: tuple[str, ...]) -> tuple[str, ...]:
    return (
        f"{side}_palm",
        *(f"{side}_{d}_DP" for d in digits),
        *(f"{side}_{d}_fingertip" for d in digits),
    )


@register_embodiment("floating_hands")
class FloatingHands:
    """Two floating hands of any prepared URDF (left + right) as one Newton robot."""

    name = "floating_hands"

    def __init__(self, config: FloatingHandsConfig | None = None) -> None:
        if config is None:
            raise ValueError("FloatingHands needs a FloatingHandsConfig")
        self.config = config

    def _add_hand(self, builder: newton.ModelBuilder, side: str, urdf_path, base_pos) -> dict[str, int]:
        import warp as wp  # noqa: PLC0415

        dummy_mass = 1e-4
        bodies = [
            builder.add_link(mass=dummy_mass, xform=wp.transform(wp.vec3(0.0, 0.0, 0.0)), label=f"{side}_wrist_p{a}_body")
            for a in "xyz"
        ]
        j_px = builder.add_joint_prismatic(
            parent=-1, child=bodies[0], axis=newton.Axis.X,
            parent_xform=wp.transform(wp.vec3(*base_pos), wp.quat_identity()),
            label=f"{side}_wrist_x", friction=0.01, armature=0.01,
        )
        j_py = builder.add_joint_prismatic(
            parent=bodies[0], child=bodies[1], axis=newton.Axis.Y, label=f"{side}_wrist_y", friction=0.01, armature=0.01
        )
        j_pz = builder.add_joint_prismatic(
            parent=bodies[1], child=bodies[2], axis=newton.Axis.Z, label=f"{side}_wrist_z", friction=0.01, armature=0.01
        )
        builder.add_articulation([j_px, j_py, j_pz], label=f"{side}_wrist_position")
        builder.add_urdf(
            source=str(urdf_path),
            xform=wp.transform(wp.vec3(0.0, 0.0, 0.0)),
            base_joint={
                "joint_type": newton.JointType.BALL,
                "label": f"{side}_wrist_rotvec",
                "angular_axes": [
                    newton.ModelBuilder.JointDofConfig(axis=newton.Axis.X, armature=0.01, friction=0.01),
                    newton.ModelBuilder.JointDofConfig(axis=newton.Axis.Y, armature=0.01, friction=0.01),
                    newton.ModelBuilder.JointDofConfig(axis=newton.Axis.Z, armature=0.01, friction=0.01),
                ],
            },
            parent_body=bodies[2],
            force_show_colliders=False,
            enable_self_collisions=self.config.self_collisions,
            ignore_inertial_definitions=False,
            collapse_fixed_joints=False,
            force_position_velocity_actuation=True,
        )
        return capture_body_ids(builder, _semantic_frame_names(side, self.config.digits))

    def _apply_control_config(self, builder: newton.ModelBuilder) -> None:
        cfg = self.config
        overrides = dict(cfg.joint_overrides)
        overrides.update(cfg.finger_overrides)
        passive_damping = builder.custom_attributes["mujoco:dof_passive_damping"].values
        joint_ids = tuple(j for j, t in enumerate(builder.joint_type) if t != newton.JointType.FIXED)
        specs = resolve_joint_controls(tuple(builder.joint_label[j] for j in joint_ids), cfg.default_joint, overrides)
        for j, spec in zip(joint_ids, specs, strict=True):
            qd_start = builder.joint_qd_start[j]
            q_start = builder.joint_q_start[j]
            lin, ang = builder.joint_dof_dim[j]
            n = lin + ang
            effort = spec.mode == "effort"
            is_ball = builder.joint_type[j] == newton.JointType.BALL
            for k in range(n):
                dof = qd_start + k
                if effort:
                    builder.joint_target_ke[dof] = 0.0
                    builder.joint_target_kd[dof] = 0.0
                    builder.joint_target_mode[dof] = int(newton.JointTargetMode.EFFORT)
                    passive_damping[dof] = spec.kd
                else:
                    builder.joint_target_ke[dof] = spec.kp
                    builder.joint_target_kd[dof] = spec.kd
                    builder.joint_target_mode[dof] = int(newton.JointTargetMode.POSITION_VELOCITY)
                builder.joint_armature[dof] = spec.armature
                builder.joint_effort_limit[dof] = spec.effort_limit
                if spec.velocity_limit is not None:
                    builder.joint_velocity_limit[dof] = spec.velocity_limit
                if spec.friction is not None:
                    builder.joint_friction[dof] = spec.friction
                builder.joint_target_pos[dof] = spec.default_pos
            if not is_ball:
                for k in range(n):
                    builder.joint_q[q_start + k] = spec.default_pos
        if cfg.gravity_compensation:
            actgravcomp = builder.custom_attributes["mujoco:jnt_actgravcomp"].values
            for dof in range(builder.joint_dof_count):
                actgravcomp[dof] = True
            body_gravcomp = builder.custom_attributes["mujoco:gravcomp"].values
            for b in range(len(builder.body_label)):
                body_gravcomp[b] = 1.0

    def _capture_geometry(self, builder: newton.ModelBuilder, body_start: dict[str, tuple[int, int]]):
        shapes_by_body: dict[int, list[int]] = {}
        for shape_id, body_id in enumerate(builder.shape_body):
            shapes_by_body.setdefault(int(body_id), []).append(shape_id)
        geometry = {}
        for side, (b0, b1) in body_start.items():
            links = []
            for b in range(b0, b1):
                shape_ids = tuple(shapes_by_body.get(b, ()))
                if not shape_ids:
                    continue
                name = str(builder.body_label[b]).rsplit("/", 1)[-1]
                links.append(HandLinkGeometry(link_name=name, shape_ids=shape_ids, object_contact=True))
            if not links:
                raise ValueError(f"{side} hand has no collision shapes")
            geometry[side] = tuple(links)
        return geometry

    def build(self, builder: newton.ModelBuilder) -> EmbodimentLayout:
        newton.solvers.SolverMuJoCo.register_custom_attributes(builder)
        builder.default_shape_cfg.ke = 1.0e3
        builder.default_shape_cfg.kd = 1.0e2
        builder.default_shape_cfg.margin = 0.0
        builder.default_shape_cfg.gap = 0.0
        semantic: dict[str, int] = {}
        body_span: dict[str, tuple[int, int]] = {}
        for side, path, base in (
            ("left", self.config.left_urdf_path, self.config.left_base_pos),
            ("right", self.config.right_urdf_path, self.config.right_base_pos),
        ):
            b0 = len(builder.body_label)
            semantic.update(self._add_hand(builder, side, path, base))
            body_span[side] = (b0, len(builder.body_label))
        geometry = self._capture_geometry(builder, body_span)
        if self.config.pad_condim is not None or self.config.pad_torsional is not None or self.config.pad_mu is not None:
            condim = builder.custom_attributes["mujoco:condim"].values
            for side_links in geometry.values():
                for link in side_links:
                    for shape in link.shape_ids:
                        if self.config.pad_condim is not None:
                            condim[shape] = int(self.config.pad_condim)
                        if self.config.pad_torsional is not None:
                            builder.shape_material_mu_torsional[shape] = float(self.config.pad_torsional)
                        if self.config.pad_mu is not None:
                            builder.shape_material_mu[shape] = float(self.config.pad_mu)
        shape_count = len(builder.shape_body)
        collapse_result = builder.collapse_fixed_joints()
        if len(builder.shape_body) != shape_count:
            raise ValueError("fixed-joint collapse changed shape IDs required by hand geometry ownership")
        frames = {f.name: f for f in resolve_body_frames(semantic, collapse_result)}
        self._apply_control_config(builder)
        return self._extract_layout(builder, frames, geometry)

    def _extract_layout(self, builder, frames: dict[str, BodyFrame], geometry) -> EmbodimentLayout:
        wrist_pos: dict[str, list[tuple[int, int]]] = {"left": [], "right": []}
        wrist_orient: dict[str, list[int]] = {"left": [], "right": []}
        wrist_orient_q: dict[str, int] = {}
        finger: dict[str, list[tuple[int, int]]] = {"left": [], "right": []}
        finger_names: dict[str, list[str]] = {"left": [], "right": []}
        for j, label in enumerate(builder.joint_label):
            jtype = builder.joint_type[j]
            if jtype == newton.JointType.FIXED:
                continue
            name = str(label).rsplit("/", 1)[-1]
            head = str(label).split("/", 1)[0]
            side = "right" if (head.startswith("right") or name.startswith("right")) else "left"
            qd_start = builder.joint_qd_start[j]
            q_start = builder.joint_q_start[j]
            lin, ang = builder.joint_dof_dim[j]
            if name.endswith(_WRIST_POS):
                wrist_pos[side].append((qd_start, q_start))
            elif jtype == newton.JointType.BALL:
                wrist_orient[side] = [qd_start + k for k in range(lin + ang)]
                wrist_orient_q[side] = q_start
            else:
                if lin + ang != 1:
                    raise ValueError(f"finger joint {label!r} must have one DOF")
                finger[side].append((qd_start, q_start))
                finger_names[side].append(name)
        digits = self.config.digits
        hands = []
        for side in ("left", "right"):
            order = sorted(range(len(finger[side])), key=lambda i: finger[side][i][0])
            hands.append(
                HandLayout(
                    side=side,
                    wrist_pos_dof_ids=tuple(d for d, _ in sorted(wrist_pos[side])),
                    wrist_orient_dof_ids=tuple(wrist_orient[side]),
                    wrist_orient_q_id=wrist_orient_q[side],
                    finger_dof_ids=tuple(finger[side][i][0] for i in order),
                    link_geometry=geometry[side],
                    wrist_pos_q_ids=tuple(q for _, q in sorted(wrist_pos[side])),
                    finger_q_ids=tuple(finger[side][i][1] for i in order),
                    finger_joint_names=tuple(finger_names[side][i] for i in order),
                    palm_frame=frames[f"{side}_palm"],
                    dp_frames=tuple(frames[f"{side}_{d}_DP"] for d in digits),
                    fingertip_frames=tuple(frames[f"{side}_{d}_fingertip"] for d in digits),
                )
            )
        return EmbodimentLayout(num_joint_q=len(builder.joint_q), num_joint_dof=builder.joint_dof_count, hands=tuple(hands))

    def bind_reference(self, builder: newton.ModelBuilder, layout: EmbodimentLayout, reference) -> RobotReferenceBinding:
        if not isinstance(reference, HandPoseReference):
            raise TypeError("FloatingHands requires a HandPoseReference")
        joint_q = np.tile(np.asarray(builder.joint_q, dtype=np.float32), (reference.num_frames, 1))
        joint_target = np.tile(np.asarray(builder.joint_target_pos, dtype=np.float32), (reference.num_frames, 1))
        for hand in layout.hands:
            wrist_pos = np.asarray(reference.wrist_pos_w(hand.side), dtype=np.float32)
            wrist_quat = np.asarray(reference.wrist_quat_w(hand.side), dtype=np.float32)
            fingers = np.asarray(reference.finger_joint_pos(hand.side), dtype=np.float32)[
                :, list(finger_joint_order(hand, reference))
            ]
            joint_q[:, hand.wrist_pos_q_ids] = wrist_pos
            joint_q[:, hand.wrist_orient_q_id : hand.wrist_orient_q_id + 4] = wxyz_to_xyzw(wrist_quat)
            joint_q[:, hand.finger_q_ids] = fingers
            joint_target[:, hand.wrist_pos_dof_ids] = wrist_pos
            joint_target[:, hand.wrist_orient_dof_ids] = wxyz_to_rotvec(wrist_quat)
            joint_target[:, hand.finger_dof_ids] = fingers
        return build_robot_reference_binding(builder, layout, joint_q, joint_target, reference.fps)


assert isinstance(FloatingHands(FloatingHandsConfig(left_urdf_path=Path("l"), right_urdf_path=Path("r"))), Embodiment)
