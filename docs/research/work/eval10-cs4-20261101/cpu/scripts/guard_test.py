"""tools/no_oracle.py on this job's names (BUILD.md section 5): the cavity-safe retrain is PACKABLE if it passes, so the
pack guard must ACCEPT its run id, folders, piece sets and a stock-limit checkpoint under its names (also via a kit
checkpoints JSON), and must still REFUSE the njmax diagnostic's names and a non-stock checkpoint (no regression).
Usage: python -I guard_test.py --repo R --standin CK --neg CK1024 --work DIR --out J"""
import argparse, json, os, subprocess, sys

ap = argparse.ArgumentParser()
for k in ('repo', 'standin', 'neg', 'work', 'out'):
    ap.add_argument('--' + k, required=True)
A = ap.parse_args(); os.makedirs(A.work, exist_ok=True); G = os.path.join(A.repo, 'tools', 'no_oracle.py'); rows = []


def run(w):
    r = subprocess.run([sys.executable, '-I', G, w], capture_output=True, text=True, cwd=A.work)
    return r.returncode, (r.stderr or r.stdout).strip().splitlines()[-1][:200] if (r.stderr or r.stdout).strip() else ''


kit = os.path.join(A.work, 'checkpoints.json'); json.dump({'10': A.standin}, open(kit, 'w'))
kitneg = os.path.join(A.work, 'checkpoints_neg.json'); json.dump({'10': A.neg}, open(kitneg, 'w'))
accept = ['20261101-e10cs-abc1234', 'runs/20261101-e10cs-abc1234/results/ev10_cs/conf/r1/ep10/episode_000010.parquet',
          'perc2e10css42', 'perc2e10css43', 'refs/perc2e10css43_glockt/ep10', 'runs/perc2e10css42_glock/ep10-s42',
          'results/perc2e10css42_glock_public/ep10/best/policy.safetensors', 'results/ev10_cs', 'ev10_cs.sh', 'e10cs', 'eval10-cs4-20261101',
          'meshes/carve/ev10cs4', 'meshes/carve/ev10cs5', os.path.join(A.repo, 'meshes/carve/ev10cs4'), os.path.join(A.repo, 'meshes/carve/ev10cs5'),
          '10:results/ev10_cs/conf/r1/ep10', A.standin, kit]
refuse = ['20261101-e10nj-451b82d', 'results/ev10_nj', 'perc2e10njs43', A.neg, kitneg]
for w in accept:
    rc, why = run(w); rows.append(dict(word=w.replace(A.work, '<W>'), want='accept', rc=rc, ok=rc == 0, why=why))
for w in refuse:
    rc, why = run(w); rows.append(dict(word=w.replace(A.work, '<W>'), want='refuse', rc=rc, ok=rc != 0, why=why))
out = dict(ok=all(r['ok'] for r in rows), cases=rows)
json.dump(out, open(A.out, 'w'), indent=1)
for r in rows:
    print(('PASS ' if r['ok'] else 'FAIL ') + f"{r['want']}: {r['word'][-90:]} (rc {r['rc']})")
print(f"RESULT: {sum(r['ok'] for r in rows)}/{len(rows)} as expected")
sys.exit(0 if out['ok'] else 1)
