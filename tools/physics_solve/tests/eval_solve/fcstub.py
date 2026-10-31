"""Stub of FlashCHORD's python for the eval_solve.sh dry run (2026-10-31): stands in for the GPU tools
(tools/physics_solve/solve.py, jitter_check.py, tools/trace_rollout.py zero) with fast fakes that write the same output
files. solve: copy of the input with +1 mm on robot_right_wrist_position (frames 10-19) and a matching offsets array;
jitter: deterministic fake scores; trace_rollout zero: the reference's own object poses (a perfect replay).
STUB_FAIL_EP=<N>: the solve of episode N exits 1. Calls are logged to $STUB_LOG (start/end, for the concurrency check)."""
import hashlib, json, os, re, sys, time
import numpy as np, pyarrow as pa, pyarrow.parquet as pq

args = sys.argv[1:]; script = os.path.basename(args[0]); m = re.search(r'/ep(\d+)/', ' '.join(args)); ep = m.group(1) if m else '?'
LOG = os.environ.get('STUB_LOG', '/dev/null')
def note(x):
    with open(LOG, 'a') as f:
        f.write(f'{time.time():.2f} {x} {script} ep{ep}\n')
note('start')
def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default
if script == 'solve.py':
    inp, out = args[1], args[2]
    time.sleep(float(os.environ.get('STUB_SOLVE_S', '3')))
    if os.environ.get('STUB_FAIL_EP') == ep:
        print('Traceback: stub solve failure', file=sys.stderr); note('end'); sys.exit(1)
    t = pq.read_table(inp); T = len(t.column('robot_left_wrist_position')[0].as_py())
    c = 'robot_right_wrist_position'; i = t.column_names.index(c)
    v = np.array(t.column(c)[0].as_py(), float).reshape(T, 3); v[10:20, 0] += 0.001
    t = t.set_column(i, c, pa.array([v.tolist()], type=t.schema.field(i).type)); pq.write_table(t, out)
    off = np.zeros((T, 56)); off[10:20, 0] = 0.001; base = os.path.splitext(out)[0]
    g = lambda c_: t.column(c_)[0].as_py(); names = g('object_body_names'); B = len(names)          # truth = the reference's poses
    q = np.concatenate([np.array(g('object_body_position'), float).reshape(T, B, 3), np.array(g('object_body_wxyz'), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]], -1)
    np.savez_compressed(base + '_solve.npz', offsets=off, q=q.astype(np.float32), frame=np.arange(T), labels=np.array([f'track3_{n}/object' for n in names]))
    json.dump(dict(args=dict(argv=args), T=T, replans=[dict(t=k, active=['right']) for k in range(0, T - 1, 10)], deadline_t=None,
                   rollbacks=0, paced_replans=0, mean_iters=7.0, wall_s=3.0), open(base + '_solve.json', 'w'))
    open(base + '_solve.log', 'w').write('stub solve\n')
    print(f'[3s] fresh load of {os.path.basename(out)}: target buffers bit-identical to the truth env: {{"wrist_pos_w": true}}')
elif script == 'jitter_check.py':
    ref = args[1]; k = int(opt('--k', 8)); h = int(hashlib.md5(open(ref, 'rb').read()).hexdigest()[:6], 16) / 16 ** 6
    j = [round(0.5 + 0.3 * h + 0.1 * x / k, 4) for x in range(k - 1)]
    json.dump(dict(ref=os.path.abspath(ref), device=opt('--device'), k=k, sig_pos=0.0005, sig_fin=0.005, seed=int(opt('--seed', 0)),
                   nominal=round(0.5 + 0.3 * h, 4), jittered=j, mean=round(float(np.mean(j)), 4), sd=round(float(np.std(j)), 4),
                   min=min(j), max=max(j), wall_s=0.1), open(opt('--json'), 'w'))
    time.sleep(0.5)
elif script == 'trace_rollout.py':
    out, ref, N = args[2], args[3], int(args[4]); t = pq.read_table(ref); g = lambda c: t.column(c)[0].as_py()
    names = g('object_body_names'); B = len(names)
    OP = np.array(g('object_body_position'), float).reshape(-1, B, 3)[:N]; OQ = np.array(g('object_body_wxyz'), float).reshape(-1, B, 4)[:N][..., [1, 2, 3, 0]]
    q = np.concatenate([OP, OQ], -1).astype(np.float32)
    np.savez_compressed(out, q=q, frame=np.arange(N), labels=np.array([f'track3_{n}/object' for n in names]))
else:
    print(f'fcstub: unexpected script {args}', file=sys.stderr); note('end'); sys.exit(2)
note('end')
