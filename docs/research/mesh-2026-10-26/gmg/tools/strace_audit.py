"""strace audit of a gmg process (SPEC section 2: "an strace audit runs on every production run"; build step B0).

  strace_audit.py run --log LOG [--manifest M.json] [--policy gmg|roster] [--src DIR --out FILE]
                      [--allow GLOB] [--allow-write GLOB] [--allow-net] -- CMD ...
  strace_audit.py analyze LOG [--cwd DIR] [--manifest M.json] [--policy ...] [...]

`run` executes CMD under `strace -f -qq -y -e TRACE` (opens, execs, renames, links, symlinks, clone/fork/vfork,
chdir/fchdir, connect) and analyses the log; the report goes to LOG.audit.json and stdout. The auditor imports
gmg/guard.py for its rules (deny-list, refused folders, allow-lists, det identity, run ledger), so it must be started
with the same environment as the audited run (GMG_MODE, GMG_DATA_ROOT, GMG_RUN, ...). Its own hashing runs in the
guard's internal context; the audited process is the child.

Attribution (round 3): every call is attributed to the program image its pid ran when the call started: the pid's
last successful execve that ended before it, else (a forked child before its own execve) the parent's image at the
clone, else unknown. Relative paths are joined to the -y dirfd annotation or to the pid's working directory (AT_FDCWD
annotations, chdir/fchdir, inherited at fork; the root starts in the auditor's cwd).

Every traced event is classified:
  forbidden   the path (as given, or as resolved by strace -y) has a GT substring (/scan, /loc/, _align, .parquet,
              mocap; only files with a code SUFFIX are exempt, wherever they are), matches a deny-list glob, lies in a
              revision-1 refused folder (in dev mode a path the manifest lists under a dev role is exempt) or is the
              kit scorer; a symlink target that does so; a successfully opened regular file (read or written) with a
              sha256 on the deny-list; a read data file with more than one hard link; a hard link created in the run
              folder; a det file (guard check 8) opened more often than guard.load_npz opened it (manifest
              guarded_opens), written (a copy) or read with keys outside the det filter; (clean mode) a run file read
              that neither the audited command wrote before nor the run ledger lists with its current sha256; a
              manifest output the audited command did not write; a network connection (AF_INET/AF_INET6) unless
              --allow-net;
  unlisted    (policy gmg) a successfully read regular non-code file outside the system set that no gmg role admits in
              the current mode (the allow-list is default-deny), hard-link sources included; (policy roster) any data
              read other than the --src parquets;
  writes_outside_run  a successful open for writing (O_WRONLY, O_RDWR, O_CREAT, O_TRUNC, O_APPEND, creat), a rename
              source or destination, a hard link or a symlink outside the run folder, the --out file and --allow-write
              globs (/dev/null-like devices and __pycache__/*.pyc excepted);
  unrecorded  an admitted data file that was read but is not in the manifest (opened by C code, e.g. a video
              decoder): reported, not counted;
  system      only /proc, /sys, /dev (not /dev/shm), the interpreter and venv (sys.prefix, the sysconfig library
              paths), /usr/lib*, /lib* and execve; a short list of named system files (SYSTEM_FILES: ld.so.cache,
              localtime, locale, git config, the CA bundle the environment names, ...) is exempt from the allow-list
              only. Everything else that is read is checked (substrings, deny glob, refused folder, deny sha256, det
              identity, hard links, run provenance, allow-list).
  git         read-only opens of the repository's .git/ by a pid whose image at that call is git. Every other git open
              gets the full checks; work-tree files git reads are exempt from the allow-list only.
O_RDWR opens get the read checks and the write check. forbidden_opens = forbidden + unlisted + writes_outside_run;
the pass condition is forbidden_opens == 0 and exit code 0.
"""
import argparse
import json
import os
import re
import subprocess
import stat as os_stat
import sys
import sysconfig

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)
CHILD_ENV = dict(os.environ)                     # the audited command gets the environment unchanged
GMG_RUN_ENV = os.environ.pop('GMG_RUN', None)    # the auditor itself never sets (or creates) the run folder
from gmg import guard  # noqa: E402  (rules; the auditor's own hashing runs in guard._internal())

# syscalls traced; '?' = ignore a name this architecture lacks (aarch64 has no open, creat, rename, link, ...)
TRACE = ('trace=?open,openat,?openat2,?creat,execve,?execveat,?rename,renameat,?renameat2,?link,linkat,?symlink,'
         'symlinkat,clone,?clone3,?fork,?vfork,chdir,fchdir,connect')
SPECIAL = ('/proc/', '/sys/', '/dev/')
NOT_SPECIAL = ('/dev/shm/',)
LIB_DIRS = ('/usr/lib/', '/usr/lib32/', '/usr/lib64/', '/usr/libexec/', '/lib/', '/lib32/', '/lib64/')
# named system files a process may read without a gmg role (still checked for substrings, deny glob and sha256)
SYSTEM_FILES = ('/etc/ld.so.cache', '/etc/ld.so.preload', '/etc/localtime', '/etc/nsswitch.conf', '/etc/passwd',
                '/etc/group', '/etc/hosts', '/etc/host.conf', '/etc/resolv.conf', '/etc/gai.conf', '/etc/mime.types',
                '/etc/locale.alias',
                '/etc/ssl/**', '/etc/gitconfig', '/root/.gitconfig', '/root/.config/git/**',
                '/usr/share/locale/**', '/usr/share/zoneinfo/**', '/usr/share/git-core/**')
# the CA bundle the environment names (TLS for HF downloads through the proxy): a system file, content still checked
SYSTEM_FILES += tuple(sorted({os.path.realpath(os.environ[v]) for v in ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE',
                                                                      'CURL_CA_BUNDLE') if os.environ.get(v)}))
LINE = re.compile(r'^(?P<call>\w+)\((?P<args>.*)\)\s+=\s+(?P<ret>-?\d+|\?)(?:<(?P<rpath>[^>]*)>)?'
                  r'(?P<err>\s+E[A-Z0-9]+.*)?\s*$')
# argument tokens: a quoted string, or a file descriptor (AT_FDCWD or a number) with its -y path annotation
TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"(?:\.\.\.)?|\b(AT_FDCWD|\d+)(?:<([^>]*)>)?')
OPEN_CALLS = ('open', 'openat', 'openat2', 'creat')
EXEC_CALLS = ('execve', 'execveat')
MOVE_CALLS = ('rename', 'renameat', 'renameat2')
LINK_CALLS = ('link', 'linkat')
SYMLINK_CALLS = ('symlink', 'symlinkat')
CLONE_CALLS = ('clone', 'clone3', 'fork', 'vfork')
WRITE_KINDS = ('move_src', 'move_dst', 'link_dst', 'symlink_dst')


def _unescape(s):
    try:
        return s.encode('latin-1', 'backslashreplace').decode('unicode_escape').encode('latin-1').decode('utf-8',
                                                                                                      'replace')
    except Exception:
        return s


def parse_calls(log):
    """Pass 1: every traced call of an strace -f -y log, unfinished/resumed lines joined. A call keeps the line where
    it started (idx) and where it ended (end), so events are attributed to the program image a pid ran when the call
    started. Returns (calls, execs {pid: [(end, exe)]}, parent {child: (pid, idx)})."""
    pending, calls, execs, parent = {}, [], {}, {}
    for n, line in enumerate(open(log, errors='replace')):
        line = line.rstrip('\n')
        m = re.match(r'^(\d+)\s+(.*)$', line)
        if not m:
            continue
        pid, rest = int(m.group(1)), m.group(2)
        if rest.endswith('<unfinished ...>'):
            pending[pid] = (rest[:-len('<unfinished ...>')].rstrip(), n)
            continue
        idx = n
        r = re.match(r'^<\.\.\. (\w+) resumed>(.*)$', rest)
        if r:
            head, idx = pending.pop(pid, (r.group(1) + '(', n))
            rest = head + r.group(2)
        c = LINE.match(rest)
        if not c:
            continue
        call, ret = c.group('call'), c.group('ret')
        rv = None if ret == '?' else int(ret)
        ok = rv is not None and rv >= 0
        toks, last_fd = [], None
        for t in TOKEN.finditer(c.group('args')):
            if t.group(1) is not None:
                toks.append((last_fd, _unescape(t.group(1))))
                last_fd = None
            else:
                last_fd = (t.group(2), _unescape(t.group(3)) if t.group(3) is not None else None)
        rec = dict(idx=idx, end=n, pid=pid, call=call, ok=ok, ret=rv, args=c.group('args'), toks=toks,
                   rpath=_unescape(c.group('rpath')) if c.group('rpath') else None)
        calls.append(rec)
        if call in EXEC_CALLS and ok and toks:
            execs.setdefault(pid, []).append((n, toks[0][1]))
        if call in CLONE_CALLS and ok and rv and rv > 0:
            parent[rv] = (pid, idx)
    return calls, execs, parent


def exe_at(pid, idx, execs, parent, depth=0):
    """The program image pid ran at log line idx: its last successful execve that ended before idx, else (a forked
    child before its own execve) its parent's image at the clone, else None (unknown: full checks apply)."""
    best = None
    for end, exe in execs.get(pid, ()):
        if end < idx:
            best = exe
        else:
            break
    if best is not None:
        return best
    if pid in parent and depth < 200:
        pp, pidx = parent[pid]
        return exe_at(pp, pidx, execs, parent, depth + 1)
    return None


def parse(log, cwd0=None):
    """Pass 2: file events [{idx, pid, exe, kind, call, path, rpath, ok, read, write, dir}] and network events.
    Relative paths are joined to their -y dirfd annotation or to the pid's working directory (tracked from AT_FDCWD
    annotations, chdir/fchdir and the parent at fork; the root process starts in cwd0). kind: open, exec, move_src,
    move_dst, link_src, link_dst, symlink_target, symlink_dst, connect."""
    calls, execs, parent = parse_calls(log)
    cwd, out = {}, []

    def where(pid):
        if pid not in cwd:
            pp = parent.get(pid, (None,))[0]
            cwd[pid] = cwd.get(pp, cwd0) if pp is not None else cwd0
        return cwd[pid]

    def res(pid, fd, sx):
        if sx.startswith('/'):
            return os.path.normpath(sx)
        if fd and fd[1] and fd[1].startswith('/'):
            return os.path.normpath(os.path.join(fd[1], sx))
        w = where(pid)
        return os.path.normpath(os.path.join(w, sx)) if w else sx

    for c in calls:
        pid, call, toks = c['pid'], c['call'], c['toks']
        where(pid)
        for fd, _ in toks:
            if fd and fd[0] == 'AT_FDCWD' and fd[1] and fd[1].startswith('/'):
                cwd[pid] = fd[1]
        m = re.match(r'^(?:AT_FDCWD|\d+)<([^>]*)>', c['args'])
        if m and c['args'].startswith('AT_FDCWD') and m.group(1).startswith('/'):
            cwd[pid] = m.group(1)
        exe = exe_at(pid, c['idx'], execs, parent)
        base = dict(idx=c['idx'], pid=pid, exe=exe, call=call, ok=c['ok'], rpath=None, read=False, write=False,
                    dir=False)
        if call == 'chdir' and c['ok'] and toks:
            cwd[pid] = res(pid, None, toks[0][1])
            continue
        if call == 'fchdir' and c['ok']:
            m = re.match(r'^\d+<([^>]*)>', c['args'])
            if m:
                cwd[pid] = m.group(1)
            continue
        if call == 'connect':
            fam = re.search(r'sa_family=(\w+)', c['args'])
            out.append(dict(base, kind='connect', path=None, family=fam.group(1) if fam else '?',
                            addr=re.sub(r'^\S+?,\s*', '', c['args'])[:200]))
            continue
        if not toks:
            continue
        if call in OPEN_CALLS:
            args = c['args']
            write = call == 'creat' or bool(re.search(r'O_WRONLY|O_RDWR|O_CREAT|O_TRUNC|O_APPEND', args))
            read = call != 'creat' and 'O_WRONLY' not in args
            out.append(dict(base, kind='open', path=res(pid, toks[0][0], toks[0][1]), rpath=c['rpath'], read=read,
                            write=write, dir='O_DIRECTORY' in args, trunc=call == 'creat' or 'O_TRUNC' in args))
        elif call in EXEC_CALLS:
            out.append(dict(base, kind='exec', path=res(pid, toks[0][0], toks[0][1])))
        elif call in MOVE_CALLS + LINK_CALLS and len(toks) >= 2:
            k = 'move' if call in MOVE_CALLS else 'link'
            out.append(dict(base, kind=f'{k}_src', path=res(pid, toks[0][0], toks[0][1]),
                            write=k == 'move', read=k == 'link'))
            out.append(dict(base, kind=f'{k}_dst', path=res(pid, toks[1][0], toks[1][1]), write=True))
        elif call in SYMLINK_CALLS and len(toks) >= 2:
            dst = res(pid, toks[1][0], toks[1][1])
            t = toks[0][1]
            out.append(dict(base, kind='symlink_target', path=os.path.normpath(
                t if t.startswith('/') else os.path.join(os.path.dirname(dst), t))))
            out.append(dict(base, kind='symlink_dst', path=dst, write=True))
    return out


def _interp_dirs():
    """The interpreter and venv folders (system): sys.prefix / base_prefix unless they are /, /usr or /usr/local (then
    only their sysconfig library paths), and the sysconfig library paths."""
    s = set()
    for p in (sys.prefix, sys.base_prefix, sys.exec_prefix):
        if p and os.path.realpath(p) not in ('/', '/usr', '/usr/local'):
            s.add(os.path.realpath(p))
    for scheme_vars in ({}, {'base': sys.base_prefix, 'platbase': sys.base_prefix}):
        paths = sysconfig.get_paths(vars=scheme_vars) if scheme_vars else sysconfig.get_paths()
        for k in ('stdlib', 'platstdlib', 'purelib', 'platlib'):
            if paths.get(k):
                s.add(os.path.realpath(paths[k]))
    return tuple(sorted(x.rstrip('/') + '/' for x in s))


INTERP = _interp_dirs()


def _special(p):
    return p.startswith(SPECIAL) and not p.startswith(NOT_SPECIAL)


def _interp(p):
    return p.startswith(INTERP) or p.startswith(LIB_DIRS)


def _guard_config():
    s = {os.path.realpath(guard.DENYLIST_REPO), os.path.realpath(guard.DET_REGISTRY),
         os.path.realpath(guard.FROZEN_EVAL_TRACKS)}
    for src in guard.DENY['sources']:
        s.add(os.path.realpath(src['path']))
    return s


def _admitted_by_any_role(p):
    roles = guard.CLEAN_ROLES + (guard.DEV_ROLES if guard.mode() == 'dev' else ())
    for role in roles:
        try:
            guard.check(p, role)
            return role
        except guard.GuardError:
            continue
    return None


def _globs_match(p, globs):
    return any(guard._glob_re(g).match(p) for g in globs)


def _content(p):
    """(deny-list entry, det identity) of a regular file, hashed in the guard's internal context."""
    with guard._internal():
        try:
            d = guard.DENY['sha256'].get(guard._sha256(p))
        except OSError:
            d = None
        try:
            det = guard._det_identity(p, p)
        except OSError:
            det = None
    return d, det


def _is_git(exe):
    return bool(exe) and (os.path.basename(exe).startswith('git') or '/git-core/' in exe)


def _nlink(p):
    try:
        st = os.stat(p)
    except OSError:
        return 0
    return st.st_nlink if os_stat.S_ISREG(st.st_mode) else 0


def analyze(log, manifest=None, policy='gmg', src=None, out=None, allow=(), allow_write=(), cwd0=None,
            allow_net=False):
    man = json.load(open(manifest)) if manifest else {}
    man_inputs = {i['realpath']: i for i in man.get('inputs', [])}
    guarded = {k: int(v) for k, v in (man.get('guarded_opens') or {}).items()}
    run = (man.get('roots') or {}).get('run') or (os.path.realpath(GMG_RUN_ENV) if GMG_RUN_ENV else None)
    gcfg = _guard_config()
    git_dir = os.path.join(guard.CFG['repo'], '.git') + '/'
    repo = guard.CFG['repo'] + '/'
    ev = parse(log, cwd0)
    rep = dict(log=os.path.abspath(log), policy=policy, mode=guard.mode(), manifest=manifest, events=len(ev),
               opens_ok=sum(e['ok'] for e in ev if e['kind'] == 'open'), forbidden=[], unlisted=[], unrecorded=[],
               writes_outside_run=[], network=[], local_sockets=0, system=0, system_files=0, code_outside_interp=0,
               git=0, git_tree_reads=0, data_reads=[], det_reads={}, written=[], moves=0, links=0, symlinks=0,
               interp_dirs=list(INTERP), cwd0=cwd0)
    data_reads, det_reads, written, content = set(), {}, set(), {}
    src_r = os.path.realpath(src) if src else None
    out_r = os.path.realpath(out) if out else None
    log_r = os.path.realpath(log)
    ledger = guard._ledger(run) if (run and guard.mode() == 'clean') else {}

    def _c(p):
        if p not in content:
            content[p] = _content(p)
        return content[p]

    def in_run(p):
        return bool(run) and p.startswith(run + '/')

    def _read_checks(e, item, p, given, code, git, exempt_roster):
        """Checks of a successful read (open for reading, link source) of a regular file."""
        if not e['read'] or not p.startswith('/') or not os.path.isfile(p):
            return
        if _interp(p):                                   # interpreter, venv, /usr/lib*, /lib*: system
            if not code:
                d, det = _c(p)
                if d:
                    rep['forbidden'].append(dict(item, reason=f'sha256 on the deny-list ({d})'))
                elif det:
                    det_reads[p] = det_reads.get(p, 0) + 1
                    return
            rep['system'] += 1
            return
        d, det = _c(p)
        if d:
            rep['forbidden'].append(dict(item, reason=f'sha256 on the deny-list ({d})'))
            return
        if det:
            det_reads[p] = det_reads.get(p, 0) + 1
        if code:
            rep['code_outside_interp'] += 1
            return
        if p in gcfg:
            rep['system'] += 1
            return
        if _globs_match(p, SYSTEM_FILES) or (given and _globs_match(given, SYSTEM_FILES)):
            rep['system_files'] += 1
            return
        if _nlink(p) > 1:
            rep['forbidden'].append(dict(item, reason=f'regular file with {_nlink(p)} hard links'))
            return
        if allow and _globs_match(p, allow):
            return
        data_reads.add(p)
        if policy == 'roster':
            if not exempt_roster:
                rep['unlisted'].append(dict(item, reason='roster policy: only the --src parquets may be read'))
            return
        if in_run(p) and guard.mode() == 'clean' and os.path.basename(p) not in guard.PROTECTED \
                and p not in written:
            rel = os.path.relpath(p, run)
            shas = ledger.get(rel)
            if not shas or _c_sha(p) not in shas:
                rep['forbidden'].append(dict(item, reason=f'run provenance: {rel} was read but neither written by '
                                                          f'the audited command before nor listed in the ledger'))
                return
        if git and p.startswith(repo):
            rep['git_tree_reads'] += 1                   # git reading the work tree: content checks above, no role
            return
        role = _admitted_by_any_role(p)
        if role is None and not in_run(p):
            rep['unlisted'].append(dict(item, reason='no gmg role admits this file (allow-list is default-deny)'))
        elif manifest and p not in man_inputs and not in_run(p):
            rep['unrecorded'].append(dict(item, role=role))

    for e in ev:
        kind = e['kind']
        item = dict(pid=e['pid'], exe=e['exe'], call=e['call'], kind=kind, path=e['path'], rpath=e['rpath'],
                    ok=e['ok'], read=e['read'], write=e['write'])
        if kind == 'connect':
            fam = e['family']
            if fam in ('AF_INET', 'AF_INET6'):
                rep['network'].append(dict(item, family=fam, addr=e['addr']))
            else:
                rep['local_sockets'] += 1
            continue
        given = e['path'] if e['path'].startswith('/') else None
        p = e['rpath'] if (kind == 'open' and e['ok'] and e['rpath'] and e['rpath'].startswith('/')) else e['path']
        code = guard._is_code(p)
        git = _is_git(e['exe'])                              # the image this pid ran when the call started
        reason = None
        exempt_roster = policy == 'roster' and src_r and p.startswith(src_r + '/') and p.endswith('.parquet')
        for q in dict.fromkeys(x for x in (given, p) if x):
            if exempt_roster or not q.startswith('/'):
                continue
            r = guard._path_reason(q, '*audit*', code=guard._is_code(q) and code, rp=p)
            if r and r.startswith('refused folder') and guard.mode() == 'dev':
                rec = man_inputs.get(p)
                if rec and rec['role'] in guard.DEV_ROLES:
                    r = None
            if not r and guard._match(q, guard.KIT_SCORER_HOOK):
                r = 'the kit scorer'
            if r:
                reason = r
                break
        if reason:
            rep['forbidden'].append(dict(item, reason=reason))
            continue
        if kind == 'exec' or (p.startswith('/') and _special(p)):
            rep['system'] += 1
            continue
        if kind == 'symlink_target':
            continue
        if git and p.startswith(git_dir) and not e['write']:
            rep['git'] += 1                                  # git reading its own repository data (.git/)
            continue
        if not e['ok'] or e['dir']:
            continue
        rep['moves'] += kind == 'move_dst'
        rep['links'] += kind == 'link_dst'
        rep['symlinks'] += kind == 'symlink_dst'
        if e['write']:
            ok_w = p.startswith('/') and ((in_run(p)) or p in (out_r, log_r) or
                                          (code and '/__pycache__/' in p and p.endswith('.pyc')) or
                                          _globs_match(p, allow_write))
            if not ok_w:
                why = dict(move_src='rename source outside the run folder (a file moved away from outside it)',
                           move_dst='rename destination outside the run folder',
                           link_dst='hard link created outside the run folder',
                           symlink_dst='symlink created outside the run folder').get(kind, 'write outside the run folder')
                rep['writes_outside_run'].append(dict(item, reason=why))
            if kind == 'link_dst' and in_run(p):
                rep['forbidden'].append(dict(item, reason='hard link created in the run folder (files with more than '
                                                          'one link are never inputs)'))
            if kind == 'move_dst' or (kind == 'open' and (e.get('trunc') or not e['read'])):
                written.add(p)                           # new content (a read-write open joins after its read checks)
        try:
            _read_checks(e, item, p, given, code, git, exempt_roster)
        finally:
            if kind == 'open' and e['write']:
                written.add(p)
    # det files: every open must be one guard.load_npz made (manifest guarded_opens); the keys read must be mask keys
    for p, n in sorted(det_reads.items()):
        g = guarded.get(p, 0)
        if n > g:
            rep['forbidden'].append(dict(path=p, ok=True, read=True, write=False, call='open*', pid=None,
                                         reason=f'det file ({_c(p)[1]}) opened {n} times, {g} by guard.load_npz'))
    for p, rec in man_inputs.items():
        if rec.get('det_identity') or rec.get('role') == 'det':
            bad = [k for k in rec.get('keys', []) if not guard._key_ok(k, guard.NPZ_KEYS['det'])]
            if bad:
                rep['forbidden'].append(dict(path=p, call='manifest', pid=None, ok=True, read=True, write=False,
                                             reason=f'det file read with keys {bad}'))
    # every output the manifest declares was written by the audited command (open for writing or rename into place)
    for o in man.get('outputs', []) if run else []:
        p = os.path.join(run, o['path'])
        if p not in written:
            rep['forbidden'].append(dict(path=p, call='manifest', pid=None, ok=True, read=False, write=True,
                                         reason=f'manifest output ({o.get("how")}) not written by the audited command'))
    # files written: no det copy and no deny-listed content may be left behind
    for p in sorted(written):
        if os.path.isfile(p) and not guard._is_code(p):
            content.pop(p, None)
            d, det = _c(p)
            if d or det:
                rep['forbidden'].append(dict(path=p, call='write', pid=None, ok=True, read=False, write=True,
                                             reason=f'written file is a det file ({det})' if det else
                                             f'written file has a deny-listed sha256 ({d})'))
    if not allow_net:
        for x in rep['network']:
            rep['forbidden'].append(dict(x, reason=f'network connection ({x["family"]}) without --allow-net'))
    rep['data_reads'] = sorted(data_reads)
    rep['det_reads'] = det_reads
    rep['written'] = sorted(written)
    rep['allow_net'] = bool(allow_net)
    rep['forbidden_opens'] = len(rep['forbidden']) + len(rep['unlisted']) + len(rep['writes_outside_run'])
    rep['forbidden_attempted_failed'] = sum(1 for f in rep['forbidden'] if not f['ok'])
    return rep


def _c_sha(p):
    with guard._internal():
        try:
            return guard._sha256(p)
        except OSError:
            return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('run', 'analyze'):
        p = sub.add_parser(name)
        if name == 'analyze':
            p.add_argument('log')
            p.add_argument('--cwd', default=None, help='working directory the audited command started in')
        else:
            p.add_argument('--log', required=True)
        p.add_argument('--manifest', default=None)
        p.add_argument('--policy', default='gmg', choices=('gmg', 'roster'))
        p.add_argument('--src', default=None, help='roster policy: folder of the public parquets')
        p.add_argument('--out', default=None, help='roster policy: the one output file')
        p.add_argument('--allow', action='append', default=[],
                       help='extra glob of files the command may read (still checked for GT paths, deny sha, det)')
        p.add_argument('--allow-write', action='append', default=[], help='extra glob the command may write')
        p.add_argument('--allow-net', action='store_true',
                       help='report network connections (AF_INET/AF_INET6) instead of counting them as forbidden')
        if name == 'run':
            p.add_argument('command', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    kw = dict(allow=a.allow, allow_write=a.allow_write, allow_net=a.allow_net)
    if a.cmd == 'run':
        cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
        os.makedirs(os.path.dirname(os.path.abspath(a.log)), exist_ok=True)
        cwd0 = os.getcwd()
        r = subprocess.run(['strace', '-f', '-qq', '-y', '-e', TRACE, '-o', a.log, *cmd], env=CHILD_ENV)
        rep = analyze(a.log, a.manifest, a.policy, a.src, a.out, cwd0=cwd0, **kw)
        rep['command'] = cmd
        rep['returncode'] = r.returncode
    else:
        rep = analyze(a.log, a.manifest, a.policy, a.src, a.out, cwd0=a.cwd, **kw)
    json.dump(rep, open(a.log + '.audit.json', 'w'), indent=1)
    short = {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in rep.items()}
    print(json.dumps(short))
    for k in ('forbidden', 'unlisted', 'writes_outside_run'):
        for x in rep[k][:20]:
            print(k.upper(), json.dumps(x))
    sys.exit(0 if rep['forbidden_opens'] == 0 and rep.get('returncode', 0) == 0 else 1)


if __name__ == '__main__':
    main()
