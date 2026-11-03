"""Overlay for PREREG_spoonflip spans: rectified frame, spoon mask (tint), reference outline (green) and the 180-degree
alternative outline (red). Usage: python -I spoon_overlay.py EP VIDEO CALIB REF TABLE POSES VOS KSRC MESH_DIR ALT OUT FRAMES"""
import sys, os, numpy as np, cv2, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'pipeline'))
from identity_fix import rectified_frames
EP, VID, CAL, REF, TAB, POS, VOS, KSRC, MD, ALT, OUT = sys.argv[1:12]; FR = [int(x) for x in sys.argv[12].split(',')]
imgs, _ = rectified_frames(VID, CAL, FR)
t = pq.read_table(REF).to_pandas(); on = t['object_name'].iloc[0]; names = on.split('__') if isinstance(on, str) else list(on); b = names.index('wooden_spoon')
pos = np.array([[np.asarray(list(v), float) for v in fr] for fr in t['object_body_position'].iloc[0]])[:, b]
qq = np.array([[np.asarray(list(v), float) for v in fr] for fr in t['object_body_wxyz'].iloc[0]])[:, b]
iT = np.linalg.inv(np.load(TAB)['T_table_from_world']); W = np.load(POS)['world_T_cam']; K = np.load(KSRC)['K'].astype(float)
m = trimesh.load(f'{MD}/wooden_spoon.glb', force='mesh'); c = m.bounds.mean(0); w, U = np.linalg.eigh(np.cov(np.asarray(m.vertices).T))
ax = U[:, 2] if ALT == 'ROLL' else U[:, 0]; R = Rot.from_rotvec(np.pi * ax).as_matrix(); F = np.eye(4); F[:3, :3] = R; F[:3, 3] = c - R @ c
mk = np.unpackbits(np.load(VOS)['wooden_spoon'], axis=-1)[:, :, :400]
tiles = []
for f in FR:
    im = cv2.cvtColor(imgs[f].astype(np.uint8), cv2.COLOR_GRAY2BGR); H, Wd = im.shape[:2]
    mm = cv2.resize(mk[f].astype(np.uint8), (Wd, H), interpolation=cv2.INTER_NEAREST) > 0; im[mm] = (0.6 * im[mm] + 0.4 * np.array([255, 200, 0])).astype(np.uint8)
    M = np.eye(4); M[:3, :3] = Rot.from_quat(np.r_[qq[f, 1:4], qq[f, 0]]).as_matrix(); M[:3, 3] = pos[f]; X0 = np.linalg.inv(W[f]) @ iT @ M
    for X, col in ((X0, (0, 255, 0)), (X0 @ F, (0, 0, 255))):
        v = np.asarray(m.vertices) @ X[:3, :3].T + X[:3, 3]; uv = v @ K.T; uv = uv[:, :2] / uv[:, 2:3]
        s = np.zeros((H, Wd), np.uint8); cv2.fillPoly(s, [np.round(uv[fc]).astype(np.int32) for fc in np.asarray(m.faces)], 1)
        cs, _ = cv2.findContours(s, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(im, cs, -1, col, 3)
        # bowl end marker: the template point farthest along +L
        tip = np.asarray(m.vertices)[np.argmax(np.asarray(m.vertices) @ U[:, 2])]; pt = X[:3, :3] @ tip + X[:3, 3]; q = K @ pt
        cv2.circle(im, (int(q[0] / q[2]), int(q[1] / q[2])), 9, col, -1)
    cv2.putText(im, f'eval {EP} f{f}: green=ref, red={ALT}, tint=mask, dot=+L end', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    x0, x1 = max(0, int(uv[:, 0].min()) - 250), min(Wd, int(uv[:, 0].max()) + 250); y0, y1 = max(0, int(uv[:, 1].min()) - 200), min(H, int(uv[:, 1].max()) + 200)
    tiles.append(cv2.resize(im[y0:y1, x0:x1] if (x1 - x0) > 100 and (y1 - y0) > 100 else im, (800, 500)))
rows = [np.hstack(tiles[i:i + 2] + ([np.zeros_like(tiles[0])] if len(tiles[i:i + 2]) == 1 else [])) for i in range(0, len(tiles), 2)]
cv2.imwrite(OUT, np.vstack(rows)); print('wrote', OUT)
