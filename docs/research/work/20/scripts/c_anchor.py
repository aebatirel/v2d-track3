"""DIG 20 stage C: end-to-end slot-0 anchor window (inference-safe: video + a frame-0 slot-0 mask only).
Rule MC: c_a = min(M, C + L); M = first object-motion step >= T + kappa * head-flow (mm), C = first frame of a 2-frame
run with intruder touch area >= A px; window (b/c rows) = [0, c_a - n - margin], n = cam-a pairing (Stage A,
sync_table.json; default 1). Mask: PNG (255 = object) in the D18 undistorted pinhole cam-a frame (1014x760, f=500).
usage: c_anchor.py <public|evaluation> <ep> <mask.png> [n_pair=1]
       c_anchor.py selftest <public ep>   (renders the GT frame-0 mask; analysis only)"""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from c_lib import *
from c_detect import features
from c_motion import motion
PAR = dict(A=120, T=2.0, kappa=0.15, L=10, margin=3, max_frames=160)


def anchor_window(F, M0, depth_m, n_pair=1, p=PAR):
    rows, box, _ = features(F, M0)
    r = rows; hit = r[:, 1] >= p['A']; C = None
    for i in range(1, len(hit)):
        if hit[i] and hit[i - 1]: C = int(r[i - 1, 0]); break
    mr, r0 = motion(F, M0)
    st = mr[:, 1:4]; ok = np.isfinite(st).all(1)
    mm = np.where(ok, np.hypot(st[:, 0], st[:, 1]) + np.radians(np.abs(np.nan_to_num(st[:, 2]))) * r0, 0) * depth_m / 500 * 1000
    hf = np.nan_to_num(mr[:, 6], nan=99.0)
    idx = np.nonzero(mm >= p['T'] + p['kappa'] * hf)[0]; M = int(mr[idx[0], 0]) if len(idx) else None
    cands = [x for x in (M, None if C is None else C + p['L']) if x is not None]
    ca = min(cands) if cands else len(F)
    end = ca - n_pair - p['margin']
    return dict(C_a=C, M_a=M, c_a=ca, c_bc=ca - n_pair, window_end_row=end, empty=end < 0,
                frames_processed=len(F), note='empty -> fall back to the static end propagated backward')


if __name__ == '__main__':
    if sys.argv[1] == 'selftest':
        ep = int(sys.argv[2]); g = gt_ref(ep); R, C = cam0(ep)
        M0, z = silhouette(g['name'], g['e']['pose'][0, g['j']], R, C)
        n = json.load(open(f'{ROOT}/work/20/out/sync_table.json'))['episodes'][f'p{ep}']['pairing_a_to_b'][0]['n']
        F = frames('public', ep, 'a', n_max=PAR['max_frames'])
        out = anchor_window(F, M0, z, n)
        print(json.dumps(out), '| GT pert', g['pert'], 'robust', g['pert_r'], 'on', g['on'])
    else:
        split, ep, mpath = sys.argv[1], int(sys.argv[2]), sys.argv[3]; n = float(sys.argv[4]) if len(sys.argv) > 4 else 1
        M0 = (cv2.imread(mpath, cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8) * 255
        F = frames(split, ep, 'a', n_max=PAR['max_frames'])
        depth = float(os.environ.get('DEPTH_M', 0.55))   # object depth for px -> mm (stereo or prior); 0.55 m typical
        print(json.dumps(anchor_window(F, M0, depth, n)))
