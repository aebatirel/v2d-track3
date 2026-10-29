"""Compact per-frame timeline of one object from frames.py output: pose metrics + links within MM (default 5)."""
import sys, json
path, obj = sys.argv[1], sys.argv[2]; f0, f1, step = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]); MM = float(sys.argv[6]) if len(sys.argv) > 6 else 5.0
AB = {'thumb': 'T', 'index': 'I', 'middle': 'M', 'ring': 'R', 'pinky': 'P', 'hand': 'palm'}
for l in open(path):
    r = json.loads(l); f = r['f']
    if f < f0 or f >= f1 or (f - f0) % step:
        continue
    o = r['obj'][obj]; ls = []
    for k, v in sorted(o['links'].items(), key=lambda kv: kv[1]['d_mm']):
        if v['d_mm'] > MM:
            continue
        side, ln = k.split(':'); fi = ln.split('_')[0]; seg = ln.split('_', 1)[1] if '_' in ln else ''
        name = side + AB.get(fi, fi) + ('' if fi == 'hand' else seg.replace('MCP_VL', 'K'))
        ls.append(f"{name}[{v['region'][:2]}{v['face']}{v['world'][:2]}/{v['on_link'][:3]}]")
    print(f"f{f:3d} lift {o['lift_cm']:5.1f} low {o['low_mm']:5.1f} tilt {o['tilt_deg']:5.1f} turn {o['turn_deg']:5.1f} slide {o['slide_mm']:5.1f} oo {o.get('objobj_mm', -1):6.1f} n{len(ls):2d} " + ' '.join(ls))
