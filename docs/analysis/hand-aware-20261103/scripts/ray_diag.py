"""DIAGNOSTIC (reads mocap via the scorer dump): split each object's position error into the component along the camera
ray (+ = estimate farther than truth) and the lateral part, per 5-frame block. Camera centres come from the track's
poses.npz world_T_cam, mapped by the scorer's frame-0 scene alignment (Kabsch raw -> aligned over all frames).
Usage: ray_diag.py DUMP.npz POSES.npz NAMES_CSV OBJ [BLOCK]"""
import sys, numpy as np
D = np.load(sys.argv[1]); W = np.load(sys.argv[2])['world_T_cam']; names = sys.argv[3].split(','); s = names.index(sys.argv[4])
B = int(sys.argv[5]) if len(sys.argv) > 5 else 5
raw, ach, ref = D['raw'][..., :3].reshape(-1, 3), D['ach'][..., :3].reshape(-1, 3), D['ref'][:, s, :3]
cs, cd = raw.mean(0), ach.mean(0); U, _, Vt = np.linalg.svd((raw - cs).T @ (ach - cd)); R = Vt.T @ U.T
if np.linalg.det(R) < 0: Vt[-1] *= -1; R = Vt.T @ U.T
c = (W[:, :3, 3] - cs) @ R.T + cd
d = D['ach'][:, s, :3] - ref; u = ref - c[:len(ref)]; u /= np.linalg.norm(u, axis=1, keepdims=True)
ray = (d * u).sum(1) * 100; lat = np.linalg.norm(d - (d * u).sum(1, keepdims=True) * u, axis=1) * 100
n = len(ray) // B * B
print('ray/5f:', ' '.join('%+.1f' % x for x in ray[:n].reshape(-1, B).mean(1)))
print('lat/5f:', ' '.join('%.1f' % x for x in lat[:n].reshape(-1, B).mean(1)))
