# Summary of out/b2/front{rest,}_e*.jsonl: per frame and axis variant, marker image offsets and bowl offsets (image-plane mm,
# + toward M1), with the midpoint-line fit info.  Usage: b2_sumrest.py [rest|held] [variant]
import sys, json, glob, numpy as np
kind = sys.argv[1] if len(sys.argv) > 1 else 'rest'; VAR = sys.argv[2] if len(sys.argv) > 2 else 'midpts'
pat = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b2/' + ('frontrest_e*.jsonl' if kind == 'rest' else 'front_e*.jsonl')
for f in sorted(glob.glob(pat)):
    ep = f.split('_e')[-1].split('.')[0]
    for l in open(f):
        o = json.loads(l)
        if 'err' in o: print(f'e{ep} k{o["k"]}: {o["err"]}'); continue
        v = VAR if VAR in o['variants'] else o['axis_variant']
        mo = o['markers_off_var'][v]; ov = o['off_var'].get(v, {}); mi = o.get('midpts_info')
        print(f"e{ep:>2} k{o['k']:<3} {v:6s} M {mo[0]:+5.1f} {mo[1]:+5.1f} {mo[2]:+5.1f} asym {mo[0]+mo[1]:+5.1f} | bowl tip {ov.get('tip', np.nan):+5.2f} c15-45 {ov.get('c15_45', np.nan):+5.2f} c45-75 {ov.get('c45_75', np.nan):+5.2f} area {ov.get('area', np.nan):+5.2f}"
              + (f" | midpts n {mi['n']} span {mi['span']:.0f} rms {mi['rms']:.2f}" if mi else '') + f" | hw {o['handle_hw_mm']:.1f} wmax {o.get('wmax', 0):.1f}")
