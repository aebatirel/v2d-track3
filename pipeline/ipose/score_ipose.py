"""Score control vs pot-network variants on the test episodes (after inference; reads mocap via score_registered.py).
Usage: python -I score_ipose.py RESULTS_DIR OUT_JSON --meshes M13P --t3 T3 --kit KIT --scorer score_registered.py
         [--arms R,RM] [--variants N,NP,NS,NT] [--eps 2,27,44,45] [--control DIR]
RESULTS_DIR/<arm>/ep<E>/poses_world_vo_<V>.npz. Gate (PREREG): variant N, mean pot dAUC >= +0.02, min >= -0.01.
"""
import argparse, json, os, subprocess, numpy as np

p = argparse.ArgumentParser()
p.add_argument('res'); p.add_argument('out')
p.add_argument('--meshes', required=True); p.add_argument('--t3', required=True); p.add_argument('--kit', required=True)
p.add_argument('--scorer', required=True); p.add_argument('--arms', default='R,RM'); p.add_argument('--variants', default='N,NP,NS,NT')
p.add_argument('--eps', default='2,27,44,45')
p.add_argument('--control', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../docs/analysis/ipose-20261103/control'))
a = p.parse_args()
OBJ = 'white_pot'
cache = json.load(open(a.out)) if os.path.exists(a.out) else {}


def score(ep, src, tag):
    key = f'{tag}/ep{ep}'
    if key in cache: return cache[key]
    oj, pf = f'{a.res}/scores/{tag}_ep{ep}.json', f'{a.res}/scores/{tag}_ep{ep}_pf.npz'
    os.makedirs(os.path.dirname(oj), exist_ok=True)
    subprocess.run(['python3', '-I', a.scorer, str(ep), src, '--meshes', a.meshes, '--t3', a.t3, '--kit', a.kit,
                    '--reg_seeds', '10', '--out', oj, '--per_frame', pf], check=True, capture_output=True)
    r = json.load(open(oj)); P = np.load(pf); names = list(P['names']); s = names.index(OBJ)
    add = P['perception_add_cm'][:, s]; pos = P['perception_pos_cm'][:, s]
    out = dict(AUC=r['perception_seedmean']['per_obj_AUC'][OBJ], MPPE_cm=r['perception_seedmean']['MPPE_cm'],
               ADD_cm_mean=round(float(add.mean()), 3), ADD_cm_median=round(float(np.median(add)), 3), pos_cm_mean=round(float(pos.mean()), 3),
               lost_frames=int((add > 3).sum()), frames=int(len(add)))
    if os.path.exists(os.path.dirname(src) + '/diag.json') and tag != 'control':
        d = json.load(open(os.path.dirname(src) + '/diag.json'))
        out['fallback'] = int(sum(d['fb_P'] if tag.endswith('/NP') else d['fb_N']))
    cache[key] = out; json.dump(cache, open(a.out, 'w'), indent=1)
    print(key, out, flush=True)
    return out


eps = [int(e) for e in a.eps.split(',')]
base = {e: score(e, f'{a.control}/ep{e}_poses_world_vo.npz', 'control') for e in eps}
summary = {}
for arm in a.arms.split(','):
    for V in a.variants.split(','):
        src = {e: f'{a.res}/{arm}/ep{e}/poses_world_vo_{V}.npz' for e in eps}
        if not all(os.path.exists(s) for s in src.values()): continue
        r = {e: score(e, src[e], f'{arm}/{V}') for e in eps}
        d = {e: round(r[e]['AUC'] - base[e]['AUC'], 4) for e in eps}
        summary[f'{arm}/{V}'] = dict(dAUC=d, mean=round(float(np.mean(list(d.values()))), 4), min=min(d.values()),
                                    gate=bool(V == 'N') and np.mean(list(d.values())) >= 0.02 and min(d.values()) >= -0.01,
                                    dMPPE={e: round(r[e]['MPPE_cm'] - base[e]['MPPE_cm'], 3) for e in eps},
                                    lost={e: r[e]['lost_frames'] for e in eps},
                                    medADD_rel={e: round(r[e]['ADD_cm_median'] / base[e]['ADD_cm_median'] - 1, 3) for e in eps})
        rel = summary[f'{arm}/{V}']['medADD_rel']
        summary[f'{arm}/{V}']['secondary'] = (V == 'N') and float(np.mean(list(rel.values()))) <= -0.2 and max(rel.values()) <= 0
        print(arm, V, summary[f'{arm}/{V}'], flush=True)
cache['summary'] = summary; cache['control'] = {str(e): base[e] for e in eps}
json.dump(cache, open(a.out, 'w'), indent=1)
