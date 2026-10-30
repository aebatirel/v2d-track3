"""strace audit of a gmg process (SPEC section 2: "an strace audit runs on every production run"; build step B0).

  strace_audit.py run --log LOG [--manifest M.json] [--policy gmg|roster] [--src DIR --out FILE] -- CMD ...
  strace_audit.py analyze LOG [--manifest M.json] [--policy ...]

`run` executes CMD under `strace -f -qq -y -e trace=open,openat,openat2,creat,execve,execveat` and analyses the log;
the report goes to LOG.audit.json and stdout. The process must be started with the same environment as the audited
run (GMG_MODE, GMG_DATA_ROOT, GMG_RUN, ...), because the rules are taken from gmg/guard.py in this process.

Every traced open (successful or not) is classified:
  forbidden   the path (as given, or as resolved by strace -y) has a GT substring (/scan, /loc/, _align, .parquet,
              mocap; code files exempt), matches a deny-list glob, or lies in a revision-1 refused folder (in dev mode
              a path the manifest lists under a dev role is exempt); or a successfully read file's sha256 is on the
              deny-list;
  unlisted    (policy gmg) a successfully read regular data file that no gmg role admits in the current mode (the
              allow-list is default-deny); (policy roster) any data read other than the --src parquets;
  unrecorded  an admitted data file that was read but is not in the manifest (opened by C code, e.g. a video
              decoder): reported, not counted;
  system      code, libraries, /proc, /sys, /dev, /etc, the venv, the repo's .git, the guard's own deny-list files;
  git         opens by a git child process (the manifest's commit lookup): checked for forbidden paths only.
forbidden_opens = len(forbidden) + len(unlisted). The pass condition of B0 is forbidden_opens == 0.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402  (rules; the auditor's own hook refuses nothing it needs)

TRACE = 'trace=open,openat,openat2,creat,execve,execveat'
SYSTEM_PREFIXES = ('/usr/', '/lib/', '/lib64/', '/bin/', '/sbin/', '/etc/', '/proc/', '/sys/', '/dev/', '/run/',
                   '/var/lib/', '/var/cache/', '/opt/', '/root/.cache/', '/root/.config/', '/root/.local/',
                   '/root/.gitconfig', '/root/.ccr/', '/snap/')
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
    """[{pid, call, path, rpath, ok, write, dir}] from an strace -f -y log (unfinished/resumed lines joined)."""
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
                path = os.path.join(d.group(1), path)
        out.append(dict(pid=pid, call=call, path=path, rpath=_unescape(c.group('rpath')) if c.group('rpath') else None,
                        ok=ok, write=call == 'creat' or bool(re.search(r'O_WRONLY|O_RDWR|O_CREAT', args)),
                        dir='O_DIRECTORY' in args))
    return out


def _is_system(p):
    if p.startswith(SYSTEM_PREFIXES) or guard._is_code(p):
        return True
    if p.startswith(os.path.join(guard.CFG['repo'], '.git') + '/') or p == os.path.join(guard.CFG['repo'], '.git'):
        return True
    return any(p.startswith(x.rstrip('/') + '/') for x in {sys.prefix, sys.base_prefix} if x)


def _guard_config():
    s = {os.path.realpath(guard.DENYLIST_REPO)}
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


def analyze(log, manifest=None, policy='gmg', src=None, out=None, allow=()):
    man = json.load(open(manifest)) if manifest else {}
    man_inputs = {i['realpath']: i for i in man.get('inputs', [])}
    run = (man.get('roots') or {}).get('run') or guard.CFG['run']
    gcfg = _guard_config()
    ev = parse(log)
    exe = {}
    for e in ev:
        if e['call'].startswith('execve') and e['ok']:
            exe[e['pid']] = e['path']
    rep = dict(log=os.path.abspath(log), policy=policy, mode=guard.mode(), manifest=manifest, events=len(ev),
               opens_ok=sum(e['ok'] for e in ev), forbidden=[], unlisted=[], unrecorded=[], writes_outside_run=[],
               system=0, git=0, data_reads=[])
    data_reads = set()
    src_r = os.path.realpath(src) if src else None
    out_r = os.path.realpath(out) if out else None
    for e in ev:
        given = e['path'] if e['path'].startswith('/') else None
        p = e['rpath'] if (e['ok'] and e['rpath'] and e['rpath'].startswith('/')) else (given or e['path'])
        is_git = os.path.basename(exe.get(e['pid'], '')).startswith('git') or '/git-core/' in exe.get(e['pid'], '')
        code = _is_system(p) or guard._is_code(p)
        reason = None
        exempt_roster = policy == 'roster' and src_r and p.startswith(src_r + '/') and p.endswith('.parquet')
        for q in dict.fromkeys(x for x in (given, p) if x):
            if exempt_roster:
                break
            r = guard._path_reason(q, '*audit*', code=code, rp=p)
            if r and r.startswith('refused folder') and guard.mode() == 'dev':
                rec = man_inputs.get(p)
                if rec and rec['role'] in guard.DEV_ROLES:
                    r = None
            if r:
                reason = r
                break
        item = dict(pid=e['pid'], call=e['call'], path=e['path'], rpath=e['rpath'], ok=e['ok'], write=e['write'])
        if reason:
            rep['forbidden'].append(dict(item, reason=reason))
            continue
        if e['call'].startswith('execve'):
            rep['system'] += 1
            continue
        if is_git:
            rep['git'] += 1
            continue
        if code or p in gcfg:
            rep['system'] += 1
            continue
        if not e['ok']:
            continue
        if e['write']:
            if not (run and p.startswith(run + '/')) and p != out_r and p != os.path.realpath(log):
                rep['writes_outside_run'].append(item)
            continue
        if e['dir'] or not os.path.isfile(p):
            continue
        if any(guard._glob_re(a).match(p) for a in allow):
            continue
        data_reads.add(p)
        try:
            d = guard.DENY['sha256'].get(guard._sha256(p))
        except OSError:
            d = None
        if d:
            rep['forbidden'].append(dict(item, reason=f'sha256 on the deny-list ({d})'))
            continue
        if policy == 'roster':
            if not exempt_roster:
                rep['unlisted'].append(dict(item, reason='roster policy: only the --src parquets may be read'))
            continue
        role = _admitted_by_any_role(p)
        if role is None and not (run and p.startswith(run + '/')):
            rep['unlisted'].append(dict(item, reason='no gmg role admits this file (allow-list is default-deny)'))
        elif manifest and p not in man_inputs and not (run and p.startswith(run + '/')):
            rep['unrecorded'].append(dict(item, role=role))
    rep['data_reads'] = sorted(data_reads)
    rep['forbidden_opens'] = len(rep['forbidden']) + len(rep['unlisted'])
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
        p.add_argument('--allow', action='append', default=[], help='extra glob of files the command may read')
        if name == 'run':
            p.add_argument('command', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    if a.cmd == 'run':
        cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
        os.makedirs(os.path.dirname(os.path.abspath(a.log)), exist_ok=True)
        r = subprocess.run(['strace', '-f', '-qq', '-y', '-e', TRACE, '-o', a.log, *cmd])
        rep = analyze(a.log, a.manifest, a.policy, a.src, a.out, a.allow)
        rep['command'] = cmd
        rep['returncode'] = r.returncode
        log = a.log
    else:
        rep = analyze(a.log, a.manifest, a.policy, a.src, a.out, a.allow)
        log = a.log
    json.dump(rep, open(log + '.audit.json', 'w'), indent=1)
    short = {k: (len(v) if isinstance(v, list) else v) for k, v in rep.items()}
    print(json.dumps(short))
    for k in ('forbidden', 'unlisted'):
        for x in rep[k][:20]:
            print(k.upper(), json.dumps(x))
    sys.exit(0 if rep['forbidden_opens'] == 0 and rep.get('returncode', 0) == 0 else 1)


if __name__ == '__main__':
    main()
