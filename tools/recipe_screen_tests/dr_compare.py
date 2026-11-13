"""Checks of ops/box/patch_flashchord_dr.py from dr_patch_test.py outputs (recipe screen, physics-solver.md section 8).
Usage: dr_compare.py OUT_DIR [pos_mm rot_rad joint_rad]   (OUT_DIR holds stock.npz, dr_off.npz, dr_on.npz, ...; see
run_cpu_tests.sh). Prints one line per check (PASS / FAIL) and the measured numbers; exit 1 if any check fails."""
import json, os, sys

import numpy as np

D = sys.argv[1]
POS, ROT, JNT = (float(x) for x in sys.argv[2:5]) if len(sys.argv) >= 5 else (1.5, 0.015, 0.01)
L = lambda n: dict(np.load(os.path.join(D, n + '.npz'))) if os.path.exists(os.path.join(D, n + '.npz')) else None  # noqa: E731
KEYS = ('r1', 'h20', 'h40', 'r2', 'ex', 'ex5', 'frame1', 'finger1', 'frame2', 'finger2')
fails = []; report = {}


def check(name, ok, **numbers):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  {json.dumps(numbers)}" if numbers else ''))
    report[name] = dict(ok=bool(ok), **numbers)
    if not ok:
        fails.append(name)


def same(a, b, keys=KEYS):
    return all(np.array_equal(a[k], b[k]) for k in keys)


def angle(q1, q2):  # radians between xyzw quaternions (..., 4)
    d = np.abs(np.sum(q1.astype(np.float64) * q2.astype(np.float64), -1)) / (np.linalg.norm(q1, axis=-1) * np.linalg.norm(q2, axis=-1))
    return 2 * np.arccos(np.clip(d, 0, 1))


def split(z, key):
    """object positions (W, O, 3), object quats (W, O, 4), fingers (W, F), the other coordinates (W, rest)."""
    q = z[key].astype(np.float64); oq = z['obj_q'].astype(int); fq = z['finger_q'].astype(int)
    pos = np.stack([q[:, i:i + 3] for i in oq], 1); quat = np.stack([q[:, i + 3:i + 7] for i in oq], 1)
    used = set(fq.tolist()) | {i + k for i in oq for k in range(7)}
    rest = q[:, [c for c in range(q.shape[1]) if c not in used]]
    return pos, quat, q[:, fq], rest


def perturbation(on, base, key, tag):
    """bounds of on[key] - base[key] (same reset frames and openings) and the per-world noise vectors."""
    p1, q1, f1, r1 = split(on, key); p0, q0, f0, r0 = split(base, key)
    dp = (p1 - p0) * 1e3; ang = angle(q1, q0); dfi = f1 - f0
    lo, hi = on['finger_lo'].astype(np.float64), on['finger_hi'].astype(np.float64)
    at_limit = (np.isclose(f1, lo[None], atol=1e-6) | np.isclose(f1, hi[None], atol=1e-6)) & (np.abs(dfi) < JNT - 1e-6)
    check(f'{tag}: object position offset within +-{POS} mm per axis, all nonzero',
          np.abs(dp).max() <= POS + 1e-3 and (np.abs(dp) > 0).all(),
          max_abs_mm=round(float(np.abs(dp).max()), 4), mean_abs_mm=round(float(np.abs(dp).mean()), 4))
    check(f'{tag}: object rotation within sqrt(3)*{ROT} rad, all nonzero', ang.max() <= np.sqrt(3) * ROT + 2e-4 and (ang > 0).all(),
          max_rad=round(float(ang.max()), 5), mean_rad=round(float(ang.mean()), 5))
    check(f'{tag}: finger offsets within +-{JNT} rad (clamped at limits), not all zero',
          np.abs(dfi).max() <= JNT + 1e-6 and (np.abs(dfi) > 0).mean() > 0.5,
          max_abs_rad=round(float(np.abs(dfi).max()), 5), share_nonzero=round(float((np.abs(dfi) > 0).mean()), 3),
          at_joint_limit=int(at_limit.sum()))
    check(f'{tag}: every other coordinate (wrists, other joints) unchanged', np.array_equal(r1, r0), n_coords=int(r1.shape[1]))
    noise = np.concatenate([dp.reshape(len(dp), -1), ang.reshape(len(ang), -1), dfi], 1)
    dist = min(np.abs(noise[i] - noise[j]).max() for i in range(len(noise)) for j in range(i + 1, len(noise)))
    check(f'{tag}: the noise differs between worlds', dist > 0, min_pairwise_maxabs=float(dist))
    return noise


def residual(on, base, key):
    p1, q1, _, _ = split(on, key); p0, q0, _, _ = split(base, key)
    e = np.linalg.norm(p1 - p0, axis=-1) * 1e3; a = angle(q1, q0)
    return dict(pos_median_mm=round(float(np.median(e)), 4), pos_max_mm=round(float(e.max()), 4),
                rot_median_rad=round(float(np.median(a)), 5), rot_max_rad=round(float(a.max()), 5))


stock, off, on = L('stock'), L('dr_off'), L('dr_on')
check('inert: patched, FC_DR_RESET unset == stock (sampled resets, 40 steps incl. the hold, 2nd reset, explicit reset, 5 steps)',
      same(stock, off) and int(off['dr_installed']) == 0)
if L('boxref') is not None and L('box_off') is not None:
    check('inert, box patch set (VOC + FDR + DR, FC_VOC_INERTIA/FC_FDR_* set, FC_DR_RESET unset) == the same without the DR patch',
          same(L('boxref'), L('box_off')))
check('DR on: upstream reset draws unchanged (frames, finger openings, both resets)',
      all(np.array_equal(on[k], stock[k]) for k in ('frame1', 'finger1', 'frame2', 'finger2')) and int(on['dr_installed']) == 1,
      frames=on['frame1'].tolist())
n1 = perturbation(on, stock, 'r1', 'DR on, 1st sampled reset')
n2 = perturbation(on, stock, 'r2', 'DR on, 2nd sampled reset')
check('DR on: a new draw at every reset (2nd reset noise != 1st, per world)', all(np.abs(n1[w] - n2[w]).max() > 0 for w in range(len(n1))))
check('DR on: explicit reset to frame 0 (after two perturbed episodes) == stock and == the reference row (bit-exact)',
      same(on, stock, ('ex',)) and np.array_equal(on['ex'], np.repeat(on['ref_q'][:1], len(on['ex']), 0)))
x1 = L('stock_x1')
if x1 is not None:   # the steps after an explicit reset depend on the pre-reset history in stock FlashCHORD too
    check('control (stock): one extra step of history before the resets changes the 5 steps after the explicit reset',
          np.array_equal(x1['ex'], stock['ex']) and not np.array_equal(x1['ex5'], stock['ex5']),
          max_abs=float(np.abs(x1['ex5'] - stock['ex5']).max()), dr_vs_stock_max_abs=float(np.abs(on['ex5'] - stock['ex5']).max()))
se, de = L('stock_ev'), L('dr_on_ev')
if se is not None and de is not None:
    check("evaluator sequence (sampled reset, explicit reset to frame 0, 5 steps) with DR ON in the process == stock (bit-exact)",
          same(se, de, ('ev', 'ev5')))
be, bre = L('box_on_ev'), L('boxref_ev')
if be is not None and bre is not None:
    check('evaluator sequence, box patch set + DR ON == box patch set without DR (bit-exact)', same(be, bre, ('ev', 'ev5')))
check('DR on: explicit reset clears the mark; 2 perturbed resets counted per world',
      (on['dr_flag_after_explicit'] == 0).all() and (on['dr_count'] == 2).all(), count=on['dr_count'].tolist())
o43 = L('dr_on43'); sp = L('dr_on_sp')
if o43 is not None:
    check('DR seed 43 draws differ from seed 42', not np.array_equal(o43['r1'], on['r1']))
if sp is not None:
    check("FC_DR_RESET '1.5 0.015 0.01' (spaces) == '1.5,0.015,0.01'", same(sp, on))
report['residual_dr_vs_stock'] = {k: residual(on, stock, k) for k in ('r1', 'h20', 'h40')}
print('object offset DR vs stock (same frames): right after the reset / after the 20-step VOC-1 hold / 20 steps later:',
      json.dumps(report['residual_dr_vs_stock']))
sb, sbo, sbn, son, dsr = L('s_bank'), L('sdr_bank_off'), L('sdr_bank_on'), L('sdr_on'), L('dsr_bank_on')
if sb is not None:
    check('with the state-bank patch, FC_DR_RESET unset: == state-bank patch alone (bank share 0.5)', same(sb, sbo)
          and np.array_equal(sb['bank_flag1'], sbo['bank_flag1']), bank_worlds=int((sb['bank_flag1'] > 0).sum()))
    check('with the state-bank patch, no bank, DR on: == DR patch alone', same(son, on))
    check('with the state-bank patch + bank + DR: same frames and bank draws as without DR',
          all(np.array_equal(sbn[k], sb[k]) for k in ('frame1', 'finger1', 'bank_flag1')))
    perturbation(sbn, sb, 'r1', 'bank + DR, 1st reset (banked and reference worlds)')
    check('bank + DR: explicit reset == the same without DR (bit-exact), bank flag cleared',
          same(sbn, sb, ('ex',)) and (sbn['bank_flag_after_explicit'] == 0).all() and (sbn['dr_flag_after_explicit'] == 0).all())
    if dsr is not None:
        check('patch order DR -> states == states -> DR (bank + DR run bit-exact)', same(dsr, sbn))
bo, br = L('box_on'), L('boxref')
if bo is not None and br is not None:
    perturbation(bo, br, 'r1', 'box patch set + DR on')
    check('box patch set + DR on: explicit reset == without DR (bit-exact)', same(bo, br, ('ex',)))
    report['residual_box'] = {k: residual(bo, br, k) for k in ('r1', 'h20', 'h40')}
    print('box patch set (VOC inertia fix on): object offset DR vs no DR after reset / hold / +20 steps:', json.dumps(report['residual_box']))
for z, n in ((stock, 'stock'), (on, 'dr_on'), (bo, 'box_on')):
    if z is not None:
        check(f'{n}: simulation finite', int(z['finite']) == 1)
json.dump(report, open(os.path.join(D, 'dr_compare.json'), 'w'), indent=1)
print(f"{len(report)} entries, {len(fails)} FAIL" + (f": {fails}" if fails else ''))
sys.exit(1 if fails else 0)
