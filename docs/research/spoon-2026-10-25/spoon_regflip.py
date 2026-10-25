"""Does the kit's mesh registration flip our spoon? (2026-10-25, GT-free; hypothesis H1 of
docs/analysis/eval-20261024-low-scores.md §5). Stand-ins for the hidden scan: N plausible spoons drawn from the template
generator within the measured parameter brackets (spoon/frame_mc.py SPEC), built in the generator's construction frame,
where the true alignment to our template (the default build, same frame) is ~identity. Our template is registered to
each with the kit's own `_register_object_body` and the exact seeds the scorer uses for the 10 spoon eval episodes
(1_000_003 * episode + 101 * slot). A registration whose rotation is > 90 deg from identity is a flip (bowl <-> handle
end, or the bowl's concave face turned over).
Usage: python -I spoon_regflip.py KIT_DIR [N] [seed]"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as R

kit = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 30; seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '../../..'))
sys.path.insert(0, os.path.join(REPO, 'spoon')); sys.path.insert(0, kit)
import spoon_template as st  # noqa: E402
import frame_mc as mc  # noqa: E402
from v2dlb import track3_pose as T3  # noqa: E402
from v2dlb.object_mesh import _surface_moments  # noqa: E402

SLOTS = {3: 1, 5: 1, 6: 1, 15: 1, 16: 1, 32: 1, 33: 1, 35: 0, 36: 0, 37: 0}   # spoon slot per eval episode (kit roster)
base = st.build_spoon(st.resolve_params({})); cand = (np.asarray(base['V'], float), np.asarray(base['F'], np.int64))
rng = np.random.default_rng(seed); rows = []
for i in range(N):
    try:
        b = st.build_spoon(st.resolve_params(mc.draw(rng)))
    except Exception as e:
        print(i, 'build failed', e); continue
    ref = (np.asarray(b['V'], float), np.asarray(b['F'], np.int64)); rc, _ = _surface_moments(*ref)
    for ep, slot in SLOTS.items():
        _, Rot_ = T3._register_object_body(cand, ref, rc, 1_000_003 * ep + 101 * slot)
        ang = float(np.degrees(R.from_matrix(np.asarray(Rot_)).magnitude()))
        rows.append(dict(variant=i, ep=ep, angle_deg=round(ang, 1)))
    a_ = [r['angle_deg'] for r in rows if r['variant'] == i]
    print(i, 'angles', a_, flush=True)
ang = np.array([r['angle_deg'] for r in rows]); flips = ang > 90
summary = dict(N_variants=len({r['variant'] for r in rows}), registrations=len(rows), flips=int(flips.sum()),
               flip_share=round(float(flips.mean()), 3), angle_median=round(float(np.median(ang)), 1),
               angle_p95_nonflip=round(float(np.percentile(ang[~flips], 95)), 1) if (~flips).any() else None,
               flips_by_episode={ep: int(sum(r['angle_deg'] > 90 for r in rows if r['ep'] == ep)) for ep in SLOTS},
               flip_angles=sorted({round(r['angle_deg']) for r in rows if r['angle_deg'] > 90}))
print(json.dumps(summary))
json.dump(dict(summary=summary, rows=rows), open(os.path.join(HERE, 'spoon_regflip.json'), 'w'), indent=1)
