"""One-time public roster: object names in slot order from the public parquets, names only (module M0r of SPEC v1
rev 1, sections 3 and 7; build step B0).

The public parquets hold ground truth (observation.objects[].pose). The gmg never opens them: its guard refuses every
'.parquet' path. This tool is the one exception, run once in its own audited process, and it reads only the leaf
column observation.objects.list.element.name by column projection (pyarrow reads the footer and that one column
chunk; the pose and visible chunks are never read or decoded). The gmg then reads only gmg/roster_public.json.

  roster_public.py fetch   --dest DIR             download the 20 public parquets (HF nvidia/video_to_data_challenge,
                                                  track_3/public/data/chunk-000) into a new empty folder
  roster_public.py build   --src DIR --out JSON   the names-only reader (run it under the audit, below)
  roster_public.py audited --src DIR --out JSON --log LOG [--delete-src]
                                                  build under tools/strace_audit.py (policy roster: the process may
                                                  read the --src parquets and write --out, nothing else), then add the
                                                  audit summary and the code commit to JSON; --delete-src removes the
                                                  parquets afterwards

This file imports neither gmg nor its guard (the guard's open hook would refuse the parquets).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

HF = 'https://huggingface.co'
DATASET = 'nvidia/video_to_data_challenge'
PREFIX = 'track_3/public/data/chunk-000'
LEAF = 'observation.objects.list.element.name'
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
AUDIT = os.path.join(HERE, 'strace_audit.py')
EP = re.compile(r'^episode_(\d{6})\.parquet$')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def fetch(dest):
    if os.path.isdir(dest) and os.listdir(dest):
        sys.exit(f'fetch: {dest} is not empty (downloads go into a new empty folder)')
    os.makedirs(dest, exist_ok=True)
    with urllib.request.urlopen(f'{HF}/api/datasets/{DATASET}/tree/main/{PREFIX}') as r:
        tree = json.load(r)
    files = sorted(x['path'] for x in tree if x.get('type') == 'file' and x['path'].endswith('.parquet'))
    out = []
    for p in files:
        name = os.path.basename(p)
        if not EP.match(name):
            continue
        dst = os.path.join(dest, name)
        subprocess.run(['curl', '-sSLf', '-o', dst, f'{HF}/datasets/{DATASET}/resolve/main/{p}'], check=True)
        out.append(dict(name=name, bytes=os.path.getsize(dst), sha256=sha256(dst)))
    print(json.dumps(dict(dest=dest, files=len(out), bytes=sum(x['bytes'] for x in out))))
    return out


def build(src, out):
    import pyarrow
    import pyarrow.parquet as pq
    names = sorted(n for n in os.listdir(src) if EP.match(n))
    if not names:
        sys.exit(f'build: no episode_*.parquet in {src}')
    episodes, files = {}, {}
    for n in names:
        ep = int(EP.match(n).group(1))
        path = os.path.join(src, n)
        pf = pq.ParquetFile(path)
        schema = pf.metadata.schema
        leaves = [schema.column(i).path for i in range(len(schema))]
        if LEAF not in leaves:
            sys.exit(f'build: {n} has no leaf {LEAF} (leaves {leaves})')
        t = pf.read(columns=[LEAF], use_threads=False)
        # the projection must hold the name leaf only: no pose, no visible
        flat = []

        def walk(tp, pre):
            if pyarrow.types.is_struct(tp):
                for f in tp:
                    walk(f.type, f'{pre}.{f.name}')
            elif pyarrow.types.is_list(tp) or pyarrow.types.is_large_list(tp):
                walk(tp.value_type, pre + '[]')
            else:
                flat.append(pre)
        for f in t.schema:
            walk(f.type, f.name)
        if len(flat) != 1 or 'pose' in flat[0] or 'visible' in flat[0] or not flat[0].endswith('.name'):
            sys.exit(f'build: projection of {n} is not names-only: {flat}')
        rows = t.column(0).to_pylist()
        slots = [tuple(o['name'] for o in (r or [])) for r in rows]
        uniq = sorted(set(slots))
        first = list(slots[0]) if slots else []
        rg = pf.metadata.row_group(0)
        name_bytes = sum(pf.metadata.row_group(g).column(leaves.index(LEAF)).total_compressed_size
                         for g in range(pf.metadata.num_row_groups))
        episodes[str(ep)] = first
        files[str(ep)] = dict(name=n, sha256=sha256(path), bytes=os.path.getsize(path), rows=len(rows),
                              row_groups=pf.metadata.num_row_groups, name_column_bytes=int(name_bytes),
                              constant_membership=len(uniq) == 1, distinct_slot_lists=[list(u) for u in uniq][:4],
                              leaves_in_file=len(leaves), leaves_read=1)
        del rg
    res = dict(schema='gmg-roster-public/1',
               note=('Object names in slot order (the list order of observation.objects) for the 20 public episodes. '
                     'Written once by gmg/tools/roster_public.py from the leaf column ' + LEAF + ' only (column '
                     'projection; pose and visible never read). The gmg reads this file (role roster), never a '
                     'parquet. Episode keys are the episode_index from the file names.'),
               source=dict(dataset=DATASET, prefix=PREFIX, column=LEAF), pyarrow=pyarrow.__version__,
               created_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               episodes=dict(sorted(episodes.items(), key=lambda kv: int(kv[0]))),
               files=dict(sorted(files.items(), key=lambda kv: int(kv[0]))))
    with open(out, 'w') as f:
        json.dump(res, f, indent=1)
    print(json.dumps(dict(out=out, episodes=len(episodes),
                          constant=all(v['constant_membership'] for v in files.values()))))
    return res


def audited(src, out, log, delete_src=False):
    src, out, log = os.path.realpath(src), os.path.abspath(out), os.path.abspath(log)
    cmd = [sys.executable, AUDIT, 'run', '--policy', 'roster', '--src', src, '--out', out, '--log', log, '--',
           sys.executable, '-I', os.path.abspath(__file__), 'build', '--src', src, '--out', out]
    env = {k: v for k, v in os.environ.items() if not k.startswith('GMG_')}
    env['GMG_MODE'] = 'clean'
    r = subprocess.run(cmd, env=env, cwd='/tmp', capture_output=True, text=True)
    sys.stdout.write(r.stdout[-4000:])
    sys.stderr.write(r.stderr[-4000:])
    rep = json.load(open(log + '.audit.json'))
    res = json.load(open(out))
    commit = subprocess.run(['git', '--no-optional-locks', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True,
                            text=True).stdout.strip()
    parquets = [p for p in rep['data_reads'] if p.startswith(src + '/') and p.endswith('.parquet')]
    res['code_commit'] = commit
    res['audit'] = dict(tool='gmg/tools/strace_audit.py --policy roster', events=rep['events'],
                        opens_ok=rep['opens_ok'], forbidden_opens=rep['forbidden_opens'],
                        forbidden=rep['forbidden'][:20], unlisted=rep['unlisted'][:20],
                        writes_outside_run=len(rep['writes_outside_run']),
                        data_reads=[os.path.basename(p) for p in rep['data_reads']],
                        parquets_read=len(parquets), other_data_reads=len(rep['data_reads']) - len(parquets),
                        returncode=rep.get('returncode'), log_sha256=sha256(log),
                        command=' '.join(os.path.basename(c) if c.startswith('/') else c for c in rep['command']))
    with open(out, 'w') as f:
        json.dump(res, f, indent=1)
    if delete_src and rep['forbidden_opens'] == 0:
        shutil.rmtree(src)
        res['audit']['src_deleted'] = True
        with open(out, 'w') as f:
            json.dump(res, f, indent=1)
    print(json.dumps(dict(out=out, forbidden_opens=rep['forbidden_opens'], parquets_read=len(parquets),
                          other_data_reads=len(rep['data_reads']) - len(parquets), returncode=r.returncode)))
    return 0 if rep['forbidden_opens'] == 0 and r.returncode == 0 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch')
    f.add_argument('--dest', required=True)
    b = sub.add_parser('build')
    b.add_argument('--src', required=True)
    b.add_argument('--out', required=True)
    a = sub.add_parser('audited')
    a.add_argument('--src', required=True)
    a.add_argument('--out', required=True)
    a.add_argument('--log', required=True)
    a.add_argument('--delete-src', action='store_true')
    x = ap.parse_args()
    if x.cmd == 'fetch':
        fetch(x.dest)
    elif x.cmd == 'build':
        build(x.src, x.out)
    else:
        sys.exit(audited(x.src, x.out, x.log, x.delete_src))


if __name__ == '__main__':
    main()
