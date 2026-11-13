"""GT-free overlay QA for T5 (public ep24): board 2 is untouched by our hands until about f105, so its frame-0 world pose,
held and seen through a camera W'[t], should stay on the board in the image if W' is right. Draws, on rectified cam-c crops
around board 2: red = our board-2 track (cam_T_obj, camera-independent), yellow = the frame-0 hold seen through perc2's
stored camera, cyan = the frame-0 hold seen through the T5 camera. Reads only our outputs, our meshes, the video and the
public calibration (no mocap). Usage: python -I t5_overlay.py POSES W_T5.npy VIDEO CALIB MESHDIR OUT.png [frames]
"""
import sys
import cv2
import numpy as np
import trimesh

sys.path.insert(0, '/home/user/v2d-track3/pipeline')
from refine import assert_inference_input  # noqa: E402
from track_overlay import rectify_maps  # noqa: E402

poses, wnew, video, calib, mdir, out = sys.argv[1:7]
frames = [int(x) for x in (sys.argv[7] if len(sys.argv) > 7 else '0,36,45,60,75,100').split(',')]
for f in (poses, wnew, video, calib, mdir):
    assert_inference_input(f)
P = np.load(poses); W0 = P['world_T_cam']; Wn = np.load(wnew); T = P['cam_T_wooden_piece_2']
mesh = trimesh.load(f'{mdir}/wooden_piece_2.glb', force='mesh'); X = np.asarray(mesh.vertices); F = np.asarray(mesh.faces)
MC, K = rectify_maps(calib)
cap = cv2.VideoCapture(video); imgs = {}; t = 0
while len(imgs) < len(frames):
    ok, f = cap.read()
    if not ok:
        break
    if t in frames:
        imgs[t] = cv2.remap(f, MC[0], MC[1], cv2.INTER_LINEAR)
    t += 1


def uv(M):
    Y = X @ M[:3, :3].T + M[:3, 3]
    return np.stack([Y[:, 0] / Y[:, 2] * K[0, 0] + K[0, 2], Y[:, 1] / Y[:, 2] * K[1, 1] + K[1, 2]], 1)


SC = 2                                                     # crop upscale; contours drawn at the upscaled resolution
tiles = []
for t in frames:
    c = uv(T[t]).mean(0).astype(int)
    x0, y0 = max(c[0] - 150, 0), max(c[1] - 105, 0)
    crop = cv2.resize(imgs[t][y0:y0 + 210, x0:x0 + 300], (600, 420), interpolation=cv2.INTER_CUBIC)
    hold0, holdn = np.linalg.inv(W0[t]) @ W0[0] @ T[0], np.linalg.inv(Wn[t]) @ Wn[0] @ T[0]
    for M, col in ((T[t], (0, 0, 255)), (hold0, (0, 220, 255)), (holdn, (255, 255, 0))):
        m = np.zeros((420, 600), np.uint8)
        q = np.round((uv(M) - [x0, y0]) * SC).astype(np.int32)
        cv2.fillPoly(m, list(q[F]), 1)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(crop, cs, -1, col, 1)
    cv2.putText(crop, f'f{t}', (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    tiles.append(crop)
rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
cv2.imwrite(out, np.vstack(rows))
print('wrote', out)
