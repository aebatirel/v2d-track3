#!/usr/bin/env python3
"""Print a per-object table of screen.py output. Usage: python3 summ.py SCREEN.json"""
import json, sys
d = json.load(open(sys.argv[1]))
f = lambda x, k=1: '-' if x is None else (f'{x:.{k}f}' if isinstance(x, float) else str(x))  # noqa: E731
print('ep kind obj T | jump_cm(f) jump_deg(f) n>5cm n>20d | below_min(f) n<-3 | h0 | float_p50 float_max n>3 rest | tilt_p50 tilt_max n>20 ontab | tilt0 | refperc max(f) p50 deg_max n>5cm n>20d | pen_max(f) share>2')
for it in d['items']:
    if 'error' in it:
        print(it['ep'], it['kind'], 'ERROR', it['error']); continue
    pen = it.get('pen')
    for nm, o in it['objects'].items():
        s = (f"{it['ep']:>2} {it['kind']} {nm[:12]:12s} {it['T']:3d} | {f(o['jump_cm_max'])}({o['jump_cm_argmax']}) {f(o['jump_deg_max'],0)}({o['jump_deg_argmax']}) "
             f"{o['n_step_gt5cm']} {o['n_step_gt20deg']} | {f(o['below_cm_min'])}({o['below_cm_argmin']}) {o['n_below_3cm']} | {f(o['h0_cm'])} | "
             f"{f(o['float_rest_cm_p50'])} {f(o['float_rest_cm_max'])} {o['n_float_rest_gt3cm']} {o['free_rest_frames']} | "
             f"{f(o['tilt_rest_deg_p50'],0)} {f(o['tilt_rest_deg_max'],0)} {o['n_tilt_rest_gt20']} {o['on_table_rest_frames']} | {f(o['tilt0_deg'],0)}")
        if 'refperc_cm_max' in o:
            s += f" | {f(o['refperc_cm_max'])}({o['refperc_cm_argmax']}) {f(o['refperc_cm_p50'])} {f(o['refperc_deg_max'],0)} {o['n_refperc_gt5cm']} {o['n_refperc_gt20deg']}"
        if pen:
            s += f" | {f(pen['max_cm'])}({pen['argmax_frame']}) {f(pen['share_gt2cm'],2)}"
        print(s)
