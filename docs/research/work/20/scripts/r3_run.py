"""DIG 20 Stage C round 3: frozen MC detector (r_run.decide, parameters NOT retuned) on the round-3 GT-free masks
(out/c3/mask0_<key>.png, depth from out/c3/pose0_<key>.json). usage: r3_run.py <public|evaluation> <ep> ..."""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import c_lib as L
from c_detect import features
from c_motion import motion
from r_run import decide, PAR
O3 = f'{L.ROOT}/work/20/out/c3'
if __name__ == '__main__':
    split = sys.argv[1]
    for ep in map(int, sys.argv[2:]):
        key = f'{"p" if split == "public" else "e"}{ep}'
        M0 = (cv2.imread(f'{O3}/mask0_{key}.png', cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8) * 255
        depth = json.load(open(f'{O3}/pose0_{key}.json'))['depth_m']
        F = L.frames(split, ep, 'a', n_max=PAR['max_frames'])
        fr, box, _ = features(F, M0)
        mr, r0 = motion(F, M0)
        d = decide(fr, mr, r0, depth, key)
        np.savez(f'{O3}/run_{key}.npz', frows=fr, mrows=mr, r0=r0, depth=depth, dec=json.dumps(d))
        print(key, json.dumps(d), f'depth {depth:.2f} r0 {r0:.0f}', flush=True)
