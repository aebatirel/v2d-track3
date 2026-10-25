"""Board-board interpenetration along OUR poses (GT-free): approach-1 study, 2026-10-25.

Inputs are inference-legal only: our meshes and our poses (perception tracks cam_T_<obj>, or the reference parquet the
policy tracks). No scan, no mocap.

For every frame t: T_BA = inv(T_B[t]) @ T_A[t]. A's solid samples (pitch PITCH, warp winding number) are mapped into B
and tested against B's signed distance, and vice versa. Reports per frame: overlap volume (mean of both directions),
max penetration depth, centroid and extent of the overlap in A's frame; the relative pose of B in A.
Also: the assembled segment (|t_rel| < ASM_M and still), jitter of the relative pose there (deviation from a 9-frame
median), the insertion direction (B's relative path in A's frame over the PRE frames before the first overlap), and
'claim' counts per solid sample of A (frames inside B) and of B (frames inside A), saved for cross-episode comparison.

Usage: python pair_overlap.py MESH_A MESH_B SRC OUT.npz [--names A B] [--frames a:b:s]
       SRC = poses.npz (cam_T_<name>) or a reference parquet (object_body_position / object_body_wxyz)."""
import argparse, json

import numpy as np
import trimesh
import warp as wp
from scipy.spatial.transform import Rotation as R

wp.config.quiet = True
wp.init()
PITCH, ASM_M, STILL_MM, PRE = 0.0015, 0.02, 2.0, 40


@wp.kernel
def _sd_w(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), maxd: float, out: wp.array(dtype=float)):
    i = wp.tid(); p = pts[i]
    q = wp.mesh_query_point_sign_winding_number(mesh, p, maxd, 2.0, 0.5)
    d = maxd
    if q.result:
        d = wp.length(p - wp.mesh_eval_position(mesh, q.face, q.u, q.v)) * q.sign
    out[i] = d


class SD:
    def __init__(self, m):
        with wp.ScopedDevice('cpu'):
            self.wm = wp.Mesh(points=wp.array(np.asarray(m.vertices, np.float32), dtype=wp.vec3),
                              indices=wp.array(np.asarray(m.faces, np.int32).ravel(), dtype=int), support_winding_number=True)

    def __call__(self, P, maxd=0.1):
        with wp.ScopedDevice('cpu'):
            out = wp.zeros(len(P), dtype=float)
            wp.launch(_sd_w, dim=len(P), inputs=[self.wm.id, wp.array(np.ascontiguousarray(P, np.float32), dtype=wp.vec3), maxd, out])
            return out.numpy()


def solid(m, sd):
    lo = m.bounds[0] - 2 * PITCH; hi = m.bounds[1] + 2 * PITCH
    n = np.ceil((hi - lo) / PITCH).astype(int) + 1
    G = np.stack(np.meshgrid(*[lo[k] + PITCH * np.arange(n[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
    d = sd(G)
    return G[d < 0], -d[d < 0]


def load_mesh(p):
    m = trimesh.load(p, force='mesh')
    return trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)


def load_poses(src, na, nb):
    if src.endswith('.npz'):
        P = np.load(src)
        return P[f'cam_T_{na}'], P[f'cam_T_{nb}']
    import pyarrow.parquet as pq
    row = pq.read_table(src).to_pylist()[0]
    names = list(row['object_body_names']); pos = np.array(row['object_body_position'], float)
    q = np.array(row['object_body_wxyz'], float)
    out = []
    for n in (na, nb):
        k = names.index(n); T = np.tile(np.eye(4), (len(pos), 1, 1))
        T[:, :3, :3] = R.from_quat(q[:, k, [1, 2, 3, 0]]).as_matrix(); T[:, :3, 3] = pos[:, k]
        out.append(T)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mesh_a'); ap.add_argument('mesh_b'); ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--names', nargs=2, default=['wooden_piece_1', 'wooden_piece_2'])
    ap.add_argument('--frames', default='0:100000:1')
    a = ap.parse_args()
    mA, mB = load_mesh(a.mesh_a), load_mesh(a.mesh_b); sA, sB = SD(mA), SD(mB)
    SA, dA = solid(mA, sA); SB, dB = solid(mB, sB); v = PITCH ** 3 * 1e6
    TA, TB = load_poses(a.src, *a.names)
    f0, f1, fs = map(int, a.frames.split(':')); F = list(range(f0, min(f1, len(TA)), fs))
    cntA = np.zeros(len(SA), np.int32); cntB = np.zeros(len(SB), np.int32); rows = []
    rel = []
    for t in F:
        T = np.linalg.inv(TB[t]) @ TA[t]                       # A -> B
        Ti = np.linalg.inv(T)                                  # B -> A
        rel.append(Ti)
        inA = sB(SA @ T[:3, :3].T + T[:3, 3]) < 0                # A samples inside B
        inB = sA(SB @ Ti[:3, :3].T + Ti[:3, 3]) < 0              # B samples inside A
        dpen = sB(SA[inA] @ T[:3, :3].T + T[:3, 3]) if inA.any() else np.zeros(0)
        cntA += inA; cntB += inB
        r = dict(t=t, ovl_cm3=round(float((inA.sum() + inB.sum()) / 2 * v), 3), pen_mm=round(float(-dpen.min() * 1e3), 2) if len(dpen) else 0.0,
                 rel_t_cm=np.round(Ti[:3, 3] * 100, 2).tolist())
        if inA.sum() > 20:
            P = SA[inA]; r['cen_A_cm'] = np.round(P.mean(0) * 100, 2).tolist(); r['ext_A_cm'] = np.round((P.max(0) - P.min(0)) * 100, 2).tolist()
        rows.append(r)
    rel = np.array(rel); tr = rel[:, :3, 3]
    still = np.r_[np.inf, np.linalg.norm(np.diff(tr, axis=0), axis=1) * 1e3] < STILL_MM
    asm = (np.linalg.norm(tr, axis=1) < ASM_M) & still
    idx = np.flatnonzero(asm)
    res = dict(mesh_a=a.mesh_a, mesh_b=a.mesh_b, src=a.src, frames=[F[0], F[-1], fs], solidA_cm3=round(len(SA) * v, 1),
               solidB_cm3=round(len(SB) * v, 1), n_asm=int(asm.sum()))
    if len(idx):
        # jitter of the relative pose inside the assembled segment (deviation from a 9-frame running median)
        med = np.array([np.median(tr[max(0, i - 4):i + 5], 0) for i in range(len(tr))])
        jit = np.linalg.norm(tr - med, axis=1)[idx] * 1e3
        rv = R.from_matrix(rel[:, :3, :3]); rmean = R.from_matrix(rel[idx, :3, :3]).mean()
        rot_dev = (rv[idx] * rmean.inv()).magnitude() * 180 / np.pi
        ov = np.array([rows[i]['ovl_cm3'] for i in idx]); pen = np.array([rows[i]['pen_mm'] for i in idx])
        res.update(asm_frames=[F[idx[0]], F[idx[-1]]], asm_rel_t_mean_cm=np.round(tr[idx].mean(0) * 100, 2).tolist(),
                   asm_rel_t_std_mm=np.round(tr[idx].std(0) * 1e3, 2).tolist(), asm_rel_rotvec_mean_deg=np.round(rmean.as_rotvec() * 180 / np.pi, 2).tolist(),
                   asm_jitter_mm_med_p90=[round(float(np.median(jit)), 2), round(float(np.percentile(jit, 90)), 2)],
                   asm_rot_dev_deg_med_p90=[round(float(np.median(rot_dev)), 2), round(float(np.percentile(rot_dev, 90)), 2)],
                   asm_ovl_cm3_med_min_max=[round(float(np.median(ov)), 2), round(float(ov.min()), 2), round(float(ov.max()), 2)],
                   asm_pen_mm_med=round(float(np.median(pen)), 2))
        # insertion direction: B's relative path in A's frame over PRE frames before the first frame with overlap > 0.5 cm3
        first = next((i for i, r in enumerate(rows) if r['ovl_cm3'] > 0.5), None)
        if first is not None:
            j0 = max(0, first - PRE // fs); d = tr[min(idx[0], len(tr) - 1)] - tr[j0]
            res.update(first_overlap_frame=F[first], approach_vec_A_cm=np.round(d * 100, 2).tolist(),
                       approach_dir_A=np.round(d / (np.linalg.norm(d) + 1e-12), 3).tolist())
    np.savez_compressed(a.out, SA=SA.astype(np.float32), SB=SB.astype(np.float32), cntA=cntA, cntB=cntB, frames=np.array(F),
                        asm=asm, rel=rel.astype(np.float32), ovl=np.array([r['ovl_cm3'] for r in rows]), pen=np.array([r['pen_mm'] for r in rows]))
    res['rows_every_10'] = rows[::10]
    json.dump(res, open(a.out.replace('.npz', '.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'rows_every_10'}))


if __name__ == '__main__':
    main()
