"""strace audit of a gmg process (SPEC section 2: "an strace audit runs on every production run"; build step B0).

  strace_audit.py run --log LOG [--manifest M.json] [--policy gmg|roster] [--src DIR --out FILE]
                      [--allow GLOB] [--allow-write GLOB] -- CMD ...
  strace_audit.py analyze LOG [--manifest M.json] [--policy ...] [...]

`run` executes CMD under `strace -f -qq -y -e trace=open,openat,openat2,creat,execve,execveat` and analyses the log;
the report goes to LOG.audit.json and stdout. The auditor imports gmg/guard.py for its rules (deny-list, refused
folders, allow-lists, det identity), so it must be started with the same environment as the audited run (GMG_MODE,
GMG_DATA_ROOT, GMG_RUN, ...). Its own hashing runs in the guard's internal context; the audited process is the child.

Every traced open (successful or not) is classified (round 2 rules, after verification round 1):
  forbidden   the path (as given, or as resolved by strace -y; relative openat paths joined to their dirfd) has a GT
              substring (/scan, /loc/, _align, .parquet, mocap; only files with a code SUFFIX are exempt, wherever they
              are), matches a deny-list glob, or lies in a revision-1 refused folder (in dev mode a path the manifest
              lists under a dev role is exempt); or a successfully opened regular file (read or written) has a sha256
              on the deny-list; or a det file (guard check 8: name, store folder, sha256 registry, signature keys) was
              opened more often than guard.load_npz opened it (manifest guarded_opens), was written (a copy), or was
              read with keys outside the det filter;
  unlisted    (policy gmg) a successfully read regular non-code file outside the system set that no gmg role admits in
              the current mode (the allow-list is default-deny); (policy roster) any data read other than the --src
              parquets;
  writes_outside_run  a successful open for writing (O_WRONLY, O_RDWR, O_CREAT, O_TRUNC, O_APPEND, creat) outside the
              run folder, the --out file and --allow-write globs (/dev/null-like devices and __pycache__/*.pyc
              excepted);
  unrecorded  an admitted data file that was read but is not in the manifest (opened by C code, e.g. a video
              decoder): reported, not counted;
  system      only /proc, /sys, /dev (not /dev/shm), the interpreter and venv (sys.prefix, the sysconfig library
              paths), /usr/lib*, /lib* and execve; a short list of named system files (SYSTEM_FILES: ld.so.cache,
              localtime, locale, git config, ...) is exempt from the allow-list only. Everything else that is read is
              checked (substrings, deny glob, refused folder, deny sha256, det identity, allow-list).
  git         opens by a git child process (the manifest's commit lookup): path rules only.
O_RDWR opens get the read checks and the write check. forbidden_opens = forbidden + unlisted + writes_outside_run;
the pass condition is forbidden_opens == 0 and exit code 0.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import sysconfig

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)
CHILD_ENV = dict(os.environ)                     # the audited command gets the environment unchanged
GMG_RUN_ENV = os.environ.pop('GMG_RUN', None)    # the auditor itself never sets (or creates) the run folder
from gmg import guard  # noqa: E402  (rules; the auditor's own hashing runs in guard._internal())

TRACE = 'trace=open,openat,openat2,creat,execve,execveat'
SPECIAL = ('/proc/', '/sys/', '/dev/')
NOT_SPECIAL = ('/dev/shm/',)
LIB_DIRS = ('/usr/lib/', '/usr/lib32/', '/usr/lib64/', '/usr/libexec/', '/lib/', '/lib32/', '/lib64/')
# named system files a process may read without a gmg role (still checked for substrings, deny glob and sha256)
SYSTEM_FILES = ('/etc/ld.so.cache', '/etc/ld.so.preload', '/etc/localtime', '/etc/nsswitch.conf', '/etc/passwd',
                '/etc/group', '/etc/hosts', '/etc/host.conf', '/etc/resolv.conf', '/etc/gai.conf', '/etc/mime.types',
                '/etc/locale.alias',
                '/etc/ssl/**', '/etc/gitconfig', '/root/.gitconfig', '/root/.config/git/**',
                '/usr/share/locale/**', '/usr/share/zoneinfo/**', '/usr/share/git-core/**')
CALL = re.compile(r'^(?P<call>open|openat|openat2|creat|execve|execveat)\((?P<args>.*)\)\s+=\s+(?P<ret>-?\d+|\?)'
                  r'(?:<(?P<rpath>[^>]*)>)?(?P<err>\s+E[A-Z0-9]+.*)?\s*$')
QSTR = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _unescape(s):
    try:
        return s.encode('latin-1', 'backslashreplace').decode('unicode_escape').encode('latin-1').decode('utf-8',
                                                                                                      'replace')
    except Exception:
        return s


def parse(log):
    """[{pid, call, path, rpath, ok, read, write, dir}] from an strace -f -y log (unfinished/resumed lines joined)."""
    pending, out = {}, []
    for line in open(log, errors='replace'):
        line = line.rstrip('\n')
        m = re.match(r'^(\d+)\s+(.*)$', line)
        if not m:
            continue
        pid, rest = int(m.group(1)), m.group(2)
        if rest.endswith('<unfinished ...>'):
            pending[pid] = rest[:-len('<unfinished ...>')].rstrip()
            continue
        r = re.match(r'^<\.\.\. (\w+) resumed>(.*)$', rest)
        if r:
            rest = pending.pop(pid, r.group(1) + '(') + r.group(2)
        c = CALL.match(rest)
        if not c:
            continue
        args = c.group('args')
        q = QSTR.search(args)
        if not q:
            continue
        path = _unescape(q.group(1))
        call, ret = c.group('call'), c.group('ret')
        ok = ret != '?' and not ret.startswith('-')
        if call in ('openat', 'openat2') and not path.startswith('/'):
            d = re.match(r'^(?:\d+|AT_FDCWD)<([^>]*)>,', args)        # -y annotates the dirfd (and the cwd)
            if d:
                path = os.path.join(_unescape(d.group(1)), path)
        exe = call.startswith('execve')
        write = call == 'creat' or bool(re.search(r'O_WRONLY|O_RDWR|O_CREAT|O_TRUNC|O_APPEND', args))
        read = not exe and call != 'creat' and 'O_WRONLY' not in args
        out.append(dict(pid=pid, call=call, path=path, rpath=_unescape(c.group('rpath')) if c.group('rpath') else None,
                        ok=ok, read=read, write=write and not exe, dir='O_DIRECTORY' in args))
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


def analyze(log, manifest=None, policy='gmg', src=None, out=None, allow=(), allow_write=()):
    man = json.load(open(manifest)) if manifest else {}
    man_inputs = {i['realpath']: i for i in man.get('inputs', [])}
    guarded = {k: int(v) for k, v in (man.get('guarded_opens') or {}).items()}
    run = (man.get('roots') or {}).get('run') or (os.path.realpath(GMG_RUN_ENV) if GMG_RUN_ENV else None)
    gcfg = _guard_config()
    ev = parse(log)
    exe = {}
    for e in ev:
        if e['call'].startswith('execve') and e['ok']:
            exe[e['pid']] = e['path']
    rep = dict(log=os.path.abspath(log), policy=policy, mode=guard.mode(), manifest=manifest, events=len(ev),
               opens_ok=sum(e['ok'] for e in ev), forbidden=[], unlisted=[], unrecorded=[], writes_outside_run=[],
               system=0, system_files=0, code_outside_interp=0, git=0, data_reads=[], det_reads={}, written=[],
               interp_dirs=list(INTERP))
    data_reads, det_reads, written, content = set(), {}, set(), {}
    src_r = os.path.realpath(src) if src else None
    out_r = os.path.realpath(out) if out else None
    log_r = os.path.realpath(log)

    def _c(p):
        if p not in content:
            content[p] = _content(p)
        return content[p]

    for e in ev:
        given = e['path'] if e['path'].startswith('/') else None
        p = e['rpath'] if (e['ok'] and e['rpath'] and e['rpath'].startswith('/')) else (given or e['path'])
        is_git = os.path.basename(exe.get(e['pid'], '')).startswith('git') or '/git-core/' in exe.get(e['pid'], '')
        code = guard._is_code(p)
        reason = None
        exempt_roster = policy == 'roster' and src_r and p.startswith(src_r + '/') and p.endswith('.parquet')
        for q in dict.fromkeys(x for x in (given, p) if x):
            if exempt_roster:
                break
            r = guard._path_reason(q, '*audit*', code=guard._is_code(q) and code, rp=p)
            if r and r.startswith('refused folder') and guard.mode() == 'dev':
                rec = man_inputs.get(p)
                if rec and rec['role'] in guard.DEV_ROLES:
                    r = None
            if r:
                reason = r
                break
        item = dict(pid=e['pid'], call=e['call'], path=e['path'], rpath=e['rpath'], ok=e['ok'], read=e['read'],
                    write=e['write'])
        if reason:
            rep['forbidden'].append(dict(item, reason=reason))
            continue
        if e['call'].startswith('execve') or _special(p):
            rep['system'] += 1
            continue
        if is_git:
            rep['git'] += 1
            continue
        if not e['ok'] or e['dir']:
            continue
        if e['write']:
            ok_w = (run and p.startswith(run + '/')) or p in (out_r, log_r) or \
                (code and '/__pycache__/' in p and p.endswith('.pyc')) or _globs_match(p, allow_write)
            if not ok_w:
                rep['writes_outside_run'].append(dict(item, reason='write outside the run folder'))
            written.add(p)
        if not e['read'] or not os.path.isfile(p):
            continue
        if _interp(p):                                   # interpreter, venv, /usr/lib*, /lib*: system
            if not code:
                d, det = _c(p)
                if d:
                    rep['forbidden'].append(dict(item, reason=f'sha256 on the deny-list ({d})'))
                elif det:
                    det_reads[p] = det_reads.get(p, 0) + 1
                    continue
            rep['system'] += 1
            continue
        d, det = _c(p)
        if d:
            rep['forbidden'].append(dict(item, reason=f'sha256 on the deny-list ({d})'))
            continue
        if det:
            det_reads[p] = det_reads.get(p, 0) + 1
        if code:
            rep['code_outside_interp'] += 1
            continue
        if p in gcfg:
            rep['system'] += 1
            continue
        if _globs_match(p, SYSTEM_FILES) or (given and _globs_match(given, SYSTEM_FILES)):
            rep['system_files'] += 1
            continue
        if allow and _globs_match(p, allow):
            continue
        data_reads.add(p)
        if policy == 'roster':
            if not exempt_roster:
                rep['unlisted'].append(dict(item, reason='roster policy: only the --src parquets may be read'))
            continue
        role = _admitted_by_any_role(p)
        if role is None and not (run and p.startswith(run + '/')):
            rep['unlisted'].append(dict(item, reason='no gmg role admits this file (allow-list is default-deny)'))
        elif manifest and p not in man_inputs and not (run and p.startswith(run + '/')):
            rep['unrecorded'].append(dict(item, role=role))
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
    # files written: no det copy and no deny-listed content may be left behind
    for p in sorted(written):
        if os.path.isfile(p) and not guard._is_code(p):
            content.pop(p, None)
            d, det = _c(p)
            if d or det:
                rep['forbidden'].append(dict(path=p, call='write', pid=None, ok=True, read=False, write=True,
                                             reason=f'written file is a det file ({det})' if det else
                                             f'written file has a deny-listed sha256 ({d})'))
    rep['data_reads'] = sorted(data_reads)
    rep['det_reads'] = det_reads
    rep['written'] = sorted(written)
    rep['forbidden_opens'] = len(rep['forbidden']) + len(rep['unlisted']) + len(rep['writes_outside_run'])
    rep['forbidden_attempted_failed'] = sum(1 for f in rep['forbidden'] if not f['ok'])
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('run', 'analyze'):
        p = sub.add_parser(name)
        if name == 'analyze':
            p.add_argument('log')
        else:
            p.add_argument('--log', required=True)
        p.add_argument('--manifest', default=None)
        p.add_argument('--policy', default='gmg', choices=('gmg', 'roster'))
        p.add_argument('--src', default=None, help='roster policy: folder of the public parquets')
        p.add_argument('--out', default=None, help='roster policy: the one output file')
        p.add_argument('--allow', action='append', default=[],
                       help='extra glob of files the command may read (still checked for GT paths, deny sha, det)')
        p.add_argument('--allow-write', action='append', default=[], help='extra glob the command may write')
        if name == 'run':
            p.add_argument('command', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    if a.cmd == 'run':
        cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
        os.makedirs(os.path.dirname(os.path.abspath(a.log)), exist_ok=True)
        r = subprocess.run(['strace', '-f', '-qq', '-y', '-e', TRACE, '-o', a.log, *cmd], env=CHILD_ENV)
        rep = analyze(a.log, a.manifest, a.policy, a.src, a.out, a.allow, a.allow_write)
        rep['command'] = cmd
        rep['returncode'] = r.returncode
    else:
        rep = analyze(a.log, a.manifest, a.policy, a.src, a.out, a.allow, a.allow_write)
    json.dump(rep, open(a.log + '.audit.json', 'w'), indent=1)
    short = {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in rep.items()}
    print(json.dumps(short))
    for k in ('forbidden', 'unlisted', 'writes_outside_run'):
        for x in rep[k][:20]:
            print(k.upper(), json.dumps(x))
    sys.exit(0 if rep['forbidden_opens'] == 0 and rep.get('returncode', 0) == 0 else 1)


if __name__ == '__main__':
    main()
