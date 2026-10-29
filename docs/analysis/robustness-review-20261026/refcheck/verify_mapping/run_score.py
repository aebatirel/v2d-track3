"""Score a list of stored public rollouts with myscore.py and write one json line per rollout.
Usage: python -I run_score.py SELECT OUT.jsonl
  SELECT = 'all' | 'eps:21,27,...' | 'sample:N' (stratified) ; lib per rollout is taken from the mapping rows
  (checked separately, see check_libs.py), everything else is recomputed here.
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import myscore as M

SP = M.SP
ROWS = f'{SP}/work/mapping/rows.jsonl'


def main():
    sel, out = sys.argv[1], sys.argv[2]
    rows = [json.loads(l) for l in open(ROWS)]
    rows = [r for r in rows if 'error' not in r]
    if sel.startswith('eps:'):
        eps = {int(x) for x in sel[4:].split(',')}
        rows = [r for r in rows if r['ep'] in eps]
    elif sel.startswith('sample:'):
        n = int(sel[7:]); rng = np.random.default_rng(12345)
        rows = [rows[i] for i in sorted(rng.choice(len(rows), n, replace=False))]
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['sha256'] for l in open(out)}
    t0 = time.time(); k = 0
    with open(out, 'a') as fo:
        for r in rows:
            if r['sha256'] in done:
                continue
            ep = r['ep']; names = M.gt(ep)[0]
            try:
                frames, sim, ref, md, valid = M.read_rollout(f"{SP}/store/{r['path']}", names)
            except Exception as e:
                fo.write(json.dumps(dict(sha256=r['sha256'], path=r['path'], ep=ep, error=str(e)[:200])) + '\n'); continue
            S, S_obj = M.sim_vs_ref(sim, ref, per_object=True)
            T, T_obj = M.registered(ep, r['lib'], sim, frames)
            R, R_obj = M.registered(ep, r['lib'], ref, frames)
            row = dict(sha256=r['sha256'], path=r['path'], ep=ep, lib=r['lib'], frames=int(len(frames)),
                       frame0=int(frames[0]), valid=valid, ck=md.get('flash_chord.checkpoint_sha256'),
                       refpq=md.get('flash_chord.reference_parquet'), ref_digest=M.ref_digest(ref),
                       S=S, S_obj={n: S_obj[b] for b, n in enumerate(names)}, T=T, T_obj=T_obj, R=R, R_obj=R_obj,
                       their=dict(S=r['S'], T=r['T'], R=r['R'], ck=r.get('checkpoint_sha256'), ref_digest=r['ref_digest']))
            fo.write(json.dumps(row) + '\n'); fo.flush(); k += 1
            print(f"[{time.time() - t0:6.0f}s] {k} ep{ep} {r['lib']} S {S}/{r['S']} T {T}/{r['T']} R {R}/{r['R']}", flush=True)


if __name__ == '__main__':
    main()
