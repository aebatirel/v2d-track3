import sys, json, numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, '.')
import refpose
L = '/home/user/v2d-track3/meshes/library_v3/'
names = ['wooden_piece_1', 'wooden_piece_2']
sets = {'library_v3': [trimesh.load(L + n + '.glb', force='mesh') for n in names],
        'B1_box': [trimesh.load(f'out/boards/{n}_box_body.glb', force='mesh') for n in names],
        'B1_boxslot': [trimesh.load(f'out/boards/{n}_boxslot_body.glb', force='mesh') for n in names]}
res = {}
for key in ['ep24', 'ev25']:
    nm, pos, q = refpose.load(key)
    assert nm == names
    for lab, ms in sets.items():
        out = []
        for f in [len(pos) - 1, len(pos) - 20, len(pos) - 40]:
            W = []
            for i in range(2):
                m = ms[i].copy(); T = np.eye(4); T[:3, :3] = refpose.R_of(q[f, i]); T[:3, 3] = pos[f, i]; m.apply_transform(T); W.append(m)
            try:
                inter = W[0].intersection(W[1], engine='manifold'); v = float(inter.volume) * 1e6 if len(inter.faces) else 0.0
            except Exception as e:
                v = float('nan')
            out.append(round(v, 2))
        res[f'{key}/{lab}'] = out
print(json.dumps(res, indent=0))
json.dump(res, open('out/boards/overlap.json', 'w'))
# picture of slotted boards in their own frames
fig, axs = plt.subplots(1, 2, figsize=(10, 4))
for j, n in enumerate(names):
    m = trimesh.load(f'out/boards/{n}_boxslot_body.glb', force='mesh')
    P = m.sample(30000); c = P.mean(0); ev, V = np.linalg.eigh(np.cov((P - c).T))
    X = (P - c) @ V
    axs[j].scatter(X[:, 2] * 100, X[:, 1] * 100, s=0.2); axs[j].set_aspect('equal'); axs[j].set_title(n + ' B1 box-with-slot (plan view)')
plt.tight_layout(); plt.savefig('out/boards/boxslot_plan.png', dpi=70)
