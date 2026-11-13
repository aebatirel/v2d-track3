import sys, numpy as np, cv2
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
from gmg import gen_inputs as GI
geo = GI.camera_geometry(f'{S}/data/calib.json')
z = dict(np.load(f'{S}/data/sweep/ep2/hands.npz'))
P = dict(np.load(f'{S}/data/sweep/ep2/poses.npz'))
k = int(sys.argv[1]); j = k + 1
cap = cv2.VideoCapture(f'{S}/data/store/ep2_a.mp4')
for i in range(j + 1):
    ok, img = cap.read()
for s, col in (('left', (255, 0, 0)), ('right', (0, 0, 255))):
    print(s, 'valid', z['valid_' + s][k], 'meas', z['measured_' + s][k], 'uv', z['uv_a_' + s][k][:3])
    uv = z['uv_a_' + s][k]
    for (u, v) in uv:
        if np.isfinite(u):
            cv2.circle(img, (int(u), int(v)), 8, col, -1)
caps = GI.hand_capsules(z, P, k)
m, zn = GI.hand_layer(caps, geo)
img[m] = (0.5 * img[m] + 0.5 * np.array([255, 255, 0])).astype(np.uint8)
cv2.imwrite(f'{S}/gmg/b2/diag/hand_k{k}.jpg', cv2.resize(img, (1014, 760)))
