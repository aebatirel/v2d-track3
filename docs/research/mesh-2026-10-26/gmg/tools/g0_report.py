"""G0 report (build step B3; PREREG B.12, with the B.9 definitions of K-a and K-b; dev process, tier DEV, $0, CPU).

  GMG_MODE=dev python -m gmg.tools.g0_report fetch  --run RUN --store-run RUN_ID      (network: HF store, not audited)
  GMG_MODE=dev python -m gmg.tools.g0_report report --run RUN --bundle CLEAN_EP2_BUNDLE (audited, no network)

fetch: copies the G0 box outputs (runs/<RUN_ID>/results/g0/: setup and job logs, sam3d/*.ply, *.json, gen_log.jsonl)
and the job inputs (runs/<RUN_ID>/inputs/) from the private HF store into RUN/box/ and RUN/inputs/ (own run files).

report: for every SAM 3D run (primary and control):
  placement  obj_T_mesh = inv(camA_T_obj[k]) camA_T_mesh from SAM 3D's metric layout only (PREREG B.12: no ICP);
  remesh     M10 remesh.watertight (1.5 mm, largest component, fit_budget 4000), pack.pack (own kit decode, V1);
  K-a / K-b  (B.9) fsv_far(c) - fsv_far(SHELL) <= 0.05 and V2 passes against the partner's samples; the SHELL is the
             route-A shell of the same clean bundle (producers/shell.py at the dev t0); K-a over the lid's primary
             runs, K-b over the pot's: at least half pass;
  also       (B.12) the placed mesh's extents along the owned points' PCA axes against the owned points' own extents
             (0.5-99.5 percentiles), the share of placed surface outside the bundle grid (fsv_far's outside_grid);
             (F-I1.10) the box's layout record, runtime, sha256s, the GT-free convention check (pointmap points to the
             posed mesh); (F-I1.9, report only) physcheck.placement over the good frames; a montage.
B.12 outcome from the primary runs only: SUPPORTED if >= 1 of 2 lid runs pass K-a and >= 1 of 2 pot runs pass K-b;
NOT SUPPORTED if no lid run passes K-a; otherwise MIXED. The controls are reported beside it and change nothing.
Nothing is scored against scans; no scan, mocap or library file is read.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from gmg import guard, gen_inputs as GI, remesh as RM, pack as PK, score as SC  # noqa: E402

T0 = time.time()
FSV_TOL = 0.05                      # PREREG B.9 K-a / K-b: fsv_far(c) - fsv_far(shell) <= 0.05


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def fetch(a):
    from huggingface_hub import snapshot_download
    guard.set_run(a.run)
    store = os.environ.get('HF_STORE', 'aebatirel/v2d-store')
    tmp = os.path.join(a.run, 'box_dl')
    p = snapshot_download(store, repo_type='dataset', local_dir=tmp,
                          allow_patterns=[f'runs/{a.store_run}/results/g0/**', f'runs/{a.store_run}/inputs/**',
                                          f'runs/{a.store_run}/*.log', f'runs/{a.store_run}/COMMIT',
                                          f'runs/{a.store_run}/run_state/**'])
    src = os.path.join(p, 'runs', a.store_run)
    import shutil
    for sub, dst in (('results/g0', 'box'), ('inputs', 'inputs')):
        s = os.path.join(src, sub)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(a.run, dst), dirs_exist_ok=True)
    for f in os.listdir(src):
        if os.path.isfile(os.path.join(src, f)):
            shutil.copy(os.path.join(src, f), os.path.join(a.run, 'box', f))
    shutil.rmtree(tmp)
    n = 0
    for root, _, files in os.walk(a.run):
        for f in files:
            if f not in guard.PROTECTED:
                guard.register_output(os.path.join(root, f)); n += 1
    guard.write_manifest(os.path.join(a.run, 'manifest_fetch.json'), extra=dict(step='B3', what='G0 fetch',
                                                                               store_run=a.store_run))
    log(f'fetched {n} files from {store} runs/{a.store_run}')


def pca_extents(mesh, P):
    """Extents of MESH (surface samples) and of the points P along P's PCA axes (0.5-99.5 percentiles)."""
    import trimesh
    c = P.mean(0)
    U = np.linalg.svd(P - c, full_matrices=False)[2]
    S, _ = trimesh.sample.sample_surface(mesh, 50000, seed=0)
    pr = lambda X: np.percentile((X - c) @ U.T, [0.5, 99.5], axis=0)  # noqa: E731
    ep, em = pr(P), pr(np.asarray(S))
    return dict(axes=U.round(4).tolist(), owned_mm=np.round((ep[1] - ep[0]) * 1e3, 1).tolist(),
                mesh_mm=np.round((em[1] - em[0]) * 1e3, 1).tolist(),
                ratio=np.round((em[1] - em[0]) / np.maximum(ep[1] - ep[0], 1e-9), 3).tolist())


def render_panels(mesh, P, inp_dir, rec, side=300):
    """Three panels: the placed mesh projected into its input view (undistorted image, pinhole K) over the RGB with the
    mask outline; two orthographic views (PCA axes 0-1 and 0-2 of the owned points) of mesh surface samples (green)
    over the owned points (grey)."""
    import cv2
    import trimesh
    from PIL import Image
    js = json.load(open(guard.open_input(os.path.join(inp_dir, rec['tag'] + '.json'), 'own')))
    rgb = np.array(Image.open(guard.open_input(os.path.join(inp_dir, js['files']['rgb']), 'own')).convert('RGB'))
    mk = np.array(Image.open(guard.open_input(os.path.join(inp_dir, js['files']['mask']), 'own'))) > 127
    K = np.array(js['K']); T = np.array(js['camA_T_obj'])
    S, _ = trimesh.sample.sample_surface(mesh, 40000, seed=0)
    S = np.asarray(S)
    X = S @ T[:3, :3].T + T[:3, 3]
    ok = X[:, 2] > 0.05
    u = (K[0, 0] * X[ok, 0] / X[ok, 2] + K[0, 2]).astype(int); v = (K[1, 1] * X[ok, 1] / X[ok, 2] + K[1, 2]).astype(int)
    img = rgb[:, :, ::-1].copy()
    inn = (u >= 0) & (u < img.shape[1]) & (v >= 0) & (v < img.shape[0])
    ov = img.copy()
    ov[v[inn], u[inn]] = (0, 255, 0)
    img = cv2.addWeighted(img, 0.5, ov, 0.5, 0)
    cs, _ = cv2.findContours(mk.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(img, cs, -1, (255, 255, 0), 2)
    ys, xs = np.nonzero(mk)
    allx = np.concatenate([xs, u[inn]]); ally = np.concatenate([ys, v[inn]])
    cx, cy = (allx.min() + allx.max()) / 2, (ally.min() + ally.max()) / 2
    s = max(allx.max() - allx.min(), ally.max() - ally.min()) * 1.3
    x0, y0 = int(max(cx - s / 2, 0)), int(max(cy - s / 2, 0))
    x1, y1 = int(min(cx + s / 2, img.shape[1])), int(min(cy + s / 2, img.shape[0]))
    p1 = cv2.resize(img[y0:y1, x0:x1], (side, side), interpolation=cv2.INTER_AREA)
    c = P.mean(0)
    U = np.linalg.svd(P - c, full_matrices=False)[2]
    A, B = (P - c) @ U.T, (S - c) @ U.T
    lim = max(np.abs(np.percentile(A, [0.5, 99.5], axis=0)).max(), np.abs(B).max()) * 1.1
    outs = []
    for i, j in ((0, 1), (0, 2)):
        pan = np.full((side, side, 3), 255, np.uint8)
        for Q, col in ((A, (150, 150, 150)), (B, (0, 170, 0))):
            q = Q[np.random.default_rng(0).choice(len(Q), min(len(Q), 30000), replace=False)]
            pu = ((q[:, i] / lim + 1) * side / 2).astype(int); pv = ((1 - (q[:, j] / lim + 1) / 2) * side).astype(int)
            m = (pu >= 0) & (pu < side) & (pv >= 0) & (pv < side)
            pan[pv[m], pu[m]] = col
        cv2.putText(pan, f'PCA {i}-{j}, half-width {lim * 1e3:.0f} mm', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (0, 0, 0), 1, cv2.LINE_AA)
        outs.append(pan)
    return [p1] + outs


def report(a):
    import trimesh
    from gmg.tools.g0_inputs import load_clean_bundle
    from gmg.tools import b11_views as B11
    from gmg.producers import shell as P_SHELL
    from gmg.run_episode import _t0
    guard.set_run(a.run)
    start = dict(start_commit=guard._git('rev-parse', 'HEAD'))
    out = os.path.join(a.run, 'report')
    os.makedirs(out, exist_ok=True)
    RM.consts(); SC.consts(); GI.consts()
    b = load_clean_bundle(os.path.realpath(a.bundle))
    t0, t0src = _t0()
    box = os.path.join(a.run, 'box', 'sam3d')
    inp = os.path.join(a.run, 'inputs')
    recs = []
    with open(guard.open_input(os.path.join(box, 'gen_log.jsonl'), 'own')) as f:
        for line in f:
            r = json.loads(line)
            if r.get('ok'):
                recs.append(r)
    log(f'{len(recs)} ok SAM 3D records; bundle {b.meta["tier"]} {b.objects}; t0 {t0 * 1e3:.2f} mm ({t0src})')
    shells, far = {}, {}
    for o in b.objects:
        t = time.time()
        c = P_SHELL.produce(dict(bundle=b, obj=o, t0=t0))[0]
        m, pinfo = PK.pack(c.mesh, os.path.join(out, 'shell', f'{o}.glb'))
        far[o] = SC.far_free_grid(b.obs(o))
        fs = SC.fsv_far(m, b.obs(o), far[o])
        shells[o] = dict(cid=c.cid, fsv_far=fs['fsv_far'], outside_grid=fs['outside_grid'], faces=pinfo['faces'],
                         v1=pinfo['v1']['watertight'], v2=SC.v2(m, b, o))
        log(f'shell {o}: fsv_far {fs["fsv_far"]:.4f} ({time.time() - t:.0f} s)')
    rows = []
    for r in recs:
        t = time.time()
        o = r['obj']
        ob = b.obs(o)
        P = np.asarray(ob['pts'], np.float64)[np.asarray(ob['own']) == 0]
        raw = trimesh.load(guard.open_input(os.path.join(box, r['path']), 'own'), force='mesh', process=False)
        Tm = np.asarray(r['obj_T_mesh'], np.float64)
        placed = trimesh.Trimesh(np.asarray(raw.vertices) @ Tm[:3, :3].T + Tm[:3, 3], np.asarray(raw.faces),
                                 process=False)
        mb, rinfo = RM.watertight(placed)
        glb = os.path.join(out, 'placed', f"{r['tag']}_s{r['seed']}.glb")
        m, pinfo = PK.pack(mb, glb)
        fs = SC.fsv_far(m, ob, far[o])
        v2 = SC.v2(m, b, o)
        d = fs['fsv_far'] - shells[o]['fsv_far']
        k_pass = bool(d <= FSV_TOL and not v2['veto'])
        sc = np.cbrt(abs(np.linalg.det(Tm[:3, :3])))
        row = dict(tag=r['tag'], seed=r['seed'], obj=o, kind=r['kind'], k=r['k'], j=r['j'],
                   fsv_far=round(fs['fsv_far'], 4), fsv_shell=round(shells[o]['fsv_far'], 4), fsv_diff=round(d, 4),
                   outside_grid=round(fs['outside_grid'], 4), v2_veto=bool(v2['veto']), v2=v2['partners'],
                   K_pass=k_pass, v1=pinfo['v1']['watertight'], faces=pinfo['faces'],
                   remesh=dict((k, rinfo.get(k)) for k in ('coverage', 'components', 'kept_volume_share', 'flags',
                                                            'faces_mc', 'decode_watertight', 'volume_m3')),
                   layout_scale_m=round(float(sc), 4), pca=pca_extents(m, P),
                   box=dict((k, r.get(k)) for k in ('sec', 'gpu_peak_gb', 'faces_raw', 'pointmap_to_mesh_mm',
                                                     'closed_form_max_m', 'affine_fit_max_m', 'layout', 'camA_T_mesh',
                                                     'obj_T_mesh', 'camA_T_obj', 'sha256_inputs', 'sha256_mesh',
                                                     'extent_cam_m')))
        try:
            from gmg import physcheck
            row['placement_FI19'] = {k: v for k, v in physcheck.placement(m, b, o).items() if k != 'per_frame_t_mm'}
        except Exception as e:                                          # noqa: BLE001
            if isinstance(e, guard.GuardError):
                raise
            row['placement_FI19'] = dict(error=f'{type(e).__name__}: {e}')
        try:
            row['_panels'] = render_panels(m, P, inp, r)
        except Exception as e:                                          # noqa: BLE001
            if isinstance(e, guard.GuardError):
                raise
            row['_panels'] = None
            row['panel_error'] = f'{type(e).__name__}: {e}'
        rows.append(row)
        log(f"{r['tag']} s{r['seed']}: fsv {fs['fsv_far']:.4f} (shell {shells[o]['fsv_far']:.4f}, diff {d:+.4f}) V2 "
            f"{'VETO' if v2['veto'] else 'ok'} -> {'PASS' if k_pass else 'fail'}; scale {sc:.3f} m; pca ratio "
            f"{row['pca']['ratio']} ({time.time() - t:.0f} s)")
    lid = [x for x in rows if x['kind'] == 'primary' and x['obj'] == 'white_pot_lid']
    pot = [x for x in rows if x['kind'] == 'primary' and x['obj'] == 'white_pot']
    n_lid, n_pot = sum(x['K_pass'] for x in lid), sum(x['K_pass'] for x in pot)
    Ka = bool(lid) and n_lid >= len(lid) / 2
    Kb = bool(pot) and n_pot >= len(pot) / 2
    if len(lid) < 2 or len(pot) < 2:
        outcome = 'INCOMPLETE'
    elif n_lid >= 1 and n_pot >= 1:
        outcome = 'SUPPORTED'
    elif n_lid == 0:
        outcome = 'NOT SUPPORTED'
    else:
        outcome = 'MIXED'
    ctrl = {o: dict(n=sum(1 for x in rows if x['kind'] == 'control' and x['obj'] == o),
                    pass_=sum(x['K_pass'] for x in rows if x['kind'] == 'control' and x['obj'] == o))
            for o in b.objects}
    summ = dict(prereg='B.12', bundle=os.path.realpath(a.bundle), bundle_tier=b.meta['tier'], process_tier='DEV',
                flags=['dev_process_clean_bundle'], t0_mm=round(t0 * 1e3, 4), fsv_tol=FSV_TOL, shells=shells,
                K_a=dict(runs=len(lid), passed=n_lid, pass_=Ka), K_b=dict(runs=len(pot), passed=n_pot, pass_=Kb),
                outcome=outcome, controls=ctrl,
                rows=[{k: v for k, v in x.items() if not k.startswith('_')} for x in rows])
    with open(os.path.join(out, 'summary.json'), 'w') as f:
        json.dump(summ, f, indent=1, default=float)
    guard.register_output(os.path.join(out, 'summary.json'))
    for o in b.objects:
        mr = []
        for x in [y for y in rows if y['obj'] == o]:
            if x['_panels'] is None:
                continue
            lines = [f"{x['kind']} k={x['k']} seed {x['seed']}: fsv_far {x['fsv_far']:.3f} (shell {x['fsv_shell']:.3f},"
                     f" diff {x['fsv_diff']:+.3f}) V2 {'VETO' if x['v2_veto'] else 'ok'} -> "
                     f"{'PASS' if x['K_pass'] else 'fail'}",
                     f"scale {x['layout_scale_m']:.3f} m | PCA extent ratio mesh/owned {x['pca']['ratio']} | "
                     f"outside grid {x['outside_grid']:.2f}"]
            mr.append((x['_panels'], lines))
        hdr = [f"G0 ep2 {o}: SAM 3D with our depth pointmap, placed by its layout only, remeshed (M10)",
               "panels: placed mesh projected into the input view (green; cyan = input mask) | owned points (grey) "
               "and mesh (green), PCA 0-1 | PCA 0-2"]
        B11.save_png(os.path.join(out, f'montage_{o}.png'), B11.montage(mr, hdr))
    guard.write_manifest(os.path.join(a.run, 'manifest.json'), extra=dict(step='B3', prereg='B.12', outcome=outcome,
                                                                         **start))
    log(f'B.12: K-a {n_lid}/{len(lid)} K-b {n_pot}/{len(pot)} -> {outcome}; controls {ctrl}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('fetch', 'report'))
    ap.add_argument('--run', required=True)
    ap.add_argument('--store-run', dest='store_run')
    ap.add_argument('--bundle')
    a = ap.parse_args()
    if guard.mode() != 'dev':
        raise SystemExit('g0_report: dev only (GMG_MODE=dev)')
    fetch(a) if a.cmd == 'fetch' else report(a)


if __name__ == '__main__':
    main()
