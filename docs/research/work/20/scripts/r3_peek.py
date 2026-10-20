"""DIG 20 Stage C round 3: dump cam-a frame 0 (D18 pinhole) and Lab maps for flat-object clips (design look only)."""
import sys, os, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import c_lib as L
O = f'{L.ROOT}/work/20/out/c3'
tiles = []
for key in sys.argv[1:]:
    split = 'public' if key[0] == 'p' else 'evaluation'; ep = int(key[1:])
    F = L.frames(split, ep, 'a', n_max=1)[0]
    lab = cv2.cvtColor(F, cv2.COLOR_BGR2LAB)
    cv2.imwrite(f'{O}/f0_{key}.jpg', F)
    o = F.copy(); cv2.putText(o, key, (10, 30), 0, 1, (0, 255, 255), 2)
    tiles.append(cv2.resize(o, (507, 380)))
while len(tiles) % 3: tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
cv2.imwrite(f'{O}/f0_sheet.jpg', np.vstack(rows))
