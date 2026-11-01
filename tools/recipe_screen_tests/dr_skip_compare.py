"""Compare dr_skip_test.py outputs (FC_DR_SKIP_IMMEDIATE). Usage: dr_skip_compare.py DIR  (R0 R1 R2 R3 .npz; R0e R4e)
R0 immediate patch only (no DR code)   R1 DR code, DR unset, SKIP=1   R2 DR on   R3 DR on + SKIP=1   R0e / R4e evalseq of R0 / R3."""
import os, sys
import numpy as np
D = sys.argv[1]; L = lambda n: dict(np.load(os.path.join(D, n + '.npz'), allow_pickle=True))  # noqa: E731
r0, r1, r2, r3 = L('R0'), L('R1'), L('R2'), L('R3'); fails = []
def check(name, ok, info=''):
    print(('PASS ' if ok else 'FAIL ') + name + (f'  [{info}]' if info else '')); ok or fails.append(name)
def obj_off(a, b, oq):                                            # per world: max object position offset (mm)
    return np.array([max(np.abs(a[w, q:q + 3] - b[w, q:q + 3]).max() for q in oq) * 1000 for w in range(a.shape[0])])
check('copies: R0 immediate-patched without DR code; R1-R3 with both', r0['immediate_patched'] == 1 and r0['dr_installed'] == 0
      and r1['immediate_patched'] == 1 and r2['dr_installed'] == 1 and r3['dr_installed'] == 1 and r1['dr_installed'] == 0,
      f"R1 dr_installed {r1['dr_installed']} (DR unset: hook imports nothing)")
for i in (1, 2):
    imm = (r0[f'frame{i}'] == 0) & (r0[f'finger{i}'] == 1.0) & (r0[f'ssr{i}'] == r0['voc_decay'])
    check(f'reset {i}: immediate starts occur (some, not all)', 0 < imm.sum() < len(imm), f'{int(imm.sum())} of {len(imm)} worlds')
    same_draws = all(np.array_equal(r0[f'{k}{i}'], x[f'{k}{i}']) for x in (r1, r2, r3) for k in ('frame', 'finger', 'ssr'))
    check(f'reset {i}: upstream draws (frame, finger factor, steps_since_reset) identical in R0-R3', same_draws)
    check(f'reset {i}: DR unset + SKIP=1 is bit-identical to no DR code', np.array_equal(r0[f'r{i}'], r1[f'r{i}']))
    o2, o3 = obj_off(r2[f'r{i}'], r0[f'r{i}'], r0['obj_q']), obj_off(r3[f'r{i}'], r0[f'r{i}'], r0['obj_q'])
    check(f'reset {i}: without SKIP every world is perturbed, immediate ones included', (o2 > 0).all(), f'min offset {o2.min():.3f} mm')
    check(f'reset {i}: with SKIP the immediate worlds are bit-identical to no DR', np.array_equal(r3[f'r{i}'][imm], r0[f'r{i}'][imm]))
    check(f'reset {i}: with SKIP the other worlds are perturbed (<= 1.5 mm)', (o3[~imm] > 0).all() and (o3[~imm] <= 1.5 + 1e-3).all(),
          f'{o3[~imm].min():.3f}-{o3[~imm].max():.3f} mm')
    if i == 1:                                                     # first reset: same noise stream (count 0) for unskipped worlds
        check('reset 1: unskipped worlds get the same noise with and without SKIP', np.array_equal(r3['r1'][~imm], r2['r1'][~imm]))
imm1 = (r0['frame1'] == 0) & (r0['finger1'] == 1.0) & (r0['ssr1'] == r0['voc_decay'])
imm2 = (r0['frame2'] == 0) & (r0['finger2'] == 1.0) & (r0['ssr2'] == r0['voc_decay'])
check('skip counter = immediate starts per world over both resets', np.array_equal(r3['skips'], imm1.astype(int) + imm2.astype(int)), f"{r3['skips'].sum()} skipped")
check('perturbation counter = the other starts; no skips without the flag', np.array_equal(r3['count'], 2 - r3['skips'])
      and r2['skips'].sum() == 0 and np.array_equal(r2['count'], np.full_like(r2['count'], 2)))
e0, e4 = L('R0e'), L('R4e')
check("evaluator's sequence with DR + SKIP in the process: bit-identical to no DR code", np.array_equal(e0['ev'], e4['ev']) and np.array_equal(e0['ev5'], e4['ev5']))
print(f'{len(fails)} FAIL' if fails else 'ALL PASS'); sys.exit(1 if fails else 0)
