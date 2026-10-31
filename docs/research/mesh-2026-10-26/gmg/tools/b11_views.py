"""PREREG B.11 (build step B2, dev only, $0): generator views and Phase-1 exclusive masks on the CPU.

For each episode (default 2, 11, 26): the dev bundle (bundle.from_obs_all: obs_all + tracks), the census of the
bundle, MediaPipe hands (role dev_hands, dev only), the FoundationStereo depth (role depth) and the colour video
(role video). gen_inputs chooses the views of every tracked object and builds the exclusive masks; SAM2 refinement
runs if --refine sam2 (CPU, weights in GMG_WEIGHTS_ROOT). B.11 checks per chosen view:
  (1) no partner pixel inside the target mask (every partner owned point projected one by one, and every partner
      footprint pixel), on the projected mask (after closing and filling) and on the final mask (after refinement);
  (2) a view chosen in separated mode is a separated frame of the census.
Outputs in RUN/b11/ep<N>/: report.json, table.json (per-frame rows), <obj>.png (montage of the chosen views: overlay,
generator input, valid depth). Nothing is scored; no scan, mocap or library file is read.

Usage (dev only):
  GMG_MODE=dev python -m gmg.tools.b11_views --run RUN [--eps 2,11,26] [--refine sam2|none]
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

T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def read_frames(path, js):
    """Colour frames J (set of indices) of the video at PATH, decoded sequentially (seeking is not frame-exact)."""
    import cv2
    rp = guard.open_input(path, 'video')
    cap = cv2.VideoCapture(rp)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out, want, j = {}, set(int(x) for x in js), 0
    while want and j <= max(want):
        ok, img = cap.read()
        if not ok:
            break
        if j in want:
            out[j] = img
        j += 1
    cap.release()
    return out, n


def video_len(path):
    import cv2
    rp = guard.open_input(path, 'video')
    cap = cv2.VideoCapture(rp)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return n


# ------------------------------------------------------------------------------------------------ montage
def _tint(img, m, col, a):
    out = img.astype(np.float32)
    out[m] = (1 - a) * out[m] + a * np.asarray(col, np.float32)
    return out.astype(np.uint8)


def _contour(img, m, col, th=2):
    import cv2
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(img, cs, -1, col, th)
    return img


def _label(img, lines, scale=0.5):
    import cv2
    y = 16
    for s in lines:
        cv2.putText(img, s, (5, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, s, (5, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)
        y += 18
    return img


def panels(img, F, res, geo, inpainted=None, side=300):
    """Three square panels of one view: overlay, generator input, valid depth inside the mask."""
    import cv2
    L, q, M = res['layers'], res['parts'], res['projected']
    x0, y0, x1, y1 = GI.crop_box(F if F.any() else q['S'], geo, pad=0.35)
    obj = res['obj']
    Pfp = GI.partner_union(L, obj, dilate=False)
    ov = img.copy()
    ov = _tint(ov, Pfp, (0, 0, 255), 0.45)                    # partner footprint: red
    ov = _tint(ov, q['Hc'], (255, 0, 0), 0.45)                # MediaPipe hand capsules in front of the target: blue
    ov = _tint(ov, q['Oc'], (0, 165, 255), 0.55)              # depth occluders (> 20 mm in front): orange
    ov = _tint(ov, F, (0, 255, 0), 0.30)                      # final target mask: green
    _contour(ov, q['Pd'], (0, 0, 255), 2)                     # dilated partner border
    if res['info'].get('refined'):
        _contour(ov, M, (255, 255, 0), 1)                     # projected mask: cyan
    _contour(ov, F, (0, 255, 0), 2)
    for (x, y) in res['info'].get('pos', []):
        cv2.circle(ov, (int(x), int(y)), 6, (0, 255, 0), -1)
    for (x, y) in res['info'].get('neg', []):
        cv2.circle(ov, (int(x), int(y)), 6, (0, 0, 255), -1)
    base = inpainted if inpainted is not None else img
    gi = np.full_like(img, 128)
    gi[F] = base[F]
    if inpainted is not None:                                 # contact mode: show the inpainted context too
        gi = (0.5 * inpainted.astype(np.float32) + 0.5 * gi.astype(np.float32)).astype(np.uint8)
        gi[F] = base[F]
        _contour(gi, F, (0, 255, 0), 2)
    dep = np.zeros_like(img)
    if L.valid is not None:
        V = F & L.valid
        z = L.depth_z
        if V.any():
            zz = z[V]
            lo, hi = np.percentile(zz, 2), np.percentile(zz, 98)
            g = np.clip((z - lo) / max(hi - lo, 1e-3), 0, 1)
            cm = cv2.applyColorMap((255 * (1 - np.nan_to_num(g))).astype(np.uint8), cv2.COLORMAP_TURBO)
            dep[V] = cm[V]
        dep[F & ~L.valid] = (255, 0, 255)                     # invalid depth inside the mask: magenta
    out = []
    for im in (ov, gi, dep):
        c = im[y0:y1, x0:x1]
        out.append(cv2.resize(c, (side, side), interpolation=cv2.INTER_AREA))
    return out


def montage(rows, header, side=300):
    import cv2
    W = 3 * side
    head = np.zeros((18 * len(header) + 8, W, 3), np.uint8)
    _label(head, header, 0.42)
    body = [head]
    for pnl, lines in rows:
        body.append(_label(np.zeros((40, W, 3), np.uint8), lines, 0.42))
        body.append(np.concatenate(pnl, 1))
        body.append(np.zeros((4, W, 3), np.uint8))
    if not rows:
        body.append(_label(np.zeros((60, W, 3), np.uint8), ['no view: generator not run for this object'], 0.5))
    return np.concatenate(body, 0)


def save_png(path, img):
    """Palette PNG (256 colours, adaptive) to keep the montage small."""
    from PIL import Image
    im = Image.fromarray(img[:, :, ::-1]).quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    im.save(path, optimize=True)
    guard.register_output(path)
    return os.path.getsize(path)


# ------------------------------------------------------------------------------------------------ one episode
def run_episode(ep, out, refiner, geo):
    D = guard.CFG['data']
    t = time.time()
    b = BU.from_obs_all(ep)
    log(f'ep{ep}: dev bundle {time.time() - t:.0f} s, objects {b.objects}')
    hands = guard.load_npz(os.path.join(D, 'data', 'sweep', f'ep{ep}', 'hands.npz'), 'dev_hands')
    a_off = int(hands['a_offset']) if 'a_offset' in hands else 1
    if a_off != geo.a_offset:
        raise ValueError(f'ep{ep}: hands a_offset {a_off} != {geo.a_offset}')
    dpath = os.path.join(D, 'cache', 'depth', 'public', f'ep{ep}', 'depths_fs0.5.npy')
    depth = np.load(guard.open_input(dpath, 'depth'), mmap_mode='r')
    vpath = os.path.join(D, 'data', 'store', f'ep{ep}_a.mp4')
    nv = video_len(vpath)
    census = b.meta['contact']
    t = time.time()
    table = GI.frame_table(b, None, geo, hands, depth, n_video=nv, objs=b.objects)
    log(f'ep{ep}: frame table {time.time() - t:.0f} s ({ {o: len(v) for o, v in table.items()} } rows)')
    picks = {}
    for o in b.objects:
        picks[o] = GI.choose_views(b, o, census, table=table[o])
    js = {GI.colour_frame(v, geo) for o in b.objects for v in picks[o][0]}
    frames, _ = read_frames(vpath, js)
    rep = dict(ep=ep, objects=b.objects, a_offset=geo.a_offset, video_frames=nv, depth_frames=int(len(depth)),
               partner_dilate_px_cam_a=GI.partner_dilate_px(geo), refine=None if refiner is None else refiner.name,
               census={k: dict(frames=len(v['frames']), contact=len(v['contact']), separated=len(v['separated']),
                               sep3d=len(v['sep3d']), overlap2d=v['overlap2d'])
                       for k, v in census.items()},
               targets={}, sigma_mm=b.meta.get('sigma_mm'))
    ok_all = True
    for o in b.objects:
        views, crep = picks[o]
        sep = GI.separated_frames(census, o, b.partners(o))
        rows, vrecs = [], []
        for v in views:
            img = frames.get(GI.colour_frame(v, geo))
            if img is None:
                raise ValueError(f'ep{ep} {o}: colour frame {GI.colour_frame(v, geo)} missing')
            F, res = GI.masks(v, b, img, geo=geo, hands=hands, depth=depth, refine=refiner)
            res['obj'] = o
            t_proj = GI.partner_pixel_test(res['projected'], b, o, v.k, geo, layers=res['layers'])
            t_fin = GI.partner_pixel_test(F, b, o, v.k, geo, layers=res['layers'])
            hand_in = int((F & res['parts']['H']).sum())
            sep_ok = (v.mode != 'separated') or sep is None or v.k in sep
            inp = None
            if v.mode == 'contact':
                inp = GI.inpaint_partners(img, F, res['layers'], o, GI.crop_box(F, geo, pad=0.35))
            ok = bool(t_proj['pass'] and t_fin['pass'] and sep_ok and hand_in == 0 and F.any())
            ok_all &= ok
            vr = dict(view=dict(k=v.k, j=v.j, mode=v.mode, rank=v.rank, min_angle_deg=v.min_angle_deg,
                                area=v.area, hand_share=v.hand_share, depth_share=v.depth_share,
                                partner_share=v.partner_share),
                      masks=res['info'], b11_projected=t_proj, b11_final=t_fin, hand_px_in_final=hand_in,
                      separated_frame=None if sep is None else bool(v.k in sep), separated_ok=sep_ok, pass_=ok)
            vrecs.append(vr)
            refl = ''
            if res['info'].get('refined'):
                fl2 = [x for x in res['info']['flags'] if x.startswith('refine_')]
                refl = f" | sam2 iou {res['info']['refined_iou_projected']:.2f} {' '.join(fl2) or 'trim'}"
            ang = '' if v.min_angle_deg is None else f" | {v.min_angle_deg:.1f} deg from earlier views"
            lines = [f"#{v.rank} k={v.k} (colour {v.j}) {v.mode} | area {v.area} px | hand {100 * v.hand_share:.0f}% "
                     f"| valid depth {100 * v.depth_share:.0f}% | partner overlap {100 * v.partner_share:.0f}%{ang}",
                     f"B.11: partner points in mask {t_fin['points_inside']}, footprint px in mask "
                     f"{t_fin['footprint_inside']}, min gap {t_fin['min_dist_px']} px | separated frame "
                     f"{vr['separated_frame']}{refl} | {'PASS' if ok else 'FAIL'}"]
            rows.append((panels(img, F, res, geo, inpainted=inp), lines))
        crep['view_results'] = vrecs
        crep['pass'] = all(x['pass_'] for x in vrecs)
        rep['targets'][o] = crep
        nv_ = crep['n_views']
        fl = ','.join(crep['flags']) or '-'
        header = [f"ep{ep} target {o} | partners {','.join(b.partners(o))} | mode {crep['mode']} | {nv_} view(s)",
                  f"flags {fl} | refine {rep['refine'] or 'none'}",
                  f"qualifying {crep['qualifying']} of {crep['frames']} frames, separated {crep['separated']}; "
                  f"pool span {crep['pool_span_deg']} deg (p90 {crep['pool_p90_deg']})",
                  "panels: overlay (green target, red partner, blue hand capsule, orange depth occluder, cyan",
                  "projected mask) | generator input | valid depth in the mask (magenta: no valid depth)"]
        png = os.path.join(out, f'ep{ep}_{o}.png')
        size = save_png(png, montage(rows, header))
        crep['montage'] = dict(path=os.path.basename(png), bytes=size)
        log(f'ep{ep} {o}: {crep["mode"]}, {nv_} view(s), flags {fl}, pass {crep["pass"]}, montage {size} B')
    rep['pass'] = ok_all
    for name, obj in (('report', rep), ('table', table)):
        p = os.path.join(out, f'ep{ep}_{name}.json')
        with open(p, 'w') as f:
            json.dump(obj, f, indent=1 if name == 'report' else None, default=float)
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', required=True)
    ap.add_argument('--eps', default='2,11,26')
    ap.add_argument('--refine', choices=('sam2', 'none'), default='sam2')
    ap.add_argument('--sam2', default='sam2.1-hiera-tiny', help='folder in the weights root')
    a = ap.parse_args()
    if guard.mode() != 'dev':
        raise SystemExit('b11_views: dev only (GMG_MODE=dev): it reads obs_all dev bundles and dev_hands')
    guard.set_run(a.run)
    # the manifest takes HEAD when it is written; record the code state at the start too (another agent may commit
    # to the shared checkout while this runs)
    start = dict(start_commit=guard._git('rev-parse', 'HEAD'),
                 start_code_dirty_files=(guard._git('status', '--porcelain', '--', *[
                     os.path.relpath(d, guard.CFG['repo']) for d in guard.CODE_DIRS]) or '').splitlines())
    out = os.path.join(a.run, 'b11')
    os.makedirs(out, exist_ok=True)
    geo = GI.camera_geometry(os.path.join(guard.CFG['data'], 'data', 'calib.json'))
    GI.consts()
    refiner = None
    if a.refine == 'sam2':
        t = time.time()
        refiner = GI.Sam2Refiner(os.path.join(guard.CFG['weights'], a.sam2), geo)
        log(f'SAM2 {a.sam2} loaded on the CPU in {time.time() - t:.0f} s')
    summ = {}
    for ep in [int(x) for x in a.eps.split(',')]:
        r = run_episode(ep, out, refiner, geo)
        summ[ep] = dict(pass_=r['pass'], targets={o: dict(mode=t['mode'], n_views=t['n_views'], flags=t['flags'],
                                                          pass_=t['pass']) for o, t in r['targets'].items()})
    allp = all(v['pass_'] for v in summ.values())
    with open(os.path.join(out, 'summary.json'), 'w') as f:
        json.dump(dict(prereg='B.11', pass_=allp, episodes=summ, refine=a.refine), f, indent=1)
    guard.write_manifest(os.path.join(a.run, 'manifest.json'), extra=dict(step='B2', prereg='B.11', pass_=allp, **start))
    log(f'B.11 {"PASS" if allp else "FAIL"}: {json.dumps(summ)}')


if __name__ == '__main__':
    main()
