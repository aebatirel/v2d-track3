"""G0 inputs (build step B3, PREREG B.11 re-run and B.12 inputs; dev process, tier DEV, $0, CPU).

PREREG B.12: "Bundle: ep2, clean if B4 has run". B4 has run, so this reads the CLEAN ep2 bundle of the B4 run through
the dev-only role clean_run (as interlock.load_bundle_any). M9 (gen_inputs.choose_views, Phase-1 exclusive masks,
SAM2 refinement on the CPU) chooses the views of both tracked objects; PREREG B.11 is re-run on them (no partner pixel
in any chosen mask, before and after SAM2; separated-mode views are separated frames). B.11 must pass before any SAM 3D
input is written.

Runs written (PREREG B.12, F-I1.10 records):
  primary  lid = M9's first view (best separated, hand-free), pot = M9's first view (best lid-off, separated), with
           the final exclusive mask;
  control  (report only; not part of the B.12 outcome) per target, a contact frame of the pair with 3-D contact
           (census d3 <= 10 mm) whose naive mask is hand-free (else the smallest hand share <= 25 %) with valid depth
           >= 0.6, largest target footprint, ties to the earliest frame; naive mask = target footprint minus hand
           pixels (MediaPipe capsules, depth occluders outside the partner's footprint), partner pixels kept, largest
           component, no SAM2: the analogue of the 29 Oct contact-frame input.
Each run gets: the undistorted cam_a frame (RGB, pinhole K = cam_a K), its mask, the pointmap of our FoundationStereo
depth of frame k in that camera (NaN outside the mask, and where the depth lies more than 20 mm behind the target's
projected front surface or in a filled hole of its footprint), camA_T_obj, sha256s (gen_inputs.sam3d_input).

Outputs in RUN/g0/: inputs/<tag>.{png,_mask.png,_pointmap.npz,json}, report.json, table.json, montage_<obj>.png,
jobs.json (the list of SAM 3D jobs: tag, seeds). Nothing is scored; no scan, mocap or library file is read.

Usage (dev only):
  GMG_MODE=dev python -m gmg.tools.g0_inputs --run RUN --bundle DATA/gmg/runs/<b4 run>/bundle/public/ep2
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

from gmg import guard, bundle as BU, gen_inputs as GI  # noqa: E402
from gmg.tools import b11_views as B11  # noqa: E402

T0 = time.time()
SEEDS = (0, 1)                      # PREREG B.12: seeds 0 and 1
CONTACT_3D_M = 0.010                # PREREG A.6 contact: 3-D gap <= 10 mm (control frames: lid seated on the pot)


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def load_clean_bundle(path):
    """bundle.load_bundle for a clean run's bundle folder read by a dev process (role clean_run, tier DEV); the same
    reads as interlock.load_bundle_any."""
    meta = guard.load_json(os.path.join(path, 'episode.json'), 'clean_run')
    tp = meta['tracks']['path']
    guard.open_input(tp, 'tracks', expect_sha256=meta['tracks']['sha256'])
    poses = guard.load_npz(tp, 'tracks')
    obs = {}
    for o in meta['objects']:
        z = guard.load_npz(os.path.join(path, f'{o}.npz'), 'clean_run', keys=list(BU.BUNDLE_KEYS))
        d = {k: z[k] for k in BU.BUNDLE_KEYS}
        d['vox'] = float(d['vox']); d['args'] = str(d['args'])
        obs[o] = d
    return BU.Bundle(meta, obs, poses, path=path)


def naive_layers(b, k, obj, geo, hands, depth, c):
    """Naive mask of OBJ at frame k: target footprint S minus hand pixels (MediaPipe capsules in front of it, and depth
    occluders outside every partner's footprint), partner pixels KEPT (the analogue of the 29 Oct input, whose mask was
    the target's full silhouette with the partner inside it); largest connected component. Returns (mask, layers, parts,
    stats)."""
    from scipy.ndimage import label
    L = GI.frame_layers(b, k, geo, hands, depth, c)
    S = L.fp[obj]
    Pfp = GI.partner_union(L, obj, dilate=True)
    Hc = L.hand & (L.hand_z <= L.zf[obj]) & S
    O = GI.occluders(L, obj, c)
    Oc = (O & S & ~Pfp) if O is not None else np.zeros_like(S)
    H = Hc | Oc
    M = S & ~H
    lab, n = label(M)
    if n > 1:
        sz = np.bincount(lab.ravel()); sz[0] = 0
        M = lab == int(np.argmax(sz))
    nS = int(S.sum())
    st = dict(k=int(k), area_fp=nS, area=int(M.sum()), hand_share=round(float(H.sum()) / max(nS, 1), 4),
              partner_share=round(float((S & Pfp).sum()) / max(nS, 1), 4),
              depth_share=None if L.valid is None else round(float((M & L.valid).sum()) / max(int(M.sum()), 1), 4))
    return M, L, dict(S=S, Pd=Pfp, Sp=S, H=H, Hc=Hc, Oc=Oc), st


def control_view(b, obj, table, census, geo, hands, depth, c):
    """The control frame of OBJ (module docstring rule): census contact frames of the pair with 3-D contact (d3 <= 10
    mm), in order of decreasing target footprint (ties: earlier frame); the first whose naive mask is hand-free with
    valid depth >= 0.6 is taken; if none is hand-free, the smallest hand share <= 25 % (ties: larger footprint, earlier
    frame). Returns (View in mode 'contact_naive' or None, info)."""
    partners = b.partners(obj)
    rows = {r['k']: r for r in table if r['area_fp'] > 0}
    d3, contact = {}, None
    for p in partners:
        cs = census[f'{obj}|{p}']
        fr = [int(f) for f in cs['frames']]
        dd = dict(zip(fr, cs['d3_mm']))
        cset = set(int(f) for f in cs['contact'])
        contact = cset if contact is None else contact & cset
        for f in fr:
            d3[f] = min(d3.get(f, np.inf), dd[f] if dd[f] is not None else np.inf)
    cand = sorted([k for k in rows if k in (contact or set()) and d3.get(k, np.inf) <= CONTACT_3D_M * 1e3],
                  key=lambda k: (-rows[k]['area_fp'], k))
    seen, pick = [], None
    for k in cand:
        _, _, _, st = naive_layers(b, k, obj, geo, hands, depth, c)
        seen.append(st)
        if st['hand_share'] == 0 and st['depth_share'] is not None and st['depth_share'] >= c['depth_min']:
            pick = st
            break
    if pick is None:
        ok = [s for s in seen if s['hand_share'] <= c['hands_max'] and s['depth_share'] is not None
              and s['depth_share'] >= c['depth_min']]
        pick = min(ok, key=lambda s: (s['hand_share'], -s['area_fp'], s['k'])) if ok else None
    info = dict(pool=len(cand), examined=len(seen), hand_free_found=bool(pick and pick['hand_share'] == 0))
    if pick is None:
        return None, info
    r = rows[pick['k']]
    v = GI.View(obj=obj, k=int(r['k']), j=int(r['j']), mode='contact_naive', dir=r['dir'], area=int(pick['area']),
                hand_share=float(pick['hand_share']), depth_share=float(pick['depth_share']),
                partner_share=float(pick['partner_share']), rank=0)
    info.update(d3_mm=round(float(d3[v.k]), 2), naive=pick)
    return v, info


def naive_mask(b, v, geo, hands, depth, c):
    M, L, q, st = naive_layers(b, v.k, v.obj, geo, hands, depth, c)
    info = dict(k=v.k, j=GI.colour_frame(v, geo), projected_area=int(q['S'].sum()), final_area=int(M.sum()),
                refined=False, flags=['naive_mask'], hand_share=st['hand_share'],
                partner_px_in_mask=int((M & GI.partner_union(L, v.obj, dilate=False)).sum()))
    return M, dict(info=info, layers=L, parts=q, projected=M)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', required=True)
    ap.add_argument('--bundle', required=True, help='clean bundle folder of ep2 (B4 run)')
    ap.add_argument('--depth', default=None, help='depth cache (role depth); default DATA/data/depth/ep<N>/...')
    ap.add_argument('--sam2', default='sam2.1-hiera-tiny')
    a = ap.parse_args()
    if guard.mode() != 'dev':
        raise SystemExit('g0_inputs: dev only (GMG_MODE=dev): it reads a clean bundle through role clean_run')
    import cv2
    guard.set_run(a.run)
    start = dict(start_commit=guard._git('rev-parse', 'HEAD'),
                 start_code_dirty_files=(guard._git('status', '--porcelain', '--', *[
                     os.path.relpath(d, guard.CFG['repo']) for d in guard.CODE_DIRS]) or '').splitlines())
    out = os.path.join(a.run, 'g0')
    os.makedirs(out, exist_ok=True)
    D = guard.CFG['data']
    c = GI.consts()
    geo = GI.camera_geometry(os.path.join(D, 'data', 'calib.json'))
    t = time.time()
    b = load_clean_bundle(os.path.realpath(a.bundle))
    ep = int(b.meta['ep'])
    log(f'ep{ep}: clean bundle (tier {b.meta["tier"]}, run {os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(a.bundle)))))}) '
        f'{time.time() - t:.0f} s, objects {b.objects}')
    hands = guard.load_npz(os.path.join(D, 'data', 'sweep', f'ep{ep}', 'hands.npz'), 'dev_hands')
    if int(hands['a_offset']) != geo.a_offset:
        raise ValueError('a_offset mismatch')
    dpath = a.depth or os.path.join(D, 'data', 'depth', f'ep{ep}', 'depths_fs0.5.npy')
    depth = np.load(guard.open_input(dpath, 'depth'), mmap_mode='r')
    vpath = os.path.join(D, 'data', 'store', f'ep{ep}_a.mp4')
    nv = B11.video_len(vpath)
    census = b.meta['contact']
    t = time.time()
    table = GI.frame_table(b, None, geo, hands, depth, n_video=nv, objs=b.objects)
    log(f'frame table {time.time() - t:.0f} s ({ {o: len(v) for o, v in table.items()} } rows)')
    t = time.time()
    refiner = GI.Sam2Refiner(os.path.join(guard.CFG['weights'], a.sam2), geo)
    log(f'SAM2 {a.sam2} loaded in {time.time() - t:.0f} s')
    picks, ctrl = {}, {}
    for o in b.objects:
        picks[o] = GI.choose_views(b, o, census, table=table[o])
        ctrl[o] = control_view(b, o, table[o], census, geo, hands, depth, c)
    js = {GI.colour_frame(v, geo) for o in b.objects for v in picks[o][0][:1]}
    js |= {GI.colour_frame(ctrl[o][0], geo) for o in b.objects if ctrl[o][0] is not None}
    frames, _ = B11.read_frames(vpath, js)
    maps = GI.undistort_maps(geo)
    rep = dict(ep=ep, bundle=os.path.realpath(a.bundle), bundle_tier=b.meta['tier'], objects=b.objects,
               a_offset=geo.a_offset, video_frames=nv, depth=os.path.relpath(dpath, D), depth_frames=int(len(depth)),
               partner_dilate_px_cam_a=GI.partner_dilate_px(geo), refine=refiner.name, seeds=list(SEEDS),
               census={k: dict(frames=len(v['frames']), contact=len(v['contact']), separated=len(v['separated']),
                               sep3d=len(v['sep3d']), overlap2d=v['overlap2d'], j_mm=v.get('j_mm'),
                               band_mm=v.get('band_mm')) for k, v in census.items()},
               sigma_mm=b.meta.get('sigma_mm'), targets={}, jobs=[])
    b11_ok = True
    rec_inputs = []
    for o in b.objects:
        views, crep = picks[o]
        sep = GI.separated_frames(census, o, b.partners(o))
        rows, vrecs = [], []
        todo = []
        if views:
            todo.append(('primary', views[0]))
        else:
            crep['flags'].append('no_view_g0')
        cv_, cinfo = ctrl[o]
        crep['control'] = cinfo
        if cv_ is not None:
            todo.append(('control', cv_))
        for kind, v in todo:
            img = frames[GI.colour_frame(v, geo)]
            if kind == 'primary':
                F, res = GI.masks(v, b, img, geo=geo, hands=hands, depth=depth, refine=refiner)
            else:
                F, res = naive_mask(b, v, geo, hands, depth, c)
            res['obj'] = o
            vr = dict(kind=kind, view=dict(k=v.k, j=v.j, mode=v.mode, rank=v.rank, area=v.area,
                                           hand_share=v.hand_share, depth_share=v.depth_share,
                                           partner_share=v.partner_share), masks=res['info'])
            if kind == 'primary':
                t_proj = GI.partner_pixel_test(res['projected'], b, o, v.k, geo, layers=res['layers'])
                t_fin = GI.partner_pixel_test(F, b, o, v.k, geo, layers=res['layers'])
                hand_in = int((F & res['parts']['H']).sum())
                sep_ok = (v.mode != 'separated') or sep is None or v.k in sep
                ok = bool(t_proj['pass'] and t_fin['pass'] and sep_ok and hand_in == 0 and F.any())
                b11_ok &= ok
                vr.update(b11_projected=t_proj, b11_final=t_fin, hand_px_in_final=hand_in,
                          separated_frame=None if sep is None else bool(v.k in sep), separated_ok=sep_ok, b11_pass=ok)
                head = f"B.11 partner pts {t_fin['points_inside']} px {t_fin['footprint_inside']} gap " \
                       f"{t_fin['min_dist_px']} px | {'PASS' if ok else 'FAIL'}"
            else:
                t_fin = GI.partner_pixel_test(F, b, o, v.k, geo, layers=res['layers'])
                vr.update(partner_in_mask=t_fin)
                head = f"control (naive mask): partner pts in mask {t_fin['points_inside']}, footprint px " \
                       f"{t_fin['footprint_inside']}"
            tag = f'ep{ep}_{o}_{kind}_k{v.k}'
            inp = GI.sam3d_input(v, b, img, F, geo=geo, depth=depth, maps=maps, zfront=res['layers'].zf[o])
            vr['sam3d_input'] = dict(tag=tag, **inp['stats'])
            vrecs.append(vr)
            rec_inputs.append((tag, inp, dict(ep=ep, obj=o, kind=kind, k=v.k, j=v.j, mode=v.mode,
                                              partners=b.partners(o), seeds=list(SEEDS),
                                              mask_info={k_: res['info'].get(k_) for k_ in (
                                                  'projected_area', 'final_area', 'refined', 'flags',
                                                  'refined_iou_projected')})))
            lines = [f"{kind}: k={v.k} (colour {v.j}) {v.mode} | area {v.area} px | hand {100 * v.hand_share:.0f}% "
                     f"| depth {100 * v.depth_share:.0f}% | partner overlap {100 * v.partner_share:.0f}%",
                     f"{head} | pointmap valid {100 * inp['stats']['pointmap_valid_share']:.0f}% of the mask"]
            rows.append((B11.panels(img, F, res, geo), lines))
        crep['g0_views'] = vrecs
        rep['targets'][o] = crep
        header = [f"G0 ep{ep} target {o} | partners {','.join(b.partners(o))} | M9 mode {crep['mode']} | "
                  f"{crep['n_views']} M9 view(s), flags {','.join(crep['flags']) or '-'}",
                  'rows: primary (M9 first view, exclusive mask, SAM2 trim) | control (contact frame, naive mask)',
                  'panels: overlay (green target, red partner, blue hand, orange occluder) | input | valid depth']
        png = os.path.join(out, f'montage_{o}.png')
        B11.save_png(png, B11.montage(rows, header))
        log(f'{o}: views {[(x["kind"], x["view"]["k"]) for x in vrecs]} B.11 primary '
            f'{[x.get("b11_pass") for x in vrecs if x["kind"] == "primary"]}')
    rep['b11_pass'] = bool(b11_ok)
    if b11_ok:
        idir = os.path.join(out, 'inputs')
        for tag, inp, meta in rec_inputs:
            r = GI.write_sam3d_input(idir, tag, inp, meta)
            rep['jobs'].append(dict(tag=tag, seeds=list(SEEDS), kind=meta['kind'], obj=meta['obj'], k=meta['k'],
                                    sha256=r['sha256']))
        with open(os.path.join(out, 'jobs.json'), 'w') as f:
            json.dump(rep['jobs'], f, indent=1)
        guard.register_output(os.path.join(out, 'jobs.json'))
    else:
        log('B.11 FAILED on the clean bundle: no SAM 3D input written (PREREG B.11: G0 stops before SAM 3D)')
    for name, obj in (('report', rep), ('table', table)):
        p = os.path.join(out, f'{name}.json')
        with open(p, 'w') as f:
            json.dump(obj, f, indent=1 if name == 'report' else None, default=float)
        guard.register_output(p)
    guard.write_manifest(os.path.join(a.run, 'manifest.json'), extra=dict(step='B3', prereg='B.11 (clean ep2) + '
                                                                         'B.12 inputs', b11_pass=rep['b11_pass'],
                                                                         **start))
    log(f"B.11 on the clean ep2 bundle: {'PASS' if b11_ok else 'FAIL'}; jobs {[j['tag'] for j in rep['jobs']]}")


if __name__ == '__main__':
    main()
