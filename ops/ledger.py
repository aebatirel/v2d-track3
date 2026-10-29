#!/usr/bin/env python3
"""Shared GPU spend ledger in the HF store (ledger/spend.jsonl), visible to every session on any branch (2026-10-29).

Rule for every session that rents a box: before `ops/vast.sh create`, check `ops/vast.sh show` and the Vast credit,
read this ledger, and add a `planned` line; after the box is destroyed, add an `actual` line with the measured cost.
  python3 ops/ledger.py show
  python3 ops/ledger.py add planned <run_id> <est_usd> "<purpose>" [approval]
  python3 ops/ledger.py add actual  <run_id> <usd>     "<note>"
  python3 ops/ledger.py budget <usd> "<note>"          record an owner top-up / cap
"""
import datetime, json, os, sys, tempfile

from huggingface_hub import HfApi, hf_hub_download

STORE = os.environ.get('HF_STORE', 'aebatirel/v2d-store')
PATH = 'ledger/spend.jsonl'
SESSION = os.environ.get('LEDGER_SESSION', 'unknown-session')


def read():
    try:
        p = hf_hub_download(STORE, PATH, repo_type='dataset', force_download=True)
        return [json.loads(l) for l in open(p) if l.strip()]
    except Exception:
        return []


def write(rows, msg):
    with tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False) as f:
        f.write(''.join(json.dumps(r) + '\n' for r in rows))
    HfApi().upload_file(path_or_fileobj=f.name, path_in_repo=PATH, repo_id=STORE, repo_type='dataset',
                        commit_message=msg)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'show'
    rows = read()
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
    if cmd == 'show':
        planned = {r['run']: r['usd'] for r in rows if r['kind'] == 'planned'}
        actual = {r['run']: r['usd'] for r in rows if r['kind'] == 'actual'}
        budget = sum(r['usd'] for r in rows if r['kind'] == 'budget')
        for r in rows:
            print(f"{r['time']}  {r['kind']:<8} {r.get('run', '-'):<34} ${r['usd']:>7.2f}  {r.get('session', '')}  "
                  f"{r.get('note', '')}")
        open_runs = sorted(set(planned) - set(actual))
        print(f"budget ${budget:.2f}; actual ${sum(actual.values()):.2f}; planned but not closed: "
              f"{open_runs} (${sum(planned[r] for r in open_runs):.2f})")
    elif cmd == 'add':
        kind, run, usd, note = sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5]
        r = dict(time=now, kind=kind, run=run, usd=usd, session=SESSION, note=note)
        if len(sys.argv) > 6:
            r['approval'] = sys.argv[6]
        write(rows + [r], f'ledger: {kind} {run} ${usd:.2f}')
        print(json.dumps(r))
    elif cmd == 'budget':
        r = dict(time=now, kind='budget', run='-', usd=float(sys.argv[2]), session=SESSION, note=sys.argv[3])
        write(rows + [r], f'ledger: budget ${r["usd"]:.2f}')
        print(json.dumps(r))


if __name__ == '__main__':
    main()
