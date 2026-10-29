"""Where does the human hold the plate? Contact points of our reference's contact slots in the object's PCA frame
(axis1 = long axis, handle ring at negative axis1 for both plates; axis3 = plate normal), per slot (mkref's probe
order, tools/contact_slots.py), plus the side of the plate (axis3 sign of the contact relative to the local mid-surface)
to tell a clamp across the thickness (thumb and fingers on opposite faces) from a one-sided contact. Our reference and
our mesh only. 2026-10-25: earlier versions labelled the slots with the mano_link_names column (MANO link order), which
does not describe mkref's slots (approach3-grasp-taxonomy.md §9)."""
import os, sys, json
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as R
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools'))
from contact_slots import slot_names, short  # noqa: E402
t = pq.read_table(sys.argv[1]); side, obj, f0, f1 = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
names = t.column('object_body_names')[0].as_py(); j = names.index(obj); ln = [short(n) for n in slot_names(t)]
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)[:, j]
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[:, j][:, [1, 2, 3, 0]]
m = trimesh.load(f'{REPO}/meshes/library_v3/{obj}.glb', force='mesh'); V = m.vertices; c = V.mean(0)
W = np.linalg.svd(V - c, full_matrices=False)[2]
# orient axis1 so the handle ring (narrower end) is negative: compare widths at both ends
P = (V - c) @ W.T
lo = P[P[:, 0] < np.percentile(P[:, 0], 15)]; hi = P[P[:, 0] > np.percentile(P[:, 0], 85)]
if np.ptp(lo[:, 1]) > np.ptp(hi[:, 1]):
    W[0] *= -1; W[1] *= -1
pq_ = trimesh.proximity.ProximityQuery(m)
n = np.array(t.column(f'mano_{side}_object_contact_normals')[0].as_py(), float).reshape(T, -1, 3)
pid = np.array(t.column(f'mano_{side}_object_contact_part_ids')[0].as_py()).reshape(T, -1)
Pc = np.array(t.column(f'mano_{side}_object_contact_positions')[0].as_py(), float).reshape(T, -1, 3)
out = {}
rows = []
for f in range(f0, f1):
    for k, l in enumerate(ln):
        if np.linalg.norm(n[f, k]) > 1e-3 and pid[f, k] == j + 1:
            X = R.from_quat(OQ[f]).inv().apply(Pc[f, k] - OP[f]); cp, _, tri = pq_.on_surface([X]); nrm = m.face_normals[tri[0]]
            rows.append((f, l, *((X - c) @ W.T), float(nrm @ W[2])))
import collections
G = collections.defaultdict(list)
for r in rows:
    G[r[1]].append(r)
print(f'{side} hand on {obj}, frames {f0}-{f1} ({f1 - f0}): per contact slot: share of frames, mean PCA position (cm) [axis1 long, axis2 width, axis3 normal], '
      'share on the +axis3 face / -axis3 face / edge (|n.axis3|<0.5) of the mesh')
for g in ln:
    r = G.get(g, [])
    if not r:
        continue
    a = np.array([x[2:] for x in r]); fn = a[:, 3]
    print(f'  {g:10s} share {len(r) / (f1 - f0):.2f}  pos ({100 * a[:, 0].mean():5.1f}, {100 * a[:, 1].mean():5.1f}, {100 * a[:, 2].mean():5.1f}) sd ({100 * a[:, 0].std():4.1f}, {100 * a[:, 1].std():4.1f})  '
          f'+face {np.mean(fn > 0.5):.2f} -face {np.mean(fn < -0.5):.2f} edge {np.mean(np.abs(fn) <= 0.5):.2f}')
# ring/handle region: axis1 < handle limit
a = np.array([x[2] for x in rows]); print(f'  contacts with axis1 < -5 cm (handle ring region): {np.mean(a < -0.05):.2f}; mesh axis1 range {100 * P[:, 0].min():.1f}..{100 * P[:, 0].max():.1f} cm (sign-fixed: {"flipped" if W[0] @ np.linalg.svd(V - c, full_matrices=False)[2][0] < 0 else "as PCA"})')
# per-frame opposition across the plate thickness: thumb on one face, a finger (index..pinky) on the other face
fr = collections.defaultdict(lambda: {'th': set(), 'fi': set(), 'palm': False})
for r in rows:
    f, g, nz = r[0], r[1], r[5]
    face = 1 if nz > 0.5 else (-1 if nz < -0.5 else 0)
    if g == 'palm':
        fr[f]['palm'] = True
    elif g.startswith('thumb'):
        fr[f]['th'].add(face)
    else:
        fr[f]['fi'].add(face)
nfr = f1 - f0
opp = sum(1 for v in fr.values() if (1 in v['th'] and -1 in v['fi']) or (-1 in v['th'] and 1 in v['fi']))
th = sum(1 for v in fr.values() if v['th']); fi = sum(1 for v in fr.values() if v['fi'])
print(f'  frames with thumb contact {th / nfr:.2f}, finger contact {fi / nfr:.2f}, palm {sum(v["palm"] for v in fr.values()) / nfr:.2f}, '
      f'thumb-vs-finger opposition across the faces {opp / nfr:.2f}')
