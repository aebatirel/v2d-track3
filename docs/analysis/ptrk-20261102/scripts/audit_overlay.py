"""Overlay images for the eval audit: rectified ego_cam_c frame (grey), each object's PACKED-reference silhouette
(outline, colour per object) and its SAM2 video mask (tint, same colour). GT-free (eval).
Usage: python -I audit_overlay.py EP VIDEO_C CALIB REF_PARQUET TABLE_NPZ PERC_POSES VOS_NPZ KSRC MESH_DIR OUT_PNG FRAMES"""
import sys, os, json, numpy as np, cv2, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'pipeline'))
from identity_fix import rectified_frames
EP, VID, CAL, REF, TAB, POS, VOS, KSRC, MD, OUT = sys.argv[1:11]
FR = [int(x) for x in sys.argv[11].split(',')]
imgs, _ = rectified_frames(VID, CAL, FR)
t = pq.read_table(REF).to_pandas(); on = t['object_name'].iloc[0]; names = on.split('__') if isinstance(on, str) else list(on)
pos = np.array([[np.asarray(list(v), float) for v in fr] for fr in t['object_body_position'].iloc[0]])
qq = np.array([[np.asarray(list(v), float) for v in fr] for fr in t['object_body_wxyz'].iloc[0]])
iT = np.linalg.inv(np.load(TAB)['T_table_from_world']); W = np.load(POS)['world_T_cam']; K = np.load(KSRC)['K'].astype(float)
V = np.load(VOS); cols = [(0, 255, 0), (255, 80, 0), (0, 160, 255)]
tiles = []
for f in FR:
    im = cv2.cvtColor(imgs[f].astype(np.uint8), cv2.COLOR_GRAY2BGR); H, Wd = im.shape[:2]
    for b, n in enumerate(names):
        c = cols[b % 3]
        if n in V.files:
            mk = np.unpackbits(V[n], axis=-1)[f, :, :400].astype(np.uint8)
            mk = cv2.resize(mk, (Wd, H), interpolation=cv2.INTER_NEAREST) > 0
            im[mk] = (0.6 * im[mk] + 0.4 * np.array(c)).astype(np.uint8)
        M = np.eye(4); M[:3, :3] = Rot.from_quat(np.r_[qq[f, b, 1:4], qq[f, b, 0]]).as_matrix(); M[:3, 3] = pos[f, b]
        X = np.linalg.inv(W[f]) @ iT @ M; m = trimesh.load(f'{MD}/{n}.glb', force='mesh')
        v = np.asarray(m.vertices) @ X[:3, :3].T + X[:3, 3]; uv = v @ K.T; uv = uv[:, :2] / uv[:, 2:3]
        sil = np.zeros((H, Wd), np.uint8)
        cv2.fillPoly(sil, [np.round(uv[fc]).astype(np.int32) for fc in np.asarray(m.faces)], 1)
        cs, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(im, cs, -1, c, 3)
        cv2.putText(im, f'{n} (outline=ref, tint=mask)', (20, 40 + 40 * b), cv2.FONT_HERSHEY_SIMPLEX, 1.0, c, 2)
    cv2.putText(im, f'eval {EP} f{f}', (20, H - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    tiles.append(cv2.resize(im, (800, 500)))
rows = [np.hstack(tiles[i:i + 2] + ([np.zeros_like(tiles[0])] if len(tiles[i:i + 2]) == 1 else [])) for i in range(0, len(tiles), 2)]
cv2.imwrite(OUT, np.vstack(rows))
print('wrote', OUT)
