"""Summary and pack-10 hand-off of an eval-episode physics solve box (2026-10-31, ops/jobs/eval_solve.sh). GT-free: every
number is about OUR reference (sim_vs_ref: pipeline/qa.py's metric via tools/physics_solve/jitter_check.py and
tools/trace_score.py); nothing reads ground truth.
Usage: eval_solve_summary.py O "EPS" --run RUN_ID [--root /content]
  O/ep<N>/: inputs.json (tools/physics_solve/eval_inputs.py check), jitter_in.json / jitter_ps.json (64-copy jitter of the
  input and of the solved reference, same seed = same noise draws), solve.out, zero_score_{in,ps}.txt and
  rest_check_{in,ps}.json (official zero-action replay + tools/rest_check.py of each), work.txt (the working directory,
  holding ref_in.parquet, ref_ps.parquet and ref_ps_solve.json/.npz/.log); writes O/summary.json, O/handoff.tsv, O/handoff.md (stdout: the
  summary JSON). Store path of a local file ROOT/<rel> = runs/<RUN_ID>/<rel> (ops/box/store.sh push-run).
No verdict: pack 10's own per-episode rule decides what is used. Reported per episode: Delta = jittered mean(solved) -
jittered mean(input), the G2 check (physics-solver.md section 5.2 / G2 result: ep2 +0.239, ep12 +0.254 at this scale).
"""
import argparse, hashlib, json, os, re, sys

import numpy as np

EDIT_COLS = {f'robot_{s}_{c}' for s in ('left', 'right') for c in ('wrist_position', 'wrist_wxyz', 'finger_joints')}


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jl(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('O'); ap.add_argument('eps'); ap.add_argument('--run', required=True)
    ap.add_argument('--root', default='/content'); a = ap.parse_args()
    root = a.root.rstrip('/')
    sp = lambda p: f'runs/{a.run}/{os.path.relpath(p, root)}' if p and os.path.abspath(p).startswith(root + '/') else None  # noqa: E731
    out = dict(run=a.run, episodes={}, solved=[], failed={}); rows = []
    for e in a.eps.split():
        d = f'{a.O}/ep{e}'; r = dict(ep=int(e)); out['episodes'][f'ep{e}'] = r
        inp = jl(f'{d}/inputs.json')
        if not inp:
            why = open(f'{d}/dropped.txt').read().strip() if os.path.exists(f'{d}/dropped.txt') else 'no input check'
            r['status'] = f'dropped: {why}'; out['failed'][e] = r['status']; continue
        if not inp.get('ok'):
            r['status'] = f"input refused: {inp.get('refused')}"; out['failed'][e] = r['status']; continue
        tb = inp.get('table', {})
        r['input'] = dict(mode=inp['mode'], md5=inp['md5'], frames=inp['frames'], objects=inp['objects'],
                          store_path=(open(f'{d}/input_store_path.txt').read().strip() if os.path.exists(f'{d}/input_store_path.txt') else None),
                          asset_roots=inp['asset_roots'], asset_digest=inp['asset_digest'], n_asset_files=len(inp['asset_files']),
                          masses=inp.get('masses'), stage_md5=inp['stage_md5'],
                          packed_policy=dict(run=tb.get('packed_run'), checkpoint=tb.get('packed_checkpoint'), sha256=tb.get('packed_sha256')),
                          table_lib=tb.get('lib'), table_pieces=tb.get('pieces'))
        work = open(f'{d}/work.txt').read().strip() if os.path.exists(f'{d}/work.txt') else ''
        fin, fps = f'{work}/ref_in.parquet', f'{work}/ref_ps.parquet'
        if work and os.path.exists(fin):
            r['input_copy'] = dict(store_path=sp(fin), md5=md5(fin), identical_to_input=md5(fin) == inp['md5'])
            sdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(work))), 'reconstructed_stage')   # <base>/
            # processed/sequence_id=<seq>/robot_name=<robot> -> <base>/reconstructed_stage (FlashCHORD's lookup)
            r['stage_copy'] = [sp(os.path.join(sdir, x)) for x in sorted(os.listdir(sdir))] if os.path.isdir(sdir) else []
            r['stage_copy_md5'] = [md5(os.path.join(sdir, x)) for x in sorted(os.listdir(sdir))] if os.path.isdir(sdir) else []
        for tag in ('in', 'ps'):
            j = jl(f'{d}/jitter_{tag}.json')
            if j:
                r[f'jitter_{tag}'] = {k: j[k] for k in ('nominal', 'mean', 'sd', 'min', 'max', 'k', 'seed', 'sig_pos', 'sig_fin', 'device', 'wall_s') if k in j}
        s = jl(f'{work}/ref_ps_solve.json') if work else None
        if s:
            r['solve'] = {k: s.get(k) for k in ('wall_s', 'deadline_t', 'rollbacks', 'paced_replans', 'mean_iters', 'T')}
            r['solve']['replans'] = len(s.get('replans', []))
            r['solve']['planned_replans'] = sum(1 for x in s.get('replans', []) if x.get('active'))
        if work and os.path.exists(fps):
            r['solved'] = dict(store_path=sp(fps), md5=md5(fps))
            for x in ('_solve.json', '_solve.npz', '_solve.log'):
                if os.path.exists(f'{work}/ref_ps{x}'):
                    r['solved'][x.strip('_').replace('.', '_')] = sp(f'{work}/ref_ps{x}')
            try:                                         # what the solver changed: only the target columns
                import pyarrow.parquet as pq
                ti, tp = pq.read_table(fin), pq.read_table(fps)
                diff = sorted(c for c in ti.column_names if c not in tp.column_names or not ti.column(c).equals(tp.column(c)))
                r['solved']['changed_columns'] = diff
                r['solved']['only_target_columns_changed'] = set(diff) <= EDIT_COLS and ti.column_names == tp.column_names
                z = np.load(f'{work}/ref_ps_solve.npz'); off = z['offsets']
                r['solved']['frames_edited'] = int((np.abs(off) > 0).any(1).sum())
            except Exception as ex:
                r['solved']['diff_error'] = str(ex)[:200]
        for tag in ('in', 'ps'):                         # official zero-action replay (nominal) + rest check of each
            zs = f'{d}/zero_score_{tag}.txt'
            if os.path.exists(zs):
                r[f'zero_{tag}'] = {k: float(v) for k, v in re.findall(r'(floor_vs_ref|zero_action|truth):?\s+(?:sim_vs_ref\s+)?([0-9.]+)', open(zs).read())}
            rc = jl(f'{d}/rest_check_{tag}.json')
            if rc is not None:
                r[f'rest_check_{tag}'] = rc
        for x in ('zero_score_in.txt', 'rest_check_in.json', 'zero_score_ps.txt', 'rest_check_ps.json', 'jitter_in.json', 'jitter_ps.json'):
            if os.path.exists(f'{d}/{x}'):
                r.setdefault('result_files', {})[x] = sp(f'{d}/{x}')
        if 'jitter_in' in r and 'jitter_ps' in r:
            r['delta_jittered'] = round(r['jitter_ps']['mean'] - r['jitter_in']['mean'], 4)
        ok = 'solved' in r and 'jitter_ps' in r and 'jitter_in' in r and r['solved'].get('only_target_columns_changed', False)
        if ok and 'rest_check_ps' not in r:              # glock_public.sh REUSE_REF needs a rest_check.json: flag, keep
            r['warning'] = 'no rest_check_ps.json (zero replay or rest_check failed): pack 10 must make one before REUSE_REF'
        if ok:
            r['status'] = 'solved'; out['solved'].append(int(e))
        else:
            tail = ''
            if os.path.exists(f'{d}/solve.out'):
                tail = ' '.join(open(f'{d}/solve.out', errors='replace').read().strip().splitlines()[-2:])[:300]
            r['status'] = 'failed: ' + ', '.join(k for k in ('solved', 'jitter_in', 'jitter_ps') if k not in r) + \
                ('' if 'solved' not in r or r['solved'].get('only_target_columns_changed') else ' (non-target columns changed)') + \
                (f' | {tail}' if tail else '')
            out['failed'][e] = r['status']
        ji, jp = r.get('jitter_in', {}), r.get('jitter_ps', {})
        rows.append([f'ep{e}', r['status'].split(':')[0], r['input'].get('store_path') or '', inp['md5'],
                     r.get('solved', {}).get('store_path') or '', r.get('solved', {}).get('md5') or '',
                     ';'.join(str(x) for x in (r.get('stage_copy') or [])), ','.join(inp['asset_roots']), inp['asset_digest'],
                     f"{ji.get('mean', '')}", f"{ji.get('sd', '')}", f"{jp.get('mean', '')}", f"{jp.get('sd', '')}",
                     f"{r.get('delta_jittered', '')}", f"{ji.get('nominal', '')}", f"{jp.get('nominal', '')}",
                     f"{r.get('solved', {}).get('frames_edited', '')}", f"{(r.get('solve') or {}).get('deadline_t')}",
                     (r.get('result_files') or {}).get('rest_check_ps.json') or ''])
    v = [x['delta_jittered'] for x in out['episodes'].values() if 'delta_jittered' in x and x.get('status') == 'solved']
    out['delta_jittered'] = dict(n=len(v), mean=round(float(np.mean(v)), 4) if v else None, min=min(v) if v else None,
                                 negative=[k for k, x in out['episodes'].items() if x.get('delta_jittered', 0) < 0])
    out['note'] = ('GT-free: jittered zero-action sim_vs_ref vs OUR reference (64 copies, 0.5 mm / 0.005 rad target noise, '
                   'seed 0, common random numbers), input vs solved, as G2. No verdict here: pack 10\'s per-episode rule '
                   'decides. robot_<side>_frames (the RL hand-tracking target) and the object reference are unchanged; '
                   'the solved reference names the same asset files as the input (object_urdf_paths unchanged).')
    hdr = ['ep', 'status', 'input_store_path', 'md5_in', 'solved_store_path', 'md5_out', 'stage_store_path', 'asset_root',
           'asset_digest', 'jit_in_mean', 'jit_in_sd', 'jit_ps_mean', 'jit_ps_sd', 'delta', 'nominal_in', 'nominal_ps',
           'frames_edited', 'deadline_t', 'rest_check_ps']
    with open(f'{a.O}/handoff.tsv', 'w') as f:
        f.write('\t'.join(hdr) + '\n')
        for x in rows:
            f.write('\t'.join(map(str, x)) + '\n')
    with open(f'{a.O}/handoff.md', 'w') as f:
        f.write(f'# Eval solve hand-off, run {a.run}\n\n{out["note"]}\n\n| ' + ' | '.join(['ep', 'status', 'md5 in', 'md5 out', 'jittered in',
                'jittered solved', 'delta', 'solved store path']) + ' |\n|' + '---|' * 8 + '\n')
        for x in rows:
            f.write(f'| {x[0]} | {x[1]} | {x[3][:8]} | {x[5][:8]} | {x[9]} ± {x[10]} | {x[11]} ± {x[12]} | {x[13]} | `{x[4]}` |\n')
    json.dump(out, open(f'{a.O}/summary.json', 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
