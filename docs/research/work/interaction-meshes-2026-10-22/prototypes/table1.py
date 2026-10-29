"""Table support check: height of each object's lowest point above OUR table plane at rest frames.
Plane: recon_mesh.table_plane (RANSAC on our FoundationStereo depth) at frame 0 (world = rectified-left camera 0) and,
independently, at the last frame (moved to world by our VO) -- only for episodes whose depth cache is local.
Poses: our tracks (loc/perc/ep<N>/poses.npz). Meshes: ours (v2, v3/v4 where relevant); 'scan' rows are DIAGNOSTIC.
Also: reference parquets (loc/val/tree<N>, mkref table frame, table top z = 0.60): lowest points of the reference
meshes at frame 0 / last frame.
Writes census/table_support.json and .csv."""
import os, sys, json, csv
sys.dont_write_bytecode = True
import numpy as np, trimesh
from scipy.ndimage import median_filter
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import recon_mesh as rm

S = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
OUT = f'{S}/interact/census'
LIB = '/home/user/v2d-track3/meshes'
K = rm.rectified_K(f'{S}/loc/t3/calib.json')


def scan_path(n):
    p = f'{S}/loc/t3/mesh/{n}/{n}_visual.glb'
    return p if os.path.exists(p) else f'{S}/loc/t3/mesh/{n}/{n}.glb'


def verts(n, var):
    p = scan_path(n) if var == 'scan' else f'{LIB}/library_{var}/{n}.glb'
    return np.asarray(trimesh.load(p, force='mesh').vertices, np.float64)


def segs(mask):
    out, t = [], 0
    while t < len(mask):
        if mask[t]:
            s = t
            while t < len(mask) and mask[t]:
                t += 1
            out.append((s, t - 1))
        else:
            t += 1
    return out


rows, res = [], {}
for ep in (2, 18, 27):
    names = json.load(open(f'{S}/loc/perc/ep{ep}/result.json'))['objects']
    P = np.load(f'{S}/loc/perc/ep{ep}/poses.npz'); W = P['world_T_cam'].astype(np.float64)
    D = np.load(f'{S}/loc/depth/ep{ep}/depths_fs0.5.npy', mmap_mode='r'); T = min(len(W), len(D))
    Wo = {n: W[:T] @ P[f'cam_T_{n}'][:T].astype(np.float64) for n in names}
    o0 = Wo[names[0]][0][:3, 3]
    n0, c0, f0 = rm.table_plane(np.asarray(D[0]), K, o0)
    # last frame, own fit in camera T-1, moved to world
    oc = (np.linalg.inv(W[T - 1]) @ Wo[names[0]][T - 1])[:3, 3]
    n1c, c1c, f1 = rm.table_plane(np.asarray(D[T - 1]), K, oc)
    R, t = W[T - 1][:3, :3], W[T - 1][:3, 3]; n1 = R @ n1c; c1 = c1c - n1 @ t
    tilt = float(np.degrees(np.arccos(np.clip(n0 @ n1, -1, 1))))
    res[ep] = dict(names=names, plane0=dict(n=n0.tolist(), c=float(c0), inlier_frac=f0),
                   planeT=dict(n=n1.tolist(), c=float(c1), inlier_frac=f1, tilt_vs_plane0_deg=tilt), objects={})
    for n in names:
        p = Wo[n][:, :3, 3]
        mov = median_filter(np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)], 5) > 0.004
        rest = segs(~mov)
        first, last = rest[0], rest[-1]
        for var in ['v2'] + (['v3'] if n == 'mini_sweeper' else []) + ['scan']:
            V = verts(n, var)
            h0 = np.array([(V @ Wo[n][k][:3, :3].T + Wo[n][k][:3, 3]) @ n0 + c0 for k in range(T)]).min(1)   # plane0
            h1 = np.array([(V @ Wo[n][k][:3, :3].T + Wo[n][k][:3, 3]) @ n1 + c1 for k in range(T)]).min(1)   # planeT
            r = dict(ep=ep, obj=n, mesh=var, first_rest=f'{first[0]}-{first[1]}', last_rest=f'{last[0]}-{last[1]}',
                     h_f0_cm=round(h0[0] * 100, 2), h_first_rest_med_cm=round(float(np.median(h0[first[0]:first[1] + 1])) * 100, 2),
                     h_last_rest_med_plane0_cm=round(float(np.median(h0[last[0]:last[1] + 1])) * 100, 2),
                     h_last_rest_med_planeT_cm=round(float(np.median(h1[last[0]:last[1] + 1])) * 100, 2),
                     h_min_all_frames_plane0_cm=round(float(h0.min()) * 100, 2), rest_frames=int((~mov).sum()))
            rows.append(r); res[ep]['objects'].setdefault(n, {})[var] = r
            print(r, flush=True)
    print(f'ep{ep} plane0 inl {f0:.2f}, planeT inl {f1:.2f}, tilt {tilt:.2f} deg, '
          f'planeT offset at obj0 f0: {(n1 @ o0 + c1) - (n0 @ o0 + c0):.4f} m', flush=True)

# references (mkref table frame, z up, table top at 0.60)
import pyarrow.parquet as pq
ref = {}
for ep in (12, 18, 24, 27):
    t = pq.read_table(f'{S}/loc/val/tree{ep}/processed/sequence_id=t3_ep0{ep:02d}/robot_name=sharpa_wave/ref.parquet',
                      columns=['object_body_names', 'object_mesh_paths', 'object_body_position', 'object_body_wxyz'])
    names = t.column('object_body_names')[0].as_py(); paths = t.column('object_mesh_paths')[0].as_py()
    pos = np.array(t.column('object_body_position')[0].as_py(), float); q = np.array(t.column('object_body_wxyz')[0].as_py(), float)
    ref[ep] = {}
    for j, n in enumerate(names):
        V = np.asarray(trimesh.load(paths[j], force='mesh').vertices)
        h = np.array([(Rot.from_quat(q[k, j][[1, 2, 3, 0]]).apply(V) + pos[k, j])[:, 2].min() - 0.60 for k in range(len(pos))])
        ref[ep][n] = dict(mesh=paths[j].split('scratchpad/')[-1], h_f0_cm=round(h[0] * 100, 2), h_last_cm=round(h[-1] * 100, 2),
                          h_min_cm=round(h.min() * 100, 2), h_p10_cm=round(float(np.percentile(h, 10)) * 100, 2))
        print('ref', ep, n, ref[ep][n], flush=True)
json.dump(dict(own_depth_plane=res, references=ref), open(f'{OUT}/table_support.json', 'w'), indent=1, default=float)
with open(f'{OUT}/table_support.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
