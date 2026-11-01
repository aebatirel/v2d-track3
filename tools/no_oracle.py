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
  - the eval-10 njmax diagnostic (2026-11-01, ops/jobs/ev10_nj.sh; docs/research/work/eval10-njmax-20261101/PREREG.md):
    a policy trained with sim.njmax 1024 takes changed physics into evaluation (the evaluator rebuilds sim from the
    checkpoint's stored config), so it never enters a pack: its run ids <date>-e10nj-<sha>, its folders perc2e10nj*
    (refs/perc2e10njs<seed>_glock*, runs/perc2e10njs<seed>_glock, results/perc2e10njs<seed>_glock_public) and its result
    folder results/ev10_nj (both of its checkpoints: the 1024 one and the 512 copy of it), i.e. any 'e10nj' / 'ev10_nj'.
Refused by content: a word, a part of it (EP:DIR, RUN@sub, ck=PATH) or a JSON string that is an existing file or
directory is resolved (directories walked to depth 3, symlinks followed); a file whose real path matches BAD, or whose
sha256 is a public scan or a scan-templated track (ops/provenance/denylist.json without its library_v* entries, which
are our pack meshes), is refused, so symlink farms and renamed byte copies are caught. A checkpoint (.safetensors) is also
refused when its stored training config names a refused folder or holds non-stock contact limits (sim / env.sim njmax and
nconmax other than FlashCHORD's sim=rl 512 / 256, which every pack policy trained with), so a renamed copy of the njmax
diagnostic's checkpoint is caught by content. NOT caught: a scan converted to
another format under a neutral name, so the scan cells must keep their asset roots under scanlib / oracle names (B5).
Exit 1 on any refusal. Usage: python tools/no_oracle.py WORD|FILE.json ...  (pack_eval.sh, h5_reeval.sh, submit_pack.sh)
"""
import hashlib, json, os, re, struct, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAD = re.compile(r'oracle|\d{8}-orc[A-Za-z0-9]*-'                                    # oracle twins; every -orc run
                 r'|perc2scan|perc2gf|(?<![A-Za-z0-9])hT(?![a-z])|(?<![A-Za-z])leak(?:[_/-]|$)'   # leak-study folders
                 r'|(?i:scanlib)|(?<![A-Za-z0-9_])t3/(?:mesh|urdf)/(?!wooden_spoon)|track_3/public/(?:mesh|urdf)'
                 r'|20261022-r5ks'                                                   # scan geometry
                 r'|e10nj|ev10_nj')                                                  # eval-10 njmax diagnostic (changed physics)
STOCK_SIM = (512, 256)                                                               # FlashCHORD configs/sim/rl.yaml njmax, nconmax
# Owner-approved exception (owner, in this session, 1 Nov 2026 ~11:30 UTC; docs/research/work/eval10-njmax-20261101/
# PREREG_AMENDMENT_pack11.md): ONE checkpoint, the eval-10 policy trained with sim.njmax 1024 / nconmax 512 (training
# only) whose stock-config copy ck512 stores and is evaluated at 512 / 256. An input is accepted under it only when its
# own content names this sha256: the .safetensors file's sha256, a rollout parquet's flash_chord.checkpoint_sha256, or a
# rollout json's checkpoint_sha256. Every other non-stock-limit checkpoint and every e10nj / ev10_nj name stays refused.
ALLOW_CKPT = {'aaa077ebae863650c926d13550d368704889d445bcfc96ef9e4773f17c04d55f':
              'eval-10 ck512 of run 20261101-e10nj-451b82d (trained njmax 1024 / nconmax 512; evaluated at stock 512 / 256)'}
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


def ckpt_sim(path):  # [(key, njmax, nconmax)] of the stored config's sim blocks that are NOT stock (empty if stock / unreadable)
    try:
        with open(path, 'rb') as f:
            n = struct.unpack('<Q', f.read(8))[0]; h = json.loads(f.read(n))
        c = json.loads(h.get('__metadata__', {}).get('user.resolved_config_json', '{}'))
    except Exception:
        return []
    blocks = [('sim', c.get('sim')), ('env.sim', (c.get('env') or {}).get('sim') if isinstance(c.get('env'), dict) else None)]
    return [(k, b.get('njmax'), b.get('nconmax')) for k, b in blocks
            if isinstance(b, dict) and ('njmax' in b or 'nconmax' in b) and (b.get('njmax'), b.get('nconmax')) != STOCK_SIM]


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


def named_checkpoint(path):  # the checkpoint sha256 a file is (.safetensors) or names (rollout .parquet / .json); else None
    try:
        r = os.path.realpath(path)
        if not os.path.isfile(r):
            return None
        if r.endswith('.safetensors'):
            return sha256(r)
        if r.endswith('.parquet'):
            import pyarrow.parquet as pq
            v = (pq.read_schema(r).metadata or {}).get(b'flash_chord.checkpoint_sha256')
            return v.decode() if v else None
        if r.endswith('.json') and os.path.getsize(r) < (1 << 20):
            d = json.load(open(r))
            return d.get('checkpoint_sha256') if isinstance(d, dict) else None
    except Exception:
        return None
    return None


def allowed(path):  # the owner-approved exception names exactly this file's checkpoint (ALLOW_CKPT)
    return named_checkpoint(path) in ALLOW_CKPT


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
            if allowed(f):                                                   # ALLOW_CKPT: this one checkpoint only
                continue
            if BAD.search(r):
                return f' ({f} -> {r})'
            if r.endswith('.safetensors'):
                c = [c for c in ckpt_config(r) if BAD.search(c)]
                if c:
                    return f' (checkpoint config: {c[0]})'
                c = ckpt_sim(r)
                if c:
                    return (f' (checkpoint config: {c[0][0]} njmax {c[0][1]} / nconmax {c[0][2]}, not the stock '
                            f'{STOCK_SIM[0]} / {STOCK_SIM[1]}: changed evaluation physics)')
            elif r.lower().endswith(HASHED) and os.path.isfile(r) and os.path.getsize(r) <= MAX_HASH:
                h = sha256(r)
                if h in sha:
                    return f' ({f}: sha256 of {sha[h]})'
    return None


def main(argv):
    bad, sha = [], deny_sha()
    for w in argv:
        if allowed(w):                                                       # ALLOW_CKPT: accepted whole, by content
            print(f'no_oracle: accepted by the owner-approved exception: {w} '
                  f'(checkpoint {named_checkpoint(w)[:12]}…: {ALLOW_CKPT[named_checkpoint(w)]})')
            continue
        todo = [(w, w)]
        if w.endswith('.json') and os.path.isfile(w):
            todo = [(f'{w}: {s}', s) for s in strings(json.load(open(w)))]
        for where, s in todo:
            r = why(s, sha)
            if r is not None:
                bad.append(where + r)
    if bad:
        print('REFUSED: oracle-twin / leak-study (mocap- or scan-derived) or eval-10 njmax-diagnostic (changed physics) '
              'input, never for an eval pack:\n  '
              + '\n  '.join(bad[:10]), file=sys.stderr)
        sys.exit(1)
    print(f'no_oracle: {len(argv)} inputs checked, none oracle-derived')


if __name__ == '__main__':
    main(sys.argv[1:])
