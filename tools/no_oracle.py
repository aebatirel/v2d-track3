"""Leak guard (2026-10-30, oracle twins; B8 of the leak decomposition, 30 Oct): refuse anything mocap- or scan-derived
on its way into an eval pack (CLAUDE.md).

Refused by name (BAD), in a word, a JSON string, a resolved file path or a checkpoint's stored training config:
  - the oracle twins (ops/jobs/oracle_twins.sh): perception /content/oracle/ep<N>, references refs/oracle<V>/ and
    refs/oracle_*/, runs runs/oracle*/, results results/oracle*/ and results/hard_ab/ep<N>/oracle_*; store runs
    <date>-orc<X>-<sha>, which also covers every run of the leak decomposition (its run ids must carry -orc);
  - the leak decomposition's folders (docs/research/work/leak-decomp-20261030/PLAN.md §7 B8): scan-template tracks
    perc2scan (P_s), blind-mesh tracks perc2gf (P_gf), hand timing matched to mocap (a delimited 'hT' token:
    hands_hT/, refs/glockt_hT/, c7-hT), results/leak_p1, results/leak_cells and any leak-decomp / leak/ folder;
  - scan geometry: 'scanlib' (physics_arms.sh's /content/scanlib; the scan cells' asset roots), the organisers' public
    scans and URDFs (t3/mesh/<obj>/, t3/urdf/, track_3/public/mesh|urdf; our wooden_spoon in t3/ is allowed) and the
    ASSET_SRC=public runs 20261022-r5ks* (scan assets in the simulator).
Refused by content: a word, a part of it (EP:DIR, RUN@sub, ck=PATH) or a JSON string that is an existing file or
directory is resolved (directories walked to depth 3, symlinks followed); a file whose real path matches BAD, or whose
sha256 is a public scan or a scan-templated track (ops/provenance/denylist.json without its library_v* entries, which
are our pack meshes), is refused, so symlink farms and renamed byte copies are caught. NOT caught: a scan converted to
another format under a neutral name, so the scan cells must keep their asset roots under scanlib / oracle names (B5).
Exit 1 on any refusal. Usage: python tools/no_oracle.py WORD|FILE.json ...  (pack_eval.sh, h5_reeval.sh, submit_pack.sh)
"""
import hashlib, json, os, re, struct, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAD = re.compile(r'oracle|\d{8}-orc[A-Za-z0-9]*-'                                    # oracle twins; every -orc run
                 r'|perc2scan|perc2gf|(?<![A-Za-z0-9])hT(?![a-z])|(?<![A-Za-z])leak(?:[_/-]|$)'   # leak-study folders
                 r'|(?i:scanlib)|(?<![A-Za-z0-9_])t3/(?:mesh|urdf)/(?!wooden_spoon)|track_3/public/(?:mesh|urdf)'
                 r'|20261022-r5ks')                                                  # scan geometry
HASHED = ('.glb', '.gltf', '.obj', '.stl', '.ply', '.urdf', '.npz')                # files whose sha256 is compared
MAX_HASH, MAX_FILES, DEPTH = 256 << 20, 5000, 3


def strings(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield str(k); yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)
    elif isinstance(x, str):
        yield x


def ckpt_config(path):  # the resolved config a FlashCHORD checkpoint stores (empty if unreadable)
    try:
        with open(path, 'rb') as f:
            n = struct.unpack('<Q', f.read(8))[0]; h = json.loads(f.read(n))
        return list(strings(json.loads(h.get('__metadata__', {}).get('user.resolved_config_json', '{}'))))
    except Exception:
        return []


def deny_sha():  # sha256 -> what: public scans and scan-templated tracks (the library_v* entries are our pack meshes)
    try:
        d = json.load(open(os.path.join(REPO, 'ops', 'provenance', 'denylist.json')))['sha256']
    except Exception:
        return {}
    return {k: v for k, v in d.items() if not v.startswith('meshes/library_')}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def files(p):  # p itself, or the files under directory p (depth-limited, symlinks followed)
    if not os.path.isdir(p):
        yield p; return
    n = 0
    for root, dirs, fs in os.walk(p, followlinks=True):
        if root[len(p):].count(os.sep) >= DEPTH:
            dirs[:] = []
        for f in sorted(fs):
            yield os.path.join(root, f); n += 1
            if n >= MAX_FILES:
                return


def broad(p):  # the repo, the working directory or one of their parents: not a pack input, never walked
    r = os.path.realpath(p).rstrip(os.sep) + os.sep
    return os.path.isdir(p) and any((os.path.realpath(q) + os.sep).startswith(r) for q in (REPO, os.getcwd()))


def why(s, sha):
    """Why the string s is refused, or None."""
    if BAD.search(s):
        return ''
    for part in dict.fromkeys([s] + re.split(r'[:@,=\s]', s)):              # EP:DIR, RUN@sub, ck=PATH
        if not part or not os.path.exists(part) or broad(part):
            continue
        for f in files(part):
            r = os.path.realpath(f)
            if BAD.search(r):
                return f' ({f} -> {r})'
            if r.endswith('.safetensors'):
                c = [c for c in ckpt_config(r) if BAD.search(c)]
                if c:
                    return f' (checkpoint config: {c[0]})'
            elif r.lower().endswith(HASHED) and os.path.isfile(r) and os.path.getsize(r) <= MAX_HASH:
                h = sha256(r)
                if h in sha:
                    return f' ({f}: sha256 of {sha[h]})'
    return None


def main(argv):
    bad, sha = [], deny_sha()
    for w in argv:
        todo = [(w, w)]
        if w.endswith('.json') and os.path.isfile(w):
            todo = [(f'{w}: {s}', s) for s in strings(json.load(open(w)))]
        for where, s in todo:
            r = why(s, sha)
            if r is not None:
                bad.append(where + r)
    if bad:
        print('REFUSED: oracle-twin / leak-study (mocap- or scan-derived) input, never for an eval pack:\n  '
              + '\n  '.join(bad[:10]), file=sys.stderr)
        sys.exit(1)
    print(f'no_oracle: {len(argv)} inputs checked, none oracle-derived')


if __name__ == '__main__':
    main(sys.argv[1:])
