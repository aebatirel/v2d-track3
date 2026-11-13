"""FlashDexRetarget-style training rewards for FlashCHORD (v2d experiment, 2026-10-22). Installed as
flash_chord/objectives/v2d_fdr.py by ops/box/patch_flashchord_fdr.py and hooked into TrackingObjective only when one of
the variables below is set in the training process; with none set, FlashCHORD is unchanged.

Training reward only. The terms reuse two existing objective slots so the checkpoint's resolved config keeps
FlashCHORD's own term names and loads in the unpatched evaluator (which rebuilds the objective but never acts on it):

FC_FDR_OBJ=1 -> the "object_keypoints" slot holds FDR's point-match reward (arXiv 2610.01849 Sec. III-B,
  tracking_obj_pcd_match_error_exp) instead of FlashCHORD's six unit axis vectors 1 m out:
  points sampled on each object's own mesh, e = mean of the top-k distances between the points at the simulated and
  at the reference pose, value = shaped_objective(e^2, objective.object_keypoints.var, shape) (Laplacian var 0.1 gives
  FDR's exp(-10 e)); the slot is the mean over objects.
  FC_FDR_OBJ_POINTS (128), FC_FDR_OBJ_TOPK (3, at most 4), FC_FDR_OBJ_RADIUS ("true" = the object's own size, the
  default; a number rescales the points to that largest radius, FDR uses 0.058).
  FC_FDR_OBJ_MODE=centroid (2026-11-13, after the Track 3 winner's talk) replaces the point match by six keypoints on
  a FC_FDR_OBJ_LEVER (default 0.1 m) lever arm around each object's surface centroid, along the object-frame axes:
  value = mean over objects and keypoints of shaped_objective(d^2, var, shape), so with LAPLACIAN and
  objective.object_keypoints.var=0.03 each keypoint scores exp(-d / 3 cm). 1 deg of rotation then moves a keypoint
  1.7 mm (FlashCHORD's 1 m vectors: 17 mm), closer to how ADD-AUC weighs rotation. Default mode "topk" = unchanged.
  FC_FDR_OBJ_SIGMA (either mode, optional) replaces objective.object_keypoints.var for this term only, so arms with
  different widths can share a box through ENV_EP<N> (the checkpoint's resolved config still shows the config var;
  the training log line "v2d_fdr: ..." records the value used).
FC_FDR_TIPS=1 -> the "force_closure" slot (enable it: objective.force_closure.enabled=true, weight > 0) holds FDR's
  one-sided fingertip distance bound (tracking_ref_mano_tip_distance_bound_exp): per fingertip
  eps = max(0, d_sim - d_ref), value = mean over both hands' five tips of exp(-eps / FC_FDR_TIP_SIGMA (0.01 m)).
  d_sim: simulated fingertip to the nearest object surface at its simulated pose; d_ref: the reference robot
  fingertip to the nearest object surface at the reference pose. Unsigned distances to each object's visual mesh;
  FDR uses the human (MANO) tips for d_ref, we use our reference robot tips (after contact retargeting they are our
  cleanest hand-object distances). No contact labels are needed.
"""

from __future__ import annotations

import inspect
import os
import sys

import numpy as np
import warp as wp

from flash_chord.objectives.config import OBJECTIVE_TERM_NAMES
from flash_chord.objectives.shaping import shaped_objective

_OBJECT_KEYPOINTS = OBJECTIVE_TERM_NAMES.index("object_keypoints")
_FORCE_CLOSURE = OBJECTIVE_TERM_NAMES.index("force_closure")


def enabled_flags() -> tuple[bool, bool]:
    return os.environ.get("FC_FDR_OBJ", "0") not in ("", "0"), os.environ.get("FC_FDR_TIPS", "0") not in ("", "0")


@wp.kernel
def _zero(values: wp.array(dtype=wp.float32)) -> None:
    values[wp.tid()] = 0.0


@wp.kernel
def object_points_objective(
    body_q: wp.array(dtype=wp.transform),
    object_body_ids: wp.array(dtype=wp.int32),  # [n_obj] per-world object body ids
    target_pos: wp.array(dtype=wp.vec3),  # [W * n_obj] command object positions
    target_quat: wp.array(dtype=wp.quat),  # [W * n_obj] command object quats (xyzw)
    points: wp.array(dtype=wp.vec3),  # [n_obj * n_points] object-frame points
    body_object_ids: wp.array(dtype=wp.int32),  # [n_obj] logical object of each body
    object_scales: wp.array(dtype=wp.float32),  # [W * num_objects]
    n_obj: int,
    num_objects: int,
    n_points: int,
    top_k: int,
    bodies_per_world: int,
    var: float,
    kind: int,
    objective: wp.array(dtype=wp.float32),  # [W] atomic: mean over objects
) -> None:
    """Per (world, object body): FDR point match on the top-k point errors; launch over W*n_obj."""
    tid = wp.tid()
    body = tid % n_obj
    world = tid // n_obj
    xf = body_q[world * bodies_per_world + object_body_ids[body]]
    p_sim = wp.transform_get_translation(xf)
    q_sim = wp.transform_get_rotation(xf)
    p_ref = target_pos[world * n_obj + body]
    q_ref = target_quat[world * n_obj + body]
    scale = object_scales[world * num_objects + body_object_ids[body]]
    m1 = float(0.0)
    m2 = float(0.0)
    m3 = float(0.0)
    m4 = float(0.0)
    for i in range(n_points):
        v = points[body * n_points + i] * scale
        d = wp.length((p_sim + wp.quat_rotate(q_sim, v)) - (p_ref + wp.quat_rotate(q_ref, v)))
        if d > m1:
            m4 = m3
            m3 = m2
            m2 = m1
            m1 = d
        elif d > m2:
            m4 = m3
            m3 = m2
            m2 = d
        elif d > m3:
            m4 = m3
            m3 = d
        elif d > m4:
            m4 = d
    e = m1
    if top_k == 2:
        e = (m1 + m2) / 2.0
    elif top_k == 3:
        e = (m1 + m2 + m3) / 3.0
    elif top_k >= 4:
        e = (m1 + m2 + m3 + m4) / 4.0
    wp.atomic_add(objective, world, shaped_objective(e * e, var, kind, 0.0) / float(n_obj))


_AXES_NP = np.array(
    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]],
    dtype=np.float32,
)


@wp.kernel
def object_centroid_keypoints_objective(
    body_q: wp.array(dtype=wp.transform),
    object_body_ids: wp.array(dtype=wp.int32),  # [n_obj] per-world object body ids
    target_pos: wp.array(dtype=wp.vec3),  # [W * n_obj] command object positions
    target_quat: wp.array(dtype=wp.quat),  # [W * n_obj] command object quats (xyzw)
    centroids: wp.array(dtype=wp.vec3),  # [n_obj] object-frame surface centroids (unscaled)
    axes: wp.array(dtype=wp.vec3),  # [6] unit axis vectors
    lever: float,
    body_object_ids: wp.array(dtype=wp.int32),  # [n_obj] logical object of each body
    object_scales: wp.array(dtype=wp.float32),  # [W * num_objects]
    n_obj: int,
    num_objects: int,
    bodies_per_world: int,
    var: float,
    kind: int,
    objective: wp.array(dtype=wp.float32),  # [W] atomic: mean over objects and keypoints
) -> None:
    """Per (world, object body, keypoint): shaped error of centroid + lever * axis; launch over W*n_obj*6."""
    tid = wp.tid()
    kp = tid % 6
    body = (tid // 6) % n_obj
    world = tid // (6 * n_obj)
    xf = body_q[world * bodies_per_world + object_body_ids[body]]
    scale = object_scales[world * num_objects + body_object_ids[body]]
    v = centroids[body] * scale + axes[kp] * lever
    p_sim = wp.transform_get_translation(xf) + wp.quat_rotate(wp.transform_get_rotation(xf), v)
    p_ref = target_pos[world * n_obj + body] + wp.quat_rotate(target_quat[world * n_obj + body], v)
    d = p_sim - p_ref
    wp.atomic_add(objective, world, shaped_objective(wp.dot(d, d), var, kind, 0.0) / float(6 * n_obj))


def surface_centroid(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Area-weighted centroid of a triangle surface (exact; robust to open meshes)."""
    tri = vertices[faces]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    return (tri.mean(axis=1) * area[:, None]).sum(axis=0) / area.sum()


@wp.func
def _nearest_surface(
    x: wp.vec3,
    p: wp.vec3,
    q: wp.quat,
    scale: float,
    mesh: wp.uint64,
    max_dist: float,
) -> float:
    """Distance from world point x to a mesh posed at (p, q) with isotropic scale; max_dist when nothing is nearer."""
    local = wp.quat_rotate_inv(q, x - p) / scale
    hit = wp.mesh_query_point_no_sign(mesh, local, max_dist / scale)
    if hit.result:
        return wp.length(local - wp.mesh_eval_position(mesh, hit.face, hit.u, hit.v)) * scale
    return max_dist


@wp.kernel
def tip_distance_bound_objective(
    body_q: wp.array(dtype=wp.transform),
    timestep: wp.array(dtype=wp.int32),
    num_frames: int,
    tip_body_ids: wp.array(dtype=wp.int32),  # [n_hands * n_tips] per-world fingertip bodies
    tip_local_pos: wp.array(dtype=wp.vec3),  # [n_hands * n_tips] body-frame fingertip offsets
    ref_tip_pos_w: wp.array(dtype=wp.vec3),  # [T * n_hands * n_tips] reference robot fingertips
    object_body_ids: wp.array(dtype=wp.int32),  # [n_obj]
    target_pos: wp.array(dtype=wp.vec3),  # [W * n_obj]
    target_quat: wp.array(dtype=wp.quat),  # [W * n_obj]
    meshes: wp.array(dtype=wp.uint64),  # [n_obj] object-frame visual meshes
    body_object_ids: wp.array(dtype=wp.int32),
    object_scales: wp.array(dtype=wp.float32),
    n_obj: int,
    num_objects: int,
    n_tip_slots: int,  # n_hands * n_tips
    bodies_per_world: int,
    sigma: float,
    max_dist: float,
    objective: wp.array(dtype=wp.float32),  # [W] atomic: mean over all fingertips
) -> None:
    """Per (world, fingertip): exp(-max(0, d_sim - d_ref) / sigma); launch over W*n_hands*n_tips."""
    tid = wp.tid()
    slot = tid % n_tip_slots
    world = tid // n_tip_slots
    frame = timestep[world]
    if frame < 0:
        frame = 0
    if frame >= num_frames:
        frame = num_frames - 1
    tip_xf = body_q[world * bodies_per_world + tip_body_ids[slot]]
    x_sim = wp.transform_point(tip_xf, tip_local_pos[slot])
    x_ref = ref_tip_pos_w[frame * n_tip_slots + slot]
    d_sim = max_dist
    d_ref = max_dist
    for body in range(n_obj):
        scale = object_scales[world * num_objects + body_object_ids[body]]
        xf = body_q[world * bodies_per_world + object_body_ids[body]]
        d_sim = wp.min(
            d_sim,
            _nearest_surface(x_sim, wp.transform_get_translation(xf), wp.transform_get_rotation(xf), scale, meshes[body], max_dist),
        )
        d_ref = wp.min(
            d_ref,
            _nearest_surface(x_ref, target_pos[world * n_obj + body], target_quat[world * n_obj + body], scale, meshes[body], max_dist),
        )
    eps = wp.max(d_sim - d_ref, 0.0)
    wp.atomic_add(objective, world, wp.exp(-eps / sigma) / float(n_tip_slots))


def _body_mesh(model, body_id: int) -> tuple[np.ndarray, np.ndarray]:
    """One object's surface in its body frame: its visual mesh, else the union of its colliding mesh shapes."""
    import newton

    visible, collide = int(newton.ShapeFlags.VISIBLE), int(newton.ShapeFlags.COLLIDE_SHAPES)
    shape_body = model.shape_body.numpy()
    flags = model.shape_flags.numpy()
    xforms = model.shape_transform.numpy()
    scales = model.shape_scale.numpy()
    shapes = [
        s for s in np.flatnonzero(shape_body == body_id)
        if model.shape_source[s] is not None and hasattr(model.shape_source[s], "vertices")
    ]
    visual = [s for s in shapes if flags[s] & visible and not flags[s] & collide]
    if visual:
        chosen = [max(visual, key=lambda s: len(model.shape_source[s].vertices))]
    else:
        chosen = [s for s in shapes if flags[s] & collide]
    if not chosen:
        raise ValueError(f"v2d_fdr: object body {body_id} has no mesh shape")
    vertices, faces, offset = [], [], 0
    for s in chosen:
        src = model.shape_source[s]
        v = np.asarray(src.vertices, dtype=np.float64) * scales[s]
        f = np.asarray(src.indices, dtype=np.int64).reshape(-1, 3)
        p, q = xforms[s][:3], xforms[s][3:]  # warp transform: p, quat xyzw
        x, y, z, w = q
        rot = np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ]
        )
        vertices.append(v @ rot.T + p)
        faces.append(f + offset)
        offset += len(v)
    return np.concatenate(vertices), np.concatenate(faces)


def _sample_surface(vertices: np.ndarray, faces: np.ndarray, count: int, seed: int) -> np.ndarray:
    """Area-weighted uniform points on a triangle mesh (deterministic)."""
    tri = vertices[faces]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    rng = np.random.default_rng(seed)
    face = rng.choice(len(faces), size=count, p=area / area.sum())
    r1, r2 = np.sqrt(rng.random(count)), rng.random(count)
    t = tri[face]
    return (1 - r1)[:, None] * t[:, 0] + (r1 * (1 - r2))[:, None] * t[:, 1] + (r1 * r2)[:, None] * t[:, 2]


def attach(objective, model, embodiment, robot_reference, reference, command, device=None) -> None:
    """Build the fixed FDR buffers on a freshly built TrackingObjective (only when a flag is set)."""
    use_obj, use_tips = enabled_flags()
    objective.v2d_fdr_obj = use_obj and objective.enabled[_OBJECT_KEYPOINTS]
    objective.v2d_fdr_tips = use_tips and objective.enabled[_FORCE_CLOSURE]
    if use_tips and not objective.enabled[_FORCE_CLOSURE]:
        print("v2d_fdr: FC_FDR_TIPS set but objective.force_closure is disabled: tip term OFF", flush=True)
    if not (objective.v2d_fdr_obj or objective.v2d_fdr_tips):
        return
    wp.load_module(sys.modules[__name__], device=device)  # compile before the environment captures its CUDA graphs
    body_ids = command.body_ids.numpy().astype(int)
    surfaces = [_body_mesh(model, int(b)) for b in body_ids]
    objective.v2d_fdr_num_objects = int(command.object_scales.shape[0] // command.world_count)
    log = []
    objective.v2d_fdr_mode = os.environ.get("FC_FDR_OBJ_MODE", "topk")
    if objective.v2d_fdr_mode not in ("topk", "centroid"):
        raise ValueError(f"FC_FDR_OBJ_MODE must be topk or centroid, got {objective.v2d_fdr_mode}")
    if objective.v2d_fdr_obj and objective.v2d_fdr_mode == "centroid":
        lever = float(os.environ.get("FC_FDR_OBJ_LEVER", "0.1"))
        if not lever > 0.0:
            raise ValueError(f"FC_FDR_OBJ_LEVER must be positive, got {lever}")
        cents = np.stack([surface_centroid(v, f) for v, f in surfaces]).astype(np.float32)
        objective.v2d_fdr_centroids = wp.array(cents, dtype=wp.vec3, device=device)
        objective.v2d_fdr_axes = wp.array(_AXES_NP, dtype=wp.vec3, device=device)
        objective.v2d_fdr_lever = lever
        for body, c in enumerate(cents):
            log.append(f"body {body_ids[body]}: centroid ({c[0]:+.3f}, {c[1]:+.3f}, {c[2]:+.3f}) m, lever {lever} m")
        log.append(f"shape {objective.config.object_keypoints.shape}")
    elif objective.v2d_fdr_obj:
        n_points = int(os.environ.get("FC_FDR_OBJ_POINTS", "128"))
        top_k = int(os.environ.get("FC_FDR_OBJ_TOPK", "3"))
        if not 1 <= top_k <= 4:
            raise ValueError(f"FC_FDR_OBJ_TOPK must be 1-4, got {top_k}")
        radius = os.environ.get("FC_FDR_OBJ_RADIUS", "true")
        points = []
        for body, (v, f) in enumerate(surfaces):
            p = _sample_surface(v, f, n_points, seed=body)
            if radius != "true":
                p = p * (float(radius) / np.linalg.norm(p, axis=1).max())
            points.append(p)
            log.append(f"body {body_ids[body]}: {n_points} points, max radius {np.linalg.norm(p, axis=1).max():.3f} m")
        objective.v2d_fdr_points = wp.array(np.concatenate(points).astype(np.float32), dtype=wp.vec3, device=device)
        objective.v2d_fdr_n_points, objective.v2d_fdr_top_k = n_points, top_k
    if objective.v2d_fdr_tips:
        sides = objective.config.sides
        tip_frames = [frame for side in sides for frame in embodiment.hand(side).fingertip_frames]
        ref_tips = np.stack([robot_reference.hand(side).fingertip_pos_w for side in sides], axis=1)  # (T, H, 5, 3)
        objective.v2d_fdr_tip_slots = len(tip_frames)
        if ref_tips.shape[1] * ref_tips.shape[2] != len(tip_frames):
            raise ValueError(f"v2d_fdr: reference tips {ref_tips.shape} do not match {len(tip_frames)} fingertip frames")
        objective.v2d_fdr_tip_body_ids = wp.array([f.body_id for f in tip_frames], dtype=wp.int32, device=device)
        objective.v2d_fdr_tip_local = wp.array(
            np.asarray([f.body_to_frame_pos for f in tip_frames], dtype=np.float32), dtype=wp.vec3, device=device
        )
        objective.v2d_fdr_ref_tips = wp.array(ref_tips.reshape(-1, 3).astype(np.float32), dtype=wp.vec3, device=device)
        objective.v2d_fdr_mesh_objects = [
            wp.Mesh(
                points=wp.array(v.astype(np.float32), dtype=wp.vec3, device=device),
                indices=wp.array(f.reshape(-1).astype(np.int32), dtype=wp.int32, device=device),
            )
            for v, f in surfaces
        ]
        objective.v2d_fdr_meshes = wp.array([m.id for m in objective.v2d_fdr_mesh_objects], dtype=wp.uint64, device=device)
        objective.v2d_fdr_sigma = float(os.environ.get("FC_FDR_TIP_SIGMA", "0.01"))
        objective.v2d_fdr_max_dist = float(os.environ.get("FC_FDR_TIP_MAXDIST", "1.0"))
        log.append(f"tips: {len(tip_frames)} fingertip frames, sigma {objective.v2d_fdr_sigma} m")
    sigma_env = os.environ.get("FC_FDR_OBJ_SIGMA", "")
    objective.v2d_fdr_obj_var = float(sigma_env) if sigma_env else float(objective.config.object_keypoints.var)
    if not objective.v2d_fdr_obj_var > 0.0:
        raise ValueError(f"FC_FDR_OBJ_SIGMA must be positive, got {sigma_env}")
    if objective.v2d_fdr_obj:
        log.append(f"object var {objective.v2d_fdr_obj_var} ({'FC_FDR_OBJ_SIGMA' if sigma_env else 'config'})")
    print(f"v2d_fdr: object points {'ON (' + objective.v2d_fdr_mode + ')' if objective.v2d_fdr_obj else 'off'}, tip bound "
          f"{'ON' if objective.v2d_fdr_tips else 'off'}; " + "; ".join(log), flush=True)


def evaluate(objective, state, timestep) -> bool:
    """Overwrite the reused slots after FlashCHORD's own evaluation; True when the score must be recomposed."""
    if not (getattr(objective, "v2d_fdr_obj", False) or getattr(objective, "v2d_fdr_tips", False)):
        return False
    buffers, command = objective.buffers, objective.command
    if objective.v2d_fdr_obj and getattr(objective, "v2d_fdr_mode", "topk") == "centroid":
        wp.launch(_zero, dim=objective.world_count, inputs=[buffers.object_keypoints])
        wp.launch(
            object_centroid_keypoints_objective,
            dim=objective.world_count * objective.num_bodies * 6,
            inputs=[
                state.body_q,
                command.body_ids,
                command.body_target_pos_w,
                command.body_target_quat_w,
                objective.v2d_fdr_centroids,
                objective.v2d_fdr_axes,
                objective.v2d_fdr_lever,
                command.body_object_ids,
                command.object_scales,
                objective.num_bodies,
                objective.v2d_fdr_num_objects,
                objective.bodies_per_world,
                objective.v2d_fdr_obj_var,
                int(objective.config.object_keypoints.shape),
            ],
            outputs=[buffers.object_keypoints],
        )
    elif objective.v2d_fdr_obj:
        wp.launch(_zero, dim=objective.world_count, inputs=[buffers.object_keypoints])
        wp.launch(
            object_points_objective,
            dim=objective.world_count * objective.num_bodies,
            inputs=[
                state.body_q,
                command.body_ids,
                command.body_target_pos_w,
                command.body_target_quat_w,
                objective.v2d_fdr_points,
                command.body_object_ids,
                command.object_scales,
                objective.num_bodies,
                objective.v2d_fdr_num_objects,
                objective.v2d_fdr_n_points,
                objective.v2d_fdr_top_k,
                objective.bodies_per_world,
                objective.v2d_fdr_obj_var,
                int(objective.config.object_keypoints.shape),
            ],
            outputs=[buffers.object_keypoints],
        )
    if objective.v2d_fdr_tips:
        wp.launch(_zero, dim=objective.world_count, inputs=[buffers.force_closure])
        wp.launch(
            tip_distance_bound_objective,
            dim=objective.world_count * objective.v2d_fdr_tip_slots,
            inputs=[
                state.body_q,
                timestep,
                objective.num_frames,
                objective.v2d_fdr_tip_body_ids,
                objective.v2d_fdr_tip_local,
                objective.v2d_fdr_ref_tips,
                command.body_ids,
                command.body_target_pos_w,
                command.body_target_quat_w,
                objective.v2d_fdr_meshes,
                command.body_object_ids,
                command.object_scales,
                objective.num_bodies,
                objective.v2d_fdr_num_objects,
                objective.v2d_fdr_tip_slots,
                objective.bodies_per_world,
                objective.v2d_fdr_sigma,
                objective.v2d_fdr_max_dist,
            ],
            outputs=[buffers.force_closure],
        )
    return True


def install(cls) -> None:
    """Wrap TrackingObjective.build/evaluate (idempotent)."""
    if getattr(cls, "_v2d_fdr_installed", False):
        return
    original_build = cls.build.__func__
    original_evaluate = cls.evaluate
    signature = inspect.signature(original_build)

    def build(klass, *args, **kwargs):
        objective = original_build(klass, *args, **kwargs)
        bound = signature.bind(klass, *args, **kwargs)
        bound.apply_defaults()
        a = bound.arguments
        attach(objective, a["model"], a["embodiment"], a["robot_reference"], a["reference"], a["command"], a["device"])
        return objective

    def evaluate(self, state, timestep, terminated):
        original_evaluate(self, state, timestep, terminated)
        if evaluate_fdr(self, state, timestep):
            self.buffers.compose(terminated, self.action_rate_l2, self.action_l2)

    evaluate_fdr = globals()["evaluate"]
    cls.build = classmethod(build)
    cls.evaluate = evaluate
    cls._v2d_fdr_installed = True
