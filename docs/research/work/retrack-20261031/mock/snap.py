"""Normalised snapshot of one perc_leak mock run, and the diff of two snapshots (2026-10-31, re-track build).
usage: snap.py snap MR OUT.json      every file under MR/content/{results,push} (+ job.log, perc2_audit.log, hf.log,
                                     rc.txt, push.out): path -> md5 of its NORMALISED content. Normalised = the MR path
                                     replaced by <MR>; UTC timestamps (job.log, the push message) and the seconds of each perc2 run blanked;
                                     run.json t0 / t1 / depth stats, inputs.json and bundle.json depth stats (inode,
                                     mtime) and every 'seconds' blanked; a tar is its member list + each member's
                                     normalised md5 (tar headers carry mtimes). Binary files (npz, npy, jpg): raw md5.
       snap.py diff A.json B.json    exit 0 when identical, else lists the differing paths (1).
Everything blanked is a wall-clock or inode value: what perc2 saw, wrote and what the job pushed is compared exactly."""
import hashlib, io, json, os, re, sys, tarfile

TS = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ')                      # job.log stamps, push commit message
DUR = [(re.compile(r'(perc_leak ep\d+ \w+ rc=-?\d+) \d+ s:'), r'\1 _ s:'),
       (re.compile(r'(rc -?\d+) \d+ s '), r'\1 _ s '),
       (re.compile(r'"seconds": -?\d+'), '"seconds": _')]


def norm_json(o):
    if isinstance(o, dict):
        return {k: ('_' if k in ('t0', 't1', 'seconds', 'depth_stat_before', 'depth_stat_after', 'stat') else norm_json(v))
                for k, v in o.items()}
    if isinstance(o, list):
        return [norm_json(v) for v in o]
    return o


def norm(name, data, mr):
    base = os.path.basename(name)
    if base.endswith(('.npz', '.npy', '.jpg')):
        return hashlib.md5(data).hexdigest()
    if base.endswith('.tar'):
        with tarfile.open(fileobj=io.BytesIO(data)) as t:
            return {m.name: norm(m.name, t.extractfile(m).read(), mr) for m in t.getmembers() if m.isfile()}
    s = data.decode('utf-8', 'replace').replace(mr, '<MR>')
    if base.endswith('.json') and not base.endswith('.jsonl'):
        try:
            s = json.dumps(norm_json(json.loads(s)), sort_keys=True)
        except Exception:
            pass
    s = TS.sub('[TS]', s)
    for r, t in DUR:
        s = r.sub(t, s)
    return hashlib.md5(s.encode()).hexdigest()


def snap(mr, out):
    res = {}
    for top in ('content/results', 'content/push'):
        for r, ds, fs in os.walk(f'{mr}/{top}'):
            for f in fs:
                p = f'{r}/{f}'
                if os.path.islink(p) or os.path.basename(p).startswith('depths_'):
                    res[os.path.relpath(p, mr)] = 'LINK-OR-DEPTH'; continue
                res[os.path.relpath(p, mr)] = norm(p, open(p, 'rb').read(), mr)
    for f in ('content/job.log', 'perc2_audit.log', 'hf.log', 'rc.txt', 'push.out', 'gdino_tries.txt'):
        if os.path.exists(f'{mr}/{f}'):
            res[f] = norm(f, open(f'{mr}/{f}', 'rb').read(), mr)
    json.dump(res, open(out, 'w'), indent=0, sort_keys=True)
    print(f'snap {mr}: {len(res)} files -> {out}')


def diff(a, b):
    A, B = json.load(open(a)), json.load(open(b))
    bad = sorted(k for k in set(A) | set(B) if A.get(k) != B.get(k))
    print(f'{os.path.basename(a)} vs {os.path.basename(b)}: {len(A)} / {len(B)} files, {len(bad)} differ'
          + ''.join(f'\n  DIFF {k}' for k in bad[:30]))
    return 1 if bad else 0


if __name__ == '__main__':
    if sys.argv[1] == 'snap':
        snap(os.path.abspath(sys.argv[2]), sys.argv[3])
    else:
        sys.exit(diff(sys.argv[2], sys.argv[3]))
