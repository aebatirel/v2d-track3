"""Inputs of the eval-episode physics solve (2026-10-31, ops/jobs/eval_solve.sh; physics-solver.md section 9 "Actions").
Which store files a grasp-lock eval episode's solve needs, and a check that what was pulled is exactly what the packed
policy trained on. Reads our own references, URDFs and the pack builder's table only; NO ground truth (eval episodes have
none; no mocap, no `pose` field of observation.objects is opened).

Table: docs/research/physics-2026-10-30/eval_solve/packed_refs.json (byte copy of focused-pascal's
docs/research/work/masses-eval-20261031/packed_refs.json): per eval episode the packed policy's grasp-lock reference
(source_run, reference, md5, asset_root, lib, pieces, pull_files).

  eval_inputs.py files TAB EP [--root /content] [--ref STORE_PATH] [--stage STORE_PATH] [--extra "STORE_PATH ..."]
      prints "<store path>\t<local path>" per file to pull, the reference first. Table mode: the table's pull_files under
      runs/<source_run>/refs/glockt/ep<N>/ (reference + support stage) and, when the reference has its own asset copy,
      under runs/<source_run>/<asset_root>/ (URDFs + meshes). Override (--ref, e.g. eval 10's V4p reference): that
      parquet, its support stage <base>/reconstructed_stage/<seq>_support.usda (or --stage) and --extra files
      (e.g. its own asset copy). Local path = ROOT/<path inside the run>, as store.sh pull-run places files.
  eval_inputs.py assets TAB "EP:PARQUET ..." [--root /content] [--lib L] [--pieces P]
      prints "LIB=<dir name> PIECES=<repo-relative dir or empty>" for the box's shared ROOT/assets (make_assets.py), or
      "LIB= PIECES=" when no reference names it; exit 1 when the references need different builds of it.
  eval_inputs.py check TAB EP PARQUET [--root /content] [--want_md5 X] [--override] --out JSON
      md5 (table mode: must equal the table's; override: must equal --want_md5 if given), objects (table mode: as the
      table), every object URDF exists under the expected asset root (table mode: the table's asset_root) and every mesh
      a URDF names exists, the support stage FlashCHORD will load exists; writes JSON with md5s of the reference, the
      stage and every asset file the URDFs use. Exit 0 = OK, 2 = refused (reason in the JSON and on stderr).
"""
import argparse, glob, hashlib, json, os, re, sys


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def table(tab, ep):
    d = json.load(open(tab))['episodes']
    if str(ep) not in d:
        sys.exit(f'episode {ep} is not in {tab}')
    r = d[str(ep)]
    if r['mode'] != 'glock':
        sys.exit(f'episode {ep} is a {r["mode"]} episode, not grasp lock (out of scope)')
    return r


def run_rel(store_path):
    """runs/<run>/<rel> -> (run, rel)."""
    p = store_path.split('/')
    if len(p) < 3 or p[0] != 'runs':
        sys.exit(f'not a store run path: {store_path}')
    return p[1], '/'.join(p[2:])


def hive(rel):
    """<base>/processed/sequence_id=<seq>/robot_name=<robot>/<file> -> (base, seq, robot)."""
    m = re.match(r'(.*)/processed/sequence_id=([^/]+)/robot_name=([^/]+)/[^/]+\.parquet$', rel)
    if not m:
        sys.exit(f'not a reference path <base>/processed/sequence_id=<seq>/robot_name=<robot>/<file>.parquet: {rel}')
    return m.group(1), m.group(2), m.group(3)


def to_local(rel, root):
    return os.path.join(root, rel)


def cmd_files(a):
    r = table(a.tab, a.ep)
    out = []
    if a.ref:                                            # override (e.g. eval 10's V4p reference)
        run, rel = run_rel(a.ref); base, seq, _ = hive(rel)
        stage = a.stage or f'runs/{run}/{base}/reconstructed_stage/{seq}_support.usda'
        for f in [a.ref, stage] + (a.extra.split() if a.extra else []):
            out.append((f, to_local(run_rel(f)[1], a.root)))
    else:
        pre = f"runs/{r['source_run']}/"
        keep = [pre + f'refs/glockt/ep{a.ep}/']
        if not r['shared_assets']:
            ar = r['asset_root']
            if not ar.startswith('/content/'):
                sys.exit(f'asset_root {ar} is not under /content')
            keep.append(pre + ar[len('/content/'):].rstrip('/') + '/')
        sel = [f for f in r['pull_files'] if any(f.startswith(k) for k in keep)]
        if pre + r['reference'] not in sel:
            sys.exit(f"the table's reference {pre + r['reference']} is not among its pull_files")
        sel = [pre + r['reference']] + [f for f in sel if f != pre + r['reference']]   # the reference first
        out = [(f, to_local(f[len(pre):], a.root)) for f in sel]
    for f, l in out:                                     # line 1 = the reference
        print(f'{f}\t{l}')


def urdf_paths(parquet):
    import pyarrow.parquet as pq
    t = pq.read_table(parquet, columns=['object_urdf_paths', 'object_body_names', 'robot_left_wrist_position'])
    return t.column('object_urdf_paths')[0].as_py(), t.column('object_body_names')[0].as_py(), len(t.column('robot_left_wrist_position')[0].as_py())


def local(p, root):
    """A reference names absolute box paths (/content/...); under a test root they live at ROOT/..."""
    return os.path.join(root, p[len('/content/'):]) if p.startswith('/content/') else p


def cmd_assets(a):
    need = set()
    for spec in a.pairs.split():
        ep, _, pq_ = spec.partition(':')
        r = table(a.tab, ep)
        try:
            urdfs, _, _ = urdf_paths(pq_)
        except Exception as ex:                          # unreadable: refused later by `check` (md5)
            print(f'ep{ep}: {pq_} unreadable ({str(ex)[:120]}); not counted here', file=sys.stderr); continue
        roots = {os.path.dirname(os.path.dirname(u)) for u in urdfs}
        if '/content/assets' in roots:
            need.add((a.lib or r['lib'], a.pieces if a.pieces is not None else (r['pieces'] or '')))
    if len(need) > 1:
        print(f'conflict: the references naming /content/assets need different builds {sorted(need)}', file=sys.stderr); sys.exit(1)
    lib, pieces = need.pop() if need else ('', '')
    print(f'LIB={lib} PIECES={pieces}')


def cmd_check(a):
    r = table(a.tab, a.ep); res = dict(ep=int(a.ep), parquet=a.parquet, mode='override' if a.override else 'table', ok=False)

    def refuse(msg):
        res['refused'] = msg; json.dump(res, open(a.out, 'w'), indent=1); print(f'REFUSED ep{a.ep}: {msg}', file=sys.stderr); sys.exit(2)
    if not os.path.isfile(a.parquet):
        refuse(f'no reference file {a.parquet}')
    res['md5'] = m = md5(a.parquet)
    want = a.want_md5 if a.override else r['md5']
    res['want_md5'] = want or None
    if want and m != want:
        refuse(f'reference md5 {m} != expected {want}')
    urdfs, names, T = urdf_paths(a.parquet); res.update(objects=names, frames=T, urdf_paths=urdfs)
    if not a.override and names != r['objects']:
        refuse(f'objects {names} != the table\'s {r["objects"]}')
    roots = sorted({os.path.dirname(os.path.dirname(u)) for u in urdfs}); res['asset_roots'] = roots
    if not a.override and roots != [r['asset_root'].rstrip('/')]:
        refuse(f'asset roots {roots} != the table\'s {r["asset_root"]}')
    files = {}
    for u in urdfs:
        lu = local(u, a.root)
        if not os.path.isfile(lu):
            refuse(f'object URDF missing: {u}')
        files[u] = md5(lu)
        for mf in re.findall(r'filename="([^"]+)"', open(lu).read()):
            p = os.path.normpath(os.path.join(os.path.dirname(u), mf)); lp = local(p, a.root)
            if not os.path.isfile(lp):
                refuse(f'{u} names {mf}, missing ({p})')
            files[p] = md5(lp)
        res.setdefault('masses', {})[os.path.basename(u)] = re.findall(r'<mass value="([^"]+)"', open(lu).read())
    res['asset_files'] = files
    res['asset_digest'] = hashlib.md5(''.join(f'{k} {v}\n' for k, v in sorted(files.items())).encode()).hexdigest()
    seqd = os.path.dirname(os.path.dirname(os.path.abspath(a.parquet)))     # .../processed/sequence_id=<seq>
    seq = os.path.basename(seqd).split('=', 1)[1]; robot = os.path.basename(os.path.dirname(os.path.abspath(a.parquet))).split('=', 1)[1]
    sdir = os.path.join(os.path.dirname(os.path.dirname(seqd)), 'reconstructed_stage')
    cands = [os.path.join(sdir, f'{seq}_{robot}_support.usda'), os.path.join(sdir, f'{seq}_support.usda')]
    st = next((c for c in cands if os.path.isfile(c)), None)
    if st is None:
        refuse(f'no support stage {cands[-1]} (FlashCHORD would fall back to another stage)')
    res['stage'] = st; res['stage_md5'] = md5(st)
    res['parquets_in_dir'] = sorted(os.path.basename(x) for x in glob.glob(os.path.join(os.path.dirname(a.parquet), '*.parquet')))
    res['table'] = {k: r.get(k) for k in ('source_run', 'reference', 'md5', 'traj_fingerprint', 'asset_root', 'lib', 'pieces',
                                          'packed_run', 'packed_checkpoint', 'packed_sha256', 'frames', 'env')}
    res['ok'] = True
    json.dump(res, open(a.out, 'w'), indent=1)
    print(f"ep{a.ep}: reference {m} ({res['mode']}), {T} frames, objects {names}, assets {roots} ({len(files)} files, digest "
          f"{res['asset_digest'][:12]}), stage {os.path.basename(st)} {res['stage_md5'][:12]}")


def main():
    p = argparse.ArgumentParser(); s = p.add_subparsers(dest='cmd', required=True)
    f = s.add_parser('files'); f.add_argument('tab'); f.add_argument('ep'); f.add_argument('--root', default='/content')
    f.add_argument('--ref', default=''); f.add_argument('--stage', default=''); f.add_argument('--extra', default='')
    b = s.add_parser('assets'); b.add_argument('tab'); b.add_argument('pairs'); b.add_argument('--root', default='/content')
    b.add_argument('--lib', default=''); b.add_argument('--pieces', default=None)
    c = s.add_parser('check'); c.add_argument('tab'); c.add_argument('ep'); c.add_argument('parquet')
    c.add_argument('--root', default='/content'); c.add_argument('--want_md5', default=''); c.add_argument('--override', action='store_true')
    c.add_argument('--out', required=True)
    a = p.parse_args()
    dict(files=cmd_files, assets=cmd_assets, check=cmd_check)[a.cmd](a)


if __name__ == '__main__':
    main()
