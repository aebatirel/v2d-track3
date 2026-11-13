"""G0 post-hoc diagnostic (build step B3; NOT pre-registered; dev process, tier DEV, $0, CPU). It does not change the
B.12 outcome; it separates the two things K-a / K-b mix when placement is by SAM 3D's layout only: the shape and the
placement.

  GMG_MODE=dev python -m gmg.tools.g0_diag --run RUN --bundle CLEAN_EP2_BUNDLE      (RUN = the g0_report run folder)

Written after the B.12 report showed fsv_far(c) - fsv_far(SHELL) of 0.64-0.75 on the pot runs and, in a GT-free check
of our own files, the posed meshes 4-6 cm nearer the camera than our pointmap with extents 10-17 % smaller (layout
error, not an input error: our pointmap lies on the owned points to 0.2-0.3 mm median).

For every SAM 3D run: the layout-placed mesh (as g0_report) is re-aligned to the target's owned points (largest 8 mm
component) by a trimmed ICP (gen_slot._icp: our points onto the mesh surface, 80 % trim, 40 iterations) started at the
layout placement, --variant similarity (scale free; a one-sided fit can inflate the mesh) or rigid_extent (scale from
the in-plane PCA extent ratio as gen_slot.place_by_depth, then rigid; added after the similarity variant gave lid
scales x1.32-1.38); then the same measures as g0_report (remesh M10, pack, fsv_far against
the SHELL, V2 against the partner) plus: the ICP scale, rotation and translation from the layout placement, the
trimmed residual, the extents along the owned core's PCA axes, and the mesh height above the owned points' table side
along their thinnest PCA axis (a lid-on-pot body shows as extra height). Outputs RUN/diag/summary.json and
montage_<obj>.png. Nothing is scored against scans; no scan, mocap or library file is read.
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

from gmg import guard, remesh as RM, pack as PK, score as SC  # noqa: E402

T0 = time.time()
ICP_ITERS, ICP_TRIM = 40, 0.8       # as gen_slot.place_by_depth (generic numerical, F-I2.10)


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def main():
    import trimesh
    from scipy.spatial import cKDTree
    from scipy.spatial.transform import Rotation as Rot
    from gmg import gen_slot
    from gmg.tools.g0_inputs import load_clean_bundle
    from gmg.tools.g0_report import core_points, pca_extents, render_panels
    from gmg.tools import b11_views as B11
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', required=True)
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--variant', choices=('similarity', 'rigid_extent'), default='similarity')
    a = ap.parse_args()
    if guard.mode() != 'dev':
        raise SystemExit('g0_diag: dev only')
    guard.set_run(a.run)
    start = dict(start_commit=guard._git('rev-parse', 'HEAD'))
    out = os.path.join(a.run, 'diag' if a.variant == 'similarity' else 'diag_' + a.variant)
    os.makedirs(out, exist_ok=True)
    RM.consts(); SC.consts()
    b = load_clean_bundle(os.path.realpath(a.bundle))
    with open(guard.open_input(os.path.join(a.run, 'report', 'summary.json'), 'own')) as f:
        rep = json.load(f)
    shell = {o: v['fsv_far'] for o, v in rep['shells'].items()}
    box = os.path.join(a.run, 'box', 'sam3d')
    recs = [json.loads(x) for x in open(guard.open_input(os.path.join(box, 'gen_log.jsonl'), 'own')) if x.strip()]
    recs = [r for r in recs if r.get('ok')]
    far = {o: SC.far_free_grid(b.obs(o)) for o in b.objects}
    rows = []
    for r in recs:
        t = time.time()
        o = r['obj']
        ob = b.obs(o)
        P = core_points(np.asarray(ob['pts'], np.float64)[np.asarray(ob['own']) == 0])[0]
        raw = trimesh.load(guard.open_input(os.path.join(box, r['path']), 'own'), force='mesh', process=False)
        Tm = np.asarray(r['obj_T_mesh'], np.float64)
        placed = trimesh.Trimesh(np.asarray(raw.vertices) @ Tm[:3, :3].T + Tm[:3, 3], np.asarray(raw.faces),
                                 process=False)
        G = np.asarray(trimesh.sample.sample_surface(placed, 40000, seed=0)[0])
        rng = np.random.default_rng(0)
        Ps = P[rng.choice(len(P), min(len(P), 40000), replace=False)]
        if a.variant == 'rigid_extent':
            # scale fixed by the in-plane extents (median ratio over the two major PCA axes of the owned core, as
            # gen_slot.place_by_depth), then rigid trimmed ICP: a one-sided similarity ICP can inflate the mesh
            # (our points only need to lie on part of its surface)
            cP, cG = Ps.mean(0), G.mean(0)
            UP = np.linalg.svd(Ps - cP, full_matrices=False)[2]; UG = np.linalg.svd(G - cG, full_matrices=False)[2]
            eP = np.percentile((Ps - cP) @ UP.T, 99, 0) - np.percentile((Ps - cP) @ UP.T, 1, 0)
            eG = np.percentile((G - cG) @ UG.T, 99, 0) - np.percentile((G - cG) @ UG.T, 1, 0)
            sg = float(np.median([eP[0] / eG[0], eP[1] / eG[1]]))          # mesh scale factor about its centroid
            G = cG + (G - cG) * sg
            placed = trimesh.Trimesh(cG + (np.asarray(placed.vertices) - cG) * sg, np.asarray(placed.faces),
                                     process=False)
            R, tt, s, d = gen_slot._icp(Ps, cKDTree(G), G, np.eye(3), np.zeros(3), 1.0, ICP_ITERS, ICP_TRIM,
                                        scale=False)
            s = 1.0 / sg if sg > 0 else 1.0
            s_rep = sg
        else:
            R, tt, s, d = gen_slot._icp(Ps, cKDTree(G), G, np.eye(3), np.zeros(3), 1.0, ICP_ITERS, ICP_TRIM,
                                        scale=True)
            s_rep = 1 / s
        k = d <= np.quantile(d, ICP_TRIM)
        # our points map onto the mesh by x -> s R x + t; the mesh moves onto our points by the inverse
        V = (np.asarray(placed.vertices) - tt) @ R / (s if a.variant == 'similarity' else 1.0)
        aligned = trimesh.Trimesh(V, np.asarray(placed.faces), process=False)
        mb, rinfo = RM.watertight(aligned)
        m, pinfo = PK.pack(mb, os.path.join(out, 'aligned', f"{r['tag']}_s{r['seed']}.glb"))
        fs = SC.fsv_far(m, ob, far[o])
        v2 = SC.v2(m, b, o)
        dd = fs['fsv_far'] - shell[o]
        c = P.mean(0)
        U = np.linalg.svd(P - c, full_matrices=False)[2]
        thin = U[2]
        hp = (P - c) @ thin; S = np.asarray(trimesh.sample.sample_surface(m, 40000, seed=0)[0]); hm = (S - c) @ thin
        row = dict(tag=r['tag'], seed=r['seed'], obj=o, kind=r['kind'],
                   icp=dict(variant=a.variant, scale=round(float(s_rep), 4),
                            rot_deg=round(float(np.degrees(Rot.from_matrix(R).magnitude())), 2),
                            trans_mm=round(float(np.linalg.norm(tt)) * 1e3, 1),
                            trimmed_resid_mm=round(float(d[k].mean()) * 1e3, 2),
                            resid_p90_mm=round(float(np.percentile(d, 90)) * 1e3, 2)),
                   fsv_far=round(fs['fsv_far'], 4), fsv_shell=round(shell[o], 4), fsv_diff=round(dd, 4),
                   v2_veto=bool(v2['veto']), v2=v2['partners'], would_pass=bool(dd <= 0.05 and not v2['veto']),
                   v1=pinfo['v1']['watertight'], remesh_flags=rinfo.get('flags'), pca=pca_extents(m, P),
                   thin_axis_mm=dict(owned=np.round(np.percentile(hp, [0.5, 99.5]) * 1e3, 1).tolist(),
                                     mesh=np.round(np.percentile(hm, [0.5, 99.5]) * 1e3, 1).tolist()))
        try:
            row['_panels'] = render_panels(m, P, os.path.join(a.run, 'inputs'), r)
        except Exception as e:                                          # noqa: BLE001
            if isinstance(e, guard.GuardError):
                raise
            row['_panels'] = None
            row['panel_error'] = f'{type(e).__name__}: {e}'
        rows.append(row)
        log(f"{r['tag']} s{r['seed']}: ICP scale x{row['icp']['scale']:.3f} rot {row['icp']['rot_deg']} deg trans "
            f"{row['icp']['trans_mm']} mm resid {row['icp']['trimmed_resid_mm']} mm -> fsv {fs['fsv_far']:.4f} (diff "
            f"{dd:+.4f}) V2 {'VETO' if v2['veto'] else 'ok'}; thin axis owned {row['thin_axis_mm']['owned']} mesh "
            f"{row['thin_axis_mm']['mesh']} ({time.time() - t:.0f} s)")
    summ = dict(what='G0 post-hoc diagnostic (not pre-registered; does not change the B.12 outcome)',
                icp=dict(iters=ICP_ITERS, trim=ICP_TRIM, start='layout placement', variant=a.variant,
                         scale='free' if a.variant == 'similarity' else 'in-plane PCA extent ratio, then rigid'),
                rows=[{k: v for k, v in x.items() if not k.startswith('_')} for x in rows])
    with open(os.path.join(out, 'summary.json'), 'w') as f:
        json.dump(summ, f, indent=1, default=float)
    guard.register_output(os.path.join(out, 'summary.json'))
    for o in b.objects:
        mr = [(x['_panels'], [f"{x['kind']} seed {x['seed']}: ICP x{x['icp']['scale']:.3f}, {x['icp']['rot_deg']} deg, "
                              f"{x['icp']['trans_mm']} mm | fsv {x['fsv_far']:.3f} (diff {x['fsv_diff']:+.3f}) V2 "
                              f"{'VETO' if x['v2_veto'] else 'ok'}",
                              f"thin axis mm owned {x['thin_axis_mm']['owned']} mesh {x['thin_axis_mm']['mesh']}"])
              for x in rows if x['obj'] == o and x['_panels'] is not None]
        hdr = [f"G0 ep2 {o}: POST-HOC diagnostic (not B.12): layout placement re-aligned to our owned points by a "
               f"trimmed ICP ({a.variant})", "panels: aligned mesh in the input view | owned core (grey) + mesh (green) "
               "PCA 0-1 | PCA 0-2"]
        B11.save_png(os.path.join(out, f'montage_{o}.png'), B11.montage(mr, hdr))
    guard.write_manifest(os.path.join(a.run, 'manifest_diag.json' if a.variant == 'similarity' else
                                      f'manifest_diag_{a.variant}.json'),
                         extra=dict(step='B3', what=f'G0 post-hoc diagnostic ({a.variant})', **start))
    log('done')


if __name__ == '__main__':
    main()
