#!/usr/bin/env python3
"""Repack a Track 3 submission with some episodes' rollouts replaced (pack 9b: pack 9a+ + PASS D draw-1 rollouts).

Written 1 Nov 2026 (pack 9b, docs/research/work/pack9b-20261031/BUILD.md item 8). Sibling of tools/pack_swap_meshes.py:
that tool swaps meshes and refuses any pose change; this one swaps rollouts and refuses any mesh change.

Steps (CPU, no ground truth read: the packer reads row_id from the kit's sample submission plus the roster):
 1. tools/no_oracle.py on the base results, the base meshes and every swap file (refuses mocap / oracle runs and the
    eval-10 njmax diagnostic's runs), plus each swap parquet's flash_chord.reference_parquet path (the reference the
    evaluated checkpoint trained on, e.g. refs/perc2e10njs43_glockt: caught even when the rollout is renamed);
 2. OUT/results = a byte copy of --results with, per --swap N=<rollout.parquet>, episode_<N6>.parquet and
    episode_<N6>.json replaced by that rollout and the .json next to it (same stem); OUT/meshes = a byte copy of --meshes
    (never modified). Each swap's .json must name a checkpoint_sha256 that differs from the base rollout's (a swap is a
    different policy), and equal --expect-checkpoint N=<sha256> when given; the swap parquet's flash_chord.* metadata
    (read by the packer before the .json) must carry that same checkpoint and the base rollout's eval_code_sha256 and
    eval_script_sha256 (the same official evaluator);
 3. the kit packer (tools/pack_submission.py; cwd = kit; --python, with -I), exactly as pack 7 / 8 / 9a+ were packed;
 4. checks against --base (e.g. pack 9a+): same row count, row_id order, columns and schema; code_commit_url equal to
    --code-commit on every row; object_mesh_b64 and every column other than the pose columns, checkpoint_sha256 and
    code_commit_url identical on every row; pose columns and checkpoint_sha256 may differ only on rows of a swapped
    episode; checkpoint_sha256 on every row of a swapped episode equals that swap's .json; rows of every other episode
    are identical in every column except code_commit_url;
 5. the uploader's offline steps (kit submit/v2d_submit.py validate_submission, then cd_o_submission ->
    OUT/track3_submission.cd-o.parquet validated as track_3_mesh; no Kaggle call). Meshes are unchanged, so the CD-O
    file must equal the one derived from --base row for row.
With no --swap it is a pure repack: with the base's own commit URL it must rebuild the base byte for byte (self-test).
Exit 0: checks pass. 1: a hard failure (the output folder stays for inspection; nothing is uploaded, ever).
Run it with the packing venv (pandas 3.0.6 / pyarrow 26.0.0 / numpy 2.5.4 / trimesh 5.2.0 / fast_simplification 0.2.0):
  PY -I tools/pack_swap_rollouts.py --kit KIT --results DIR --meshes DIR --base BASE.parquet --code-commit URL \
     [--swap N=PATH.parquet ...] [--expect-checkpoint N=SHA256 ...] -o OUT
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESH_COL, COMMIT_COL, CKPT_COL = 'object_mesh_b64', 'code_commit_url', 'checkpoint_sha256'
POSE_COLS = ('pos_x', 'pos_y', 'pos_z', 'quat_x', 'quat_y', 'quat_z', 'quat_w')
ROW_RE = r'^track_3/e(\d+)/w\d+/f\d+/o(\d+)$'
EVAL_KEYS = ('eval_code_sha256', 'eval_script_sha256')


def _no_oracle():  # tools/no_oracle.py as a module (for its ALLOW_CKPT, the single owner-approved checkpoint exception)
    import importlib.util
    spec = importlib.util.spec_from_file_location('no_oracle_mod', os.path.join(REPO, 'tools', 'no_oracle.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def flash_meta(path):
    """The rollout parquet's flash_chord.* schema metadata (where the packer reads the hashes first)."""
    import pyarrow.parquet as pq
    m = pq.read_schema(path).metadata or {}
    return {k.decode()[len('flash_chord.'):]: v.decode() for k, v in m.items() if k.startswith(b'flash_chord.')}


def digest(path, algo='md5'):
    h = hashlib.new(algo)
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def kv(items, what):
    out = {}
    for x in items or []:
        if '=' not in x:
            raise SystemExit(f'error: {what} {x!r} is not N=VALUE')
        k, v = x.split('=', 1)
        if not k.strip().isdigit():
            raise SystemExit(f'error: {what} {x!r}: N must be an episode number')
        n = int(k)
        if n in out:
            raise SystemExit(f'error: {what} names episode {n} twice')
        out[n] = v.strip()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--kit', required=True, help='v2d_submission_kit root (packer, roster, v2dlb)')
    ap.add_argument('--results', required=True, help="the base pack's rollouts: episode_XXXXXX.{json,parquet}")
    ap.add_argument('--meshes', required=True, help="the base pack's meshes: episode_XXXXXX/<object>.glb (copied as is)")
    ap.add_argument('--swap', action='append', default=[], help='N=<episode_XXXXXX.parquet> (its .json beside it)')
    ap.add_argument('--expect-checkpoint', action='append', default=[], help='N=<sha256> the swap .json must name')
    ap.add_argument('--base', required=True, help='base packed parquet to check against (e.g. pack 9a+)')
    ap.add_argument('--code-commit', required=True)
    ap.add_argument('--python', default=sys.executable, help='interpreter for the kit packer')
    ap.add_argument('-o', '--out', required=True, help='new output folder (must not exist)')
    ap.add_argument('--skip-no-oracle', action='store_true', help='tests only')
    args = ap.parse_args()

    kit, out = os.path.abspath(args.kit), os.path.abspath(args.out)
    sys.path.insert(0, kit)
    if os.path.exists(out):
        raise SystemExit(f'error: {out} exists; runs are never overwritten, pick a new folder')
    if not re.match(r'^https://github\.com/[\w.-]+/[\w.-]+/commit/[0-9a-f]{40}$', args.code_commit.strip()):
        raise SystemExit('error: --code-commit must be https://github.com/<owner>/<repo>/commit/<40-hex sha>')
    commit = args.code_commit.strip()
    roster = json.load(open(os.path.join(kit, 'data', 'track_3_evaluation_objects.json')))['episodes']
    roster_eps = sorted(int(e) for e in roster)
    swaps, expect = kv(args.swap, '--swap'), kv(args.expect_checkpoint, '--expect-checkpoint')
    if set(expect) - set(swaps):
        raise SystemExit(f'error: --expect-checkpoint for episodes not swapped: {sorted(set(expect) - set(swaps))}')
    swap_files = {}
    for n, p in sorted(swaps.items()):
        if n not in roster_eps:
            raise SystemExit(f'error: --swap episode {n} is not a roster episode')
        p = os.path.abspath(p)
        if not re.search(rf'episode_{n:06d}\.parquet$', p):
            raise SystemExit(f'error: --swap {n}: {p} is not an episode_{n:06d}.parquet')
        j = p[:-len('.parquet')] + '.json'
        for f in (p, j):
            if not os.path.isfile(f):
                raise SystemExit(f'error: --swap {n}: missing {f}')
        swap_files[n] = (p, j)

    if not args.skip_no_oracle:
        # The swap's reference path is passed to no_oracle as a word (it catches a renamed rollout), EXCEPT for a swap whose
        # own rollout names the one owner-approved checkpoint in tools/no_oracle.py ALLOW_CKPT: that rollout itself is still
        # checked (and accepted only by that exact sha256), its box-side reference path is not.
        allow_ckpt = _no_oracle().ALLOW_CKPT
        meta_words = [m[k] for pj in swap_files.values() for m in [flash_meta(pj[0])] for k in ('reference_parquet',)
                      if m.get(k) and m.get('checkpoint_sha256') not in allow_ckpt]
        guard = subprocess.run([sys.executable, '-I', os.path.join(REPO, 'tools', 'no_oracle.py'),
                                os.path.abspath(args.results), os.path.abspath(args.meshes),
                                *[f for pj in swap_files.values() for f in pj], *meta_words], capture_output=True, text=True)
        print(guard.stdout.strip() or guard.stderr.strip())
        if guard.returncode:
            raise SystemExit('error: tools/no_oracle.py refused an input; nothing was built')

    hard, info, swapped = [], [], []
    base_res = os.path.abspath(args.results)
    for n, (p, j) in sorted(swap_files.items()):
        bj = os.path.join(base_res, f'episode_{n:06d}.json')
        if not os.path.isfile(bj):
            raise SystemExit(f'error: base results lack episode_{n:06d}.json')
        old, new = json.load(open(bj)), json.load(open(j))
        ck_old, ck_new = str(old.get(CKPT_COL, '')).strip(), str(new.get(CKPT_COL, '')).strip()
        if not re.fullmatch(r'[0-9a-f]{64}', ck_new):
            raise SystemExit(f'error: --swap {n}: {j} names no checkpoint_sha256')
        if ck_new == ck_old:
            raise SystemExit(f'error: --swap {n}: the swap names the base checkpoint {ck_new[:12]}… (not a different policy)')
        if n in expect and ck_new != expect[n]:
            raise SystemExit(f'error: --swap {n}: checkpoint {ck_new[:12]}… is not the expected {expect[n][:12]}…')
        # The packer takes the hashes from the rollout parquet's flash_chord.* metadata first (the .json is only a
        # fallback for the checkpoint), so the swap's metadata must carry the same checkpoint as its .json and the
        # base rollout's evaluator hashes (same official evaluator pin).
        meta_new, meta_old = flash_meta(p), flash_meta(os.path.join(base_res, f'episode_{n:06d}.parquet'))
        if meta_new.get(CKPT_COL) != ck_new:
            raise SystemExit(f'error: --swap {n}: parquet metadata checkpoint {str(meta_new.get(CKPT_COL))[:12]}… '
                             f'is not the .json checkpoint {ck_new[:12]}…')
        for key in EVAL_KEYS:
            if not meta_new.get(key) or meta_new.get(key) != meta_old.get(key):
                raise SystemExit(f'error: --swap {n}: {key} {str(meta_new.get(key))[:12]}… is not the base rollout\'s '
                                 f'{str(meta_old.get(key))[:12]}… (a different evaluator)')
        swapped.append({'episode': n, 'parquet': p, 'json': j, 'parquet_md5': digest(p), 'json_md5': digest(j),
                        'checkpoint_before': ck_old, 'checkpoint_after': ck_new,
                        'eval_hashes': {k: meta_new[k] for k in EVAL_KEYS},
                        'base_parquet_md5': digest(os.path.join(base_res, f'episode_{n:06d}.parquet'))})

    os.makedirs(out)
    shutil.copytree(args.results, os.path.join(out, 'results'))
    shutil.copytree(args.meshes, os.path.join(out, 'meshes'))
    for s in swapped:
        stem = os.path.join(out, 'results', f"episode_{s['episode']:06d}")
        shutil.copy2(s['parquet'], stem + '.parquet')
        shutil.copy2(s['json'], stem + '.json')
    results = {n: digest(os.path.join(out, 'results', n)) for n in sorted(os.listdir(os.path.join(out, 'results')))}
    eps_results = sorted(int(m.group(1)) for n in results for m in [re.match(r'episode_(\d+)\.parquet$', n)] if m)
    if eps_results != roster_eps:
        raise SystemExit(f'error: results episodes {eps_results} differ from the roster {roster_eps}')
    parquet = os.path.join(out, 'track3_submission.parquet')
    cmd = [args.python, '-I', 'tools/pack_submission.py', '--track', 'track_3', '--results', os.path.join(out, 'results'),
           '--meshes', os.path.join(out, 'meshes'), '--code-commit', commit,
           '--eval-script', os.path.join(kit, 'flash_chord', 'scripts', 'evaluate_policy.py'), '-o', parquet]
    with open(os.path.join(out, 'pack.log'), 'w') as log:
        rc = subprocess.run(cmd, cwd=kit, stdout=log, stderr=subprocess.STDOUT).returncode
    packlog = open(os.path.join(out, 'pack.log')).read()
    warnings = [l for l in packlog.splitlines() if 'MESH WARNING' in l]
    if rc or not os.path.exists(parquet):
        hard.append(f'packer exit {rc}: ' + ' | '.join(packlog.strip().splitlines()[-3:]))
    if warnings:
        hard.append(f'{len(warnings)} MESH WARNING lines in pack.log (meshes are copied unchanged; the base had none)')

    check = {}
    if not hard:
        import pyarrow.parquet as pq
        ta, tb = pq.read_table(args.base), pq.read_table(parquet)
        a, b = ta.to_pandas(), tb.to_pandas()
        check['rows'] = [len(a), len(b)]
        if len(a) != len(b):
            hard.append(f'row count {len(b)} != base {len(a)}')
        elif not (a.row_id.values == b.row_id.values).all():
            hard.append('row_id order differs from the base')
        if list(a.columns) != list(b.columns) or ta.schema.remove_metadata() != tb.schema.remove_metadata():
            hard.append(f'columns/schema differ: {list(a.columns)} vs {list(b.columns)}')
        if not hard:
            ep = b.row_id.str.extract(ROW_RE)[0].astype(int).values
            in_swap = np.isin(ep, [s['episode'] for s in swapped])
            diff_cols, per_ep = {}, {}
            for c in b.columns:
                x, y = a[c].values, b[c].values
                same = ((x == y) | (np.isnan(x) & np.isnan(y))) if x.dtype.kind == 'f' else (x == y)
                if (~same).any():
                    diff_cols[c] = int((~same).sum())
                    if c != COMMIT_COL:
                        for e in sorted(set(ep[~same])):
                            per_ep.setdefault(int(e), {})[c] = int(((~same) & (ep == e)).sum())
                if c == COMMIT_COL:
                    continue
                if c in POSE_COLS or c == CKPT_COL:
                    bad = ~same & ~in_swap
                    if bad.any():
                        hard.append(f'column {c} differs on {int(bad.sum())} rows of unswapped episodes '
                                    f'{sorted({int(e) for e in ep[bad]})}')
                elif (~same).any():
                    hard.append(f'column {c} differs on {int((~same).sum())} rows (only pose columns, {CKPT_COL} on '
                                f'swapped episodes and {COMMIT_COL} may)')
            check['columns_differing'] = diff_cols
            check['differing_by_episode'] = {str(k): v for k, v in sorted(per_ep.items())}
            if not (b[COMMIT_COL] == commit).all():
                hard.append(f'{COMMIT_COL} is not {commit} on every row')
            for s in swapped:
                rows = ep == s['episode']
                s['rows'] = int(rows.sum())
                s['pose_rows_changed'] = int((~np.all([(a[c].values == b[c].values) for c in POSE_COLS], axis=0) & rows).sum())
                if not (b[CKPT_COL].values[rows] == s['checkpoint_after']).all():
                    hard.append(f"episode {s['episode']}: {CKPT_COL} is not the swap's checkpoint on every row")
                if s['pose_rows_changed'] == 0:
                    info.append(f"episode {s['episode']}: no pose row changed (the swap rollout equals the base's)")
            ma = json.loads(ta.schema.metadata[b'pandas']).get('pandas_version') if ta.schema.metadata else None
            mb = json.loads(tb.schema.metadata[b'pandas']).get('pandas_version') if tb.schema.metadata else None
            check['pandas_version'] = [ma, mb]
            if ma != mb:
                info.append(f'schema metadata pandas_version {mb} vs base {ma} (metadata only; table content compared)')
        try:
            import importlib.util
            from pathlib import Path
            spec = importlib.util.spec_from_file_location('v2d_submit_offline', os.path.join(kit, 'submit', 'v2d_submit.py'))
            sub = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sub)
            from v2dlb.track3_pose import cd_o_submission
            import pandas as pd
            config = json.load(open(os.path.join(kit, 'config', 'tracks.json')))
            frame = sub.validate_submission(Path(parquet), 'track_3', config)
            sample = pd.read_parquet(os.path.join(kit, 'data', 'track_3_mesh_sample_submission.parquet'))
            cdo = cd_o_submission(frame, sample, roster)
            cdo_path = os.path.join(out, 'track3_submission.cd-o.parquet')
            cdo.to_parquet(cdo_path, index=False)
            sub.validate_submission(Path(cdo_path), 'track_3_mesh', config)
            cdo_base = cd_o_submission(pd.read_parquet(args.base), sample, roster)
            same_ids = (cdo.row_id.values == cdo_base.row_id.values).all() if len(cdo) == len(cdo_base) else False
            cdo_diff = int((cdo[['x', 'y', 'z']].values != cdo_base[['x', 'y', 'z']].values).any(axis=1).sum()) if same_ids else -1
            check['uploader_validation'] = 'pass (offline validate_submission; CD-O file derived and validated)'
            check['cd_o_file'] = {'path': cdo_path, 'rows': len(cdo), 'sha256': digest(cdo_path, 'sha256'),
                                  'rows_changed_vs_base': cdo_diff}
            if cdo_diff != 0:
                hard.append(f'CD-O file differs from the base-derived one ({cdo_diff} rows; meshes are unchanged)')
        except (SystemExit, Exception) as error:                      # noqa: BLE001 - any failure here is hard
            hard.append(f'uploader offline validation failed: {type(error).__name__}: {error}')
        check['sha256'] = digest(parquet, 'sha256')
        check['base_sha256'] = digest(args.base, 'sha256')
        check['bytes'] = os.path.getsize(parquet)
        check['byte_identical_to_base'] = check['sha256'] == check['base_sha256']
    check['mesh_warnings'] = warnings
    status = 1 if hard else 0

    import importlib.metadata as md
    versions = {}
    for pkg in ('pandas', 'pyarrow', 'numpy', 'scipy', 'trimesh', 'fast_simplification'):
        try:
            versions[pkg] = md.version(pkg)
        except Exception:
            versions[pkg] = None
    manifest = {'tool': 'tools/pack_swap_rollouts.py', 'argv': sys.argv, 'python': sys.version.split()[0],
                'versions': versions, 'kit': kit, 'results': base_res, 'meshes': os.path.abspath(args.meshes),
                'base': os.path.abspath(args.base), 'code_commit': commit, 'packer_command': cmd, 'packer_cwd': kit,
                'results_md5': results, 'swaps': swapped, 'check': check, 'hard_failures': hard, 'info': info,
                'status': status}
    with open(os.path.join(out, 'swap_manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)
    lines = [f"pack_swap_rollouts: status {status} ({'HARD FAILURE' if hard else 'checks pass'})",
             f"swapped episodes: {[s['episode'] for s in swapped] or 'none (pure repack)'}"]
    for s in swapped:
        lines.append(f"  ep{s['episode']}: checkpoint {s['checkpoint_before'][:12]}… -> {s['checkpoint_after'][:12]}… | "
                     f"rows {s.get('rows')} pose rows changed {s.get('pose_rows_changed')} | rollout md5 {s['parquet_md5']}")
    lines.append(f"parquet: {check.get('bytes')} B sha256 {check.get('sha256')} | byte-identical to base: "
                 f"{check.get('byte_identical_to_base')} | rows {check.get('rows')} | columns differing from base: "
                 f"{check.get('columns_differing')}")
    if 'cd_o_file' in check:
        c = check['cd_o_file']
        lines.append(f"uploader: {check.get('uploader_validation')} | CD-O {c['rows']} rows sha256 {c['sha256'][:16]}... | "
                     f"rows changed vs base: {c['rows_changed_vs_base']}")
    lines += [f'HARD: {h}' for h in hard] + [f'info: {i}' for i in info]
    open(os.path.join(out, 'summary.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return status


if __name__ == '__main__':
    sys.exit(main())
