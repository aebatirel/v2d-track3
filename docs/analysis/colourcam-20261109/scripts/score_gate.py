"""Score the colour-camera test (PREREG.md) and apply its gate. Run after inference has finished; mocap is read only by
pipeline/score_registered.py here.

Usage: python -I score_gate.py RUN_ID WORK REPO T3 KIT [EPS...]
  pulls runs/RUN_ID/results/pcol/<arm>/ep<N>/{poses_world_vo.npz,result.json,track_cam.json,track_guard.json} from the
  HF store into WORK, scores every arm with score_registered.py (--meshes REPO/meshes/library_v3, --per_frame), writes
  WORK/scores/<arm>/ep<N>.json + _pf.npz, and WORK/gate.json with the pre-registered gate (AP vs CP) and the
  report-only comparisons (AP vs C, CP vs C, per object).
"""
import json, os, subprocess, sys
import numpy as np
from huggingface_hub import hf_hub_download

RUN, WORK, REPO, T3, KIT = sys.argv[1:6]
EPS = [int(x) for x in sys.argv[6:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
ARMS = ['C', 'CP', 'AP']
STORE = os.environ.get('HF_STORE', 'aebatirel/v2d-store')
NOISE = 0.00002            # |mean dAUC| of two identical control runs, 2 Nov (PREREG.md)


def pull(arm, ep, f):
    try:
        return hf_hub_download(STORE, f'runs/{RUN}/results/pcol/{arm}/ep{ep}/{f}', repo_type='dataset', local_dir=f'{WORK}/store')
    except Exception:
        return None


def score(arm, ep):
    out = f'{WORK}/scores/{arm}/ep{ep}.json'
    if os.path.exists(out):
        return json.load(open(out))
    src = pull(arm, ep, 'poses_world_vo.npz')
    for f in ('result.json', 'track_cam.json', 'track_guard.json', 'log.txt'):
        pull(arm, ep, f)
    if src is None:
        return None
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run([sys.executable, f'{REPO}/pipeline/score_registered.py', str(ep), src, '--meshes', f'{REPO}/meshes/library_v3',
                        '--t3', T3, '--kit', KIT, '--out', out, '--per_frame', out.replace('.json', '_pf.npz')],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(arm, ep, 'scoring failed', r.stderr[-400:]); return None
    return json.load(open(out))


S = {a: {e: score(a, e) for e in EPS} for a in ARMS}
P = {a: {e: (S[a][e] or {}).get('perception') for e in EPS} for a in ARMS}


def gt3(a, e):
    f = f'{WORK}/scores/{a}/ep{e}_pf.npz'
    return int((np.load(f)['perception_pos_cm'] > 3).sum()) if os.path.exists(f) else None


def compare(v, c, gated):
    rows, fallback = [], []
    for e in EPS:
        pc, pv = P[c][e], P[v][e]
        if pc is None:
            continue
        if pv is None:                                                # PREREG: a crash counts as the control's track
            pv, fallback = pc, fallback + [e]
        rows.append(dict(ep=e, C=pc['AUC'], V=pv['AUC'], dAUC=round(pv['AUC'] - pc['AUC'], 4),
                         dMPPE=round(pv['MPPE_cm'] - pc['MPPE_cm'], 3), dRPE=round(pv['RPE_cm'] - pc['RPE_cm'], 3),
                         gt3C=gt3(c, e), gt3V=gt3(v, e) if e not in fallback else gt3(c, e),
                         objC=pc['per_obj_AUC'], objV=pv['per_obj_AUC']))
    d = np.array([r['dAUC'] for r in rows])
    res = dict(variant=v, control=c, n=len(rows), crashed_counted_as_control=fallback,
               missing=[e for e in EPS if P[c][e] is None],
               mean_AUC_control=round(float(np.mean([r['C'] for r in rows])), 4), mean_AUC_variant=round(float(np.mean([r['V'] for r in rows])), 4),
               mean_dAUC=round(float(d.mean()), 5), min_dAUC=round(float(d.min()), 4), better=int((d > 0.0005).sum()),
               worse=int((d < -0.0005).sum()), mean_dMPPE=round(float(np.mean([r['dMPPE'] for r in rows])), 4),
               mean_dRPE=round(float(np.mean([r['dRPE'] for r in rows])), 4),
               gt3C=sum(r['gt3C'] or 0 for r in rows), gt3V=sum(r['gt3V'] or 0 for r in rows))
    if gated:
        res['gate'] = dict(mean=res['mean_dAUC'] >= 0.005 and res['mean_dAUC'] >= 2 * NOISE, min=res['min_dAUC'] >= -0.02,
                           mppe_rpe=res['mean_dMPPE'] <= 0 and res['mean_dRPE'] <= 0, drift=res['gt3V'] <= res['gt3C'])
        res['pass'] = all(res['gate'].values()) and not res['missing']
        res['falsified'] = res['mean_dAUC'] <= 0
    objs = {}
    for r in rows:
        for o, x in r['objV'].items():
            objs.setdefault(o, []).append(x - r['objC'][o])
    res['per_object_mean_dAUC'] = {o: [round(float(np.mean(x)), 4), len(x)] for o, x in sorted(objs.items())}
    res['rows'] = rows
    return res


out = dict(run=RUN, eps=EPS, gated=compare('AP', 'CP', True), ap_vs_c=compare('AP', 'C', False), cp_vs_c=compare('CP', 'C', False))
out['ap_track_cam'] = {e: json.load(open(p)) for e in EPS
                       if (p := f'{WORK}/store/runs/{RUN}/results/pcol/AP/ep{e}/track_cam.json') and os.path.exists(p)}
json.dump(out, open(f'{WORK}/gate.json', 'w'), indent=1)
for k in ('gated', 'ap_vs_c', 'cp_vs_c'):
    print(k, json.dumps({x: y for x, y in out[k].items() if x != 'rows'}))
print('per episode (AP vs CP): ep CP AP dAUC dMPPE dRPE >3cm CP/AP')
for r in out['gated']['rows']:
    print(r['ep'], r['C'], r['V'], r['dAUC'], r['dMPPE'], r['dRPE'], r['gt3C'], r['gt3V'])
