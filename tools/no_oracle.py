"""Leak guard (2026-10-30, oracle twins): refuse anything mocap-derived on its way into an eval pack (CLAUDE.md).

The oracle twins (ops/jobs/oracle_twins.sh) train public-episode policies on references whose object motion is mocap.
They live under oracle names only: perception /content/oracle/ep<N>, references refs/oracle<V>/ and refs/oracle_*/,
runs runs/oracle*/, results results/oracle*/ and results/hard_ab/ep<N>/oracle_*, in store runs <date>-orc<X>-<sha>.
Arguments are words (run ids, EP:RUN picks, RUN@sub,dirs, paths) and/or JSON files (e.g. checkpoints.json). Exit 1
when a word, a string in a JSON file, or the resolved training config stored in a named checkpoint (safetensors
metadata user.resolved_config_json: task.parquet, asset paths) names an oracle reference or an oracle-twin run.
Usage: python tools/no_oracle.py WORD|FILE.json ...        (pack_eval.sh, h5_reeval.sh, submit_pack.sh)
"""
import json, os, re, struct, sys

BAD = re.compile(r'oracle|\d{8}-orc[A-Za-z0-9]*-')


def strings(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield str(k); yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)
    elif isinstance(x, str):
        yield x


def ckpt_config(path):  # the resolved config a FlashCHORD checkpoint stores (empty if unreadable)
    try:
        with open(path, 'rb') as f:
            n = struct.unpack('<Q', f.read(8))[0]; h = json.loads(f.read(n))
        return list(strings(json.loads(h.get('__metadata__', {}).get('user.resolved_config_json', '{}'))))
    except Exception:
        return []


bad = []
for w in sys.argv[1:]:
    todo = [(w, w)]
    if w.endswith('.json') and os.path.isfile(w):
        todo = [(f'{w}: {s}', s) for s in strings(json.load(open(w)))]
    for where, s in todo:
        if BAD.search(s):
            bad.append(where)
        elif s.endswith('.safetensors') and os.path.isfile(s):
            bad += [f'{where} (checkpoint config: {c})' for c in ckpt_config(s) if BAD.search(c)][:3]
if bad:
    print('REFUSED: oracle-twin (mocap-derived) input, never for an eval pack:\n  ' + '\n  '.join(bad[:10]), file=sys.stderr)
    sys.exit(1)
print(f'no_oracle: {len(sys.argv) - 1} inputs checked, none oracle-derived')
