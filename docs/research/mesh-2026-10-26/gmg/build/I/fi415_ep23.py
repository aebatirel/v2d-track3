"""PREREG F-I4.15.6 step 4: public ep23 (dev), plate test and body only, both boards. No linking, slot, decision or
physics. Board 2's track is the wrong board (orchestrator; B4 identity flags): reported, never adopted.

  GMG_MODE=dev GMG_RUN=<run> python fi415_ep23.py <bundle dir> <cand dir> <pick> <video> <calib> <out_dir>

Per board: platebody.plate_info (F-I4.1 plane pair / F-I4.14 camera-side pair / one face, with the F-I4.15.1 all-point t),
resolve_one_face with the other board, plate_body_poly (F-I4.15.2: polygon, I-shape widths, FREE share of the polygon
and of the full rectangle), its default prisms (pieces_poly, cap floor(165 / objects)). Writes <out_dir>/ep23_fi415.json
and a PNG per board with a body (fi415_png.render). GT-free: our clean bundle, our picks, our tracks and video only."""
import importlib.util
import json
import os
import sys
import time

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from gmg import guard, interlock as IL, platebody as PB, silhouette as SI  # noqa: E402

bdir, cdir, pick, video, calib, out = sys.argv[1:7]
guard.set_run(os.environ['GMG_RUN'])
os.makedirs(out, exist_ok=True)
t0 = time.time()
b = IL.load_bundle_any(bdir)
objs = b.objects
mesh = {}
for o in objs:
    m = trimesh.load(os.path.join(cdir, o, f'{pick}.glb'), force='mesh')
    mesh[o] = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)
info0 = {o: PB.plate_info(b, o, mesh[o]) for o in objs}
o1, o2 = objs
info = {o1: PB.resolve_one_face(info0[o1], info0[o2]), o2: PB.resolve_one_face(info0[o2], info0[o1])}
cap = PB.k_('shapes_max') // max(1, len(objs))
res = dict(ep=23, bundle=bdir, cands=cdir, pick=pick, fi4_rev=PB.REV, code=None, cap=cap,
           note='plate test and body only (F-I4.15.6 step 4); board 2 track = wrong board: reported, not adopted',
           boards={})
spec = importlib.util.spec_from_file_location('fi415_png', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                        'fi415_png.py'))
FP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FP)
geo = SI.geometry(calib)
from gmg import simpieces as SP  # noqa: E402
res['code'] = SP.code_identity()
for o in objs:
    pi = info[o]
    row = dict(plate={k: v for k, v in pi.items() if not k.startswith('_') and k != 'planes'},
               planes=[dict(n_pts=p['n_pts'], rms_mm=p['rms_mm'], two_sided_share=p['two_sided_share'])
                       for p in pi.get('planes', [])][:6])
    if pi.get('plate'):
        ev = IL.Evidence(b, o, mesh[o], sub=False)
        bd = PB.plate_body_poly(b, o, pi, ev)
        row['body'] = bd
        if bd.get('ok'):
            R_mm = np.asarray(bd['box']['poly'], np.float64) * 1e3
            hulls, dinf = PB.pieces_poly(bd['box'], R_mm, cap)
            row['default_pieces'] = dinf
            row['body_built'] = bool(not dinf['over_cap'])
            if dinf['over_cap']:
                row['body_why'] = 'plate_body_over_cap'
            fs = FP.sep_frame(b, o)
            good = sorted(b.good_frames(o))
            fm = good[len(good) // 2] if good else None
            frames = [(f, k) for f, k in ((fs, 'separated'), (fm, 'middle good frame')) if f is not None]
            if frames:
                pg = bd['polygon']
                lines = [f'ep23 {o} F-I4.15 body only (no slot, no decision); '
                         + ('board 2 track = WRONG board, reported only' if o == o2 else 'board 1'),
                         f'yellow polygon t {bd["t_mm"]} mm ({pi.get("t_source")}), {pg["vertices"]} vertices, '
                         f'green default prisms {dinf["n"]}',
                         f'widths waist {bd["widths_mm"]["waist_30_70"]} / ends {bd["widths_mm"]["ends_outer_10"]} mm; '
                         f'FREE share {bd["free_share"]["polygon"]["free"]} vs rectangle '
                         f'{bd["free_share"]["rectangle"]["free"]}']
                row['png'] = FP.render(b, geo, video, o, bd['box'], frames, os.path.join(out, f'ep23_fi415_{o}.png'),
                                       lines, pieces=hulls)
                row['png_frames'] = frames
        else:
            row['body_built'] = False
            row['body_why'] = bd.get('why')
    else:
        row['body_built'] = False
        row['body_why'] = 'not plate-like: ' + str(pi.get('why'))
    res['boards'][o] = row
    print(o, json.dumps(dict(plate=pi.get('plate'), t_source=pi.get('t_source'), t_mm=round(pi['t_m'] * 1e3, 3)
                             if pi.get('t_m') else None, t_down_mm=pi.get('t_down_mm'), why=pi.get('why'),
                             body_built=row.get('body_built'), body_why=row.get('body_why'),
                             widths=(row.get('body') or {}).get('widths_mm'),
                             free=((row.get('body') or {}).get('free_share') or {}).get('ratio_polygon_to_rectangle'),
                             prisms=(row.get('default_pieces') or {}).get('n')), default=IL._jdefault), flush=True)
res['sec'] = round(time.time() - t0, 1)
json.dump(res, open(os.path.join(out, 'ep23_fi415.json'), 'w'), indent=1, default=IL._jdefault)
print('done', res['sec'], 's ->', out)
