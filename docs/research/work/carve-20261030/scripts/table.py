"""Compact table: carve.json overlaps + settle (default / carved) per case. Usage: table.py TAG:CARVEDIR:SETTLE_PREFIX ..."""
import json, os, sys
for arg in sys.argv[1:]:
    tag, cd, sp = arg.split(':')
    c = json.load(open(f'{cd}/carve.json')); o = c.get('overlap_cm3', {})
    line = dict(tag=tag, host=c['host'][:10], guest=c['guest'][:10], segs=c.get('rest_contact_segments'), placed=c.get('placed_frame'),
                mutual=c.get('mutual'), ov_placed=o.get('placed'), red_pct=o.get('placed_reduction_pct'), ov_f0=o.get('frame0'),
                ov_rest_max=o.get('rest_max'), all_max=o.get('all_max'), max_inc=o.get('max_increase'),
                pieces={n[6:16]: [x['hulls_before'], x['pieces'], round(x['min_piece_m3'], 13)] for n, x in c.items() if n.startswith('carve_')})
    for kind in ('def', 'cut'):
        p = f'{sp}_{kind}.json'
        if os.path.exists(p):
            s = json.load(open(p))
            line[kind] = {F: {('G' if n == c['guest'] else 'H' if n == c['host'] else n): fd[n]['at_2s'] + [fd[n]['peak_cm']]
                              for n in (c['guest'], c['host'], 'rel') if n in fd} | {'nan': fd['nan_at_step']} for F, fd in s['frames'].items()}
    print(json.dumps(line))
