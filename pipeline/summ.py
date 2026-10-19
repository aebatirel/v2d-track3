import json, glob, sys, numpy as np
rows = []
for f in sorted(glob.glob((sys.argv[1] if len(sys.argv) > 1 else '/content/perc') + '/ep*/result.json'), key=lambda p: int(p.split('/ep')[1].split('/')[0])):
    r = json.load(open(f)); a = [k for k in r if k.startswith('anchor:')]
    best = max(a, key=lambda k: r[k]['AUC'])
    rows.append((r['episode'], r['vo']['AUC'], r['vo']['SP_SR'], r['vo']['MP_SR'], r['vo']['MPPE_cm'], r[best]['AUC'], r['vo_stats']['keyframes'],
                 ' '.join(f"{n[:10]}:{x:.2f}" for n, x in r['vo']['per_obj_AUC'].items())))
for x in rows: print(f'{x[0]:3d} vo {x[1]:.3f} SP {x[2]:.0f} MP {x[3]:.0f} MPPE {x[4]:5.2f} | bestanchor {x[5]:.3f} kf {x[6]:3d} | {x[7]}')
v = np.array([x[1:6] for x in rows], float)
print('MEAN n=%d  vo AUC %.3f SP %.2f MP %.2f MPPE %.2f | best-anchor AUC %.3f (oracle)' % (len(rows), *v.mean(0)))
