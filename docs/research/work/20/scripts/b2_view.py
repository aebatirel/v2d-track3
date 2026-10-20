# Stage B (re-run): contact sheet of cam-a frames a[k+1] around the held spoon, with detected marker uv from held_e<ep>.jsonl.
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts'); from b_lib import *
ep = int(sys.argv[1]); KS = [int(x) for x in sys.argv[2].split(',')]; out = sys.argv[3]
H = {json.loads(l)['k']: json.loads(l) for l in open(f'{OUT}/held_e{ep}.jsonl')}
fa = read_frames('evaluation', ep, 'a', [k + 1 for k in KS]); tiles = []
for k in KS:
    A = fa[k + 1].copy(); h = H.get(k, {})
    if 'uv' in h:
        u = np.array(h['uv']); c = u.mean(0)
        for i, p in enumerate(u): cv2.circle(A, (int(p[0]), int(p[1])), 18, [(0, 0, 255), (0, 255, 0), (255, 0, 0)][i], 2)
    else: c = np.array([A.shape[1] / 2, A.shape[0] / 2])
    x0 = int(np.clip(c[0] - 450, 0, A.shape[1] - 900)); y0 = int(np.clip(c[1] - 300, 0, A.shape[0] - 600))
    t = A[y0:y0 + 600, x0:x0 + 900].copy(); cv2.putText(t, f'e{ep} k{k} a{k+1}', (10, 30), 0, 1, (255, 255, 255), 2); tiles.append(t)
rows = [np.hstack(tiles[i:i + 2] + [np.zeros_like(tiles[0])] * (2 - len(tiles[i:i + 2]))) for i in range(0, len(tiles), 2)]
cv2.imwrite(out, cv2.resize(np.vstack(rows), None, fx=0.6, fy=0.6), [cv2.IMWRITE_JPEG_QUALITY, 85]); print(fa[KS[0] + 1].shape)
