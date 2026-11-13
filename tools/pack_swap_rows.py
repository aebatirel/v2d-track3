#!/usr/bin/env python3
"""Row-level rollout swap into a Track 3 submission (2 Nov 2026, perfect-following lane).

Why: tools/pack_swap_rollouts.py re-runs the kit packer on the base pack's full packer inputs (results + meshes), which
live only in the scratchpads of the sessions that built packs 9a+ to 11. Measured on pack 11 (eval 10, 322 rows): every
pose column of a submission row equals the official rollout's achieved pose at (environment_id, reference_frame,
object_id) exactly (max |diff| 0.0), and the checkpoint column is the rollout's checkpoint_sha256. So a swap can be done
on the submission rows directly, with the same checks:
  1. tools/no_oracle.py on every swap file and on its flash_chord reference path;
  2. per --swap N=ROLLOUT.parquet (its .json beside it): the json's checkpoint_sha256 must equal --expect-checkpoint, differ
     from the base episode's, and its eval_code / eval_script sha256 must equal the base rows' (same official evaluator);
     the rollout must cover exactly the base episode's (world, frame, slot) keys; pose columns of those rows are replaced
     by the achieved poses, checkpoint_sha256 by the json's;
  3. code_commit_url set to --code-commit on every row;
  4. checks vs the base: same rows / row_id order / columns / dtypes; only pose columns + checkpoint_sha256 differ, only on
     swapped episodes; object_mesh_b64 and every other column identical;
  5. the kit's offline validation (submit/v2d_submit.py validate_submission) and the CD-O derivation (meshes unchanged:
     must equal the base's CD-O file row for row).
Usage: pack_swap_rows.py --kit KIT --base BASE.parquet --base-cdo BASE.cd-o.parquet --code-commit URL
                         --swap N=ROLLOUT.parquet --expect-checkpoint N=SHA256 [...] -o OUT_DIR
Exit 0 = checks pass. Nothing is uploaded.
"""
import argparse, hashlib, json, os, subprocess, sys
import numpy as np, pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSE = ['pos_x', 'pos_y', 'pos_z', 'quat_x', 'quat_y', 'quat_z', 'quat_w']
ACH = ['achieved_position_x', 'achieved_position_y', 'achieved_position_z', 'achieved_quaternion_x',
       'achieved_quaternion_y', 'achieved_quaternion_z', 'achieved_quaternion_w']


def sha(f):
    return hashlib.sha256(open(f, 'rb').read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--kit', required=True); ap.add_argument('--base', required=True); ap.add_argument('--base-cdo', required=True)
    ap.add_argument('--code-commit', required=True); ap.add_argument('--swap', action='append', default=[])
    ap.add_argument('--expect-checkpoint', action='append', default=[]); ap.add_argument('-o', required=True)
    ap.add_argument('--same-checkpoint', action='append', default=[], type=int,
                    help='episode N whose rollout re-runs the base checkpoint on an updated reference (pf-anchor PREREG): skip only the base-checkpoint check')
    a = ap.parse_args()
    os.makedirs(a.o, exist_ok=True); log = []
    def say(*x):
        s = ' '.join(str(y) for y in x); print(s); log.append(s)
    exp = dict(x.split('=', 1) for x in a.expect_checkpoint)
    base = pd.read_parquet(a.base); out = base.copy()
    key = base.row_id.str.extract(r'^track_3/e(\d+)/w(\d+)/f(\d+)/o(\d+)$').astype(int)
    key.columns = ['e', 'w', 'f', 'o']
    say('base', a.base, 'sha256', sha(a.base), 'rows', len(base))
    manifest = dict(tool='tools/pack_swap_rows.py', base=a.base, base_sha256=sha(a.base), code_commit=a.code_commit, swaps={})
    for sw in a.swap:
        n, path = sw.split('=', 1); n = int(n); js = path[:-len('.parquet')] + '.json'
        meta = json.load(open(js)); ck = meta['checkpoint_sha256']
        import pyarrow.parquet as pq                                   # the evaluator's own stamp on the rollout
        md = {k.decode(): v.decode() for k, v in (pq.read_schema(path).metadata or {}).items() if k.startswith(b'flash_chord.')}
        if md.get('flash_chord.checkpoint_sha256') != ck: say(f'ep{n}: parquet checkpoint stamp != json'); sys.exit(1)
        for c in ('eval_code_sha256', 'eval_script_sha256', 'reference_parquet'):
            if md.get(f'flash_chord.{c}'): meta[c] = md[f'flash_chord.{c}']
        r = subprocess.run([sys.executable, f'{REPO}/tools/no_oracle.py', path, js] +
                           ([meta['reference_parquet']] if meta.get('reference_parquet') else []), capture_output=True, text=True)
        if r.returncode: say('REFUSED by no_oracle:', r.stdout[-300:], r.stderr[-300:]); sys.exit(1)
        if n in map(int, exp) and exp[str(n)] != ck: say(f'ep{n}: checkpoint {ck} != expected {exp[str(n)]}'); sys.exit(1)
        m = key.e == n; rows = base[m]
        if (rows.checkpoint_sha256 == ck).any() and n not in a.same_checkpoint: say(f'ep{n}: the swap has the base checkpoint'); sys.exit(1)
        if n in a.same_checkpoint and set(rows.checkpoint_sha256) != {ck}: say(f'ep{n}: --same-checkpoint but the checkpoint differs'); sys.exit(1)
        for c in ('eval_code_sha256', 'eval_script_sha256'):
            if not meta.get(c) or set(rows[c]) != {meta[c]}:
                say(f'ep{n}: {c} differs from the base rows ({meta[c]} vs {set(rows[c])})'); sys.exit(1)
        ro = pd.read_parquet(path)
        k = key[m]; idx = pd.MultiIndex.from_arrays([k.w, k.f, k.o])
        rv = ro.set_index(['environment_id', 'reference_frame', 'object_id'])
        if set(map(tuple, rv.index)) != set(map(tuple, idx)) or len(rv) != len(idx):
            say(f'ep{n}: rollout keys do not match the base episode rows ({len(rv)} vs {len(idx)})'); sys.exit(1)
        vals = rv.loc[idx, ACH].to_numpy()
        if not np.isfinite(vals).all(): say(f'ep{n}: non-finite poses'); sys.exit(1)
        for c, j in zip(POSE, range(7)):
            out.loc[m, c] = vals[:, j].astype(base[c].dtype)
        out.loc[m, 'checkpoint_sha256'] = ck
        manifest['swaps'][n] = dict(rollout=path, rollout_sha256=sha(path), json_sha256=sha(js), checkpoint_sha256=ck,
                                    rows=int(m.sum()), pose_rows_changed=int((out.loc[m, POSE] != base.loc[m, POSE]).any(axis=1).sum()))
        say(f'ep{n}: {int(m.sum())} rows, checkpoint {rows.checkpoint_sha256.iloc[0][:12]} -> {ck[:12]}, pose rows changed',
            manifest['swaps'][n]['pose_rows_changed'])
    out['code_commit_url'] = a.code_commit
    # checks vs base
    assert list(out.columns) == list(base.columns) and (out.row_id == base.row_id).all() and (out.dtypes == base.dtypes).all()
    sw_eps = set(int(x.split('=', 1)[0]) for x in a.swap)
    for c in out.columns:
        if c in ('code_commit_url',): continue
        diff = out[c] != base[c]
        if c in POSE + ['checkpoint_sha256']:
            bad = diff & ~key.e.isin(sw_eps)
            if bad.any(): say('CHECK FAILED: column', c, 'differs outside the swapped episodes'); sys.exit(1)
        elif diff.any():
            say('CHECK FAILED: column', c, 'differs'); sys.exit(1)
    f = os.path.join(a.o, 'track3_submission.parquet'); out.to_parquet(f, index=False)
    say('wrote', f, 'sha256', sha(f), 'rows', len(out))
    # kit offline validation + CD-O (as tools/pack_swap_rollouts.py step 5)
    ok = True
    try:
        import importlib.util
        from pathlib import Path
        sys.path.insert(0, a.kit)
        spec = importlib.util.spec_from_file_location('v2d_submit_offline', os.path.join(a.kit, 'submit', 'v2d_submit.py'))
        sub = importlib.util.module_from_spec(spec); spec.loader.exec_module(sub)
        from v2dlb.track3_pose import cd_o_submission
        config = json.load(open(os.path.join(a.kit, 'config', 'tracks.json')))
        roster = json.load(open(os.path.join(a.kit, 'data', 'track_3_evaluation_objects.json')))['episodes']
        frame = sub.validate_submission(Path(f), 'track_3', config)
        sample = pd.read_parquet(os.path.join(a.kit, 'data', 'track_3_mesh_sample_submission.parquet'))
        cdo = cd_o_submission(frame, sample, roster); cp = os.path.join(a.o, 'track3_submission.cd-o.parquet')
        cdo.to_parquet(cp, index=False); sub.validate_submission(Path(cp), 'track_3_mesh', config)
        cb = pd.read_parquet(a.base_cdo)
        same = len(cdo) == len(cb) and (cdo.row_id.values == cb.row_id.values).all()
        nd = int((cdo[['x', 'y', 'z']].values != cb[['x', 'y', 'z']].values).any(axis=1).sum()) if same else -1
        say('uploader offline validation pass; CD-O', cp, 'sha256', sha(cp), 'rows changed vs base CD-O', nd)
        manifest['cd_o'] = dict(sha256=sha(cp), rows=len(cdo), rows_changed_vs_base=nd)
        ok = nd == 0
    except (SystemExit, Exception) as e:
        say('uploader offline validation FAILED:', type(e).__name__, str(e)[:400]); ok = False
    manifest['checks_pass'] = ok; manifest['out_sha256'] = sha(f)
    json.dump(manifest, open(os.path.join(a.o, 'swap_manifest.json'), 'w'), indent=1, default=str)
    open(os.path.join(a.o, 'pack.log'), 'w').write('\n'.join(log) + '\n')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
