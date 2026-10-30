"""gmg input guard (module M0 of SPEC v1 rev 1, sections 2, 3 and 7; build step B0, round 3).

Every gmg input goes through this module. It decides, before a file is opened, whether the file may be read, and it
records every input that passes with its sha256, so a run's manifest lists exactly what the run read.

  open_input(path, role) -> realpath     check a file for a role and record it (sha256, tier). A det file (below) is
                                         refused here: it is read through load_npz only.
  load_npz(path, role, keys=None)        open_input + key filter (det files: mask keys only, under ANY role; tracks:
                                         poses only)
  load_json(path, role)                  open_input + json.load
  mode() -> 'clean' | 'dev'              env GMG_MODE, read once at import (default 'clean')
  constant(name, value, origin)          constant registry with origins (sensor, generic, kit, informed:<A.6 row>,
                                         fitted:<what>, fallback:<what>; PREREG A.6)
  manifest() / write_manifest(path)      mode, tier, commit, roots, every input with sha256, constants, refusals and
                                         the outputs this process wrote; write_manifest appends the outputs to the
                                         run's provenance ledger RUN/outputs.jsonl
  set_run(path) / run_dir()              the run folder (role own): clean DATA/gmg/runs/<yyyymmdd>-<tag>-<commit7>/,
                                         dev DATA/gmg/runs-dev/<...>/, each with the marker RUN/run_tier.json
  register_output(path)                  declare a run file this process wrote through C code or a child process
  check_io_gt(path, kind)                bridge for autokit/io_gt.py: an io_gt input inside a gmg process must also
                                         pass this guard (an io_gt root that is not on the gmg allow-list is refused)
  io_gt_roots_report()                   which io_gt roots this guard admits in the current mode

Checks of open_input, in this order (a path is refused before the file is opened; only a file that passed every path
check is hashed, which reads its bytes but decodes nothing):
  1. the role exists, and a dev-only role (obs_all, x0_pool, fixture, dev_frozen, dev_hands) is refused in clean mode;
  2. path substrings /scan, /loc/, _align, .parquet, mocap (case-insensitive; as given and resolved through links);
  3. the deny-list globs (ops/provenance/denylist.json through pipeline/provenance.py, plus the repo file itself, plus
     GMG_EXTRA_DENYLIST, which can only add entries);
  4. the revision-1 refusals (library_v1..v4 and v3x, results/prim, scratchpad prim/, lathe/, auto/, gen/mesh-*,
     crops/, evalcrops/, diag/, gmg/design/, obs_all/, obs/; round 3: the HF dataset's track_3/*/mesh/ and urdf/).
     In dev mode a dev role named in REFUSED may pass its own folder; in clean mode nothing does, and that holds even
     if a later allow-list change would admit the folder;
  5. the allow-list of the role (ROLE_PATTERNS, on the resolved path; the kit role excludes the scorer); files in the
     run folder need a valid run marker (clean mode: a clean marker bound to this folder, never DEV, never missing);
  6. the file exists, is a regular file and has exactly one hard link;
  7. its sha256 is not on the deny-list (renamed copies), and matches expect_sha256 if one is given, and, for
     data/eval/ep*/poses.npz, the frozen store run in gmg/frozen_eval_tracks.json (SPEC section 17; clean mode refuses
     eval tracks while that registry is absent);
  8. det identity (by the file, not by the role): a file named det_f<N>.npz, any .npz under DATA/data/store/ep*/, a
     file whose sha256 is in the det registry (gmg/det_registry.json plus every det file hashed in this process), or a
     zip whose member names carry the det signature keys (sim, chosen, gdino, template_*, ...). Such a file is read
     only through load_npz and only its mask keys, whatever the role;
  9. run provenance (clean mode, files in the run folder): the file was written by this process, or the run's ledger
     RUN/outputs.jsonl lists it with its current sha256. The ledger is appended only by write_manifest of a guarded
     process of this run, so a file moved, linked or copied into the run by anyone else is never an input.
A Python audit hook (installed at import) also refuses, in-process:
  - open() / os.open() (dir_fd resolved) of a path that fails checks 2-4 (files with a code suffix are exempt from
    check 2 only, since e.g. json/scanner.py contains '/scan'), of the kit scorer (so it cannot be imported), of the
    dev run root in clean mode, of a det file outside load_npz (so shutil.copy, np.load or an a+b open of a det file
    fail), of a data file with more than one hard link (under DATA, KIT, WEIGHTS or gmg/, outside the interpreter),
    and of a run file that fails check 9 (unless the open truncates it);
  - every write, rename/replace (source and destination), hard link, symlink, mkdir, truncate, remove or rmtree under
    a run root outside the current run folder, or of a run root itself; a rename into a clean run from outside it; a
    symlink in a clean run that points outside it; any hard link inside a run root; any write, rename or link onto
    run_tier.json or outputs.jsonl except by set_run / write_manifest (checked on the call stack, so the private
    thread-local flags cannot be set by hand; the same holds for the det-file door of load_npz);
  - process arguments (subprocess, exec, spawn, os.system) with a path that fails checks 2-4 or a URL that names
    ground truth (the GT substrings, the HF dataset track_3 mesh/, urdf/, data/), and such URLs in urllib requests
    and http.client request lines.
Opens from C code are not seen by the hook; the strace audit (tools/strace_audit.py) covers them, attributes every
call to the program image that made it, reconciles every det-file open against the guard's own count and checks the
manifest's outputs against the files the audited command wrote.

Roots: DATA = env GMG_DATA_ROOT (default: this session's scratchpad), KIT = env GMG_KIT_ROOT (default
DATA/kit/v2d_submission_kit), WEIGHTS = env GMG_WEIGHTS_ROOT (default DATA/weights). KIT and WEIGHTS may not contain
or lie inside DATA/data, DATA/cache, DATA/hfds, the run roots, the repository or a refused folder (import fails
otherwise). RUN = env GMG_RUN or set_run(). All are read once at import and recorded in the manifest.
Tiers (SPEC section 3): P0 raw inputs; P1 Phase-1 tracks (library-templated); own files carry the run marker's tier
(clean runs start at P1; a missing or unreadable marker means DEV, never P1); dev roles and every dev-mode run are DEV.
The worst tier wins.
"""
from __future__ import annotations

import contextlib
import datetime
import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import socket
import stat
import subprocess
import sys
import threading
import time
import zipfile

GMG_DIR = os.path.dirname(os.path.abspath(__file__))
MESH_RESEARCH = os.path.dirname(GMG_DIR)                                   # docs/research/mesh-2026-10-26
REPO = os.path.abspath(os.path.join(MESH_RESEARCH, '..', '..', '..'))
SCRATCH_DEFAULT = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
DENYLIST_REPO = os.path.join(REPO, 'ops', 'provenance', 'denylist.json')
PROVENANCE_PY = os.path.join(REPO, 'pipeline', 'provenance.py')
DET_REGISTRY = os.path.join(GMG_DIR, 'det_registry.json')           # sha256 + member names of the det dumps
FROZEN_EVAL_TRACKS = os.path.join(GMG_DIR, 'frozen_eval_tracks.json')  # SPEC section 17 (written by B19)

MODES = ('clean', 'dev')
SUBSTRINGS = ('/scan', '/loc/', '_align', '.parquet', 'mocap')
CLEAN_ROLES = ('calib', 'tracks', 'depth', 'video', 'det', 'roster', 'kit', 'weights', 'own', 'frozen')
DEV_ROLES = ('obs_all', 'x0_pool', 'fixture', 'dev_frozen', 'dev_hands')
ROLES = CLEAN_ROLES + DEV_ROLES
# npz key filters (fnmatch patterns). det_f0.npz also holds library-derived fields (sim, template_*, chosen, score*,
# verify*, rules, params, ...) and the Grounding DINO boxes (gdino): all refused (SPEC section 2). NPZ_KEYS['det']
# applies to every det file (det identity, check 8) whatever the role it is opened under.
NPZ_KEYS = dict(det=('masks', 'mask_shape', 'frame', 'K', 'image', 'depth', 'names'),
                tracks=('world_T_cam', 'cam_T_*'),
                dev_hands=('joints_left', 'joints_right', 'valid_left', 'valid_right', 'a_offset'))
DET_NAME = re.compile(r'^det_f\d+\.npz$', re.I)
DET_DIRS = ('{DATA}/data/store/ep*/**',)
# member names that mark a det dump (distinctive library-derived fields; generic names such as area, score, params are
# left out so an own bundle is not mistaken for one). A zip with at least DET_SIGNATURE_MIN of them is a det file.
DET_SIGNATURE = ('sim', 'chosen', 'gdino', 'template_extent', 'template_intensity', 'verify', 'verify_matched',
                 'score_rules', 'reprop')
DET_SIGNATURE_MIN = 2
# kit files that score (or read reference data); refused for role kit, and refused by the open hook in both modes (so
# they cannot be imported either: the source and its __pycache__ byte code)
KIT_SCORER = ('metric_code/**', 'v2dlb/object_mesh.py', 'v2dlb/object_pose.py', 'v2dlb/track3_pose.py',
              'v2dlb/mhr_metrics.py', 'v2dlb/vertices.py', 'v2dlb/trajectory.py', 'v2dlb/dataset.py')
KIT_SCORER_HOOK = tuple('{KIT}/' + s for s in KIT_SCORER) + tuple(
    '{KIT}/v2dlb/__pycache__/' + os.path.basename(s)[:-3] + '.*' for s in KIT_SCORER if s.endswith('.py'))
# named test fixtures (dev role fixture) with the sha256 prefix of the raw file. PREREG B.14 T-V2d names the hand-kit lid
# potlid/fit/ep2 by its LABEL sha prefix e1be3218a8608793, which is the sha of the budgeted mesh the label scored
# (FIXTURE_LABEL_SHA; B1 checks it after fit_budget); the raw file hashes to 4bd1751e84052f05 [M] (DEVIATIONS 18).
FIXTURE_FILES = {'{DATA}/prim/potlid/cand/white_pot_lid_ep2_fit.glb': '4bd1751e84052f05'}
FIXTURE_LABEL_SHA = {'{DATA}/prim/potlid/cand/white_pot_lid_ep2_fit.glb': 'e1be3218a8608793'}
RUNS = dict(clean='{DATA}/gmg/runs', dev='{DATA}/gmg/runs-dev')
MARKER = 'run_tier.json'            # RUN/run_tier.json: written by set_run only (the open hook refuses other writers)
LEDGER = 'outputs.jsonl'            # RUN/outputs.jsonl: the run's provenance ledger, appended by write_manifest only
PROTECTED = (MARKER, LEDGER)
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
    dev_frozen=('{GMG}/dev_constants.json',),      # B1: t0_dev (PREREG A.1 on obs_all), dev runs only
    # B2: the existing MediaPipe hands (pipeline/hands_mp.py: cam_a video + our depth + VO; no GT read) stand in for M1
    # (hands_cpu.py, build step B4) in dev runs only; clean runs use M1's own output in RUN (DEVIATIONS 6, 54)
    dev_hands=('{DATA}/data/sweep/ep*/hands.npz',),
)
EVAL_TRACKS = '{DATA}/data/eval/ep*/poses.npz'
# revision-1 refusals: (name, patterns, dev roles that may pass this folder in dev mode only)
REFUSED = (
    ('meshes/library_v1..v4, library_v3x', ('**/meshes/library_v[1-4]/**', '**/meshes/library_v3x/**'), ()),
    ('results/prim', ('**/results/prim/**',), ('x0_pool',)),
    ('scratchpad/prim', ('{DATA}/prim/**', '**/scratchpad/prim/**'), ('x0_pool',)),
    ('scratchpad/lathe', ('{DATA}/lathe/**', '**/scratchpad/lathe/**'), ('x0_pool',)),
    ('scratchpad/auto (stage-1b outputs)', ('{DATA}/auto/**', '**/scratchpad/auto/**'), ()),
    ('scratchpad/gen/mesh-* (generator outputs seeded with library_v3)',
     ('{DATA}/gen/mesh-*', '{DATA}/gen/mesh-*/**', '**/scratchpad/gen/mesh-*', '**/scratchpad/gen/mesh-*/**'),
     ('x0_pool',)),
    ('scratchpad/crops (library_v3 seeds)', ('{DATA}/crops/**', '**/scratchpad/crops/**'), ()),
    ('scratchpad/evalcrops (library_v3 seeds)', ('{DATA}/evalcrops/**', '**/scratchpad/evalcrops/**'), ()),
    ('scratchpad/diag (scan placements, load_scan)', ('{DATA}/diag/**', '**/scratchpad/diag/**'), ()),
    ('scratchpad/gmg/design (design-probe outputs)', ('{DATA}/gmg/design/**', '**/scratchpad/gmg/design/**'), ()),
    ('scratchpad/obs_all (library_v3 ROI and --others)', ('{DATA}/obs_all/**', '**/scratchpad/obs_all/**'),
     ('obs_all',)),
    ('scratchpad/obs (library ROI)', ('{DATA}/obs/**', '**/scratchpad/obs/**'), ()),
    ('HF dataset track_3 mesh/ and urdf/ (public scans and their URDFs)',
     ('**/track_3/*/mesh/**', '**/track_3/*/urdf/**', '**/track_3/*/mesh', '**/track_3/*/urdf'), ()),
)
# the folders of REFUSED as concrete paths (for the KIT/WEIGHTS root check)
REFUSED_DIRS = ('{REPO}/meshes', '{MR}/results/prim', '{DATA}/prim', '{DATA}/lathe', '{DATA}/auto', '{DATA}/gen',
                '{DATA}/crops', '{DATA}/evalcrops', '{DATA}/diag', '{DATA}/gmg/design', '{DATA}/obs_all', '{DATA}/obs')
ORIGIN_HEADS = ('sensor', 'generic', 'kit', 'informed', 'fitted', 'fallback')
# PREREG A.6 rows whose origin is 'informed' (an informed constant must name one; tests check this list against A.6)
INFORMED_A6 = ('V5', 'ball detector', 'class order', 'grammar', 'slab two-face thickness', 'track sanity',
               'identity tests', 'K-a / K-b FSV difference')
TIER_ORDER = {'P0': 0, 'P1': 1, 'DEV': 2}
RUN_NAME = re.compile(r'^\d{8}-[a-z0-9][a-z0-9._-]*-[0-9a-f]{7}$')
CODE_SUFFIX = ('.py', '.pyc', '.pyi', '.so', '.pyd', '.pth')
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
# constants SPEC section 2 says are not used (scan-informed): refused unless their origin says fitted (or fallback for
# the pre-registered t0 fallback, PREREG A.6). Names are matched loosely; values exactly.
BANNED = ((re.compile(r'radius|(^|[_.])(r|rad)([_.]|$)|ball|marker|sphere|bead', re.I), (7.0, 0.007), ('fitted',)),
          (re.compile(r'diam', re.I), (14.0, 0.014), ('fitted',)),
          (re.compile(r'thick|wall|shell|(^|[_.])t0?([_.]|$)', re.I), (2.5, 0.0025), ('fitted', 'fallback')),
          (re.compile(r'tau|v3|veto|fold', re.I), (0.2,), ('fitted',)))


class GuardError(Exception):
    """An input (or an open, rename, link, ...) is refused by the gmg guard. Deliberately not an OSError (round 3):
    library fallbacks that catch OSError (shutil.move's copy fallback, importlib's byte-code fallback, retry loops)
    must not swallow a refusal and carry on another way."""


# ------------------------------------------------------------------------------------------------ configuration
def _real(p):
    return os.path.realpath(os.path.abspath(os.path.expanduser(p)))


def _load_cfg():
    m = os.environ.get('GMG_MODE', 'clean').strip().lower() or 'clean'
    if m not in MODES:
        raise GuardError(f'gmg guard: GMG_MODE={m!r} is not one of {MODES}')
    data = _real(os.environ.get('GMG_DATA_ROOT', SCRATCH_DEFAULT))
    if data == '/':
        raise GuardError('gmg guard: GMG_DATA_ROOT may not be /')
    return dict(mode=m, data=data, repo=_real(REPO), gmg=_real(GMG_DIR), mr=_real(MESH_RESEARCH),
                kit=_real(os.environ.get('GMG_KIT_ROOT', os.path.join(data, 'kit', 'v2d_submission_kit'))),
                weights=_real(os.environ.get('GMG_WEIGHTS_ROOT', os.path.join(data, 'weights'))),
                run=None, extra_deny=os.environ.get('GMG_EXTRA_DENYLIST') or None)


CFG = _load_cfg()
_INPUTS = {}            # realpath -> record
_REFUSALS = []          # every refusal (open_input, load_npz keys, hook)
_CONSTANTS = {}         # name -> record
_SHA = {}               # (realpath, size, mtime_ns, ino) -> sha256
_IDENT = {}             # (realpath, size, mtime_ns, ino) -> det identity reason or ''
_ADMITTED = set()       # realpaths admitted by open_input (the hook lets these through in dev mode)
_GUARDED_OPENS = {}     # realpath -> opens the hook let through inside load_npz / guard internals (det reconciliation)
_RX = {}                # compiled pattern cache
_TLS = threading.local()
_HOOK = dict(installed=False, blocked=0)


def mode():
    """'clean' or 'dev' (env GMG_MODE, read once at import; default 'clean')."""
    return CFG['mode']


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


def _esc(v):
    return v.replace('[', '[[]').replace('{', '[{]').replace('*', '[*]')


def _sub(pat, raw=False):
    """Pattern with roots substituted, or None if it names an unset root (RUN before set_run)."""
    keys = dict(DATA=CFG['data'], REPO=CFG['repo'], GMG=CFG['gmg'], MR=CFG['mr'], KIT=CFG['kit'],
                WEIGHTS=CFG['weights'], RUN=CFG['run'])
    for k, v in keys.items():
        tok = '{' + k + '}'
        if tok in pat:
            if v is None:
                return None
            pat = pat.replace(tok, v if raw else _esc(v))
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


def _under(p, root):
    return p == root or p.startswith(root.rstrip('/') + '/')


def runs_root(m=None):
    """The run root of mode M (default: the current mode)."""
    return _sub(RUNS[m or mode()], raw=True)


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
    with open(path) as f:
        d = json.load(f)
    return list(d.get('globs', [])), dict(d.get('sha256', {}))


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def _stkey(rp, st=None):
    st = st or os.stat(rp)
    return (rp, st.st_size, st.st_mtime_ns, st.st_ino)


def _sha256(rp):
    """sha256 of a file (reads the bytes, decodes nothing; cached on path, size, mtime and inode)."""
    key = _stkey(rp)
    if key not in _SHA:
        _SHA[key] = _sha_file(rp)
    return _SHA[key]


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


DENY = _load_deny()


def _deny_glob(path):
    """The deny-list glob a path matches (provenance semantics: fnmatch on the absolute and the repo-relative path)."""
    rel = os.path.relpath(path, CFG['repo']) if path.startswith(CFG['repo'] + os.sep) else None
    for g in DENY['globs']:
        if fnmatch.fnmatch(path, g) or (rel is not None and fnmatch.fnmatch(rel, g)):
            return g
    r = PROV._glob_hit(path)
    return r


# ------------------------------------------------------------------------------------------------ roots
def _root_problem(name, root):
    """Why a KIT or WEIGHTS root is unsafe, or None: it may not contain (or equal) DATA, DATA/data, DATA/cache, the
    run roots, the repository or a refused folder, and may not lie inside DATA/data, DATA/cache, DATA/gmg, the
    repository or a refused folder."""
    D = CFG['data']
    keep_out = [D, os.path.join(D, 'data'), os.path.join(D, 'cache'), os.path.join(D, 'gmg'), os.path.join(D, 'hfds'),
                runs_root('clean'), runs_root('dev'), CFG['repo'], CFG['gmg']] + [_sub(x, raw=True) for x in REFUSED_DIRS]
    for p in keep_out:
        if _under(p, root):
            return f'{name} root {root} contains {p}'
    for p in [os.path.join(D, 'data'), os.path.join(D, 'cache'), os.path.join(D, 'gmg'), os.path.join(D, 'hfds'),
              CFG['repo']] + [_sub(x, raw=True) for x in REFUSED_DIRS]:
        if _under(root, p):
            return f'{name} root {root} lies inside {p}'
    r = _path_reason(root + '/x', '*root*')
    if r:
        return f'{name} root {root}: {r}'
    return None


# ------------------------------------------------------------------------------------------------ checks
def _record_refusal(path, role, reason, via='open_input'):
    _REFUSALS.append(dict(path=str(path), role=role, reason=reason, via=via,
                          utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')))


def _path_reason(q, role, *, code=False, rp=None):
    """Reason a path (absolute) fails checks 2-4 for ROLE, or None. code=True skips the substrings (a file with a code
    suffix, in the hook and the audit only)."""
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
        s = _sub(pat, raw=True)
        if s is not None and _real(s) == rp:
            return pat
    return None


# ---- run folder, its marker and its provenance ledger
def _marker_path(rp):
    return os.path.join(rp, MARKER)


def _read_marker(rp):
    """The run marker dict, None if missing, or {'invalid': reason}. A valid marker names its own folder (run = the
    folder name, root = the name of the run root of its mode) and lies in the run root of its mode, so a marker copied
    from another run, or a folder moved between the dev and the clean root, is invalid."""
    p = _marker_path(rp)
    if not os.path.lexists(p):
        return None
    try:
        with open(p) as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        return dict(invalid=f'unreadable marker: {e}')
    if not isinstance(d, dict) or d.get('mode') not in MODES or d.get('tier') not in TIER_ORDER:
        return dict(invalid=f'bad marker {d!r}')
    if d['mode'] == 'dev' and d['tier'] != 'DEV':
        return dict(invalid=f'dev marker with tier {d["tier"]!r}')
    root = runs_root(d['mode'])
    if d.get('run') != os.path.basename(rp) or d.get('root') != os.path.basename(root):
        return dict(invalid=f'marker names run {d.get("run")!r} under {d.get("root")!r}, not this folder '
                            f'{os.path.basename(rp)!r} under {os.path.basename(root)!r} (copied or moved marker)')
    if os.path.dirname(rp) != root:
        return dict(invalid=f'a {d["mode"]}-mode marker in a folder outside the {d["mode"]} run root {root}')
    return d


def set_run(path):
    """Set the run folder (role own) once. Clean mode: DATA/gmg/runs/<yyyymmdd>-<tag>-<commit7>; dev mode:
    DATA/gmg/runs-dev/<...>. A new (or empty) folder is created with the marker run_tier.json (clean: mode clean,
    tier P1; dev: mode dev, tier DEV; plus the run name and root). An existing folder needs a valid marker of the same
    mode; clean mode refuses a folder whose marker is missing, invalid or DEV (a missing marker never means P1). Only
    set_run writes the marker: the open hook refuses every other write, rename, link or symlink onto run_tier.json.
    Files already in an existing clean run folder are read only if the run's ledger (outputs.jsonl) lists them with
    their current sha256 (see _provenance_reason)."""
    rp = _real(path)
    if CFG['run'] is not None and CFG['run'] != rp:
        raise GuardError(f'gmg guard: the run folder is already {CFG["run"]}')
    parent = runs_root()
    if os.path.dirname(rp) != parent or not RUN_NAME.match(os.path.basename(rp)):
        other = runs_root('dev' if mode() == 'clean' else 'clean')
        raise GuardError(f'gmg guard: run folder {rp} must be {parent}/<yyyymmdd>-<tag>-<commit7> in {mode()} mode '
                         f'({other} is the other mode\'s run root)')
    _check_patterns(rp + '/x', 'own', run_check=False)        # a run folder inside a refused folder is refused
    exists = os.path.isdir(rp) and bool(os.listdir(rp))
    mk = _read_marker(rp)
    if exists or mk is not None:
        if mk is None:
            raise GuardError(f'gmg guard: run folder {rp} exists without {MARKER}; a missing marker is never P1 '
                             f'(refused in {mode()} mode)')
        if 'invalid' in mk:
            raise GuardError(f'gmg guard: run folder {rp}: {mk["invalid"]}')
        if mk['mode'] != mode():
            raise GuardError(f'gmg guard: run folder {rp} is a {mk["mode"]}-mode run (marker), not {mode()}')
        if mode() == 'clean' and mk['tier'] == 'DEV':
            raise GuardError(f'gmg guard: run folder {rp} is tier DEV (marker); a clean run never uses it')
        CFG['run'] = rp
    else:
        with _protected():
            os.makedirs(rp, exist_ok=True)
            CFG['run'] = rp
            try:
                body = dict(mode=mode(), tier='DEV' if mode() == 'dev' else 'P1', run=os.path.basename(rp),
                            root=os.path.basename(parent), pid=os.getpid(), schema='gmg-run-marker/2',
                            created_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
                with open(_marker_path(rp), 'x') as f:
                    json.dump(body, f)
            except BaseException:
                CFG['run'] = None
                raise
    _RX.clear()
    return rp


def _own_tier():
    """Tier of the files in the run folder: the marker's tier; DEV in dev mode, and DEV when the marker is missing or
    invalid (fail closed, never P1)."""
    if not CFG['run']:
        return 'DEV'
    mk = _read_marker(CFG['run'])
    if mk is None or 'invalid' in mk or mk['mode'] != mode():
        return 'DEV'
    return 'DEV' if mode() == 'dev' else mk['tier']


_WRITTEN = {}           # realpath under RUN -> how this process wrote it ('python' open/rename, 'registered')
_LEDGER_CACHE = {}      # run -> ((size, mtime_ns, ino), {relpath: {sha256}})
T0_NS = time.time_ns()  # process start (register_output sanity check)


def _ledger(run):
    """{relpath: {sha256}} from RUN/outputs.jsonl: the lines of this mode whose run name is this folder's. Malformed
    lines are ignored (they admit nothing)."""
    p = os.path.join(run, LEDGER)
    try:
        st = os.stat(p)
    except OSError:
        return {}
    key = (st.st_size, st.st_mtime_ns, st.st_ino)
    c = _LEDGER_CACHE.get(run)
    if c and c[0] == key:
        return c[1]
    out, name = {}, os.path.basename(run)
    with open(p, errors='replace') as f:
        for ln in f:
            try:
                d = json.loads(ln)
            except ValueError:
                continue
            if (isinstance(d, dict) and d.get('mode') == mode() and d.get('run') == name
                    and isinstance(d.get('path'), str) and isinstance(d.get('sha256'), str)):
                out.setdefault(os.path.normpath(d['path']), set()).add(d['sha256'])
    _LEDGER_CACHE[run] = (key, out)
    return out


def _provenance_reason(rp):
    """Clean mode, check 9: why an existing regular file under the current run folder may not be read, or None. It
    may be read if this process wrote it, or if the run's ledger RUN/outputs.jsonl (appended by write_manifest of a
    clean guarded process of this run) lists it with its current sha256. So a file that another process put there
    (a dev process, a shell mv/cp, an unguarded byte copy of a refused folder) is refused, whatever the marker says.
    The marker and the ledger themselves are exempt."""
    run = CFG['run']
    if mode() != 'clean' or not run or not _under(rp, run) or rp == run:
        return None
    rel = os.path.relpath(rp, run)
    if rel in PROTECTED or rp in _WRITTEN:
        return None
    try:
        st = os.stat(rp)
    except OSError:
        return None
    if not stat.S_ISREG(st.st_mode):
        return None
    shas = _ledger(run).get(rel)
    if not shas:
        return (f'run provenance: {rel} has no entry in {LEDGER} (no clean guarded process of this run wrote it; '
                f'files moved, linked or copied into a run are never inputs)')
    if _sha256(rp) not in shas:
        return f'run provenance: {rel} differs from its {LEDGER} entries (sha256)'
    return None


def register_output(path):
    """Declare a file in the run folder that this process wrote through C code or a child process (the open hook sees
    Python-level writes only), so write_manifest records it in the ledger. The file must lie in the current run
    folder, be a regular file with one link and have been modified after this process started. The strace audit
    checks that every output in a manifest was written by the audited command. Returns the realpath."""
    rp = os.path.realpath(os.path.abspath(os.fspath(path)))
    run = CFG['run']
    if not run or not _under(rp, run) or rp == run:
        raise GuardError(f'gmg guard: register_output {rp}: not in the run folder {run}')
    if os.path.basename(rp) in PROTECTED:
        raise GuardError(f'gmg guard: register_output {rp}: {os.path.basename(rp)} is written by the guard only')
    st = os.lstat(rp)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        raise GuardError(f'gmg guard: register_output {rp}: not a regular file with one link')
    if st.st_mtime_ns < T0_NS - 2_000_000_000:
        raise GuardError(f'gmg guard: register_output {rp}: not modified since this process started')
    r = _path_reason(rp, '*hook*', rp=rp)
    if r:
        raise GuardError(f'gmg guard: register_output {rp}: {r}')
    _WRITTEN.setdefault(rp, 'registered')
    return rp


def _check_patterns(path, role, *, run_check=True):
    """Checks 1-5 (no file access beyond realpath and the run marker). Returns (abs path, realpath). Raises
    GuardError."""
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
            pats = [p for p in (_sub(x, raw=True) for x in ROLE_PATTERNS[role]) if p]
            why = f'not on the {role} allow-list {pats}' if pats else f'no run folder is set (role {role})'
            raise GuardError(f'gmg guard: refused {role} input {rp}: {why}')
        if role == 'kit' and _match(rp, tuple('{KIT}/' + s for s in KIT_SCORER)):
            raise GuardError(f'gmg guard: refused kit input {rp}: the kit scorer is excluded')
        if CFG['run'] and _under(rp, CFG['run']) and mode() == 'clean' and _own_tier() == 'DEV':
            raise GuardError(f'gmg guard: refused {role} input {rp}: the run folder marker is missing, invalid or '
                             f'DEV (clean mode)')
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
    _FIXTURE_ROOTS.append(_esc(rp) + '/**')
    return rp


def _tier(role, rp):
    if role in DEV_ROLES:
        return 'DEV'
    if CFG['run'] and _under(rp, CFG['run']):
        return _own_tier()
    if role in ('tracks', 'frozen'):
        return 'P1'
    return 'P0'


# ---- det identity (check 8)
def _load_det_registry():
    """{sha256: label} and {size} of the det dumps (gmg/det_registry.json, written by tools/det_registry.py), and the
    signature keys it lists. Missing file: empty registry (in-process hashes and the names still apply)."""
    sha, sizes, sig = {}, set(), set(DET_SIGNATURE)
    src = dict(path=DET_REGISTRY, present=os.path.isfile(DET_REGISTRY))
    if src['present']:
        with open(DET_REGISTRY) as f:
            d = json.load(f)
        for e in d.get('files', []):
            sha[e['sha256']] = f'det registry: {e.get("path")}'
            sizes.add(int(e['bytes']))
        sig |= set(d.get('signature_keys', []))
        src.update(sha256=_sha_file(DET_REGISTRY), files=len(d.get('files', [])))
    sig -= set(NPZ_KEYS['det'])
    return dict(sha=sha, sizes=sizes, signature=frozenset(sig), source=src)


DETREG = _load_det_registry()


def _local_det_originals():
    """{size: [realpath]} of the det dumps present under DATA (stat only; hashed lazily when a file of the same size
    shows up, so a copy of a dump that is not in det_registry.json is still recognised)."""
    import glob
    out = {}
    for p in glob.glob(os.path.join(glob.escape(CFG['data']), 'data', 'store', 'ep*', 'det_f*.npz')):
        try:
            rp = os.path.realpath(p)
            out.setdefault(os.stat(rp).st_size, []).append(rp)
        except OSError:
            continue
    return out


_LOCAL_DET = _local_det_originals()


def _sha_det_original(rp):
    """sha256 of a local det dump, hashed by the guard itself. The open is counted in _GUARDED_OPENS (inside the hook
    the open is not seen by the hook, so it is counted here) so the strace reconciliation matches."""
    try:
        key = _stkey(rp)
    except OSError:
        return None
    if key not in _SHA:
        if getattr(_TLS, 'busy', False):
            _GUARDED_OPENS[rp] = _GUARDED_OPENS.get(rp, 0) + 1
        with _internal():
            _SHA[key] = _sha_file(rp)
    return _SHA[key]


def _npz_names(rp):
    """Member names of a zip/npz (the central directory only; no member is decompressed), or None if not a zip."""
    try:
        with open(rp, 'rb') as f:
            if f.read(4) != b'PK\x03\x04':
                return None
        with zipfile.ZipFile(rp) as z:
            return {n[:-4] if n.endswith('.npy') else n for n in z.namelist()}
    except GuardError:
        raise
    except (OSError, zipfile.BadZipFile, ValueError):
        return None


def _det_name_reason(*paths):
    """Cheap det identity: the file name or the det store folder."""
    for q in paths:
        if q and DET_NAME.match(os.path.basename(q)):
            return f'det file name {os.path.basename(q)!r}'
    for q in paths:
        if q and q.lower().endswith('.npz') and _match(q, DET_DIRS):
            return 'npz under data/store/ep*/ (det store folder)'
    return None


def _det_identity(a, rp, *, deep=True):
    """Why a file is a det file (check 8), or None. deep=True also checks the sha256 registry (only for a file whose
    size equals a registered det file) and the zip member names (signature keys)."""
    r = _det_name_reason(a, rp)
    if r or not deep or rp.startswith(('/proc/', '/sys/', '/dev/')):
        return r
    try:
        st = os.stat(rp)
    except OSError:
        return None
    if not stat.S_ISREG(st.st_mode):
        return None
    key = _stkey(rp, st)
    if key in _IDENT:
        return _IDENT[key] or None
    why = ''
    if st.st_size in DETREG['sizes'] or st.st_size in _LOCAL_DET:
        s = _sha256(rp)
        for orig in _LOCAL_DET.get(st.st_size, ()):
            if orig != rp and s not in DETREG['sha']:
                so = _sha_det_original(orig)
                if so:
                    DETREG['sha'].setdefault(so, f'local det dump {orig}')
        if s in DETREG['sha']:
            why = f'copy of a det file (sha256 {s[:16]}, {DETREG["sha"][s]})'
    if not why:
        names = _npz_names(rp)
        hit = sorted(names & DETREG['signature']) if names else []
        if len(hit) >= DET_SIGNATURE_MIN:
            why = f'det signature keys {hit[:6]}'
    _IDENT[key] = why
    return why or None


def _register_det(rp, sha, why):
    """A det file hashed in this process: its sha256 and size join the registry (so a later copy is caught)."""
    DETREG['sha'].setdefault(sha, f'hashed in process: {rp} ({why})')
    DETREG['sizes'].add(os.stat(rp).st_size)


@contextlib.contextmanager
def _internal():
    """Guard-internal file access (registry hashing, the strace auditor's own hashing): the det rule of the hook lets
    these opens through and counts them (path rules still apply)."""
    old = getattr(_TLS, 'internal', False)
    _TLS.internal = True
    try:
        yield
    finally:
        _TLS.internal = old


def check(path, role):
    """Path checks 1-5 only (nothing is opened or recorded). Returns the realpath; raises GuardError."""
    return _check_patterns(path, role)[1]


def _frozen_eval_sha(rp):
    """(expected sha256 or None, status) for an eval track file (SPEC section 17)."""
    if not _match(rp, (EVAL_TRACKS,)):
        return None, None
    if not os.path.isfile(FROZEN_EVAL_TRACKS):
        if mode() == 'clean':                       # fail closed: an unchecked eval track never enters a clean run
            raise GuardError(f'gmg guard: refused tracks input {rp}: the frozen eval-track registry '
                             f'{FROZEN_EVAL_TRACKS} is absent (SPEC section 17; tools/frozen_eval_tracks.py writes it)')
        return None, 'registry absent (dev mode)'
    with open(FROZEN_EVAL_TRACKS) as f:
        reg = json.load(f)
    ep = os.path.basename(os.path.dirname(rp))
    exp = (reg.get('files') or {}).get(ep)
    if not exp:
        raise GuardError(f'gmg guard: refused tracks input {rp}: {ep} is not in {FROZEN_EVAL_TRACKS}')
    return exp, 'checked against gmg/frozen_eval_tracks.json'


def open_input(path, role, *, expect_sha256=None, keys=None):
    """Check PATH for ROLE (module docstring, checks 1-8), record it with its sha256 and tier, return its realpath.
    A det file (check 8) is refused here unless load_npz is reading it. Raises GuardError (refused) or
    FileNotFoundError (missing)."""
    rp = None
    try:
        a, rp = _check_patterns(path, role)
        via_npz = getattr(_TLS, 'det_ok', None) == rp
        if (role == 'det' or _det_name_reason(a, rp)) and not via_npz:
            raise GuardError(f'gmg guard: refused {role} input {rp}: a det file is read through guard.load_npz only '
                             f'(mask keys)')
        _ADMITTED.add(rp)                    # the path checks passed: let the hook pass the hashing open (dev mode)
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
        frozen, frozen_status = _frozen_eval_sha(rp) if role == 'tracks' else (None, None)
        if frozen and sha != frozen:
            raise GuardError(f'gmg guard: refused tracks input {rp}: sha256 {sha[:16]} != frozen {frozen[:16]}')
        nf = _named_fixture(rp) if role == 'fixture' else None
        if nf and not sha.startswith(FIXTURE_FILES[nf]):
            raise GuardError(f'gmg guard: refused fixture {rp}: sha256 {sha[:16]} != {FIXTURE_FILES[nf]}')
        det = _det_identity(a, rp)
        if det and not via_npz:
            raise GuardError(f'gmg guard: refused {role} input {rp}: {det}; a det file is read through '
                             f'guard.load_npz only (mask keys)')
        if det:
            _register_det(rp, sha, det)
        prov = _provenance_reason(rp)
        if prov:
            raise GuardError(f'gmg guard: refused {role} input {rp}: {prov}')
    except (GuardError, OSError) as e:
        if rp is not None and rp not in _INPUTS:
            _ADMITTED.discard(rp)
        if isinstance(e, GuardError):
            _record_refusal(path, role, str(e))
        raise
    rec = _INPUTS.get(rp)
    if rec is None or rec['sha256'] != sha or rec['role'] != role:
        rec = dict(role=role, path=a, realpath=rp, sha256=sha, bytes=int(st.st_size), tier=_tier(role, rp))
        if det:
            rec['det_identity'] = det
        if frozen_status:
            rec['frozen_sha'] = frozen_status
        _INPUTS[rp] = rec
    if keys is not None:
        rec['keys'] = sorted(set(rec.get('keys', [])) | set(keys))
    _ADMITTED.add(rp)
    return rp


def _key_ok(k, pats):
    return any(fnmatch.fnmatchcase(k, p) for p in pats)


def _refuse_keys(path, role, keys, pats, why):
    bad = [k for k in keys if pats is not None and not _key_ok(k, pats)]
    if bad:
        msg = f'gmg guard: refused {role} keys {bad} of {path}: allowed {pats} ({why})'
        _record_refusal(path, role, msg, via='load_npz')
        raise GuardError(msg)


def load_npz(path, role, keys=None):
    """open_input + np.load(allow_pickle=False) of the allowed keys only. A det file (check 8: by name, store folder,
    sha256 registry or signature keys, whatever ROLE is) gets NPZ_KEYS['det']; role tracks gets NPZ_KEYS['tracks'].
    A requested key outside the filter raises GuardError before any member is decompressed; keys=None reads every
    allowed key present (refused keys are never read)."""
    import numpy as np
    a = os.path.abspath(os.fspath(path))
    rp = os.path.realpath(a)
    det = 'role det' if role == 'det' else _det_name_reason(a, rp)
    pats = NPZ_KEYS['det'] if det else NPZ_KEYS.get(role)
    if keys is not None:
        keys = list(keys)
        _refuse_keys(path, role, keys, pats, det or f'role {role}')
    old = getattr(_TLS, 'det_ok', None)
    _TLS.det_ok = rp
    try:
        rp = open_input(path, role)
        rec = _INPUTS[rp]
        if rec.get('det_identity') and not det:
            det, pats = rec['det_identity'], NPZ_KEYS['det']
            if keys is not None:
                _refuse_keys(path, role, keys, pats, det)
        with np.load(rp, allow_pickle=False) as Z:
            names = list(Z.files)
            sig = sorted(set(names) & DETREG['signature'])
            if len(sig) >= DET_SIGNATURE_MIN and pats is not NPZ_KEYS['det']:
                det, pats = f'det signature keys {sig[:6]}', NPZ_KEYS['det']
                rec['det_identity'] = det
                _register_det(rp, rec['sha256'], det)
                if keys is not None:
                    _refuse_keys(path, role, keys, pats, det)
            sel = keys if keys is not None else [k for k in names if pats is None or _key_ok(k, pats)]
            miss = [k for k in sel if k not in names]
            if miss:
                raise KeyError(f'{rp}: no keys {miss}')
            out = {k: Z[k] for k in sel}
    finally:
        _TLS.det_ok = old
    rec['keys'] = sorted(set(rec.get('keys', [])) | set(sel))
    rec['keys_not_read'] = sorted(set(names) - set(rec['keys']))
    if det:
        rec['key_filter'] = 'det'
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
    """Register a constant with its origin (PREREG A.6) and return VALUE. origin: 'sensor', 'generic' or 'kit'
    (optionally ':<note>'), 'informed:<A.6 row>' (the note must name a PREREG A.6 row whose origin is informed,
    INFORMED_A6), 'fitted:<what>' or 'fallback:<what>'. A name keeps one value and origin per run; the scan-informed
    values of SPEC section 2 (7 mm ball radius, 2.5 mm thickness, V3 tau 0.20) are refused under loosely matched names
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
    if head == 'informed' and not any(r.lower() in what.lower() for r in INFORMED_A6):
        raise GuardError(f'gmg constant {name}: origin {origin!r}: an informed constant must name its PREREG A.6 row '
                         f'(one of {INFORMED_A6})')
    if head == 'fitted' and re.search(r'scan|mocap|gt\b|ground.?truth|library|cdo|cd-o|add\b', what, re.I):
        raise GuardError(f'gmg constant {name}: fitted to {what!r}: constants are never fitted to scans or GT')
    if head == 'fitted' and re.search(r'\beval', what, re.I):
        raise GuardError(f'gmg constant {name}: fitted to {what!r}: constants are fitted on public observations only '
                         f'(SPEC section 2), never on eval episodes')
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


CODE_DIRS = (os.path.join(MESH_RESEARCH, 'gmg'), os.path.join(MESH_RESEARCH, 'autokit'),
             os.path.join(MESH_RESEARCH, 'scripts'), os.path.join(REPO, 'pipeline'))


def _outputs():
    """The files this process wrote in the run folder (open hook, os.rename/os.replace, register_output) that still
    exist, with sha256 and bytes (the manifest's outputs, appended to the ledger by write_manifest)."""
    run, out = CFG['run'], []
    if not run:
        return out
    for rp, how in sorted(_WRITTEN.items()):
        if not _under(rp, run) or rp == run or os.path.basename(rp) in PROTECTED:
            continue
        try:
            st = os.lstat(rp)
        except OSError:
            continue
        if stat.S_ISREG(st.st_mode):
            out.append(dict(path=os.path.relpath(rp, run), sha256=_sha256(rp), bytes=int(st.st_size), how=how))
    return out


def manifest(extra=None):
    """Everything a run must report about its inputs (SPEC sections 2, 6): mode, tier, code commit, roots, deny-list
    sources, every input with role, realpath, sha256, bytes and tier, the constants with origins, every refusal, and
    the outputs this process wrote in the run folder. code_dirty covers gmg/, autokit/, scripts/ and pipeline/."""
    dirty = _git('status', '--porcelain', '--', *[os.path.relpath(d, CFG['repo']) for d in CODE_DIRS])
    m = dict(schema='gmg-manifest/3', spec='SPEC v1 rev 1 (freeze fd814f6)', mode=mode(), tier=tier(),
             created_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
             commit=_git('rev-parse', 'HEAD'), code_dirty=bool(dirty), code_dirty_files=(dirty or '').splitlines(),
             code_dirs=[os.path.relpath(d, CFG['repo']) for d in CODE_DIRS],
             host=socket.gethostname(), python=sys.version.split()[0], argv=list(sys.argv), cwd=os.getcwd(),
             pid=os.getpid(), roots=roots(), runs_root=runs_root(),
             run_marker=_read_marker(CFG['run']) if CFG['run'] else None, own_tier=_own_tier() if CFG['run'] else None,
             fixture_roots=list(_FIXTURE_ROOTS),
             denylist=dict(sources=DENY['sources'], globs=len(DENY['globs']), sha256=len(DENY['sha256'])),
             det_registry=dict(DETREG['source'], sha256_known=len(DETREG['sha']),
                               signature_keys=sorted(DETREG['signature'])),
             guarded_opens=dict(sorted(_GUARDED_OPENS.items())),
             hook=dict(_HOOK), inputs=inputs(), constants=constants(), refusals=refusals(), outputs=_outputs())
    if extra:
        m['extra'] = extra
    return m


def _ledger_append(entries, man):
    """Append ENTRIES to RUN/outputs.jsonl in one write (O_APPEND). Only this function (and set_run for the marker)
    may write the protected files: the open hook checks the call stack."""
    run = CFG['run']
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    lines = ''.join(json.dumps(dict(e, run=os.path.basename(run), mode=mode(), pid=os.getpid(), manifest=man,
                                    utc=now)) + '\n' for e in entries)
    with _protected():
        fd = os.open(os.path.join(run, LEDGER), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, lines.encode())
        finally:
            os.close(fd)


def write_manifest(path, extra=None):
    """Write manifest() as JSON to PATH (inside the run folder when one is set) and append its outputs and the
    manifest file itself to the run's ledger RUN/outputs.jsonl. Returns the manifest."""
    m = manifest(extra)
    rp = _real(path)
    if CFG['run'] and not rp.startswith(CFG['run'] + '/'):
        raise GuardError(f'gmg guard: manifest {rp} must be inside the run folder {CFG["run"]}')
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    with open(rp, 'w') as f:
        json.dump(m, f, indent=1)
    if CFG['run']:
        rel = os.path.relpath(rp, CFG['run'])
        own = dict(path=rel, sha256=_sha256(rp), bytes=os.path.getsize(rp), how='manifest')
        _ledger_append([o for o in m['outputs'] if o['path'] != rel] + [own], rel)
    return m


# ------------------------------------------------------------------------------------------------ open hook
def _is_code(p):
    """A file with a code suffix (exempt from the GT substrings only, in the hook and the audit)."""
    b = os.path.basename(p)
    return b.endswith(CODE_SUFFIX) or '.so.' in b


@contextlib.contextmanager
def _protected():
    """set_run / _ledger_append: let the hook pass writes of the protected files (checked with the call stack)."""
    old = getattr(_TLS, 'protected', False)
    _TLS.protected = True
    try:
        yield
    finally:
        _TLS.protected = old


def _guard_frame(codes):
    """True if a frame of one of the guard functions CODES is on the call stack (so setting the private thread-local
    flags by hand does not open the det or protected-file doors)."""
    f = sys._getframe(1)
    for _ in range(40):
        if f is None:
            return False
        if f.f_code in codes:
            return True
        f = f.f_back
    return False


def _resolve(path, dir_fd=None, follow=True):
    """(absolute path, resolved path) of an audit-event path. follow=False resolves the parent only (rename, remove,
    symlink and mkdir act on the name itself, not on what it points to)."""
    s = os.fsdecode(path)
    if dir_fd is not None and not os.path.isabs(s):
        s = os.path.join(os.readlink(f'/proc/self/fd/{dir_fd}'), s)
    a = os.path.abspath(s)
    if follow:
        return a, os.path.realpath(a)
    return a, os.path.join(os.path.realpath(os.path.dirname(a)), os.path.basename(a))


def _path_hit(a, rp):
    """Path rules of the hook (checks 2-4, the kit scorer, the dev run root in clean mode): (path, reason) or None."""
    code = _is_code(rp)
    for q in dict.fromkeys((a, rp)):
        r = _path_reason(q, '*hook*', code=code, rp=rp)
        if r:
            return q, r
    if _match(rp, KIT_SCORER_HOOK) or _match(a, KIT_SCORER_HOOK):
        return rp, 'the kit scorer is never opened or imported by a gmg process'
    if mode() == 'clean' and _under(rp, runs_root('dev')):
        return rp, 'the dev run root is never touched in clean mode'
    return None


def _runs_hit(rp):
    """(path, reason) if RP is under a run root outside the current run folder, is the current run folder itself, or
    contains a run root (a write, rename, removal or link there would change another run or replace a run)."""
    run = CFG['run']
    for m in MODES:
        root = runs_root(m)
        if _under(root, rp):
            return rp, f'{rp} is or contains the {m} run root'
        if _under(rp, root) and not (run and _under(rp, run) and rp != run):
            return rp, f'write under the {m} run root outside the current run folder ({run})'
    return None


def _write_hit(rp):
    """(path, reason) if creating, truncating, appending, renaming or linking onto RP is refused."""
    if getattr(_TLS, 'protected', False) and _guard_frame(_PROTECTED_WRITERS):
        return None
    r = _runs_hit(rp)
    if r:
        return r
    if os.path.basename(rp) in PROTECTED and any(_under(rp, runs_root(m)) for m in MODES):
        return rp, f'{os.path.basename(rp)} is written by the guard only (set_run / write_manifest)'
    return None


def _det_door(rp):
    """An open the guard itself makes (load_npz's np.load, hashing, member names): counted for the strace
    reconciliation and let through."""
    if (getattr(_TLS, 'det_ok', None) == rp or getattr(_TLS, 'internal', False)) and _guard_frame(_DET_OPENERS):
        _GUARDED_OPENS[rp] = _GUARDED_OPENS.get(rp, 0) + 1
        return True
    return False


def _nlink_hit(rp):
    """SPEC section 2: a data file with more than one hard link is refused (files under DATA outside the interpreter,
    KIT, WEIGHTS and the gmg folder; code files and the interpreter are not checked)."""
    if _is_code(rp) or rp.startswith(_PREFIXES):
        return None
    if not any(_under(rp, CFG[k]) for k in ('data', 'kit', 'weights', 'gmg')):
        return None
    try:
        st = os.stat(rp)
    except OSError:
        return None
    if stat.S_ISREG(st.st_mode) and st.st_nlink > 1:
        return rp, f'regular file with {st.st_nlink} hard links'
    return None


def _open_reason(path, flags=0, dir_fd=None):
    """(path, reason) if the hook refuses this open, else None. Records Python-level writes in the run folder."""
    a, rp = _resolve(path, dir_fd)
    hit = _path_hit(a, rp)
    if hit:
        return hit
    write = bool(flags & WRITE_FLAGS)
    if write:
        hit = _write_hit(rp)
        if hit:
            return hit
    if _det_door(rp):
        return None
    readable = (flags & os.O_ACCMODE) != os.O_WRONLY
    if not (_is_code(rp) and not _det_name_reason(a, rp)):
        det = _det_identity(a, rp, deep=readable)
        if det:
            return rp, f'{det}: a det file is opened only inside guard.load_npz'
    if readable:
        hit = _nlink_hit(rp)
        if hit:
            return hit
    exists = os.path.lexists(rp)
    if exists and not (write and flags & os.O_TRUNC):
        r = _provenance_reason(rp)
        if r:
            return rp, r
    if write and CFG['run'] and _under(rp, CFG['run']) and rp != CFG['run'] and (exists or flags & os.O_CREAT):
        _WRITTEN.setdefault(rp, 'python')
    return None


def _tree_provenance(rp):
    """Provenance of a file, or of every regular file under a directory, in the current run (clean mode)."""
    if os.path.isdir(rp) and not os.path.islink(rp):
        for d, _, fs in os.walk(rp):
            for f in fs:
                r = _provenance_reason(os.path.join(d, f))
                if r:
                    return r
        return None
    return _provenance_reason(rp)


def _move_reason(src, dst, sfd=None, dfd=None):
    """os.rename / os.replace (and shutil.move): the source is removed and the destination written."""
    sa, srp = _resolve(src, sfd, follow=False)
    da, drp = _resolve(dst, dfd, follow=False)
    for q in ((sa, srp), (da, drp)):
        hit = _path_hit(*q)
        if hit:
            return hit
    hit = _runs_hit(srp)
    if hit:
        return srp, 'rename source: ' + hit[1]
    if os.path.basename(srp) in PROTECTED and any(_under(srp, runs_root(m)) for m in MODES):
        return srp, f'{os.path.basename(srp)} is moved by nobody'
    hit = _write_hit(drp)
    if hit:
        return hit
    run = CFG['run']
    if run and _under(drp, run):
        if mode() == 'clean' and not _under(srp, run):
            return drp, (f'rename into the clean run folder from outside it ({srp}); a clean run writes its files '
                         f'itself (temporary files inside RUN)')
        if mode() == 'clean':
            r = _tree_provenance(srp)
            if r:
                return srp, r
    if os.path.lexists(srp) and _det_identity(sa, srp, deep=False):
        return srp, 'a det file is never renamed (read it through guard.load_npz)'
    return None


def _link_reason(src, dst, sfd=None, dfd=None):
    """os.link: a second name for a file. Never inside a run root (SPEC: files with more than one link are refused),
    never of a refused or det file."""
    sa, srp = _resolve(src, sfd)
    da, drp = _resolve(dst, dfd, follow=False)
    for q in ((sa, srp), (da, drp)):
        hit = _path_hit(*q)
        if hit:
            return hit
    for q in (srp, drp):
        if any(_under(q, runs_root(m)) for m in MODES):
            return q, 'a hard link is never made inside a run root (files with more than one link are refused)'
    hit = _write_hit(drp)
    if hit:
        return hit
    if _det_identity(sa, srp, deep=True):
        return srp, 'a det file is never linked (read it through guard.load_npz)'
    return None


def _symlink_reason(target, dst, dfd=None):
    """os.symlink: the link name is a write; the target gets the path rules; in clean mode a link in the run folder
    must point inside it."""
    da, drp = _resolve(dst, dfd, follow=False)
    t = os.fsdecode(target)
    ta = os.path.abspath(t if os.path.isabs(t) else os.path.join(os.path.dirname(da), t))
    trp = os.path.realpath(ta)
    for q in ((da, drp), (ta, trp)):
        hit = _path_hit(*q)
        if hit:
            return hit
    hit = _write_hit(drp)
    if hit:
        return hit
    run = CFG['run']
    if mode() == 'clean' and run and _under(drp, run) and not (_under(trp, run) and trp != run):
        return drp, f'a symlink in the clean run folder must point inside it (target {trp})'
    for m in MODES:
        root = runs_root(m)
        if _under(trp, root) and not (run and _under(trp, run)):
            return trp, f'a symlink to another run under the {m} run root'
    return None


def _remove_reason(path, dir_fd=None, tree=False):
    """os.remove / os.unlink / os.rmdir / shutil.rmtree: never under a run root outside the current run folder, never
    a run root or one of its parents (CLAUDE.md: preserve existing runs)."""
    a, rp = _resolve(path, dir_fd, follow=False)
    hit = _runs_hit(rp)
    if hit:
        return rp, ('tree ' if tree else '') + 'removal: ' + hit[1]
    _WRITTEN.pop(rp, None)
    return None


def _truncate_reason(path, length):
    if isinstance(path, int):
        return None
    a, rp = _resolve(path)
    hit = _path_hit(a, rp) or _write_hit(rp)
    if hit:
        return hit
    if length and os.path.lexists(rp):
        r = _provenance_reason(rp)
        if r:
            return rp, r
    if CFG['run'] and _under(rp, CFG['run']) and rp != CFG['run']:
        _WRITTEN.setdefault(rp, 'python')
    return None


GT_URL = re.compile(r'track_3/[^/]+/(?:mesh|urdf|data)/', re.I)


def _url_reason(u):
    """A URL (or an http request target) that names ground truth: the GT substrings, or the HF dataset's track_3
    mesh/, urdf/ or data/ (parquet) folders."""
    low = u.lower()
    for s in SUBSTRINGS:
        if s in low:
            return f'URL contains {s!r}'
    if GT_URL.search(low):
        return 'URL names the HF dataset track_3 mesh/, urdf/ or data/ (ground truth)'
    return None


def _arg_reason(args):
    """Process arguments (subprocess, exec, spawn, system): an absolute path that fails the path rules, or a URL that
    names ground truth, is refused before the child starts."""
    if isinstance(args, (str, bytes, os.PathLike)):
        args = [args]
    for x in args or ():
        try:
            s = os.fsdecode(x)
        except TypeError:
            continue
        for tok in s.split():
            if '://' in tok:
                r = _url_reason(tok)
                if r:
                    return tok, r
            elif tok.startswith('/'):
                a = os.path.abspath(tok)
                r = _path_reason(a, '*hook*', code=_is_code(a)) or (
                    _match(a, KIT_SCORER_HOOK) and 'the kit scorer') or (
                    mode() == 'clean' and _under(a, runs_root('dev')) and 'the dev run root (clean mode)')
                if r:
                    return tok, r
    return None


def _event_reason(event, args):
    """(path, reason) if the hook refuses this audit event, else None."""
    if event == 'open':
        path = args[0] if args else None
        if path is None or isinstance(path, int):
            return None
        flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        return _open_reason(path, flags, getattr(_TLS, 'dir_fd', None))
    if event == 'os.rename':
        return _move_reason(*args[:4])
    if event == 'os.link':
        return _link_reason(*args[:4])
    if event == 'os.symlink':
        return _symlink_reason(*args[:3])
    if event in ('os.remove', 'os.rmdir'):
        return _remove_reason(args[0], args[1] if len(args) > 1 else None)
    if event == 'shutil.rmtree':
        return _remove_reason(args[0], args[1] if len(args) > 1 else None, tree=True)
    if event == 'os.mkdir':
        a, rp = _resolve(args[0], args[2] if len(args) > 2 else None, follow=False)
        if rp == CFG['run'] or os.path.lexists(rp):  # os.makedirs(..., exist_ok=True) of an existing folder: no-op
            return None
        return _path_hit(a, rp) or _write_hit(rp)
    if event == 'os.truncate':
        return _truncate_reason(*args[:2])
    if event in ('subprocess.Popen', 'os.exec', 'os.posix_spawn', 'os.spawn'):
        if _guard_frame(_SPAWNERS):                 # the strace auditor launching the command it audits
            return None
        parts = list(args[1:2]) if event != 'os.spawn' else list(args[2:3])
        parts.append(args[0] if event != 'os.spawn' else args[1])
        for p in parts:
            r = _arg_reason(p)
            if r:
                return r
        return None
    if event == 'os.system':
        return _arg_reason(args[0])
    if event == 'urllib.Request':
        r = _url_reason(str(args[0]))
        return (str(args[0]), r) if r else None
    if event == 'http.client.send':
        data = args[1] if len(args) > 1 else b''
        if isinstance(data, (bytes, bytearray)):
            line = bytes(data[:4096]).split(b'\r\n', 1)[0].decode('latin-1', 'replace')
            parts = line.split(' ')
            if len(parts) >= 2 and parts[0].isupper():
                r = _url_reason(parts[1])
                return (parts[1], r) if r else None
        return None
    return None


HOOK_EVENTS = frozenset(('open', 'os.rename', 'os.link', 'os.symlink', 'os.remove', 'os.rmdir', 'shutil.rmtree',
                         'os.mkdir', 'os.truncate', 'subprocess.Popen', 'os.exec', 'os.posix_spawn', 'os.spawn',
                         'os.system', 'urllib.Request', 'http.client.send'))


def _audit(event, args):
    if event not in HOOK_EVENTS or getattr(_TLS, 'busy', False):
        return
    _TLS.busy = True
    try:
        hit = _event_reason(event, args)
    except Exception:                                               # fail open on an internal error, but count it
        hit = None
        _HOOK['errors'] = _HOOK.get('errors', 0) + 1
    finally:
        _TLS.busy = False
    if hit:
        _HOOK['blocked'] += 1
        _record_refusal(hit[0], f'*{event}*', hit[1], via='hook')
        raise GuardError(f'gmg guard: refused {event} of {hit[0]}: {hit[1]}')


_OS_OPEN, _OS_RENAME, _OS_REPLACE = os.open, os.rename, os.replace


def _os_open(path, flags, mode=0o777, *, dir_fd=None):
    """os.open with dir_fd: the audit event carries only the relative path, so the hook is told the directory."""
    if dir_fd is None:
        return _OS_OPEN(path, flags, mode)
    old = getattr(_TLS, 'dir_fd', None)
    _TLS.dir_fd = dir_fd
    try:
        return _OS_OPEN(path, flags, mode, dir_fd=dir_fd)
    finally:
        _TLS.dir_fd = old


def _moved(src, dst, src_dir_fd, dst_dir_fd):
    """After a successful rename inside the run folder: the destination (and every file under a moved directory) is
    this process's output; the source names are gone."""
    run = CFG['run']
    if not run:
        return
    _, srp = _resolve(src, src_dir_fd, follow=False)
    _, drp = _resolve(dst, dst_dir_fd, follow=False)
    if not (_under(drp, run) and drp != run):
        _WRITTEN.pop(srp, None)
        return
    how = _WRITTEN.pop(srp, 'python')
    if os.path.isdir(drp) and not os.path.islink(drp):
        for k in [k for k in _WRITTEN if _under(k, srp)]:
            _WRITTEN.pop(k)
        for d, _, fs in os.walk(drp):
            for f in fs:
                _WRITTEN.setdefault(os.path.join(d, f), how)
    else:
        _WRITTEN[drp] = how


def _os_rename(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
    r = _OS_RENAME(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
    _moved(src, dst, src_dir_fd, dst_dir_fd)
    return r


def _os_replace(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
    r = _OS_REPLACE(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
    _moved(src, dst, src_dir_fd, dst_dir_fd)
    return r


def audit_spawn(argv, env=None):
    """tools/strace_audit.py only: run ARGV (strace and the audited command) without the hook's argument check. The
    command's own file accesses are what the audit checks, so its arguments may name files the hook would refuse (the
    roster parquets). Returns the CompletedProcess."""
    return subprocess.run(list(argv), env=env)


def install_hook():
    """Install the in-process guard (permanent for the interpreter; done at import)."""
    if not _HOOK['installed']:
        sys.addaudithook(_audit)
        os.open, os.rename, os.replace = _os_open, _os_rename, _os_replace
        _HOOK['installed'] = True


def _check_roots():
    for name in ('kit', 'weights'):
        r = _root_problem(name, CFG[name])
        if r:
            raise GuardError(f'gmg guard: refused GMG_{name.upper()}_ROOT: {r}')


_DET_OPENERS = frozenset(f.__code__ for f in (load_npz, _sha_file, _npz_names))
_PROTECTED_WRITERS = frozenset(f.__code__ for f in (set_run, _ledger_append))
_SPAWNERS = frozenset((audit_spawn.__code__,))
_PREFIXES = tuple(sorted({os.path.realpath(p).rstrip('/') + '/' for p in (sys.prefix, sys.exec_prefix)
                          if os.path.realpath(p) not in ('/', '/usr', '/usr/local')}))
sys.modules.setdefault('gmg.guard', sys.modules[__name__])
_check_roots()
install_hook()
if os.environ.get('GMG_RUN'):
    set_run(os.environ['GMG_RUN'])
