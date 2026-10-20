"""DIG 20 Stage C re-run: run the frozen Stage C detector (c_detect.features + c_motion.motion, rule MC with A=120,
T=2 mm, kappa=0.15, L=10, margin=3; parameters NOT retuned) on a GT-FREE frame-0 mask (out/c2/mask0_<key>.png from
r_pose0.py) with the stereo object depth (pose0 json) for px -> mm. Inference reads video + mask + depth only.
usage: r_run.py <public|evaluation> <ep> [ep ...] -> out/c2/run_<key>.npz (feature rows, motion rows, decision json)"""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import c_lib as L
from c_detect import features
from c_motion import motion
from r_mask import pairing0, SYNC
OUT2 = f'{L.ROOT}/work/20/out/c2'
PAR = dict(A=120, T=2.0, kappa=0.15, L=10, margin=3, max_frames=160)


def pairing_at(key, row):
    if key not in SYNC: return 1
    for s in SYNC[key]['pairing_a_to_b']:
        if s['rows'][0] <= row <= s['rows'][1]: return s['n']
    return 1


def decide(frows, mrows, r0, depth, key, p=PAR):
    hit = frows[:, 1] >= p['A']; C = None
    for i in range(1, len(hit)):
        if hit[i] and hit[i - 1]: C = int(frows[i - 1, 0]); break
    st = mrows[:, 1:4]; ok = np.isfinite(st).all(1)
    mm = np.where(ok, np.hypot(st[:, 0], st[:, 1]) + np.radians(np.abs(np.nan_to_num(st[:, 2]))) * r0, 0) * depth / 500 * 1000
    hf = np.nan_to_num(mrows[:, 6], nan=99.0)
    idx = np.nonzero(mm >= p['T'] + p['kappa'] * hf)[0]; M = int(mrows[idx[0], 0]) if len(idx) else None
    cands = [x for x in (M, None if C is None else C + p['L']) if x is not None]
    ca = min(cands) if cands else 10 ** 4
    n = pairing_at(key, ca); cbc = ca - n; end = cbc - p['margin']
    return dict(C_a=C, M_a=M, c_a=ca, n=n, c_bc=cbc, window_end_row=end, empty=bool(end < 0))


if __name__ == '__main__':
    split = sys.argv[1]
    for ep in map(int, sys.argv[2:]):
        key = f'{"p" if split == "public" else "e"}{ep}'
        mp = f'{OUT2}/mask0_{key}.png'
        if not os.path.exists(mp): print(key, 'no mask'); continue
        M0 = (cv2.imread(mp, cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8) * 255
        if M0.sum() == 0: print(key, 'empty mask'); continue
        depth = json.load(open(f'{OUT2}/pose0_{key}.json'))['depth_m']
        F = L.frames(split, ep, 'a', n_max=PAR['max_frames'])
        fr, box, _ = features(F, M0)
        mr, r0 = motion(F, M0)
        d = decide(fr, mr, r0, depth, key)
        np.savez(f'{OUT2}/run_{key}.npz', frows=fr, mrows=mr, r0=r0, depth=depth, dec=json.dumps(d))
        print(key, json.dumps(d), f'depth {depth:.2f} r0 {r0:.0f}', flush=True)
