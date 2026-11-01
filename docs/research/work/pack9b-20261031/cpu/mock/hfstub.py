"""hf CLI stub for the masses eval-retrain mock: the fake store is MR/store (a folder tree like the HF dataset).
  hf download STORE --repo-type dataset --include PATTERN --local-dir DIR   fnmatch over the store's files (the real CLI
                                                                             lists the whole store first: counted as a listing)
  hf download STORE FILE --repo-type dataset --local-dir DIR                 one file (no listing)
  hf upload STORE SRC_DIR PATH --repo-type dataset --commit-message M        copies SRC_DIR into the store at PATH
Every call is appended to MR/hf.log."""
import fnmatch, os, shutil, sys
MR = os.environ['MOCK_MR']; S = f'{MR}/store'; a = sys.argv[1:]
with open(f'{MR}/hf.log', 'a') as f:
    f.write('hf ' + ' '.join(a) + '\n')


def opt(n):
    return a[a.index(n) + 1] if n in a else None


if a[0] == 'download':
    pos = [x for i, x in enumerate(a[2:], 2) if not x.startswith('--') and not a[i - 1].startswith('--')]
    inc, out = opt('--include'), opt('--local-dir')
    if inc:
        files = [os.path.relpath(os.path.join(r, x), S) for r, _, fs in os.walk(S) for x in fs]
        hit = [f for f in files if fnmatch.fnmatch(f, inc)]
        for f in hit:
            os.makedirs(os.path.dirname(f'{out}/{f}'), exist_ok=True); shutil.copy(f'{S}/{f}', f'{out}/{f}')
        sys.exit(0)
    f = pos[0]
    if not os.path.isfile(f'{S}/{f}'):
        sys.exit(1)
    os.makedirs(os.path.dirname(f'{out}/{f}'), exist_ok=True); shutil.copy(f'{S}/{f}', f'{out}/{f}')
elif a[0] == 'upload':
    src, dst = a[2], a[3]
    shutil.copytree(src, f'{S}/{dst}', dirs_exist_ok=True, symlinks=False)
sys.exit(0)
