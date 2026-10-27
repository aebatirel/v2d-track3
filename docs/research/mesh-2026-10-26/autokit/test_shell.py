"""GT-free tests of autokit/shell.py: one synthetic wall with known geometry, then real observed points.

Synthetic (no data): an open tube (outer radius 40 mm, wall 6 mm, 100 mm tall) sampled from outside and inside with
1.2 mm depth noise along the rays. Checks: watertight; the outer face stays at 40 mm (oriented mode); with two-sided
evidence the wall is one solid 34-40 mm; without it, two slabs of thickness t; the symmetric mode moves the face out
by t/2.

Real (one episode each, obs_points.py files through autokit.io_gt): for t in {1.5, 2.5, 4.0} mm, mesh to
OUT/ep<N>_<obj>_t<t>.glb and record runtime, watertightness, body count, area, then
  - obs_fidelity (scripts/obs_fidelity.py, same obs file) of the shell, of the shell as the scorer decodes it (kit
    budget_mesh, 4096 faces / 4096 vertices) and of library_v3/<obj>.glb (our TSDF, same object frame);
  - fs_frac (autoloop_probe/fs_fidelity.py: share of mesh area in voxels our own depth saw as empty).
QA image per object: the colour crop (scratchpad/crops, our tracks + our library) next to the shells and the library
mesh, rendered from the same camera (our track cam_T_<obj>[k], rectified-left intrinsics).
No ground truth anywhere: no scan, mocap, *_align file or parquet pose is opened, and mesh_metric.py is not run.

Ablations (--ablate, t = 2.5 mm, OUT/ablate/): symmetric +-t/2 tube, no two-sided thickness, free-space clamp on.
Refined (--refined): the same at t = 2.5 mm on autokit/refine.py's output; its fidelity is still measured against the
RAW obs file (the refined points moved, so this comparison is biased against the refined run).

Usage: test_shell.py [--cases 2:white_pot_lid,21:blue_cup,...] [--ts 1.5,2.5,4.0] [--out DIR] [--no_render]
                     [--ablate 2:white_pot_lid,...] [--refined 41:white_pot] [--synthetic_only]
Writes OUT/results.jsonl (one JSON row per mesh) and OUT/qa_ep<N>_<obj>.jpg.
"""
import argparse, json, os, subprocess, sys, time

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from autokit.io_gt import load_obs, obs_path, load_poses, load_calib, SCRATCH  # noqa: E402
from autokit.shell import thin_shell  # noqa: E402

PY = f'{SCRATCH}/venv/bin/python'
SCRIPTS = os.path.abspath(os.path.join(HERE, '..', 'scripts'))
FS_FID = f'{SCRATCH}/autoloop_probe/fs_fidelity.py'
LIB = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', 'meshes', 'library_v3'))
CROPS = f'{SCRATCH}/crops'
KIT = os.environ.get('V2D_KIT', f'{SCRATCH}/kit/v2d_submission_kit')
OUT = f'{SCRATCH}/auto/stage1/shell'
CASES = '2:white_pot_lid,21:blue_cup,22:blue_cup,39:mini_dust_pan,22:water_pitcher,31:mini_sweeper,41:white_pot'


# ---------------------------------------------------------------------------------------------- synthetic
def synthetic(t=0.0025, seed=0):
    """Open tube, outer radius 40 mm, wall 6 mm; returns rows with the radial face positions of the shells."""
    rng = np.random.default_rng(seed)
    Ro, T, Hh = 0.040, 0.006, 0.100
    Ri = Ro - T
    pts, cams, frs = [], [], []
    for f, az in enumerate(np.linspace(0, 2 * np.pi, 24, endpoint=False)):
        cam = np.array([0.5 * np.cos(az), 0.5 * np.sin(az), 0.35])        # outside, above
        th = rng.uniform(0, 2 * np.pi, 40000); z = rng.uniform(0, Hh, 40000)
        X = np.stack([Ro * np.cos(th), Ro * np.sin(th), z], 1); n = X.copy(); n[:, 2] = 0; n /= Ro
        v = cam - X; v /= np.linalg.norm(v, axis=1, keepdims=True)
        vis = np.einsum('ij,ij->i', n, v) > 0.25
        X = X[vis] - v[vis] * rng.normal(0, 0.0012, (vis.sum(), 1))       # depth noise along the ray
        pts.append(X); cams.append(np.repeat(cam[None], len(X), 0)); frs.append(np.full(len(X), f))
    for f, az in enumerate(np.linspace(0, 2 * np.pi, 12, endpoint=False), start=24):
        cam = np.array([-0.25 * np.cos(az), -0.25 * np.sin(az), 0.35])   # above, across: sees the far inner face
        th = rng.uniform(0, 2 * np.pi, 40000); z = rng.uniform(0.4 * Hh, Hh, 40000)
        X = np.stack([Ri * np.cos(th), Ri * np.sin(th), z], 1); n = -X.copy(); n[:, 2] = 0; n /= Ri
        v = cam - X; v /= np.linalg.norm(v, axis=1, keepdims=True)
        vis = np.einsum('ij,ij->i', n, v) > 0.25
        X = X[vis] - v[vis] * rng.normal(0, 0.0012, (vis.sum(), 1))
        pts.append(X); cams.append(np.repeat(cam[None], len(X), 0)); frs.append(np.full(len(X), f))
    obs = dict(pts=np.concatenate(pts), cam=np.concatenate(cams), frame=np.concatenate(frs))
    rows = []
    for name, kw in [('oriented+two_sided', dict(mode='oriented', two_sided=True)),
                     ('oriented', dict(mode='oriented', two_sided=False)),
                     ('symmetric', dict(mode='symmetric', two_sided=False))]:
        m, rep = thin_shell(obs, t=t, return_report=True, **kw)
        S = trimesh.sample.sample_surface(m, 200000, seed=0)[0]
        mid = (S[:, 2] > 0.6 * Hh) & (S[:, 2] < 0.9 * Hh)               # where both faces were seen
        r = np.linalg.norm(S[mid, :2], axis=1) * 1e3
        h, e = np.histogram(r, bins=np.arange(30, 45.01, 0.5))
        peaks = [round(float(e[i] + 0.25), 2) for i in range(len(h)) if h[i] > 0.15 * h.max()
                 and h[i] >= h[max(i - 1, 0)] and h[i] >= h[min(i + 1, len(h) - 1)]]
        rows.append(dict(case='synthetic_tube', variant=name, t_mm=t * 1e3, truth_faces_mm=[Ri * 1e3, Ro * 1e3],
                         face_peaks_mm=peaks, r_p2_p98_mm=np.round(np.percentile(r, [2, 98]), 2).tolist(),
                         watertight=rep['watertight'], bodies=rep['bodies'], two_sided_frac=rep['two_sided_frac'],
                         two_sided_T=rep.get('two_sided_T_mm_p10_50_90'), sec=rep['sec']))
        print(json.dumps(rows[-1]), flush=True)
    return rows


# ---------------------------------------------------------------------------------------------- metrics
def run_json(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'{cmd}: {r.stderr[-2000:]}')
    return [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{')]


def budget(path, out):
    """The mesh as the scorer decodes it: the kit packer's budget_mesh (4096 faces, 4096 vertices), zero-area
    padding faces removed."""
    sys.path.insert(0, KIT)
    from v2dlb.mesh_budget import budget_mesh
    v, f = budget_mesh(path, 4096, 4096)
    m = trimesh.Trimesh(v, f, process=False)
    m.update_faces(m.area_faces > 0); m.remove_unreferenced_vertices()
    m.export(out)
    return dict(faces=int(len(m.faces)), watertight=bool(trimesh.Trimesh(m.vertices, m.faces, process=True).is_watertight),
                area_cm2=round(m.area * 1e4, 1))


# ---------------------------------------------------------------------------------------------- render
def render_cam(mesh, T_co, K, n=400000, H=1000, W=1600):
    """Shaded z-buffer splat of the mesh seen by the camera with pose T_co (object -> camera), intrinsics K."""
    import cv2
    P, fi = trimesh.sample.sample_surface(mesh, n, seed=0)
    N = mesh.face_normals[fi] @ T_co[:3, :3].T
    X = P @ T_co[:3, :3].T + T_co[:3, 3]
    ok = X[:, 2] > 0.05
    u = np.round(K[0, 0] * X[ok, 0] / X[ok, 2] + K[0, 2]).astype(int)
    v = np.round(K[1, 1] * X[ok, 1] / X[ok, 2] + K[1, 2]).astype(int)
    z = X[ok, 2]; N = N[ok]
    inn = (u >= 0) & (u < W) & (v >= 0) & (v < H)
    u, v, z, N = u[inn], v[inn], z[inn], N[inn]
    light = np.array([0.3, -0.4, -0.85]); light /= np.linalg.norm(light)
    sh = 0.25 + 0.75 * np.abs(N @ light)
    order = np.argsort(-z)                                    # far first, nearest written last
    img = np.full((H, W), -1.0)
    img[v[order], u[order]] = sh[order]
    hit = img >= 0
    out = np.full((H, W, 3), 245, np.uint8)
    g = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    out[hit] = np.stack([g[hit] * 0.75, g[hit] * 0.82, g[hit]], 1).astype(np.uint8)
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    return out, hit


def qa_image(ep, obj, meshes, labels, out_path):
    """[colour crop | each mesh rendered from the crop's frame], cropped to a common box."""
    import cv2
    cj = f'{CROPS}/ep{ep}/{obj}_crops.json'
    crop, k = None, None
    if os.path.isfile(cj):
        ch = json.load(open(cj))['chosen'][0]; k = int(ch['k'])
        c = cv2.imread(f'{CROPS}/ep{ep}/{ch["tag"]}.png', cv2.IMREAD_UNCHANGED)
        if c is not None:
            if c.shape[2] == 4:
                a = c[:, :, 3:4] / 255.0; c = (c[:, :, :3] * a + 245 * (1 - a)).astype(np.uint8)
            crop = c
    Pz = load_poses(ep); T = Pz[f'cam_T_{obj}']
    if k is None:                                              # no crop: the frame with the most observed points
        fr = load_obs(obs_path(obj, ep), keys=('frame',))['frame']; k = int(np.bincount(fr).argmax())
    K = load_calib()['K']
    rend = [render_cam(trimesh.load(m, force='mesh'), T[k], K) for m in meshes]
    hit = np.any([h for _, h in rend], 0)
    ys, xs = np.nonzero(hit)
    y0, y1 = max(0, ys.min() - 20), min(hit.shape[0], ys.max() + 20)
    x0, x1 = max(0, xs.min() - 20), min(hit.shape[1], xs.max() + 20)
    S = 300
    tiles = []
    if crop is not None:
        tiles.append((cv2.resize(crop, (S, S)), f'crop k{k}'))
    for (img, _), lab in zip(rend, labels):
        sub = img[y0:y1, x0:x1]; s = S / max(sub.shape[:2])
        sub = cv2.resize(sub, (int(sub.shape[1] * s), int(sub.shape[0] * s)))
        pad = np.full((S, S, 3), 245, np.uint8); pad[:sub.shape[0], :sub.shape[1]] = sub
        tiles.append((pad, lab))
    row = []
    for img, lab in tiles:
        img = img.copy(); cv2.putText(img, lab, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
        row.append(img)
    cv2.imwrite(out_path, np.hstack(row))
    return k


# ---------------------------------------------------------------------------------------------- real cases
def real_case(ep, obj, ts, out, refined=False, kw=None, tag='', render=True):
    kw = kw or {}
    os.makedirs(out, exist_ok=True)
    path = obs_path(obj, ep, refined=refined)
    obs = load_obs(path, keys=('pts', 'cam', 'frame'))
    rows, meshes = [], []
    for t in ts:
        name = f'ep{ep}_{obj}_t{t:.1f}{tag}'
        mp = f'{out}/{name}.glb'
        t0 = time.time()
        m, rep = thin_shell(obs, t=t * 1e-3, return_report=True, **kw)
        sec = time.time() - t0
        m.export(mp)
        bp = f'{out}/budget/{name}_b4096.glb'; os.makedirs(os.path.dirname(bp), exist_ok=True)
        b = budget(mp, bp)
        rows.append(dict(case=name, obs=path, refined=refined, kw=kw, t_mm=t, sec=round(sec, 1),
                         watertight=rep['watertight'], bodies=rep['bodies'], area_cm2=rep['area_cm2'],
                         faces=rep['faces'], extents_cm=rep['extents_cm'], two_sided_frac=rep['two_sided_frac'],
                         two_sided_T=rep.get('two_sided_T_mm_p10_50_90'), islands_dropped=rep['islands_dropped'],
                         grazing_or_weak_dropped_frac=rep['grazing_or_weak_dropped_frac'], weak_normal_frac=rep['weak_normal_frac'],
                         samples=rep['samples'], pitch_mm=rep['pitch_mm'], budget=b, mesh=mp))
        meshes.append(mp)
    # GT-free fidelity against the SAME episode's raw obs file (also for refined runs: the raw file is the reference)
    raw = obs_path(obj, ep)
    lib = f'{LIB}/{obj}.glb'
    allm = meshes + [r['budget'] and f'{out}/budget/{os.path.basename(r["mesh"])[:-4]}_b4096.glb' for r in rows] + [lib]
    fid = {d['mesh']: d for d in run_json([PY, f'{SCRIPTS}/obs_fidelity.py', raw] + allm)}
    fs = {d['mesh']: d for d in run_json([PY, FS_FID, raw] + meshes + [lib])}
    for r in rows:
        bn = os.path.basename(r['mesh'])
        r['fid'] = {k: fid[bn][k] for k in ('obs_to_mesh_mm', 'mesh_to_obs_mm', 'sum_mm')}
        r['fid_budget'] = {k: fid[bn[:-4] + '_b4096.glb'][k] for k in ('obs_to_mesh_mm', 'mesh_to_obs_mm', 'sum_mm')}
        r['fs_frac_pct'] = fs[bn]['fs_frac_pct']
    lrow = dict(case=f'ep{ep}_{obj}_library_v3', mesh=lib, fid={k: fid[f'{obj}.glb'][k] for k in
                ('obs_to_mesh_mm', 'mesh_to_obs_mm', 'sum_mm')}, fs_frac_pct=fs[f'{obj}.glb']['fs_frac_pct'],
                area_cm2=fs[f'{obj}.glb']['area_cm2'], watertight=fs[f'{obj}.glb']['watertight'],
                bodies=fs[f'{obj}.glb']['bodies'])
    rows.append(lrow)
    if render:
        try:
            k = qa_image(ep, obj, meshes + [lib], [f't{t:.1f}{tag}' for t in ts] + ['library_v3'],
                         f'{out}/qa_ep{ep}_{obj}{tag}.jpg')
            for r in rows:
                r['qa'] = f'{out}/qa_ep{ep}_{obj}{tag}.jpg'; r['qa_frame'] = k
        except Exception as e:                                  # rendering is QA only; record and continue
            for r in rows:
                r['qa_error'] = repr(e)[:300]
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cases', default=CASES); p.add_argument('--ts', default='1.5,2.5,4.0')
    p.add_argument('--out', default=OUT); p.add_argument('--no_render', action='store_true')
    p.add_argument('--ablate', default=''); p.add_argument('--refined', default='')
    p.add_argument('--synthetic_only', action='store_true'); p.add_argument('--no_synthetic', action='store_true')
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    res = open(f'{a.out}/results.jsonl', 'a')
    def emit(rows):
        for r in rows:
            r['when'] = time.strftime('%Y-%m-%dT%H:%M:%S'); res.write(json.dumps(r) + '\n'); res.flush()
            print(json.dumps({k: r.get(k) for k in ('case', 't_mm', 'sec', 'watertight', 'bodies', 'area_cm2', 'fid',
                                                     'fid_budget', 'fs_frac_pct', 'two_sided_frac')}), flush=True)
    if not a.no_synthetic:
        emit(synthetic())
    if a.synthetic_only:
        return
    ts = [float(x) for x in a.ts.split(',')]
    for spec in [s for s in a.cases.split(',') if s]:
        ep, obj = spec.split(':'); ep = int(ep)
        if not os.path.isfile(obs_path(obj, ep, must_exist=False)):
            emit([dict(case=f'ep{ep}_{obj}', error='no obs file yet')]); continue
        emit(real_case(ep, obj, ts, a.out, render=not a.no_render))
    for spec in [s for s in a.refined.split(',') if s]:
        ep, obj = spec.split(':'); ep = int(ep)
        if os.path.isfile(obs_path(obj, ep, refined=True, must_exist=False)):
            emit(real_case(ep, obj, [2.5], a.out, refined=True, tag='_refined', render=not a.no_render))
        else:
            emit([dict(case=f'ep{ep}_{obj}_refined', error='no refined obs file')])
    for spec in [s for s in a.ablate.split(',') if s]:
        ep, obj = spec.split(':'); ep = int(ep)
        for tag, kw in [('_sym', dict(mode='symmetric', two_sided=False)), ('_no2s', dict(two_sided=False)),
                        ('_carve', dict(carve=True))]:
            emit(real_case(ep, obj, [2.5], f'{a.out}/ablate', kw=kw, tag=tag, render=False))


if __name__ == '__main__':
    main()
