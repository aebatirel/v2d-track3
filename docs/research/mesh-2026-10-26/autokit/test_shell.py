"""GT-free tests of autokit/shell.py (stage 1b): synthetic geometry with known answers, then real observed points.

Synthetic (no data):
  - tube: an open tube (outer radius 40 mm, wall 6 mm, 100 mm tall) sampled from outside and inside with 1.2 mm
    depth noise along the rays. Checks: watertight, <= 4000 faces, the outer face stays at 40 mm (oriented mode);
    with two-sided evidence the wall is one solid 34-40 mm; without it, a slab of thickness t behind each face.
  - budget: every synthetic shell goes through the kit's budget_mesh (4096 faces / 4096 vertices) and must come
    back with the same face count (weld only), watertight, area change <= 2 %.
  - islands: a plate seen from above plus four separate pieces - a sphere cap 12 mm above the plate (ball-like,
    kept), a flat flake 10 mm above it (not ball-like, dropped), a flake 1 mm above it (touches, kept) and a speck
    of 0.2 cm^2 (dropped). Checks the kept/dropped verdicts and the dropped-area report.
  - patch: surface_patch on a host cylinder with a fin sticking out, host = the cylinder: the patch must hold the
    fin and nothing within 2 voxels of the host surface.
Real (one episode each, obs_points.py files through autokit.io_gt): per case ONE sheet (shell_sheet), then for t in
{1.5, 2.5, 4.0} mm the closed shell (solidify_sheet, <= 4000 faces) to OUT/ep<N>_<obj>_t<t>.glb, and
  - the kit's budget_mesh decode (OUT/budget/*_b4096.glb): faces in vs out (weld only?), watertight, area change;
  - obs_fidelity (scripts/obs_fidelity.py, same obs file) of the shell, its decode and library_v3/<obj>.glb;
  - fs_frac (autoloop_probe/fs_fidelity.py: share of mesh area in voxels our own depth saw as empty);
  - bodies, islands kept/dropped (area), decimation error (dense sheet -> decimated sheet), runtime.
QA image per object: colour crop (scratchpad/crops) next to the shells and library_v3 from the same camera.
No ground truth anywhere: no scan, mocap, *_align file or parquet pose is opened, and mesh_metric.py is not run.
Meshes are opened through io_gt.load_mesh when it exists (allow-listed roots), else through the local stand-in
_load_mesh below (io_gt.check_path + the same idea of roots) - the io fixer adds load_mesh in parallel.

Usage: test_shell.py [--cases 2:white_pot_lid,21:blue_cup,...] [--ts 1.5,2.5,4.0] [--out DIR] [--no_render]
                     [--synthetic_only] [--no_synthetic] [--ablate 2:white_pot_lid,...]
Writes OUT/results.jsonl (one JSON row per mesh) and OUT/qa_ep<N>_<obj>.jpg.
"""
import argparse, json, math, os, subprocess, sys, time

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from autokit.io_gt import load_obs, obs_path, load_poses, load_calib, check_path, SCRATCH  # noqa: E402
from autokit import shell as SH  # noqa: E402
from autokit.shell import thin_shell, shell_sheet, solidify_sheet, surface_patch  # noqa: E402,F401

PY = f'{SCRATCH}/venv/bin/python'
SCRIPTS = os.path.abspath(os.path.join(HERE, '..', 'scripts'))
FS_FID = f'{SCRATCH}/autoloop_probe/fs_fidelity.py'
LIB = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', 'meshes', 'library_v3'))
CROPS = f'{SCRATCH}/crops'
KIT = os.environ.get('V2D_KIT', f'{SCRATCH}/kit/v2d_submission_kit')
OUT = f'{SCRATCH}/auto/stage1b/shell'
CASES = ('2:white_pot_lid,21:blue_cup,39:mini_dust_pan,22:water_pitcher,31:mini_sweeper,41:white_pot,11:beige_cup,'
         '24:wooden_piece_1,13:plastic_dish_rack')

try:                                                   # the io fixer's guarded loader (stage 1b API contract)
    from autokit.io_gt import load_mesh as _load_mesh  # noqa: E402
    LOAD_MESH = 'io_gt.load_mesh'
except ImportError:                                    # local stand-in until it lands
    MESH_ROOTS = (f'{SCRATCH}/auto/', LIB + '/')

    def _load_mesh(path):
        rp = check_path(path)
        if not any(rp.startswith(os.path.realpath(r)) for r in MESH_ROOTS):
            raise ValueError(f'integrity: mesh path {rp!r} is outside the allow-listed roots {MESH_ROOTS}')
        return trimesh.load(rp, force='mesh')
    LOAD_MESH = 'test_shell stand-in (io_gt.check_path + roots auto/, library_v3/)'


# ---------------------------------------------------------------------------------------------- kit decode
def budget(path, out):
    """The mesh as the scorer decodes it: the kit packer's budget_mesh (4096 faces, 4096 vertices), zero-area
    padding faces removed. 'weld_only' = budget_mesh returned exactly the welded input's faces (no simplification)."""
    check_path(path)
    if KIT not in sys.path:
        sys.path.insert(0, KIT)
    from v2dlb.mesh_budget import budget_mesh
    src = trimesh.load(path, force='mesh', process=False)
    welded = trimesh.Trimesh(src.vertices, src.faces, process=True)
    v, f = budget_mesh(path, 4096, 4096)
    m = trimesh.Trimesh(v, f, process=False)
    m.update_faces(m.area_faces > 0); m.remove_unreferenced_vertices()
    m.export(out)
    mw = trimesh.Trimesh(m.vertices, m.faces, process=True)
    return dict(faces_in=int(len(welded.faces)), vertices_in=int(len(welded.vertices)), faces=int(len(m.faces)),
                weld_only=bool(len(m.faces) == len(welded.faces)), watertight=bool(mw.is_watertight),
                bodies=int(len(mw.split(only_watertight=False))), area_cm2=round(m.area * 1e4, 2),
                area_change_pct=round(100 * (m.area / max(src.area, 1e-12) - 1), 3))


def kit_check(mesh, tag, out):
    p = f'{out}/synthetic/{tag}.glb'; os.makedirs(os.path.dirname(p), exist_ok=True)
    mesh.export(p)
    return budget(p, p[:-4] + '_b4096.glb')


# ---------------------------------------------------------------------------------------------- synthetic
def _rays(X, cam, n_true, rng, noise=0.0012, cos_min=0.25):
    v = cam - X; v /= np.linalg.norm(v, axis=1, keepdims=True)
    vis = np.einsum('ij,ij->i', n_true, v) > cos_min
    return X[vis] - v[vis] * rng.normal(0, noise, (vis.sum(), 1)), vis


def synthetic_tube(out, t=0.0025, seed=0):
    """Open tube, outer radius 40 mm, wall 6 mm; rows with the radial face positions of the shells."""
    rng = np.random.default_rng(seed)
    Ro, T, Hh = 0.040, 0.006, 0.100
    Ri = Ro - T
    pts, cams, frs = [], [], []
    for f, az in enumerate(np.linspace(0, 2 * np.pi, 24, endpoint=False)):
        cam = np.array([0.5 * np.cos(az), 0.5 * np.sin(az), 0.35])        # outside, above
        th = rng.uniform(0, 2 * np.pi, 40000); z = rng.uniform(0, Hh, 40000)
        X = np.stack([Ro * np.cos(th), Ro * np.sin(th), z], 1); n = X.copy(); n[:, 2] = 0; n /= Ro
        X, _ = _rays(X, cam, n, rng)
        pts.append(X); cams.append(np.repeat(cam[None], len(X), 0)); frs.append(np.full(len(X), f))
    for f, az in enumerate(np.linspace(0, 2 * np.pi, 12, endpoint=False), start=24):
        cam = np.array([-0.25 * np.cos(az), -0.25 * np.sin(az), 0.35])   # above, across: sees the far inner face
        th = rng.uniform(0, 2 * np.pi, 40000); z = rng.uniform(0.4 * Hh, Hh, 40000)
        X = np.stack([Ri * np.cos(th), Ri * np.sin(th), z], 1); n = -X.copy(); n[:, 2] = 0; n /= Ri
        X, _ = _rays(X, cam, n, rng)
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
        lowz = (S[:, 2] > 0.1 * Hh) & (S[:, 2] < 0.3 * Hh)               # outside only seen
        r_low = np.linalg.norm(S[lowz, :2], axis=1) * 1e3
        b = kit_check(m, f'tube_{name}_t{t * 1e3:.1f}', out)
        rows.append(dict(case='synthetic_tube', variant=name, t_mm=t * 1e3, truth_faces_mm=[Ri * 1e3, Ro * 1e3],
                         face_peaks_mm=peaks, r_p2_p98_mm=np.round(np.percentile(r, [2, 98]), 2).tolist(),
                         outer_face_low_p50_mm=round(float(np.percentile(r_low, 98)), 2) if len(r_low) else None,
                         faces=rep['faces'], watertight=rep['watertight'], bodies=rep['bodies'],
                         two_sided_frac=rep['two_sided_frac'], two_sided_T=rep.get('two_sided_T_mm_p10_50_90'),
                         master_samples=rep.get('master_samples'), slave_samples=rep.get('slave_samples'),
                         decimation={k: rep['decimation'].get(k) for k in ('sheet_faces', 'border_edges',
                                                                            'dense_to_dec_mm_p50_95_99')},
                         budget=b, sec=rep['sec'],
                         ok=bool(rep['watertight'] and b['weld_only'] and b['watertight']
                                 and abs(b['area_change_pct']) <= 2 and rep['faces'] <= 4096)))
        print(json.dumps(rows[-1]), flush=True)
    return rows


def _plate_obs(rng, cams, half=0.06, z0=0.0, spacing=0.0007, noise=0.0008):
    """A square plate (side 2 * half) at height z0 seen from above by cams: pts, cam, frame."""
    g = np.arange(-half, half, spacing)
    X = np.stack(np.meshgrid(g, g), -1).reshape(-1, 2)
    X = np.c_[X, np.full(len(X), z0)]
    out = []
    for f, c in enumerate(cams):
        Y, vis = _rays(X + rng.normal(0, 1e-4, X.shape), c, np.tile([0, 0, 1.0], (len(X), 1)), rng, noise)
        out.append((Y, np.repeat(c[None], len(Y), 0), np.full(len(Y), f)))
    return out


def synthetic_islands(out, t=0.0025, seed=1):
    """Plate + separate pieces: ball cap (kept), flat flake 10 mm away (dropped), flake 1 mm away (touching, kept),
    a 0.2 cm^2 speck (dropped)."""
    rng = np.random.default_rng(seed)
    cams = [np.array([0.3 * np.cos(a), 0.3 * np.sin(a), 0.4]) for a in np.linspace(0, 2 * np.pi, 20, endpoint=False)]
    parts = _plate_obs(rng, cams)
    def add(X, N, label):
        for f, c in enumerate(cams):
            Y, vis = _rays(X, c, N, rng, 0.0006)
            parts.append((Y, np.repeat(c[None], len(Y), 0), np.full(len(Y), f)))
    # ball: sphere r 8 mm centred 20 mm above the plate centre... placed beside the plate edge, 12 mm gap
    u = rng.normal(size=(60000, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
    add(np.array([0.0, 0.0, 0.020]) + 0.008 * u, u, 'ball')
    # flat flake 30 x 30 mm, 10 mm above the plate, tilted 30 deg (not ball-like, not touching)
    g = np.arange(-0.015, 0.015, 0.0006); Q = np.stack(np.meshgrid(g, g), -1).reshape(-1, 2)
    R = np.array([[1, 0, 0], [0, np.cos(0.5), -np.sin(0.5)], [0, np.sin(0.5), np.cos(0.5)]])
    Xf = np.c_[Q, np.zeros(len(Q))] @ R.T + np.array([0.035, 0.035, 0.016]); Nf = np.tile(R[:, 2], (len(Q), 1))
    add(Xf, Nf, 'flake_far')
    # flake 25 x 25 mm, 1 mm above the plate surface... sitting 1 mm over the plate edge region (touching)
    g2 = np.arange(-0.0125, 0.0125, 0.0006); Q2 = np.stack(np.meshgrid(g2, g2), -1).reshape(-1, 2)
    Xt = np.c_[Q2, np.full(len(Q2), 0.0)] + np.array([-0.075, 0.0, 0.0]); Nt = np.tile([0, 0, 1.0], (len(Q2), 1))
    Xt[:, 2] = 0.001 + 0.0 * Xt[:, 0]
    add(Xt, Nt, 'flake_touch')                                           # 1 mm above, beyond the plate edge x<-60
    # speck 4 x 5 mm, far
    g3 = np.arange(0, 0.004, 0.0005); Q3 = np.stack(np.meshgrid(g3, g3 * 1.25), -1).reshape(-1, 2)
    add(np.c_[Q3, np.zeros(len(Q3))] + np.array([-0.04, -0.04, 0.03]), np.tile([0, 0, 1.0], (len(Q3), 1)), 'speck')
    obs = dict(pts=np.concatenate([p[0] for p in parts]), cam=np.concatenate([p[1] for p in parts]),
               frame=np.concatenate([p[2] for p in parts]))
    sh = shell_sheet(obs)
    isl = sh['rep'].get('islands', {})
    m, rep = solidify_sheet(sh, t, return_report=True)
    b = kit_check(m, f'islands_t{t * 1e3:.1f}', out)
    balls = isl.get('balls', [])
    dropped = isl.get('dropped', [])
    # verdicts: ball kept near (0,0,20mm); far flake dropped as not_ball; touch flake in the body group
    S = trimesh.sample.sample_surface(m, 100000, seed=0)[0]
    has_ball = bool(np.any(np.linalg.norm(S - [0, 0, 0.020], axis=1) < 0.010))
    has_far = bool(np.any(np.linalg.norm(S - [0.035, 0.035, 0.016], axis=1) < 0.008))
    has_touch = bool(np.any(np.linalg.norm(S[:, :2] - [-0.075, 0.0], axis=1) < 0.006))
    has_speck = bool(np.any(np.linalg.norm(S - [-0.038, -0.0375, 0.03], axis=1) < 0.004))
    row = dict(case='synthetic_islands', t_mm=t * 1e3, components=isl.get('components'), kept_balls=len(balls),
               balls=balls, dropped=dropped[:6], dropped_area_cm2=isl.get('dropped_area_cm2'), has_ball=has_ball,
               has_far_flake=has_far, has_touch_flake=has_touch, has_speck=has_speck, faces=rep['faces'],
               watertight=rep['watertight'], bodies=rep['bodies'], budget=b,
               ok=bool(has_ball and not has_far and has_touch and not has_speck and b['weld_only'] and b['watertight']))
    print(json.dumps(row, default=str), flush=True)
    return [row]


def synthetic_patch(out, t=0.0025, seed=2):
    """surface_patch with a host: a cylinder (r 40 mm, h 100 mm) with a fin (40 x 60 mm, 3 mm thick) sticking out
    radially; host = the cylinder solid. The patch must hold the fin only."""
    rng = np.random.default_rng(seed)
    R0, Hh = 0.040, 0.100
    pts, cams, frs = [], [], []
    for f, az in enumerate(np.linspace(0, 2 * np.pi, 24, endpoint=False)):
        cam = np.array([0.5 * np.cos(az), 0.5 * np.sin(az), 0.3])
        th = rng.uniform(0, 2 * np.pi, 40000); z = rng.uniform(0, Hh, 40000)
        X = np.stack([R0 * np.cos(th), R0 * np.sin(th), z], 1); n = X.copy(); n[:, 2] = 0; n /= R0
        Y, _ = _rays(X, cam, n, rng, 0.0008)
        # fin: plane y = +-1.5 mm, x in [R0, R0 + 40 mm], z in [20, 80] mm
        xs = rng.uniform(R0, R0 + 0.040, 8000); zs = rng.uniform(0.02, 0.08, 8000)
        for sgn in (1, -1):
            Xf = np.stack([xs, np.full(len(xs), sgn * 0.0015), zs], 1); nf = np.tile([0, sgn, 0.0], (len(xs), 1))
            Yf, _ = _rays(Xf, cam, nf, rng, 0.0008)
            Y = np.vstack([Y, Yf])
        pts.append(Y); cams.append(np.repeat(cam[None], len(Y), 0)); frs.append(np.full(len(Y), f))
    obs = dict(pts=np.concatenate(pts), cam=np.concatenate(cams), frame=np.concatenate(frs))
    host = trimesh.creation.cylinder(radius=R0, height=Hh, sections=128)
    host.apply_translation([0, 0, Hh / 2])
    m, rep = surface_patch(obs, None, t=t, max_faces=1500, host=host, return_report=True)
    rows = []
    if len(m.faces):
        S = trimesh.sample.sample_surface(m, 50000, seed=0)[0]
        rr = np.linalg.norm(S[:, :2], axis=1)
        near_host = float(np.mean(rr < R0 + 2 * SH.VOXEL - 1e-4))
        on_fin = float(np.mean((np.abs(S[:, 1]) < 0.006) & (S[:, 0] > R0)))
    else:
        near_host, on_fin = None, None
    b = kit_check(m, f'patch_t{t * 1e3:.1f}', out) if len(m.faces) else None
    # fin area beyond the trim (both faces + edge): ~ 2 * (40 - 4) * 60 mm^2
    fin_ref = 2 * (0.040 - 2 * SH.VOXEL) * 0.060 * 1e4
    row = dict(case='synthetic_patch', t_mm=t * 1e3, faces=rep['faces'], watertight=rep['watertight'],
               bodies=rep['bodies'], area_cm2=rep['area_cm2'], fin_ref_two_faces_cm2=round(fin_ref, 1),
               share_within_trim_of_host=near_host, share_on_fin=on_fin, host_trimmed_area_cm2=rep.get(
                   'host_trimmed_area_cm2'), budget=b,
               ok=bool(len(m.faces) and rep['watertight'] and rep['faces'] <= 1500 and near_host is not None
                       and near_host < 0.01 and on_fin > 0.98))
    print(json.dumps(row, default=str), flush=True)
    rows.append(row)
    # without a host, the patch holds the cylinder too
    m2, rep2 = surface_patch(obs, None, t=t, max_faces=4000, return_report=True)
    rows.append(dict(case='synthetic_patch_nohost', faces=rep2['faces'], watertight=rep2['watertight'],
                     area_cm2=rep2['area_cm2']))
    print(json.dumps(rows[-1]), flush=True)
    # an index subset: the fin points only (idx), with host
    S0 = obs['pts']; idx = np.flatnonzero(np.linalg.norm(S0[:, :2], axis=1) > R0 + 0.003)
    m3, rep3 = surface_patch(obs, idx, t=t, max_faces=1500, host=host, return_report=True)
    rows.append(dict(case='synthetic_patch_idx', n_idx=int(len(idx)), faces=rep3['faces'],
                     watertight=rep3['watertight'], area_cm2=rep3['area_cm2']))
    print(json.dumps(rows[-1]), flush=True)
    return rows


# ---------------------------------------------------------------------------------------------- metrics
def run_json(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'{cmd}: {r.stderr[-2000:]}')
    return [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{')]


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
    rend = [render_cam(_load_mesh(m), T[k], K) for m in meshes]
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
REP_KEYS = ('faces', 'vertices', 'watertight', 'winding_consistent', 'bodies', 'area_cm2', 'extents_cm',
            'sheet_dec_area_cm2', 'sheet_dec_area_change_pct', 'tau_v_mm_p10_50_90', 'sec_solidify',
            'min_vertex_gap_um', 'solidify_retries')
SHEET_KEYS = ('points', 'frames', 'samples', 'sheet_samples', 'two_sided_frac', 'two_sided_T_mm_p10_50_90',
              'master_samples', 'slave_samples', 'restored_samples', 'kept_pairs_both_sides', 'sheet_faces_mc',
              'sheet_faces', 'sheet_clean_removed', 'sheet_area_raw_cm2', 'sheet_area_cm2', 'islands_dropped',
              'islands_dropped_area_cm2', 'grazing_or_weak_dropped_frac', 'weak_normal_frac', 'sec_fusion',
              'sec_sheet_mc', 'sec_sheet', 'sheet_pitch_mm', 'carve_clamped_frac', 'holes_filled',
              'holes_filled_area_cm2', 'union_bodies', 'closed_area_cm2')


def real_case(ep, obj, ts, out, kw=None, tag='', render=True):
    kw = kw or {}
    os.makedirs(f'{out}/budget', exist_ok=True)
    path = obs_path(obj, ep)
    obs = load_obs(path, keys=('pts', 'cam', 'frame'))
    t0 = time.time()
    sh = shell_sheet(obs, **kw)
    sec_sheet = time.time() - t0
    isl = sh['rep'].get('islands', {})
    rows, meshes = [], []
    for t in ts:
        name = f'ep{ep}_{obj}_t{t:.1f}{tag}'
        mp = f'{out}/{name}.glb'
        t1 = time.time()
        m, rep = solidify_sheet(sh, t * 1e-3, return_report=True)
        sec = time.time() - t1
        m.export(mp)
        bp = f'{out}/budget/{name}_b4096.glb'
        b = budget(mp, bp)
        dec = rep.get('decimation', {})
        rows.append(dict(case=name, obs=path, kw=kw, t_mm=t, sec_sheet=round(sec_sheet, 1), sec_t=round(sec, 1),
                         sec_total=round(sec_sheet + sec, 1), **{k: rep.get(k) for k in REP_KEYS},
                         sheet={k: sh['rep'].get(k) for k in SHEET_KEYS},
                         islands={k: isl.get(k) for k in ('components', 'kept_balls', 'balls', 'dropped_n',
                                                          'dropped_area_cm2', 'kept_area_cm2')},
                         islands_dropped_top=isl.get('dropped', [])[:5],
                         decimation={k: dec.get(k) for k in ('sheet_faces_in', 'border_edges_in', 'sheet_faces',
                                                             'border_edges', 'clean_removed', 'post_dropped_area_cm2',
                                                             'dense_to_dec_mm_p50_95_99', 'dense_to_dec_frac_gt3mm')},
                         budget=b, mesh=mp, budget_mesh=bp))
        meshes.append(mp)
    raw = obs_path(obj, ep)
    lib = f'{LIB}/{obj}.glb'
    for p in meshes + [r['budget_mesh'] for r in rows] + [lib]:
        check_path(p)
    fid = {d['mesh']: d for d in run_json([PY, f'{SCRIPTS}/obs_fidelity.py', raw] + meshes +
                                          [r['budget_mesh'] for r in rows] + [lib])}
    fs = {d['mesh']: d for d in run_json([PY, FS_FID, raw] + meshes + [r['budget_mesh'] for r in rows] + [lib])}
    for r in rows:
        bn = os.path.basename(r['mesh']); bb = os.path.basename(r['budget_mesh'])
        r['fid'] = {k: fid[bn][k] for k in ('obs_to_mesh_mm', 'mesh_to_obs_mm', 'sum_mm')}
        r['fid_budget'] = {k: fid[bb][k] for k in ('obs_to_mesh_mm', 'mesh_to_obs_mm', 'sum_mm')}
        r['fs_frac_pct'] = fs[bn]['fs_frac_pct']; r['fs_frac_pct_budget'] = fs[bb]['fs_frac_pct']
    lb = f'{obj}.glb'
    rows.append(dict(case=f'ep{ep}_{obj}_library_v3', mesh=lib, fid={k: fid[lb][k] for k in
                     ('obs_to_mesh_mm', 'mesh_to_obs_mm', 'sum_mm')}, fs_frac_pct=fs[lb]['fs_frac_pct'],
                     area_cm2=fs[lb]['area_cm2'], watertight=fs[lb]['watertight'], bodies=fs[lb]['bodies']))
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
    p.add_argument('--ablate', default='')
    p.add_argument('--synthetic_only', action='store_true'); p.add_argument('--no_synthetic', action='store_true')
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    res = open(f'{a.out}/results.jsonl', 'a')
    def emit(rows):
        for r in rows:
            r['when'] = time.strftime('%Y-%m-%dT%H:%M:%S'); r['load_mesh'] = LOAD_MESH
            res.write(json.dumps(r, default=str) + '\n'); res.flush()
            b = r.get('budget') or {}
            print(json.dumps({k: r.get(k) for k in ('case', 't_mm', 'sec_total', 'faces', 'watertight', 'bodies',
                                                     'area_cm2', 'fid', 'fid_budget', 'fs_frac_pct', 'ok')} |
                             {'b_weld_only': b.get('weld_only'), 'b_watertight': b.get('watertight'),
                              'b_area_chg': b.get('area_change_pct')}, default=str), flush=True)
    if not a.no_synthetic:
        emit(synthetic_tube(a.out)); emit(synthetic_islands(a.out)); emit(synthetic_patch(a.out))
    if a.synthetic_only:
        return
    ts = [float(x) for x in a.ts.split(',')]
    for spec in [s for s in a.cases.split(',') if s]:
        ep, obj = spec.split(':'); ep = int(ep)
        if not os.path.isfile(obs_path(obj, ep, must_exist=False)):
            emit([dict(case=f'ep{ep}_{obj}', error='no obs file yet')]); continue
        try:
            emit(real_case(ep, obj, ts, a.out, render=not a.no_render))
        except Exception as e:                                  # record the failure and go on with the next case
            import traceback
            emit([dict(case=f'ep{ep}_{obj}', error=repr(e)[:500], tb=traceback.format_exc()[-2000:])])
    for spec in [s for s in a.ablate.split(',') if s]:
        ep, obj = spec.split(':'); ep = int(ep)
        for tag, kw in [('_sym', dict(mode='symmetric', two_sided=False)), ('_no2s', dict(two_sided=False)),
                        ('_carve', dict(carve=True))]:
            emit(real_case(ep, obj, [2.5], f'{a.out}/ablate', kw=kw, tag=tag, render=False))


if __name__ == '__main__':
    main()
