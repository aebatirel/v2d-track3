"""Stage B gap 3b: project GT-placed scan markers of public ep 11 f0 into ego_cam_b via the factory extrinsics, to
measure sphere size/contrast in cam b automatically. Upright-frame convention tested: F = diag(-1,-1,1) conjugation
(both streams rotated 180 deg before release) and both directions of the stored transform."""
import numpy as np, json, sys, cv2
W = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W)
from pnp_check import variant, world_markers, solve
cal = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json'))
C = cal['cameras']
K, D = variant(False)
uv = np.array([[795, 988], [1044, 1022], [950, 1290], [1260, 1059], [1479, 984], [1273, 888]], float)
X, lab, objs = world_markers(11, 0, ['blue_cup', 'beige_cup'])
err, (perm, rv, tv, e) = solve(uv, X, K, D)
Ta = np.eye(4); Ta[:3, :3] = cv2.Rodrigues(rv)[0]; Ta[:3, 3] = tv.ravel()        # world -> upright cam a
E = np.array(C['ego_cam_a']['extrinsics_to_stereo_left']); P = cal['stereo_pairs'][1]; L = np.array(P['left_to_right'])
F = np.diag([-1., -1., 1., 1.])
Kb = np.array(C['ego_cam_b']['intrinsic_matrix']); Db = np.array(C['ego_cam_b']['distortion_coefficients'], float)
im = cv2.imread(W + '/b/fr/p11_b_0000.png'); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
cands = {}
for nE, Ea in (('E', E), ('Einv', np.linalg.inv(E))):
    for nL, Lb in (('-', np.eye(4)), ('L', L), ('Linv', np.linalg.inv(L))):
        for nF, conj in (('F', True), ('raw', False)):
            T = Lb @ Ea
            if conj: T = F @ T @ F
            cands[f'{nE}{nL}{nF}'] = T
res = {}
yy, xx = np.mgrid[:g.shape[0], :g.shape[1]]
for n, T in cands.items():
    Tb = T @ Ta; Xc = X @ Tb[:3, :3].T + Tb[:3, 3]
    pr = cv2.projectPoints(X, cv2.Rodrigues(Tb[:3, :3])[0], Tb[:3, 3], Kb, Db)[0].reshape(-1, 2)
    res[n] = dict(t=np.round(T[:3, 3], 4).tolist(), uv=pr.round(1).tolist(), Z=np.round(Xc[:, 2], 3).tolist())
    print(n, 't', res[n]['t'], 'uv0', pr[0].round(0), 'uv5', pr[-1].round(0))
json.dump(res, open(W + '/b2/camb_proj_cands.json', 'w'), indent=1)
