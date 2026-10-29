"""Provenance manifests and the deny-list gate (mesh pipeline v5, docs/mesh-v5-spec-draft.md section 3, G0).

Tiers: P0 (raw episode media, our depth caches, MediaPipe hands lifted with our depth and VO, object names and slot
order, kit and FlashCHORD code, the spoon template), P1 (bootstrap-derived: tracks made with MESH_DIR=library_v2 and
everything computed from them; usable only if the owner accepts it, decision O1), DENY (never an inference input:
public scans, the organisers' meshes and URDFs, library_v1-v4, scan-templated tracks, the mocap oracle, prototype
grids and meshes under scratchpad/interact, ASSET_SRC=public runs). An artifact's tier is the worst tier among its
inputs; a DENY input aborts the step.

  write(out, kind, inputs, params, command=None) -> manifest dict, written to <out>.prov.json
      inputs: [{'role': 'depth|poses|hands|others|roi|seed|video|calib|mesh|grid|pieces|assets|names|code|template',
                'path': ..., 'tier': optional for raw roles}]
  check(inputs) -> 'P0' | 'P1'      raises Deny on a deny-list match (path glob or sha256) or on a derived input
                                    (mesh, tracks, grid, pieces, assets, hands, ...) that has no manifest

The deny-list is ops/provenance/denylist.json (built by tools/build_denylist.py: globs plus the sha256 of every public
scan / URDF file, every library_v1-v4 mesh and every scan-templated poses.npz, so renamed copies are caught too).
"""
import datetime, fnmatch, getpass, hashlib, json, os, socket, subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DENYLIST = os.environ.get('V2D_DENYLIST', os.path.join(REPO, 'ops', 'provenance', 'denylist.json'))
RAW_ROLES = {'video', 'calib', 'depth', 'names', 'code', 'template'}   # P0 without a manifest (unless deny-listed)
ORDER = {'P0': 0, 'P1': 1}


class Deny(Exception):
    """An input is on the deny-list or has unknown provenance."""


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


_DL = {}


def denylist():
    if 'd' not in _DL:
        d = json.load(open(DENYLIST)) if os.path.exists(DENYLIST) else {'globs': [], 'sha256': {}}
        _DL['d'] = dict(globs=list(d.get('globs', [])), sha256=dict(d.get('sha256', {})))
    return _DL['d']


def _glob_hit(path):
    p = os.path.abspath(path)
    rel = os.path.relpath(p, REPO) if p.startswith(REPO + os.sep) else None
    for g in denylist()['globs']:
        if fnmatch.fnmatch(p, g) or (rel is not None and fnmatch.fnmatch(rel, g)):
            return g
    return None


def deny_reason(path):
    """The deny-list rule a file matches (glob, or sha256 for renamed copies), or None."""
    g = _glob_hit(path)
    if g:
        return f'glob {g}'
    if os.path.isfile(path):
        s = sha256(path)
        if s in denylist()['sha256']:
            return f"sha256 of {denylist()['sha256'][s]}"
    return None


def manifest_path(path):
    return f'{path}.prov.json'


def input_tier(inp):
    """Tier of one input dict {'role', 'path', 'tier'?}; raises Deny."""
    path, role = inp['path'], inp.get('role', '')
    r = deny_reason(path)
    if r:
        raise Deny(f'{role} input {path} is on the deny-list ({r})')
    mp = manifest_path(path)
    if os.path.exists(mp):
        man = json.load(open(mp))
        if man.get('sha256') and os.path.isfile(path) and man['sha256'] != sha256(path):
            raise Deny(f'{role} input {path} does not match its manifest (sha256 changed)')
        t = man.get('tier')
        if t not in ORDER:
            raise Deny(f'{role} input {path}: manifest tier {t!r}')
        return t
    if role in RAW_ROLES:
        return inp.get('tier', 'P0')
    raise Deny(f'{role} input {path} has no provenance manifest (unknown provenance counts as DENY)')


def check(inputs):
    """The worst tier among the inputs ('P0' when there are none); raises Deny."""
    tiers = [input_tier(i) for i in inputs]
    return max(tiers, key=ORDER.get) if tiers else 'P0'


def _commit():
    try:
        return subprocess.run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return None


def write(out, kind, inputs, params=None, command=None):
    """Check the inputs, then write <out>.prov.json for the artifact OUT (a file or a directory)."""
    tier = check(inputs)
    man = dict(artifact=os.path.abspath(out), sha256=sha256(out) if os.path.isfile(out) else None, kind=kind, tier=tier,
               code_commit=_commit(), command=command, host=socket.gethostname(), user=getpass.getuser(),
               created_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), params=params or {},
               inputs=[dict(role=i.get('role'), path=os.path.abspath(i['path']),
                            sha256=sha256(i['path']) if os.path.isfile(i['path']) else None,
                            tier=input_tier(i), manifest=manifest_path(i['path']) if os.path.exists(manifest_path(i['path'])) else None)
                       for i in inputs])
    json.dump(man, open(manifest_path(out), 'w'), indent=1)
    return man
