"""GT-free summary of S10 on the stored eval tracks (hp_eval.sh outputs): holds, frames changed and the size of the
change per eval and object, from pose_opt.json / pose_opt_aux.npz only. No ground truth exists for eval; nothing is
tuned or written outside the scratchpad except this summary.
Usage: python -I hp_eval_summary.py OUT_JSON"""
import json, sys
import numpy as np
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
W = f'{S}/heldpose/eval/runs'
EPS = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
out = {}
for e in EPS:
    r = {}
    for v in ('S10g', 'S10r', 'S10t'):
        js = json.load(open(f'{W}/{v}/ep{e}/pose_opt.json'))
        aux = np.load(f'{W}/{v}/ep{e}/pose_opt_aux.npz')
        s10 = js['steps']['S10']
        T = js['T']
        for n, o in s10['objects'].items():
            cm = aux[f'S10_{n}_cm']
            ch = cm > 1e-6
            x = r.setdefault(n, {})
            x[v] = dict(T=T, holds=[(h['side'], h['a'], h['b']) for h in o['holds']],
                        hold_frames=int(sum(h['b'] - h['a'] for h in o['holds'])),
                        frames_changed=int(ch.sum()), frames_changed_ge1cm=int((cm >= 1).sum()),
                        frames_changed_ge2cm=int((cm >= 2).sum()),
                        change_cm_mean_changed=round(float(cm[ch].mean()), 3) if ch.any() else 0.0,
                        change_cm_max=round(float(cm.max()), 3),
                        vis_pred_med=[h.get('vis_pred_med') for h in o['holds']],
                        residual_cm_med=[h['residual_cm_med'] for h in o['holds']],
                        w_mean=[h['w_mean'] for h in o['holds']])
    out[str(e)] = r
    for n, x in r.items():
        g, rr = x['S10g'], x['S10r']
        print(f'eval{e:>2} {n:18s} T {g["T"]:3d} holds {len(g["holds"])} ({g["hold_frames"]} fr) | g: changed {g["frames_changed"]:3d}, '
              f'>=1cm {g["frames_changed_ge1cm"]:3d}, >=2cm {g["frames_changed_ge2cm"]:3d}, max {g["change_cm_max"]:.2f} cm | '
              f'r: >=1cm {rr["frames_changed_ge1cm"]:3d}, >=2cm {rr["frames_changed_ge2cm"]:3d}, max {rr["change_cm_max"]:.1f} | '
              f'vP {g["vis_pred_med"]} res {g["residual_cm_med"]}')
spoon = {e: out[e]['wooden_spoon'] for e in out if 'wooden_spoon' in out[e]}
tot = {v: dict(frames=sum(s[v]['T'] for s in spoon.values()), hold=sum(s[v]['hold_frames'] for s in spoon.values()),
               changed=sum(s[v]['frames_changed'] for s in spoon.values()),
               ge1=sum(s[v]['frames_changed_ge1cm'] for s in spoon.values()),
               ge2=sum(s[v]['frames_changed_ge2cm'] for s in spoon.values())) for v in ('S10g', 'S10r', 'S10t')}
print('spoon totals (10 evals):', json.dumps(tot))
json.dump(dict(note='GT-free: S10 on the stored eval tracks; no eval reference changed.', spoon_totals=tot, evals=out),
          open(sys.argv[1], 'w'), indent=1)
