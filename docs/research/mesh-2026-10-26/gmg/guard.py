"""gmg input guard (module M0 of SPEC v1 rev 1, sections 2, 3 and 7; build step B0).

Every gmg input goes through this module. It decides, before a file is opened, whether the file may be read, and it
records every input that passes with its sha256, so a run's manifest lists exactly what the run read.

  open_input(path, role) -> realpath     check a file for a role and record it (sha256, tier)
  load_npz(path, role, keys=None)        open_input + key filter (det_f0.npz: mask keys only; tracks: poses only)
  load_json(path, role)                  open_input + json.load
  mode() -> 'clean' | 'dev'              env GMG_MODE, read once at import (default 'clean')
  constant(name, value, origin)          constant registry with origins (sensor, generic, kit, informed,
                                         fitted:<what>, fallback:<what>; PREREG A.6)
  manifest() / write_manifest(path)      mode, tier, commit, roots, every input with sha256, constants, refusals
  set_run(path) / run_dir()              the run folder RUN = <data>/gmg/runs/<yyyymmdd>-<tag>-<commit7>/ (role own)
  check_io_gt(path, kind)                bridge for autokit/io_gt.py: an io_gt input inside a gmg process must also
                                         pass this guard (an io_gt root that is not on the gmg allow-list is refused)
  io_gt_roots_report()                   which io_gt roots this guard admits in the current mode

Checks of open_input, in this order (a path is refused before the file is opened; only a file that passed every path
check is hashed):
  1. the role exists, and a dev-only role (obs_all, x0_pool, fixture) is refused in clean mode;
  2. path substrings /scan, /loc/, _align, .parquet, mocap (case-insensitive; as given and resolved through links);
  3. the deny-list globs (ops/provenance/denylist.json through pipeline/provenance.py, plus the repo file itself, plus
     GMG_EXTRA_DENYLIST, which can only add entries);
  4. the revision-1 refusals (library_v1..v4 and v3x, results/prim, scratchpad prim/, lathe/, auto/, gen/mesh-*,
     crops/, evalcrops/, diag/, gmg/design/, obs_all/, obs/). In dev mode a dev role named in REFUSED may pass its
     own folder; in clean mode nothing does, and that holds even if a later allow-list change would admit the folder;
  5. the allow-list of the role (ROLE_PATTERNS, on the resolved path; the kit role excludes the scorer);
  6. the file exists, is a regular file and has exactly one hard link;
  7. its sha256 is not on the deny-list (renamed copies), and matches expect_sha256 if one is given.
A Python audit hook (installed at import) also refuses, in-process, any open() / os.open() of a path that fails checks
2-4 (code files are exempt from check 2 only, since e.g. json/scanner.py contains '/scan'). Opens from C code are not
seen by the hook; the strace audit (tools/strace_audit.py) covers them.

Roots: DATA = env GMG_DATA_ROOT (default: this session's scratchpad), KIT = env GMG_KIT_ROOT (default
DATA/kit/v2d_submission_kit), WEIGHTS = env GMG_WEIGHTS_ROOT (default DATA/weights), RUN = env GMG_RUN or set_run(),
which must be DATA/gmg/runs/<yyyymmdd>-<tag>-<commit7>. All are read once at import and recorded in the manifest.
Tiers (SPEC section 3): P0 raw inputs; P1 Phase-1 tracks (library-templated); own files carry RUN/run_tier.json
(default P1); dev roles and every dev-mode run are DEV. The worst tier wins.
"""
from __future__ import annotations

import datetime
import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import threading

GMG_DIR = os.path.dirname(os.path.abspath(__file__))
MESH_RESEARCH = os.path.dirname(GMG_DIR)                                   # docs/research/mesh-2026-10-26
REPO = os.path.abspath(os.path.join(MESH_RESEARCH, '..', '..', '..'))
SCRATCH_DEFAULT = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
DENYLIST_REPO = os.path.join(REPO, 'ops', 'provenance', 'denylist.json')
PROVENANCE_PY = os.path.join(REPO, 'pipeline', 'provenance.py')

MODES = ('clean', 'dev')
SUBSTRINGS = ('/scan', '/loc/', '_align', '.parquet', 'mocap')
CLEAN_ROLES = ('calib', 'tracks', 'depth', 'video', 'det', 'roster', 'kit', 'weights', 'own', 'frozen')
DEV_ROLES = ('obs_all', 'x0_pool', 'fixture')
ROLES = CLEAN_ROLES + DEV_ROLES
# npz key filters (fnmatch patterns). det_f0.npz also holds library-derived fields (sim, template_*, chosen, score*,
# verify*, rules, params, ...) and the Grounding DINO boxes (gdino): all refused (SPEC section 2).
NPZ_KEYS = dict(det=('masks', 'mask_shape', 'frame', 'K', 'image', 'depth', 'names'),
                tracks=('world_T_cam', 'cam_T_*'))
# kit files that score (or read reference data); refused for role kit
KIT_SCORER = ('metric_code/**', 'v2dlb/object_mesh.py', 'v2dlb/object_pose.py', 'v2dlb/track3_pose.py',
              'v2dlb/mhr_metrics.py', 'v2dlb/vertices.py', 'v2dlb/trajectory.py', 'v2dlb/dataset.py')
# named test fixtures (dev role fixture) with their sha256 prefix: PREREG B.14 T-V2d, the hand-kit lid potlid/fit/ep2
FIXTURE_FILES = {'{DATA}/prim/potlid/cand/white_pot_lid_ep2_fit.glb': 'e1be3218a8608793'}
ROLE_PATTERNS = dict(
    calib=('{DATA}/data/calib.json',),
    tracks=('{DATA}/data/sweep/ep*/poses.npz', '{DATA}/data/eval/ep*/poses.npz', '{RUN}/tracks/**'),
    depth=('{DATA}/cache/depth/{public,eval}/ep*/depths_fs*.npy', '{DATA}/data/depth/ep*/depths_fs*.npy'),
    video=('{DATA}/data/store/ep*_[abc].mp4', '{DATA}/data/eval/ep*_[abc].mp4',
           '{DATA}/t3/v/ep*_[abc].mp4', '{DATA}/t3/eval/v/ep*_[abc].mp4',
           '{DATA}/hfds/track_3/{public,evaluation}/videos/**.mp4'),
    det=('{DATA}/data/store/ep*/det_f0.npz',),
    roster=('{KIT}/data/track_3_evaluation_objects.json', '{GMG}/roster_public.json'),
    kit=('{KIT}/**',),
    weights=('{WEIGHTS}/**',),
    own=('{RUN}/**',),
    frozen=('{GMG}/frozen_constants.json', '{GMG}/deploy_variant.json'),
    obs_all=('{DATA}/obs_all/*.npz',),
    x0_pool=('{MR}/results/gen-probe/**', '{MR}/results/prim/**', '{MR}/results/lathe_obs.jsonl',
             '{DATA}/gen/mesh-*/**', '{DATA}/prim/**', '{DATA}/lathe/**'),
    fixture=('{GMG}/tests/fixtures/**',),
)
# revision-1 refusals: (name, patterns, dev roles that may pass this folder in dev mode only)
REFUSED = (
    ('meshes/library_v1..v4, library_v3x', ('**/meshes/library_v[1-4]/**', '**/meshes/library_v3x/**'), ()),
    ('results/prim', ('**/results/prim/**',), ('x0_pool',)),
    ('scratchpad/prim', ('{DATA}/prim/**', '**/scratchpad/prim/**'), ('x0_pool',)),
    ('scratchpad/lathe', ('{DATA}/lathe/**', '**/scratchpad/lathe/**'), ('x0_pool',)),
    ('scratchpad/auto (stage-1b outputs)', ('{DATA}/auto/**', '**/scratchpad/auto/**'), ()),
    ('scratchpad/gen/mesh-* (generator outputs seeded with library_v3)',
     ('{DATA}/gen/mesh-*', '{DATA}/gen/mesh-*/**', '**/scratchpad/gen/mesh-*'), ('x0_pool',)),
    ('scratchpad/crops (library_v3 seeds)', ('{DATA}/crops/**', '**/scratchpad/crops/**'), ()),
    ('scratchpad/evalcrops (library_v3 seeds)', ('{DATA}/evalcrops/**', '**/scratchpad/evalcrops/**'), ()),
    ('scratchpad/diag (scan placements, load_scan)', ('{DATA}/diag/**', '**/scratchpad/diag/**'), ()),
    ('scratchpad/gmg/design (design-probe outputs)', ('{DATA}/gmg/design/**', '**/scratchpad/gmg/design/**'), ()),
    ('scratchpad/obs_all (library_v3 ROI and --others)', ('{DATA}/obs_all/**', '**/scratchpad/obs_all/**'),
     ('obs_all',)),
    ('scratchpad/obs (library ROI)', ('{DATA}/obs/**', '**/scratchpad/obs/**'), ()),
)
ORIGIN_HEADS = ('sensor', 'generic', 'kit', 'informed', 'fitted', 'fallback')
TIER_ORDER = {'P0': 0, 'P1': 1, 'DEV': 2}
RUN_NAME = re.compile(r'^\d{8}-[a-z0-9][a-z0-9._-]*-[0-9a-f]{7}$')
CODE_SUFFIX = ('.py', '.pyc', '.pyi', '.so', '.pyd', '.pth')
# constants SPEC section 2 says are not used (scan-informed): refused unless their origin says fitted (or fallback for
# the pre-registered t0 fallback, PREREG A.6)
BANNED = ((re.compile(r'(ball|marker).*(radius|rad\b|_r$|_r_)', re.I), (7.0, 0.007), ('fitted',)),
          (re.compile(r'thick|^t0|wall', re.I), (2.5, 0.0025), ('fitted', 'fallback')),
          (re.compile(r'tau', re.I), (0.2,), ('fitted',)))


class GuardError(PermissionError, ValueError):
    """An input (or an open) is refused by the gmg guard."""


# ------------------------------------------------------------------------------------------------ configuration
def _real(p):
    return os.path.realpath(os.path.abspath(os.path.expanduser(p)))


def _load_cfg():
    m = os.environ.get('GMG_MODE', 'clean').strip().lower() or 'clean'
    if m not in MODES:
        raise GuardError(f'gmg guard: GMG_MODE={m!r} is not one of {MODES}')
    data = _real(os.environ.get('GMG_DATA_ROOT', SCRATCH_DEFAULT))
    return dict(mode=m, data=data, repo=_real(REPO), gmg=_real(GMG_DIR), mr=_real(MESH_RESEARCH),
                kit=_real(os.environ.get('GMG_KIT_ROOT', os.path.join(data, 'kit', 'v2d_submission_kit'))),
                weights=_real(os.environ.get('GMG_WEIGHTS_ROOT', os.path.join(data, 'weights'))),
                run=None, extra_deny=os.environ.get('GMG_EXTRA_DENYLIST') or None)


CFG = _load_cfg()
_INPUTS = {}            # realpath -> record
_REFUSALS = []          # every refusal (open_input, load_npz keys, hook)
_CONSTANTS = {}         # name -> record
_SHA = {}               # (realpath, size, mtime_ns, ino) -> sha256
_ADMITTED = set()       # realpaths admitted by open_input (the hook lets these through in dev mode)
_RX = {}                # compiled pattern cache
_TLS = threading.local()
_HOOK = dict(installed=False, blocked=0)


def mode():
    """'clean' or 'dev' (env GMG_MODE, read once at import; default 'clean')."""
    return CFG['mode']


def set_run(path):
    """Set the run folder (role own) once: it must be DATA/gmg/runs/<yyyymmdd>-<tag>-<commit7>. Creates it."""
    rp = _real(path)
    if CFG['run'] is not None and CFG['run'] != rp:
        raise GuardError(f'gmg guard: the run folder is already {CFG["run"]}')
    parent = os.path.join(CFG['data'], 'gmg', 'runs')
    if os.path.dirname(rp) != parent or not RUN_NAME.match(os.path.basename(rp)):
        raise GuardError(f'gmg guard: run folder {rp} must be {parent}/<yyyymmdd>-<tag>-<commit7>')
    _check_patterns(rp + '/x', 'own', run_check=False)        # a run folder inside a refused folder is refused
    os.makedirs(rp, exist_ok=True)
    CFG['run'] = rp
    _RX.clear()
    return rp


def run_dir():
    return CFG['run']


def roots():
    return {k: CFG[k] for k in ('data', 'repo', 'gmg', 'mr', 'kit', 'weights', 'run')}


# ------------------------------------------------------------------------------------------------ patterns
def _glob_re(pat):
    """Glob -> regex: ** any characters, * and ? within one path segment, [..] classes, {a,b} alternatives."""
    i, n, out = 0, len(pat), []
    while i < n:
        c = pat[i]
        if pat.startswith('**', i):
            out.append('.*')
            i += 2
        elif c == '*':
            out.append('[^/]*')
            i += 1
        elif c == '?':
            out.append('[^/]')
            i += 1
        elif c == '[' and pat.find(']', i + 1) > 0:
            j = pat.find(']', i + 1)
            inner = pat[i + 1:j]
            out.append('[' + ('^' + inner[1:] if inner.startswith('!') else inner) + ']')
            i = j + 1
        elif c == '{' and pat.find('}', i + 1) > 0:
            j = pat.find('}', i + 1)
            out.append('(?:' + '|'.join(re.escape(a) for a in pat[i + 1:j].split(',')) + ')')
            i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile('^' + ''.join(out) + '$')


def _sub(pat):
    """Pattern with roots substituted, or None if it names an unset root (RUN before set_run)."""
    keys = dict(DATA=CFG['data'], REPO=CFG['repo'], GMG=CFG['gmg'], MR=CFG['mr'], KIT=CFG['kit'],
                WEIGHTS=CFG['weights'], RUN=CFG['run'])
    for k, v in keys.items():
        tok = '{' + k + '}'
        if tok in pat:
            if v is None:
                return None
            pat = pat.replace(tok, v.replace('[', '[[]').replace('{', '[{]').replace('*', '[*]'))
    return pat


def _rx(pat):
    if pat not in _RX:
        s = _sub(pat)
        _RX[pat] = _glob_re(s) if s is not None else None
    return _RX[pat]


def _match(path, pats):
    for p in pats:
        r = _rx(p)
        if r is not None and r.match(path):
            return p
    return None


# ------------------------------------------------------------------------------------------------ deny-list
def _load_provenance():
    try:
        spec = importlib.util.spec_from_file_location('gmg_v2d_provenance', PROVENANCE_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:                                          # pragma: no cover (provenance is in the repo)
        raise GuardError(f'gmg guard: cannot load {PROVENANCE_PY}: {e}')


PROV = _load_provenance()


def _read_deny(path):
    d = json.load(open(path))
    return list(d.get('globs', [])), dict(d.get('sha256', {}))


def _load_deny():
    """Union of provenance.denylist() (V2D_DENYLIST or the repo file), the repo file and GMG_EXTRA_DENYLIST: an
    environment variable can add deny entries, never remove the repo's."""
    g0, s0 = _read_deny(DENYLIST_REPO)
    pd = PROV.denylist()
    globs, sha = list(dict.fromkeys(g0 + list(pd['globs']))), {**s0, **pd['sha256']}
    src = [dict(path=DENYLIST_REPO, sha256=_sha_file(DENYLIST_REPO), globs=len(g0), sha=len(s0))]
    if os.path.abspath(PROV.DENYLIST) != os.path.abspath(DENYLIST_REPO):
        src.append(dict(path=PROV.DENYLIST, via='V2D_DENYLIST', globs=len(pd['globs']), sha=len(pd['sha256'])))
    if CFG['extra_deny']:
        g1, s1 = _read_deny(CFG['extra_deny'])
        globs, sha = list(dict.fromkeys(globs + g1)), {**sha, **s1}
        src.append(dict(path=CFG['extra_deny'], via='GMG_EXTRA_DENYLIST', sha256=_sha_file(CFG['extra_deny']),
                        globs=len(g1), sha=len(s1)))
    return dict(globs=globs, sha256=sha, sources=src)


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def _sha256(rp):
    st = os.stat(rp)
    key = (rp, st.st_size, st.st_mtime_ns, st.st_ino)
    if key not in _SHA:
        _SHA[key] = _sha_file(rp)
    return _SHA[key]


DENY = _load_deny()


def _deny_glob(path):
    """The deny-list glob a path matches (provenance semantics: fnmatch on the absolute and the repo-relative path)."""
    rel = os.path.relpath(path, CFG['repo']) if path.startswith(CFG['repo'] + os.sep) else None
    for g in DENY['globs']:
        if fnmatch.fnmatch(path, g) or (rel is not None and fnmatch.fnmatch(rel, g)):
            return g
    r = PROV._glob_hit(path)
    return r


# ------------------------------------------------------------------------------------------------ checks
def _record_refusal(path, role, reason, via='open_input'):
    _REFUSALS.append(dict(path=str(path), role=role, reason=reason, via=via,
                          utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')))


def _path_reason(q, role, *, code=False, rp=None):
    """Reason a path (absolute) fails checks 2-4 for ROLE, or None. code=True skips the substrings (hook only)."""
    low = q.lower()
    if not code:
        for s in SUBSTRINGS:
            if s in low:
                return f'path contains {s!r}'
    g = _deny_glob(q)
    if g:
        return f'deny-list glob {g!r}'
    for name, pats, exempt in REFUSED:
        p = _match(q, pats)
        if p:
            if mode() == 'dev' and role in exempt:
                continue
            if mode() == 'dev' and role == 'fixture' and rp is not None and _named_fixture(rp):
                continue
            if role == '*hook*' and rp is not None and rp in _ADMITTED and mode() == 'dev':
                continue
            return f'refused folder: {name} (pattern {p!r}, mode {mode()})'
    return None


def _named_fixture(rp):
    for pat in FIXTURE_FILES:
        s = _sub(pat)
        if s is not None and _real(s) == rp:
            return pat
    return None


def _check_patterns(path, role, *, run_check=True):
    """Checks 1-5 (no file access beyond realpath). Returns (abs path, realpath). Raises GuardError."""
    if role not in ROLES:
        raise GuardError(f'gmg guard: unknown role {role!r} (roles: {ROLES})')
    if role in DEV_ROLES and mode() != 'dev':
        raise GuardError(f'gmg guard: role {role!r} is dev-only (GMG_MODE={mode()}): {path}')
    a = os.path.abspath(os.fspath(path))
    rp = os.path.realpath(a)
    for q in dict.fromkeys((a, rp)):
        r = _path_reason(q, role, rp=rp)
        if r:
            raise GuardError(f'gmg guard: refused {role} input {q}: {r}')
    if run_check:
        allowed = _match(rp, ROLE_PATTERNS[role])
        if role == 'fixture' and not allowed and mode() == 'dev':
            allowed = _named_fixture(rp) or _match(rp, tuple(_FIXTURE_ROOTS))
        if not allowed:
            pats = [p for p in (_sub(x) for x in ROLE_PATTERNS[role]) if p]
            why = f'not on the {role} allow-list {pats}' if pats else f'no run folder is set (role {role})'
            raise GuardError(f'gmg guard: refused {role} input {rp}: {why}')
        if role == 'kit' and _match(rp, tuple('{KIT}/' + s for s in KIT_SCORER)):
            raise GuardError(f'gmg guard: refused kit input {rp}: the kit scorer is excluded')
        if role in ('own', 'tracks') and CFG['run'] and rp.startswith(CFG['run'] + '/') and mode() == 'clean' \
                and _own_tier() == 'DEV':
            raise GuardError(f'gmg guard: refused {role} input {rp}: the run folder is tier DEV (clean mode)')
    return a, rp


_FIXTURE_ROOTS = []


def register_fixture_root(path):
    """Tests only (dev mode): admit a temporary fixture folder for role fixture. Recorded in the manifest."""
    if mode() != 'dev':
        raise GuardError('gmg guard: fixture roots are dev-only')
    rp = _real(path)
    r = _path_reason(rp + '/x', 'fixture')
    if r:
        raise GuardError(f'gmg guard: refused fixture root {rp}: {r}')
    _FIXTURE_ROOTS.append(rp.replace('[', '[[]').replace('{', '[{]').replace('*', '[*]') + '/**')
    return rp


def _own_tier():
    if not CFG['run']:
        return 'P1'
    p = os.path.join(CFG['run'], 'run_tier.json')
    try:
        t = json.load(open(p)).get('tier')
    except (OSError, ValueError):
        return 'P1'
    return t if t in TIER_ORDER else 'P1'


def _tier(role, rp):
    if role in DEV_ROLES:
        return 'DEV'
    if role in ('own', 'tracks') and CFG['run'] and rp.startswith(CFG['run'] + '/'):
        return _own_tier()
    if role in ('tracks', 'frozen'):
        return 'P1'
    return 'P0'


def check(path, role):
    """Path checks 1-5 only (nothing is opened or recorded). Returns the realpath; raises GuardError."""
    return _check_patterns(path, role)[1]


def open_input(path, role, *, expect_sha256=None, keys=None):
    """Check PATH for ROLE (module docstring, checks 1-7), record it with its sha256 and tier, return its realpath.
    Raises GuardError (refused) or FileNotFoundError (missing)."""
    try:
        a, rp = _check_patterns(path, role)
        if not os.path.exists(rp):
            raise FileNotFoundError(rp)
        if not os.path.isfile(rp):
            raise GuardError(f'gmg guard: refused {role} input {rp}: not a regular file')
        st = os.stat(rp)
        if st.st_nlink > 1:
            raise GuardError(f'gmg guard: refused {role} input {rp}: regular file with {st.st_nlink} hard links')
        sha = _sha256(rp)
        if sha in DENY['sha256']:
            raise GuardError(f'gmg guard: refused {role} input {rp}: sha256 is on the deny-list '
                             f'({DENY["sha256"][sha]})')
        if expect_sha256 and sha != expect_sha256.lower():
            raise GuardError(f'gmg guard: refused {role} input {rp}: sha256 {sha} != expected {expect_sha256}')
        nf = _named_fixture(rp) if role == 'fixture' else None
        if nf and not sha.startswith(FIXTURE_FILES[nf]):
            raise GuardError(f'gmg guard: refused fixture {rp}: sha256 {sha[:16]} != {FIXTURE_FILES[nf]}')
    except GuardError as e:
        _record_refusal(path, role, str(e))
        raise
    rec = _INPUTS.get(rp)
    if rec is None or rec['sha256'] != sha or rec['role'] != role:
        rec = dict(role=role, path=a, realpath=rp, sha256=sha, bytes=int(st.st_size), tier=_tier(role, rp))
        _INPUTS[rp] = rec
    if keys is not None:
        rec['keys'] = sorted(set(rec.get('keys', [])) | set(keys))
    _ADMITTED.add(rp)
    return rp


def _key_ok(k, pats):
    return any(fnmatch.fnmatchcase(k, p) for p in pats)


def load_npz(path, role, keys=None):
    """open_input + np.load(allow_pickle=False) of the allowed keys only. For det and tracks a requested key outside
    NPZ_KEYS[role] raises GuardError; keys=None reads every allowed key present (refused keys are never read)."""
    import numpy as np
    pats = NPZ_KEYS.get(role)
    if keys is not None:
        keys = list(keys)
        bad = [k for k in keys if pats is not None and not _key_ok(k, pats)]
        if bad:
            msg = f'gmg guard: refused {role} keys {bad} of {path}: allowed {pats}'
            _record_refusal(path, role, msg, via='load_npz')
            raise GuardError(msg)
    rp = open_input(path, role)
    with np.load(rp, allow_pickle=False) as Z:
        names = list(Z.files)
        sel = keys if keys is not None else [k for k in names if pats is None or _key_ok(k, pats)]
        miss = [k for k in sel if k not in names]
        if miss:
            raise KeyError(f'{rp}: no keys {miss}')
        out = {k: Z[k] for k in sel}
    rec = _INPUTS[rp]
    rec['keys'] = sorted(set(rec.get('keys', [])) | set(sel))
    rec['keys_not_read'] = sorted(set(names) - set(rec['keys']))
    return out


def load_json(path, role):
    rp = open_input(path, role)
    with open(rp) as f:
        return json.load(f)


# ------------------------------------------------------------------------------------------------ io_gt bridge
IO_GT_ROLES = dict(obs=('own', 'obs_all'), corr=('own',), poses=('tracks',), calib=('calib',),
                   mesh=('own', 'x0_pool', 'fixture'))


def check_io_gt(path, kind, exists=True):
    """autokit/io_gt.py calls this for every input while the gmg guard is loaded: the file must also pass this guard
    under one of IO_GT_ROLES[kind] (so an io_gt root that is not on the gmg allow-list is refused). exists=False: path
    checks only (io_gt checks a path before it downloads it). Returns the realpath."""
    roles = [r for r in IO_GT_ROLES.get(kind, ()) if r not in DEV_ROLES or mode() == 'dev']
    errs = []
    for role in roles:
        try:
            _check_patterns(path, role)
        except GuardError as e:
            errs.append(str(e))
            continue
        return open_input(path, role) if exists else check(path, role)
    msg = (f'gmg guard: refused io_gt {kind} input {path}: io_gt root not on the gmg allow-list for roles {roles} '
           f'(mode {mode()}): ' + ' | '.join(errs))
    _record_refusal(path, f'io_gt:{kind}', msg, via='io_gt')
    raise GuardError(msg)


_IO_GT_PROBE = dict(obs='ep0_x.npz', corr='ep0_x.corr.npz', poses='ep0/poses.npz', mesh='x.glb')


def io_gt_roots_report():
    """{kind: {root: 'allowed as <role>' | 'refused: <reason>'}} for autokit.io_gt.ROOTS in the current mode."""
    if MESH_RESEARCH not in sys.path:
        sys.path.insert(0, MESH_RESEARCH)
    from autokit import io_gt
    out = {}
    for kind, rts in io_gt.ROOTS.items():
        out[kind] = {}
        for r in rts:
            probe = r if os.path.splitext(r)[1] else os.path.join(r, _IO_GT_PROBE.get(kind, 'x.npz'))
            if CFG['run'] and CFG['run'].startswith(_real(r) + '/'):
                probe = os.path.join(CFG['run'], 'bundle', 'ep0_x.npz')
            res = None
            for role in [x for x in IO_GT_ROLES.get(kind, ()) if x not in DEV_ROLES or mode() == 'dev']:
                try:
                    check(probe, role)
                    res = f'allowed as {role}'
                    break
                except GuardError as e:
                    res = 'refused: ' + str(e).split(': ', 2)[-1]
            out[kind][r] = res or f'refused: no gmg role for io_gt kind {kind!r} in mode {mode()}'
    return out


# ------------------------------------------------------------------------------------------------ constants
def constant(name, value, origin):
    """Register a constant with its origin (PREREG A.6) and return VALUE. origin: 'sensor', 'generic', 'kit' or
    'informed' (optionally ':<note>'), 'fitted:<what>' or 'fallback:<what>'. A name keeps one value and origin per
    run; the scan-informed values of SPEC section 2 (7 mm ball radius, 2.5 mm thickness, V3 tau 0.20) are refused
    unless fitted (or, for the thickness, the pre-registered fallback)."""
    if not isinstance(name, str) or not re.match(r'^[A-Za-z][\w.\-]*$', name):
        raise ValueError(f'gmg constant: bad name {name!r}')
    if not isinstance(origin, str):
        raise ValueError(f'gmg constant {name}: origin must be a string')
    head, _, what = origin.partition(':')
    head = head.strip()
    if head not in ORIGIN_HEADS:
        raise ValueError(f'gmg constant {name}: origin {origin!r} must start with one of {ORIGIN_HEADS}')
    if head in ('fitted', 'fallback') and not what.strip():
        raise ValueError(f'gmg constant {name}: origin {head!r} needs ":<what>"')
    if head == 'fitted' and re.search(r'scan|mocap|gt\b|ground.?truth|library|cdo|cd-o|add\b', what, re.I):
        raise GuardError(f'gmg constant {name}: fitted to {what!r}: constants are never fitted to scans or GT')
    try:
        v = json.loads(json.dumps(value))
    except (TypeError, ValueError):
        raise ValueError(f'gmg constant {name}: value is not JSON-serialisable')
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        for rx, vals, ok in BANNED:
            if rx.search(name) and any(abs(float(v) - b) <= 1e-9 * max(1.0, abs(b)) for b in vals) and head not in ok:
                raise GuardError(f'gmg constant {name}={v} ({origin}): a scan-informed value (SPEC section 2); '
                                 f'allowed only with origin {ok}')
    old = _CONSTANTS.get(name)
    if old is not None and (old['value'] != v or old['origin'] != origin):
        raise ValueError(f'gmg constant {name}: already {old["value"]} ({old["origin"]}), now {v} ({origin})')
    f = sys._getframe(1)
    _CONSTANTS[name] = dict(name=name, value=v, origin=origin,
                            where=f'{os.path.relpath(f.f_code.co_filename, CFG["repo"])}:{f.f_lineno}')
    return value


def constants():
    return [dict(c) for c in _CONSTANTS.values()]


# ------------------------------------------------------------------------------------------------ manifest
def inputs():
    return [dict(r) for _, r in sorted(_INPUTS.items())]


def refusals():
    return [dict(r) for r in _REFUSALS]


def tier():
    """Worst tier among the recorded inputs ('DEV' for any dev-mode run)."""
    ts = [r['tier'] for r in _INPUTS.values()] + (['DEV'] if mode() == 'dev' else [])
    return max(ts, key=TIER_ORDER.get) if ts else 'P0'


def _git(*args):
    try:
        return subprocess.run(['git', '--no-optional-locks', '-C', CFG['repo'], *args], capture_output=True,
                              text=True, timeout=60).stdout.strip()
    except Exception:
        return None


def manifest(extra=None):
    """Everything a run must report about its inputs (SPEC sections 2, 6): mode, tier, code commit, roots, deny-list
    sources, every input with role, realpath, sha256, bytes and tier, the constants with origins, and every
    refusal."""
    gm = os.path.relpath(GMG_DIR, CFG['repo'])
    dirty = _git('status', '--porcelain', '--', gm, os.path.relpath(os.path.join(MESH_RESEARCH, 'autokit'),
                                                                     CFG['repo']), 'pipeline/provenance.py')
    m = dict(schema='gmg-manifest/1', spec='SPEC v1 rev 1 (freeze fd814f6)', mode=mode(), tier=tier(),
             created_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
             commit=_git('rev-parse', 'HEAD'), code_dirty=bool(dirty), code_dirty_files=(dirty or '').splitlines(),
             host=socket.gethostname(), python=sys.version.split()[0], argv=list(sys.argv), cwd=os.getcwd(),
             pid=os.getpid(), roots=roots(), fixture_roots=list(_FIXTURE_ROOTS),
             denylist=dict(sources=DENY['sources'], globs=len(DENY['globs']), sha256=len(DENY['sha256'])),
             hook=dict(_HOOK), inputs=inputs(), constants=constants(), refusals=refusals())
    if extra:
        m['extra'] = extra
    return m


def write_manifest(path, extra=None):
    """Write manifest() as JSON to PATH (inside the run folder when one is set). Returns the manifest."""
    m = manifest(extra)
    rp = _real(path)
    if CFG['run'] and not rp.startswith(CFG['run'] + '/'):
        raise GuardError(f'gmg guard: manifest {rp} must be inside the run folder {CFG["run"]}')
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    with open(rp, 'w') as f:
        json.dump(m, f, indent=1)
    return m


# ------------------------------------------------------------------------------------------------ open hook
def _is_code(rp):
    b = os.path.basename(rp)
    if b.endswith(CODE_SUFFIX) or '.so.' in b or '/__pycache__/' in rp:
        return True
    return any(rp.startswith(p.rstrip('/') + '/') for p in
               {sys.prefix, sys.base_prefix, sys.exec_prefix, '/usr/lib', '/usr/local/lib', '/usr/share'} if p)


def _hook_reason(path):
    a = os.path.abspath(os.fsdecode(path))
    rp = os.path.realpath(a)
    code = _is_code(rp)
    for q in dict.fromkeys((a, rp)):
        r = _path_reason(q, '*hook*', code=code, rp=rp)
        if r:
            return q, r
    return None


def _audit(event, args):
    if event != 'open' or getattr(_TLS, 'busy', False):
        return
    path = args[0] if args else None
    if path is None or isinstance(path, int):
        return
    _TLS.busy = True
    try:
        hit = _hook_reason(path)
    except Exception:                                               # fail open on an internal error, but count it
        hit = None
        _HOOK['errors'] = _HOOK.get('errors', 0) + 1
    finally:
        _TLS.busy = False
    if hit:
        _HOOK['blocked'] += 1
        _record_refusal(hit[0], '*open*', hit[1], via='hook')
        raise GuardError(f'gmg guard: refused open of {hit[0]}: {hit[1]}')


def install_hook():
    """Install the in-process open() guard (permanent for the interpreter; done at import)."""
    if not _HOOK['installed']:
        sys.addaudithook(_audit)
        _HOOK['installed'] = True


sys.modules.setdefault('gmg.guard', sys.modules[__name__])
install_hook()
