"""Consolidated start/end pose consistency per (task, object) and per object across tasks. Research only."""
from c11 import *
import pandas as pd, json
df = pd.read_csv('s1_poses.csv')
def cstats(a):
    z = np.exp(1j*np.radians(np.asarray(a, float))); m = np.degrees(np.angle(z.mean()))
    dev = wrap(np.asarray(a) - m); return m, float(np.sqrt(np.mean(dev**2))), float(np.ptp(dev))
rows = []
for (task, obj), g in df.groupby(['task', 'obj']):
    for k in ('0', '1'):
        up = g['up' + k].str[:2].tolist()
        m, sd, rng = cstats(g['yaw' + k])
        rows.append(dict(task=task, obj=obj, when='start' if k == '0' else 'end', n=len(g), eps=g.ep.tolist(),
                         up=up, yaw=g['yaw' + k].round(1).tolist(), yaw_mean=round(m, 1), yaw_rms=round(sd, 1),
                         tilt=g['tilt' + k].round(1).tolist(), x=g['x' + k].tolist(), y=g['y' + k].tolist(), z=g['z' + k].tolist()))
out = pd.DataFrame(rows)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 60); pd.set_option('display.max_rows', 200)
print(out[['task', 'obj', 'when', 'eps', 'up', 'yaw', 'yaw_rms', 'tilt', 'x', 'y']].to_string(index=False))
# per object across tasks, start only, upright-on-table only
print('\n== per object, start, same rest face, all tasks')
for obj, g in df.groupby('obj'):
    s = g[g.up0.str[:2] == g.up0.str[:2].mode()[0]]
    m, sd, rng = cstats(s.yaw0)
    print(f"{obj:18s} n={len(s)} up={s.up0.str[:2].iloc[0]} yaw={s.yaw0.round(1).tolist()} circ-mean {m:.1f} rms {sd:.1f}")
# per-episode centring check
print('\n== centring: mean x,y over all frames and objects (cm)')
for ep in PUBLIC:
    e = load_episode(ep); p = e['pose']
    print(ep, np.round(np.nanmean(p[:, :, :2].reshape(-1, 2), 0) * 100, 3), 'table-frame z of slot0 at f0', round(p[0, 0, 2], 4))
out.to_json('s11_consistency.json', orient='records', indent=1)
