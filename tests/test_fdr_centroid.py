"""CPU test of the centroid object-keypoint reward in ops/box/fc_v2d_fdr.py (FC_FDR_OBJ_MODE=centroid).

Checks the warp kernel against a numpy reference on random poses, the 1-degree lever arithmetic, and the area-weighted
surface centroid. Needs warp-lang 1.14 and FlashCHORD's src on PYTHONPATH (for objectives.config / shaping):
  PYTHONPATH=<video_to_data>/robotic_grounding/flash_chord/src python tests/test_fdr_centroid.py
"""
import importlib.util
import math
import os
import sys

import numpy as np
import warp as wp

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fc_v2d_fdr", os.path.join(HERE, "..", "ops", "box", "fc_v2d_fdr.py"))
fdr = importlib.util.module_from_spec(spec)
sys.modules["fc_v2d_fdr"] = fdr
spec.loader.exec_module(fdr)


def quat_rotate(q, v):  # q = (x, y, z, w)
    x, y, z, w = q
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    return r @ v


def rand_quat(rng):
    q = rng.normal(size=4)
    return q / np.linalg.norm(q)


def reference(sim_p, sim_q, ref_p, ref_q, cents, scales, lever, var, laplacian=True):
    W, n_obj = sim_p.shape[:2]
    out = np.zeros(W)
    for w in range(W):
        for b in range(n_obj):
            for a in fdr._AXES_NP:
                v = cents[b] * scales[w, b] + a * lever
                d = (sim_p[w, b] + quat_rotate(sim_q[w, b], v)) - (ref_p[w, b] + quat_rotate(ref_q[w, b], v))
                m = np.linalg.norm(d) if laplacian else d @ d
                out[w] += math.exp(-m / var) / (6 * n_obj)
    return out


def run_kernel(sim_p, sim_q, ref_p, ref_q, cents, scales, lever, var, kind, extra_bodies=3):
    W, n_obj = sim_p.shape[:2]
    bpw = n_obj + extra_bodies  # robot bodies before the objects, as in a real world
    body_ids = np.arange(extra_bodies, extra_bodies + n_obj, dtype=np.int32)
    body_q = np.zeros((W * bpw, 7), dtype=np.float32)
    body_q[:, 6] = 1.0
    for w in range(W):
        for b in range(n_obj):
            body_q[w * bpw + body_ids[b], :3] = sim_p[w, b]
            body_q[w * bpw + body_ids[b], 3:] = sim_q[w, b]
    out = wp.zeros(W, dtype=wp.float32, device="cpu")
    wp.launch(
        fdr.object_centroid_keypoints_objective,
        dim=W * n_obj * 6,
        inputs=[
            wp.array(body_q, dtype=wp.transform, device="cpu"),
            wp.array(body_ids, dtype=wp.int32, device="cpu"),
            wp.array(ref_p.reshape(-1, 3).astype(np.float32), dtype=wp.vec3, device="cpu"),
            wp.array(ref_q.reshape(-1, 4).astype(np.float32), dtype=wp.quat, device="cpu"),
            wp.array(cents.astype(np.float32), dtype=wp.vec3, device="cpu"),
            wp.array(fdr._AXES_NP, dtype=wp.vec3, device="cpu"),
            float(lever),
            wp.array(np.arange(n_obj, dtype=np.int32), dtype=wp.int32, device="cpu"),
            wp.array(scales.reshape(-1).astype(np.float32), dtype=wp.float32, device="cpu"),
            n_obj, n_obj, bpw, float(var), int(kind),
        ],
        outputs=[out],
        device="cpu",
    )
    return out.numpy()


def main():
    wp.init()
    rng = np.random.default_rng(0)
    W, n_obj = 5, 2
    ref_p = rng.normal(scale=0.3, size=(W, n_obj, 3))
    ref_q = np.stack([[rand_quat(rng) for _ in range(n_obj)] for _ in range(W)])
    sim_p = ref_p + rng.normal(scale=0.02, size=ref_p.shape)
    sim_q = np.stack([[rand_quat(rng) for _ in range(n_obj)] for _ in range(W)])
    sim_q[0] = ref_q[0]  # world 0: orientation exact
    sim_p[1] = ref_p[1]
    sim_q[1] = ref_q[1]  # world 1: exact pose -> value 1
    cents = rng.normal(scale=0.05, size=(n_obj, 3))
    scales = rng.uniform(0.9, 1.1, size=(W, n_obj))
    for kind, lap in ((0, True), (1, False)):
        got = run_kernel(sim_p, sim_q, ref_p, ref_q, cents, scales, 0.1, 0.03, kind)
        want = reference(sim_p, sim_q, ref_p, ref_q, cents, scales, 0.1, 0.03, laplacian=lap)
        assert np.allclose(got, want, atol=2e-5), (kind, got, want)
    assert abs(run_kernel(sim_p, sim_q, ref_p, ref_q, cents, scales, 0.1, 0.03, 0)[1] - 1.0) < 1e-5

    # 1 deg about z through the centroid: the x/y keypoints move 0.1 * 2 sin(0.5 deg) = 1.745 mm, z keypoints 0
    th = math.radians(1.0)
    q1 = np.array([0, 0, math.sin(th / 2), math.cos(th / 2)])
    one_p = np.zeros((1, 1, 3))
    one_q = np.array([[[0, 0, 0, 1.0]]])
    sim1_q = q1.reshape(1, 1, 4)
    got = run_kernel(one_p, sim1_q, one_p, one_q, np.zeros((1, 3)), np.ones((1, 1)), 0.1, 0.03, 0)[0]
    d = 0.1 * 2 * math.sin(th / 2)
    want = (4 * math.exp(-d / 0.03) + 2) / 6
    assert abs(got - want) < 1e-6, (got, want)
    print(f"1 deg -> keypoint shift {d * 1000:.3f} mm, value {got:.5f}")

    # surface centroid: unit cube surface, offset -> centroid at the offset
    v = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], dtype=float) + [2.0, -1.0, 0.5]
    f = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    c = fdr.surface_centroid(v, f)
    assert np.allclose(c, [2.5, -0.5, 1.0]), c
    attach_evaluate_check(rng)
    print("all centroid-reward checks passed")


def attach_evaluate_check(rng):
    """attach() + evaluate() on mocked FlashCHORD objects, both modes, with and without FC_FDR_OBJ_SIGMA."""
    from types import SimpleNamespace as NS

    W, n_obj, extra = 3, 2, 3
    bpw = n_obj + extra
    cube_v = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], dtype=float) * 0.1
    cube_f = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                       [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    fdr._body_mesh = lambda model, body_id: (cube_v + 0.01 * body_id, cube_f)  # no newton model needed
    ref_p = rng.normal(scale=0.3, size=(W, n_obj, 3))
    ref_q = np.stack([[rand_quat(rng) for _ in range(n_obj)] for _ in range(W)])
    sim_p = ref_p + rng.normal(scale=0.02, size=ref_p.shape)
    sim_q = np.stack([[rand_quat(rng) for _ in range(n_obj)] for _ in range(W)])
    body_ids = np.arange(extra, extra + n_obj, dtype=np.int32)
    body_q = np.zeros((W * bpw, 7), dtype=np.float32)
    body_q[:, 6] = 1.0
    for w in range(W):
        for b in range(n_obj):
            body_q[w * bpw + body_ids[b], :3], body_q[w * bpw + body_ids[b], 3:] = sim_p[w, b], sim_q[w, b]
    scales = np.ones((W, n_obj))
    command = NS(
        body_ids=wp.array(body_ids, dtype=wp.int32, device="cpu"),
        object_scales=wp.array(scales.reshape(-1).astype(np.float32), dtype=wp.float32, device="cpu"),
        world_count=W,
        body_target_pos_w=wp.array(ref_p.reshape(-1, 3).astype(np.float32), dtype=wp.vec3, device="cpu"),
        body_target_quat_w=wp.array(ref_q.reshape(-1, 4).astype(np.float32), dtype=wp.quat, device="cpu"),
        body_object_ids=wp.array(np.arange(n_obj, dtype=np.int32), dtype=wp.int32, device="cpu"),
    )
    state = NS(body_q=wp.array(body_q, dtype=wp.transform, device="cpu"))
    timestep = wp.zeros(W, dtype=wp.int32, device="cpu")
    for mode, sigma_env in (("centroid", ""), ("centroid", "0.03"), ("topk", "")):
        enabled = [False] * len(fdr.OBJECTIVE_TERM_NAMES)
        enabled[fdr._OBJECT_KEYPOINTS] = True
        objective = NS(
            enabled=enabled,
            config=NS(object_keypoints=NS(var=0.1 if not sigma_env else 0.5, shape=0)),
            world_count=W, num_bodies=n_obj, bodies_per_world=bpw,
            buffers=NS(object_keypoints=wp.zeros(W, dtype=wp.float32, device="cpu")),
            command=command,
        )
        os.environ.update(FC_FDR_OBJ="1", FC_FDR_OBJ_MODE=mode, FC_FDR_OBJ_SIGMA=sigma_env)
        fdr.attach(objective, None, None, None, None, command, device="cpu")
        assert fdr.evaluate(objective, state, timestep)
        got = objective.buffers.object_keypoints.numpy()
        var = float(sigma_env) if sigma_env else 0.1
        if mode == "centroid":
            cents = np.stack([fdr.surface_centroid(*fdr._body_mesh(None, int(b))) for b in body_ids])
            want = reference(sim_p, sim_q, ref_p, ref_q, cents, scales, 0.1, var)
            assert np.allclose(got, want, atol=2e-5), (mode, sigma_env, got, want)
        else:
            assert np.all((got > 0) & (got <= 1)), got
    for k in ("FC_FDR_OBJ", "FC_FDR_OBJ_MODE", "FC_FDR_OBJ_SIGMA"):
        os.environ.pop(k, None)
    print("attach/evaluate wiring ok (centroid with config var, centroid with FC_FDR_OBJ_SIGMA, topk)")


if __name__ == "__main__":
    main()
