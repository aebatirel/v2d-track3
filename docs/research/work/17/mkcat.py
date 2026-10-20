import json, re
L = {}
for f in ['out/markers_small.log', 'out/markers_small_rest.log']:
    n = None
    for l in open(f):
        if 'candidates' in l: n = l.split(':')[0]; L.setdefault(n, []); continue
        m = re.search(r'c mm \[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\] r ([\d.]+) rms ([\d.]+) cov ([\d.]+).*col \[([\d. ]+)\] ring \[([\d. ]+)\]', l)
        if not m: continue
        x, y, z, r, rms, cov = map(float, m.groups()[:6]); col = list(map(float, m.group(7).split())); ring = list(map(float, m.group(8).split()))
        L[n].append(dict(c=[x / 1000, y / 1000, z / 1000], r=r / 1000, rms=rms / 1000, cov=cov, col=col, ring=ring))
json.dump(L, open('out/cand_flat.json', 'w'), indent=1)
