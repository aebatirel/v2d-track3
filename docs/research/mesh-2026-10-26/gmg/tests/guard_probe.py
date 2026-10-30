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
