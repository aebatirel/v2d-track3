# Synthetic testbed only: compare independent vs joint solids of the box-model boards with their exact shape
# (thickness 9 mm, 13.9 x 22.7 cm, slot of width W from y = 0 to the +y edge at z = c). Truth is the synthetic model,
# not a scan. Usage: eval_synth.py GRID_A.npz JOINTDIR W_MM
import sys, os, json, numpy as np, trimesh
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact')
import vox2
gridA, jd, W = sys.argv[1], sys.argv[2], float(sys.argv[3]) / 1000
T, H, L = 0.009, 0.139, 0.227
C = {'wooden_piece_1': 0.001, 'wooden_piece_2': 0.0}
res = {}
for name, c in C.items():
    g = np.load(gridA.replace('wooden_piece_1', name)); vx, h = float(g['voxel']), float(g['half'])
    n = int(round(2 * h / vx))
    out = {}
    for tag, f in (('indep', f'{jd}/{name}_indep.npy'), ('joint', f'{jd}/{name}_solid.npy')):
        sol = np.load(f).ravel(); X = (np.stack(np.unravel_index(np.arange(n ** 3), (n,) * 3), 1) + 0.5) * vx - h
        inbox = (np.abs(X[:, 0]) < T / 2) & (np.abs(X[:, 1]) < H / 2) & (np.abs(X[:, 2]) < L / 2)
        slot = (np.abs(X[:, 0]) < T / 2) & (X[:, 1] > 0) & (X[:, 1] < H / 2) & (np.abs(X[:, 2] - c) < W / 2)
        mat = inbox & ~slot
        v3 = vx ** 3 * 1e6
        out[tag] = dict(solid_cm3=round(sol.sum() * v3, 1), slot_vox_solid=round(float(sol[slot].mean()), 2),
                        n_slot_vox=int(slot.sum()), excess_outside_cm3=round(float((sol & ~inbox).sum() * v3), 1),
                        missing_material_cm3=round(float((mat & ~sol).sum() * v3), 1))
        out[tag]['_sol'] = sol; out[tag]['_mat'] = mat; out[tag]['_slot'] = slot
    carved = out['indep']['_sol'] & ~out['joint']['_sol']; v3 = vx ** 3 * 1e6
    out['carved'] = dict(total_cm3=round(float(carved.sum() * v3), 2), in_slot_cm3=round(float((carved & out['indep']['_slot']).sum() * v3), 2),
                         in_true_material_cm3=round(float((carved & out['indep']['_mat']).sum() * v3), 2),
                         outside_board_cm3=round(float((carved & ~out['indep']['_mat'] & ~out['indep']['_slot']).sum() * v3), 2))
    for tag in ('indep', 'joint'):
        for k in ('_sol', '_mat', '_slot'):
            out[tag].pop(k)
    # mesh-level slot free fraction (points strictly inside the slot), full-resolution meshes
    rng = np.random.default_rng(0)
    Ps = np.c_[rng.uniform(-T / 2 * 0.9, T / 2 * 0.9, 3000), rng.uniform(0.005, H / 2 - 0.005, 3000), rng.uniform(c - W / 2 * 0.8, c + W / 2 * 0.8, 3000)]
    for tag, mp in (('indep', str(g['mesh']).replace('.glb', '_full.glb')), ('joint', f'{jd}/{name}_full.glb')):
        if not os.path.isabs(mp):
            mp = os.path.join('/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/joint', mp)
        m = trimesh.load(mp, force='mesh'); m.merge_vertices(); sd = vox2.SD(m, 'winding')
        out[tag]['mesh_slot_free'] = round(float((sd(Ps) >= 0).mean()), 3)
        # thickness along x through the board away from the slot: count inside along x at 20 (y,z) lines
        ys, zs = np.meshgrid(np.linspace(-0.05, 0.05, 5), np.r_[np.linspace(-0.09, -0.03, 2), np.linspace(0.03, 0.09, 2)])
        th = []
        for y_, z_ in zip(ys.ravel(), zs.ravel()):
            xs = np.arange(-0.03, 0.03, 0.0005); Q = np.c_[xs, np.full_like(xs, y_), np.full_like(xs, z_)]
            th.append((sd(Q) < 0).sum() * 0.5)
        out[tag]['thickness_mm_median'] = float(np.median(th))
    res[name] = out
print(json.dumps(res, indent=1))
json.dump(res, open(f'{jd}/eval_synth.json', 'w'), indent=1)
