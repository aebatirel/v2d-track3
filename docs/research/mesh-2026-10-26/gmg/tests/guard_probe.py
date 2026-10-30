"""Test helper: run a list of guard operations in a fresh interpreter (the guard reads its configuration once at import).

  echo '[["open", PATH, ROLE], ["npz", PATH, ROLE, KEYS], ...]' | GMG_MODE=... python guard_probe.py

Prints one JSON list: for each operation {op, status: ok|refused|missing|error, value|msg}. Used by test_guard.py only.
"""
import json
import os
import sys

MR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, MR)
from gmg import guard  # noqa: E402


def run(op):
    k = op[0]
    if k == 'open':
        return guard.open_input(op[1], op[2], **(op[3] if len(op) > 3 else {}))
    if k == 'check':
        return guard.check(op[1], op[2])
    if k == 'npz':
        return sorted(guard.load_npz(op[1], op[2], op[3] if len(op) > 3 else None))
    if k == 'json':
        return guard.load_json(op[1], op[2])
    if k == 'builtin_open':
        with open(op[1], 'rb') as f:
            return len(f.read(16))
    if k == 'np_load':
        import numpy as np
        z = np.load(op[1])
        return sorted(z.files) if hasattr(z, 'files') else list(z.shape)
    if k == 'os_open':
        fd = os.open(op[1], os.O_RDONLY)
        os.close(fd)
        return fd
    if k == 'dirfd_open':                   # os.open(rel, dir_fd=open(dir)): the hook must resolve the directory
        d = os.open(op[1], os.O_RDONLY | os.O_DIRECTORY)
        try:
            fd = os.open(op[2], os.O_RDONLY, dir_fd=d)
            os.close(fd)
            return True
        finally:
            os.close(d)
    if k == 'copyfile':
        import shutil
        shutil.copyfile(op[1], op[2])
        return True
    if k == 'write':
        os.makedirs(os.path.dirname(op[1]), exist_ok=True)
        with open(op[1], 'w') as f:
            f.write(op[2] if len(op) > 2 else 'x')
        return True
    if k == 'rplus':
        with open(op[1], 'r+b') as f:
            return len(f.read(16))
    if k == 'remove':
        os.remove(op[1])
        return True
    if k == 'open_mode':                    # open(path, mode) and read what the mode allows
        with open(op[1], op[2]) as f:
            if 'r' in op[2] or '+' in op[2]:
                f.seek(0)
                return len(f.read(16))
            return True
    if k == 'a_plus_npz':                   # open 'a+b', seek 0, np.load from the handle (a readable append open)
        import numpy as np
        with open(op[1], 'a+b') as f:
            f.seek(0)
            return sorted(np.load(f).files)
    if k == 'savez':
        import numpy as np
        os.makedirs(os.path.dirname(op[1]), exist_ok=True)
        np.savez(op[1], **{key: np.arange(3) * (i + 1) for i, key in enumerate(op[2] if len(op) > 2 else ['x'])})
        return True
    if k == 'rename':
        os.rename(op[1], op[2])
        return True
    if k == 'replace':
        os.replace(op[1], op[2])
        return True
    if k == 'link':
        os.link(op[1], op[2])
        return True
    if k == 'symlink':
        os.symlink(op[1], op[2])
        return True
    if k == 'mkdir':
        os.mkdir(op[1])
        return True
    if k == 'makedirs':
        os.makedirs(op[1], exist_ok=True)
        return True
    if k == 'rmtree':
        import shutil
        shutil.rmtree(op[1])
        return True
    if k == 'truncate':
        os.truncate(op[1], op[2])
        return True
    if k == 'shutil_move':
        import shutil
        shutil.move(op[1], op[2])
        return True
    if k == 'register_output':
        return guard.register_output(op[1])
    if k == 'outputs':
        return guard._outputs()
    if k == 'subprocess':                   # the hook checks the arguments before the child starts
        import subprocess
        return subprocess.run(op[1], capture_output=True).returncode
    if k == 'os_system':
        return os.system(op[1])
    if k == 'urllib_open':                  # OpenerDirector.open raises the audit event; no proxy, a closed port
        import urllib.request
        try:
            urllib.request.build_opener(urllib.request.ProxyHandler({})).open(op[1], timeout=0.5)
        except guard.GuardError:
            raise
        except OSError as e:
            return f'oserror {type(e).__name__}'
        return True
    if k == 'http_send':                    # an http.client request line to a local listening socket (no network)
        import http.client
        import socket
        srv = socket.socket()
        srv.bind(('127.0.0.1', 0))
        srv.listen(1)
        c = http.client.HTTPConnection('127.0.0.1', srv.getsockname()[1], timeout=0.5)
        try:
            c.request('GET', op[1])
        except guard.GuardError:
            raise
        except OSError as e:
            return f'oserror {type(e).__name__}'
        finally:
            c.close()
            srv.close()
        return True
    if k == 'import_kit':                   # import a kit module by name with the kit root on sys.path
        import importlib
        sys.path.insert(0, guard.CFG['kit'])
        try:
            importlib.import_module(op[1])
        finally:
            sys.path.remove(guard.CFG['kit'])
        return True
    if k == 'tls_det_np_load':              # set the private thread-local det door by hand, then np.load
        import numpy as np
        guard._TLS.det_ok = os.path.realpath(op[1])
        try:
            return sorted(np.load(op[1]).files)
        finally:
            guard._TLS.det_ok = None
    if k == 'internal_np_load':             # the private _internal() context, then np.load
        import numpy as np
        with guard._internal():
            return sorted(np.load(op[1]).files)
    if k == 'tls_protected_write':          # set the private protected flag by hand, then write the marker
        guard._TLS.protected = True
        try:
            with open(op[1], 'w') as f:
                f.write(op[2])
            return True
        finally:
            guard._TLS.protected = False
    if k == 'attr':
        return getattr(guard, op[1])
    if k == 'write_manifest':
        guard.write_manifest(op[1])
        return True
    if k == 'own_tier':
        return guard._own_tier()
    if k == 'runs_root':
        return guard.runs_root(*op[1:])
    if k == 'constant':
        return guard.constant(op[1], op[2], op[3])
    if k == 'constant_set':                 # a value that is not JSON-serialisable
        return guard.constant(op[1], set(op[2]), op[3])
    if k == 'constants':
        return guard.constants()
    if k == 'io_gt':
        from autokit import io_gt
        v = getattr(io_gt, op[1])(*op[2])
        return sorted(v) if isinstance(v, dict) else v
    if k == 'io_gt_attr':
        from autokit import io_gt
        return getattr(io_gt, op[1])
    if k == 'manifest':
        return guard.manifest()
    if k == 'roots_report':
        return guard.io_gt_roots_report()
    if k == 'mode':
        return guard.mode()
    if k == 'set_run':
        return guard.set_run(op[1])
    if k == 'register_fixture_root':
        return guard.register_fixture_root(op[1])
    if k == 'patch_allow':                  # simulate a future allow-list change that would admit a refused folder
        guard.ROLE_PATTERNS[op[1]] = tuple(guard.ROLE_PATTERNS[op[1]]) + (op[2],)
        guard._RX.clear()
        return True
    if k == 'tier':
        return guard.tier()
    if k == 'deny_sizes':
        return dict(globs=len(guard.DENY['globs']), sha256=len(guard.DENY['sha256']), sources=guard.DENY['sources'])
    raise ValueError(f'unknown op {k}')


def main():
    ops = json.load(sys.stdin)
    out = []
    for op in ops:
        try:
            out.append(dict(op=op, status='ok', value=run(op)))
        except guard.GuardError as e:
            out.append(dict(op=op, status='refused', msg=str(e)))
        except FileNotFoundError as e:
            out.append(dict(op=op, status='missing', msg=str(e)))
        except ValueError as e:
            st = 'refused' if str(e).startswith('integrity: refused') else 'error'
            out.append(dict(op=op, status=st, msg=f'ValueError: {e}'))
        except Exception as e:
            out.append(dict(op=op, status='error', msg=f'{type(e).__name__}: {e}'))
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
