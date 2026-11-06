"""CPU mock of the perc2 masking patch (perc2_mask_others.patch, MASK_OTHERS=1), GT-free. It executes the patch's new
frame-major block verbatim with stubs: nvdiffrast_render -> CPU splat render (offsetfix.render) at full resolution,
FoundationPose -> a stub whose track_one records what it was given and returns its last pose (no tracking is mocked),
TRACK_GUARD off. Data: public ep11, our P_o track at frames 0, 63, 64, 129, 130 (renumbered 0..4; f64 and f130 are on our
depth grid and see the others at their f63 / f129 poses, as in a dense run), our depth grid (half resolution, repeated 2x2), the rectified cam-c frames. Checks: the block runs, every object gets masked
inputs each frame, the masks hide exactly the other object's front-most pixels (dilated), and the unmasked loop is
untouched (MASK_OTHERS=0 path = the original code). Writes a PNG of what the blue cup's track_one would see.
MOCK_HULL=1 renders the others' convex hulls, 0 (default, as the patch) our meshes; MOCK_MODE depth (default, as the
patch) or render (MASK_MODE). Also reports, per call, the share of the object's own rendered silhouette that is hidden.
Usage: python -I m10_perc2_mock.py PATCHED_PERC2 TRACK_DIR DEPTH_GRID VIDEO_C CALIB OUT_PNG OUT_JSON"""
import json, os, sys, types
import numpy as np, cv2
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import refine, offsetfix as OF, occluder_mask  # noqa: F401
from track_overlay import rectify_maps

perc2, trk, grid, video, calib, out_png, out_json = sys.argv[1:8]
for f in (trk, grid, video, calib):
    refine.assert_inference_input(f)
src = open(perc2).read()
a0 = src.index("MASK_OTHERS = os.environ.get('MASK_OTHERS'")
a1 = src.index('\nelse:\n', a0)
block = src[a0:a1]
FR = [0, 63, 64, 129, 130]       # the shown frames 64 and 130 see the others at their f63 / f129 poses, as a dense run
P = np.load(f'{trk}/poses.npz'); names = [k[6:] for k in P.files if k.startswith('cam_T_')]
Z = np.load(grid); gf = [int(x) for x in Z['frames']]
near = lambda t: min(gf, key=lambda g: abs(g - t))      # f63 / f129 are not on the grid: nearest grid depth (not shown)
depths = [np.repeat(np.repeat(np.asarray(Z['depth'][gf.index(near(t))], np.float32), 2, 0), 2, 1) for t in FR]
MC, KR = rectify_maps(calib)
cap, rc, t = cv2.VideoCapture(video), {}, 0
while len(rc) < len(FR):
    ok, f = cap.read()
    if not ok:
        break
    if t in FR:
        rc[t] = cv2.cvtColor(cv2.remap(f, MC[0], MC[1], cv2.INTER_LINEAR), cv2.COLOR_BGR2GRAY)
    t += 1
rc = [rc[t] for t in FR]
objs = {n: refine.Obj(n, f'/home/user/v2d-track3/meshes/library_v3/{n}.glb') for n in names}
for o in objs.values():
    OF.mesh_model(o)


class Arr:                                               # numpy stand-in for a torch tensor (.float().cuda().cpu().numpy())
    def __init__(self, a): self.a = np.asarray(a)
    def float(self): return self
    def cuda(self): return self
    def cpu(self): return self
    def numpy(self): return self.a
    def __getitem__(self, k): return Arr(self.a[k])


fake_torch = types.SimpleNamespace(as_tensor=lambda x: Arr(x))
CALLS = []


HULL = os.environ.get('MOCK_HULL', '0') == '1'
MODE = os.environ.get('MOCK_MODE', 'depth')
HS = {}


def samples(n):                                          # what the stub renders: our mesh, or its convex hull (MASK_HULL)
    if not HULL:
        return OF.mesh_model(objs[n])[0]
    if n not in HS:
        import trimesh
        h = objs[n].mesh.convex_hull
        HS[n] = np.asarray(trimesh.sample.sample_surface(h, int(np.clip(h.area / 1.5e-6, 30000, 400000)), seed=11)[0], float)
    return HS[n]


class MeshTag:
    def __init__(self, n): self.n = n
    @property
    def convex_hull(self): return self


def nvdiffrast_render(K, H, W, ob_in_cams, glctx, mesh_tensors):
    T = ob_in_cams.numpy()[0].astype(float)
    z, lab = OF.render([(0, T, samples(mesh_tensors.n))], np.asarray(K, float), (H, W))
    return None, Arr(np.where(np.isfinite(z), z, 0)[None]), None


class StubEst:
    def __init__(self, n): self.n = n; self.seen = []
    def register(self, K, rgb, depth, ob_mask, iteration): return P[f'cam_T_{self.n}'][0].astype(float)
    def track_one(self, rgb, depth, K, iteration):
        i = len(self.seen) + 1
        self.seen.append(dict(frame=FR[i], masked_depth_px=int(((depth == 0) & (depths[i] > 0)).sum()),
                              gray_changed_px=int((rgb[..., 0] != rc[i]).sum())))
        CALLS.append((self.n, i, rgb, depth))
        return P[f'cam_T_{self.n}'][FR[i]].astype(float)            # stub: the stored track, no tracking mocked


ns = dict(os=types.SimpleNamespace(environ={'MASK_OTHERS': '1', 'MASK_DIL': '3', 'MASK_HULL': '1' if HULL else '0',
                                                         'MASK_MODE': MODE, 'MASK_TOL': '0.01'}), np=np, json=json, time=__import__('time'),
          torch=fake_torch, nvdiffrast_render=nvdiffrast_render, glctx=None, make_mesh_tensors=lambda m: m,
          meshes={n: MeshTag(n) for n in names}, names=names, KR=KR, RSZ=(1600, 1000), depths=depths, rc=rc, N=len(FR),
          rgb=lambda g: np.repeat(g[..., None], 3, 2), ests={n: StubEst(n) for n in names}, GLOG={}, MASK={n: None for n in names},
          REG_ITERS=5, TRACK_ITERS=2, TRACK_GUARD=False, plausible=lambda n, p, i: True, poses={}, OUT=os.path.dirname(out_json),
          log=lambda *a: print('[perc2 mock]', *a), W_C=None, GUARD_EVERY=10)
os.makedirs(ns['OUT'], exist_ok=True)
exec(compile(block.replace("open(f'{OUT}/mask_others.json', 'w')", "open(f'{OUT}/mock_mask_others.json', 'w')"), 'perc2_patch_block', 'exec'), ns)
res = dict(frames=FR, mask_hull=HULL, mask_mode=MODE, objects={n: ns['ests'][n].seen for n in names},
           poses_shape={n: list(ns['poses'][n].shape) for n in names})
# check: for each call, the hidden pixels equal the other object's front-most pixels (dilated), recomputed independently
chk = []
K = np.asarray(KR, float)
for n, i, rgbm, dep in CALLS:
    Ds = []
    for m in names:
        z, _ = OF.render([(0, P[f'cam_T_{m}'][FR[i - 1]].astype(float), samples(m))], K, (1000, 1600))
        Ds.append(np.where(np.isfinite(z), z, 0))
    M = occluder_mask.occluder_masks(np.stack(Ds), 3, depths[i] if MODE == 'depth' else None, 0.01)[names.index(n)]
    sil = Ds[names.index(n)] > 0
    res.setdefault('own_silhouette_hidden_frac', []).append(dict(obj=n, frame=FR[i], frac=round(float((M & sil).sum() / max(1, sil.sum())), 3)))
    chk.append(bool(np.array_equal(dep == 0, (depths[i] == 0) | M)))
res['mask_check_all_equal'] = all(chk)
json.dump(res, open(out_json, 'w'), indent=1)
print(json.dumps(res)[:800])
# picture: blue cup's inputs at f64 and f130, raw vs masked (depth as gray, gray image)
tiles = []
for n, i, rgbm, dep in CALLS:
    if n != 'blue_cup' or FR[i] not in (64, 130):
        continue
    def dv(d):
        v = np.clip((d - 0.3) / 0.5, 0, 1); v[d <= 0] = 0
        return cv2.cvtColor((v * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    T = P['cam_T_blue_cup'][FR[i]].astype(float)
    X = OF.mesh_model(objs['blue_cup'])[0] @ T[:3, :3].T + T[:3, 3]
    uv = X[:, :2] / X[:, 2:3] * [K[0, 0], K[1, 1]] + [K[0, 2], K[1, 2]]
    (x0, y0), (x1, y1) = np.clip(uv.min(0) - 120, 0, None).astype(int), np.minimum(uv.max(0) + 120, [1600, 1000]).astype(int)
    row = [cv2.cvtColor(rc[i], cv2.COLOR_GRAY2BGR), rgbm.astype(np.uint8), dv(depths[i]), dv(dep)]
    row = [cv2.resize(r[y0:y1, x0:x1], (360, 360)) for r in row]
    for r, txt in zip(row, (f'f{FR[i]} gray (raw)', 'gray, others hidden', 'depth (raw)', 'depth, others hidden')):
        cv2.rectangle(r, (0, 0), (360, 26), (0, 0, 0), -1); cv2.putText(r, txt, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    tiles.append(np.hstack(row))
cv2.imwrite(out_png, np.vstack(tiles))
print('wrote', out_png)
