# DIAGNOSTIC (public scans posed by OUR tracks) + GT-free part (our meshes): lowest point of each board relative to our
# own frame-0 depth table plane (recon_mesh.table_plane on our depth), frames where the board lies flat (first 40).
import sys, json, numpy as np, trimesh
S = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
PL = {23: ([-0.073, -0.718, -0.693], 0.531), 24: ([-0.091, -0.719, -0.689], 0.528)}
M = {'scan': lambda n: f'{S}/loc/t3/mesh/{n}/{n}_visual.glb', 'v4': lambda n: f'/home/user/v2d-track3/meshes/library_v4/{n}.glb',
     'obs12': lambda n: f'{S}/interact/obs/out2/{n}/12_fill_g0_f0_bin.glb', 'obs4': lambda n: f'{S}/interact/obs/out2/{n}/4_adj_g2_f0_cont.glb'}
for E in (23, 24):
    n0, c = PL[E]; n0 = np.array(n0); n0 /= np.linalg.norm(n0)
    P = np.load(f'{S}/loc/perc/ep{E}/poses.npz')
    for b in ('wooden_piece_1', 'wooden_piece_2'):
        row = {}
        for k, f in M.items():
            V = np.asarray(trimesh.load(f(b), force='mesh').vertices)
            h = []
            for t in range(0, 40, 4):
                T = P['world_T_cam'][t] @ P[f'cam_T_{b}'][t]
                hh = (V @ T[:3, :3].T + T[:3, 3]) @ n0 + c; h.append((float(hh.min()), float(hh.max())))
            hmin = np.array(h)
            # top height (max)
            row[k] = [round(float(np.median(hmin[:, 0])) * 1000, 1), round(float(np.median(hmin[:, 1])) * 1000, 1)]
        T = P['world_T_cam'][0] @ P[f'cam_T_{b}'][0]
        row['origin_h_mm'] = round(float(T[:3, 3] @ n0 + c) * 1000, 1)
        row['thin_axis_vs_up_deg'] = round(float(np.degrees(np.arccos(abs(T[:3, 0] @ n0)))), 1)
        print(E, b, '[lowest, highest] point above our plane, mm (median f0-40):', json.dumps(row))
