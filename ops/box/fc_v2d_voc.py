"""Virtual object controller with the full inertia tensor, for FlashCHORD training (2026-10-23).
Installed as flash_chord/runtime/v2d_voc.py by ops/box/patch_flashchord_voc.py; used only when FC_VOC_INERTIA is set.

Stock flash_chord.runtime.object_control._object_control turns the desired angular acceleration
k_ang * rotvec - d_ang * omega into a torque with ONE scalar, the mean of the inertia diagonal. For a body whose
principal inertias differ a lot, the axis with the small inertia then gets (mean / min) times the intended
acceleration. The wooden spoon (principal inertias 0.46, 25.8, 26.0 e-4 kg m^2, ratio 38) has an effective
damping of 40 * 38 = 1530 1/s about its long axis; with the 10 ms training substep (20 fps x 5) explicit damping
diverges above VOC scale ~0.13, so in the first four curriculum stages (VOC 1.0 to 0.25, ~64M of 250M steps) the
spoon explodes (measured: zero-action replay of eval ep3 from frame 0, spoon off by 1.9 m at frame 3 on CPU and by
1e8 m at frame 30 on GPU; stable with VOC 0). This kernel is the stock one with the torque computed as
R I R^T (k_ang * rotvec - d_ang * omega), I the body-frame inertia about the COM, so every axis gets the
documented acceleration-level gains. Training only: the evaluator runs with VOC 0 and never calls it.
"""
from __future__ import annotations

import warp as wp

from flash_chord.utils.quat import quat_to_rotvec


@wp.kernel
def object_control_full_inertia(
    body_q: wp.array[wp.transform],
    body_qd: wp.array[wp.spatial_vector],
    body_mass: wp.array[wp.float32],
    body_com: wp.array[wp.vec3],
    body_inertia: wp.array[wp.mat33],
    object_root_body_ids: wp.array[wp.int32],
    object_body_offsets: wp.array[wp.int32],
    object_body_ids: wp.array[wp.int32],
    target_pos: wp.array[wp.vec3],
    target_quat: wp.array[wp.quat],  # xyzw
    articulation_dof_ids: wp.array[wp.int32],
    articulation_target_pos: wp.array[wp.float32],
    k_lin: float,
    d_lin: float,
    k_ang: float,
    d_ang: float,
    max_force: float,
    max_torque: float,
    scale: wp.array[wp.float32],
    scale_count: int,
    world_count: int,
    object_count: int,
    articulation_count: int,
    articulations_per_world: int,
    bodies_per_world: int,
    num_joint_dof: int,
    gravity: float,
    mass_normalized_gains: bool,
    body_f: wp.array[wp.spatial_vector],
    joint_target_pos: wp.array[wp.float32],
    joint_target_vel: wp.array[wp.float32],
) -> None:
    i = wp.tid()
    if i < object_count:
        objects_per_world = object_count // world_count
        world = i // objects_per_world
        scale_index = 0
        if scale_count > 1:
            scale_index = world
        scale_value = scale[scale_index]
        object_id = i - world * objects_per_world
        bid = object_root_body_ids[i]
        xf = body_q[bid]
        pos = wp.transform_get_translation(xf)
        quat = wp.transform_get_rotation(xf)
        vel = body_qd[bid]
        lin_vel_com = wp.spatial_top(vel)
        ang_vel = wp.spatial_bottom(vel)
        com_offset_w = wp.quat_rotate(quat, body_com[bid])
        lin_vel = lin_vel_com - wp.cross(ang_vel, com_offset_w)
        mass = float(0.0)  # noqa: UP018
        for body_index in range(object_body_offsets[object_id], object_body_offsets[object_id + 1]):
            object_bid = world * bodies_per_world + object_body_ids[body_index]
            mass += body_mass[object_bid]
        inertia = body_inertia[bid]

        force = k_lin * (target_pos[i] - pos) - d_lin * lin_vel
        q_err = wp.mul(target_quat[i], wp.quat_inverse(quat))
        torque = k_ang * quat_to_rotvec(q_err) - d_ang * ang_vel
        if mass_normalized_gains:
            force = mass * force
            torque = wp.quat_rotate(quat, inertia * wp.quat_rotate_inv(quat, torque))  # v2d: R I R^T alpha
        force = force + wp.vec3(0.0, 0.0, gravity * mass)

        force = wp.vec3(
            wp.clamp(scale_value * force[0], -max_force, max_force),
            wp.clamp(scale_value * force[1], -max_force, max_force),
            wp.clamp(scale_value * force[2], -max_force, max_force),
        )
        torque = wp.vec3(
            wp.clamp(scale_value * torque[0], -max_torque, max_torque),
            wp.clamp(scale_value * torque[1], -max_torque, max_torque),
            wp.clamp(scale_value * torque[2], -max_torque, max_torque),
        )
        body_f[bid] = wp.spatial_vector(force, torque)

    if i < articulation_count:
        world = i // articulations_per_world
        articulation = i - world * articulations_per_world
        dof_id = world * num_joint_dof + articulation_dof_ids[articulation]
        joint_target_pos[dof_id] = articulation_target_pos[i]
        joint_target_vel[dof_id] = 0.0
