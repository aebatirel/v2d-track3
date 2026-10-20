# Stage B re-run: scan a whole spoon clip for held/rest marker triples with b_held.py's per-frame logic (unchanged), but
# decoding each video once (sequential). Output: out/b2/held_e<ep>.jsonl (resumable; skips k already present).
# Usage: b2_scan.py <ep> <step> [k0] [k1]
import sys, os, json, textwrap, cv2
ep, step = int(sys.argv[1]), int(sys.argv[2]); k0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0; k1 = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 6
src = open('/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts/b_held.py').read()
src = src.replace("OUTF = f'{OUT}/held_e{ep}.jsonl'", "OUTF = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b2/held_e%d.jsonl' % ep")
head, body = src.split("for k in ks:\n")
body = body.replace("    fr = {c: read_frames('evaluation', ep, c, [k])[k] for c in 'bc'}\n", "")
body = body.replace("    fa2 = read_frames('evaluation', ep, 'a', [k + 1, k + 2]); A = fa2[k + 1]\n", "")
assert 'read_frames' not in body
ARGS = list(sys.argv); sys.argv = ['x', str(ep), '0', '1', '1']
exec(compile(head, 'b_held_head', 'exec'))
exec(compile('def process(k, fr, fa2, A):\n' + body, 'b_held_body', 'exec'))
ep, step = int(ARGS[1]), int(ARGS[2]); k0 = int(ARGS[3]) if len(ARGS) > 3 else 0; k1 = int(ARGS[4]) if len(ARGS) > 4 else 10 ** 6
caps = {c: cv2.VideoCapture(vid('evaluation', ep, c)) for c in 'abc'}
buf = {c: {} for c in 'abc'}; i = 0
while True:
    got = {c: caps[c].read() for c in 'abc'}
    if not all(g[0] for g in got.values()): break
    for c in 'abc': buf[c][i] = got[c][1]
    k = i - 2                                         # need a[k+1], a[k+2] -> process b/c frame k once a[k+2] is decoded
    if k >= k0 and k < k1 and k % step == 0 and k not in done:
        process(k, {'b': buf['b'][k], 'c': buf['c'][k]}, {k + 1: buf['a'][k + 1], k + 2: buf['a'][k + 2]}, buf['a'][k + 1])
    for c in 'abc':
        for j in [j for j in buf[c] if j < i - 3]: del buf[c][j]
    i += 1
    if i - 2 >= k1: break
print('done', ep, 'frames', i)
