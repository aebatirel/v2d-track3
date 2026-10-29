"""refcheck/systematics: AUC of our path advanced by a FIXED half frame (ours'(t) = ours(t + 0.5), slerp/linear),
the inference-legal version of the measured +0.48-frame lag (one constant for all episodes, chosen on public data).
Also scores shifts of 0.25 and 1.0 frames, and (SHIFTS=-0.5) the opposite shift as a control: linear interpolation also
averages neighbouring frames, so a gain from smoothing alone would show for -0.5 too. Usage: [SHIFTS=a,b] python -I fixed_shift.py OUT.json"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import systematics as S                                                   # noqa: E402
from sysload import *                                                     # noqa: E402,F401

SHIFTS = tuple(float(x) for x in os.environ.get("SHIFTS", "0.25,0.5,1.0").split(","))
C = canon(); out = {}
for ep, e in sorted(C.items()):
    names, gt = load_gt(ep); H = [S.host_geometry(n, s) for s, n in enumerate(names)]
    fin, _, _ = ref_files(e)
    srcs = {'perc': (load_npz(f"{STORE}/{e['perception_path']}"), PERC_LIB[ep])}
    if fin:
        srcs['ref'] = (load_ref_parquet(fin), REF_LIB[ep])
    out[ep] = {}
    for k, (ours, lib) in srcs.items():
        REG = [S.registration(ep, s, n, our_mesh_path(lib, n)) for s, n in enumerate(names)]
        b7 = {n: S.to7(ours[n]) for n in names}
        row = {'0': S.kit_auc(ep, names, b7, gt, H, REG)[0]}
        for L in SHIFTS:
            row[str(L)] = S.kit_auc(ep, names, {n: S.shift_path(b7[n], L) for n in names}, gt, H, REG)[0]
        out[ep][k] = row
    print(ep, out[ep], flush=True)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
for k in ('perc', 'ref'):
    rows = [v[k] for v in out.values() if k in v]
    print(k, len(rows), {L: round(float(np.mean([r[L] for r in rows])), 4) for L in rows[0]},
          'episodes improved:', {L: sum(r[L] > r['0'] for r in rows) for L in rows[0] if L != '0'}, 'of', len(rows))
