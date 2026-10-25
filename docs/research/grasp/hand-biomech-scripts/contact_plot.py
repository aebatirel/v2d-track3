"""Plot where the perceived human hand touches an object (contact slots of OUR reference, object frame, PCA axes).
Slots are coloured by digit in mkref's slot order (tools/contact_slots.py). 2026-10-25: earlier versions coloured slot 0
as the palm and slots 1-3 as the thumb (MANO link order); in mkref's order those are the thumb, index, middle and ring
tips (approach3-grasp-taxonomy.md §9).
Usage: contact_plot.py PARQUET LIBRARY_DIR SIDE OBJECT F0 F1 OUT_PNG"""
import os, sys
import numpy as np
import pyarrow.parquet as pq
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'tools'))
from contact_slots import slot_names, digit_slots  # noqa: E402

parquet, lib, side, obj, f0, f1, out = sys.argv[1:8]; f0, f1 = int(f0), int(f1)
t = pq.read_table(parquet); names = t.column('object_body_names')[0].as_py(); k = names.index(obj)
P = np.array(t.column('object_body_position')[0].as_py(), float)[:, k]
Q = np.array(t.column('object_body_wxyz')[0].as_py(), float)[:, k][:, [1, 2, 3, 0]]
pid = np.array(t.column(f'mano_{side}_object_contact_part_ids')[0].as_py())
cpos = np.array(t.column(f'mano_{side}_object_contact_positions')[0].as_py(), float)
m = trimesh.load(f'{lib}/{obj}.glb', force='mesh')
com = m.center_mass if m.is_watertight else m.vertices.mean(0)
_, _, Vt = np.linalg.svd(m.vertices - m.vertices.mean(0), full_matrices=False)
S, _ = trimesh.sample.sample_surface(m, 20000, seed=0); S = (S - com) @ Vt.T
pts, lab = [], []
for f in range(f0, f1 + 1):
    R = Rot.from_quat(Q[f])
    for l in np.where(pid[f] == k + 1)[0]:
        pts.append(Vt @ (R.inv().apply(cpos[f, l] - P[f]) - com)); lab.append(l)
pts = np.array(pts) * 100; lab = np.array(lab); S = S * 100
DIG = digit_slots(slot_names(t))
col = np.where(np.isin(lab, DIG['palm']), 'green', np.where(np.isin(lab, DIG['thumb']), 'red', 'blue'))
fig, ax = plt.subplots(1, 3, figsize=(16, 5.5))
for i, (a, b) in enumerate([(0, 1), (0, 2), (1, 2)]):
    ax[i].scatter(S[:, a], S[:, b], s=0.2, c='0.7')
    if len(pts): ax[i].scatter(pts[:, a], pts[:, b], s=6, c=col, alpha=0.5)
    ax[i].set_aspect('equal'); ax[i].set_xlabel(f'pca{a+1} cm'); ax[i].set_ylabel(f'pca{b+1} cm'); ax[i].grid(lw=0.3)
fig.suptitle(f'{obj} {side} f{f0}-{f1}: palm green, thumb red, fingers blue (perceived contacts, mkref slot labels, our mesh)')
fig.tight_layout(); fig.savefig(out, dpi=65)
print(len(pts), 'contacts')
