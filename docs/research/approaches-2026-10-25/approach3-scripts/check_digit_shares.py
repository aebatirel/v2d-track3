"""Cross-check: digit shares from tools/contact_slots.py (the fixed analysis helper, --per frames) on the hold_phases holds
must equal the 'correct:' columns of approach3-scripts/out/digit_shares.txt.
Usage: python -I check_digit_shares.py REPO TAG=REF ..."""
import os, re, subprocess, sys

repo = sys.argv[1]
sys.path.insert(0, os.path.join(repo, 'pipeline'))
from hold_phases import hold_phases  # noqa: E402

want = {}
for ln in open(os.path.join(repo, 'docs/research/approaches-2026-10-25/approach3-scripts/out/digit_shares.txt')):
    m = re.match(r'(\S+)\s+([lr]) (.{13}) +(\d+)- *(\d+) correct: (.*?) \|', ln)
    want[(m.group(1), m.group(2), int(m.group(4)), int(m.group(5)))] = m.group(6)
n = bad = 0
for spec in sys.argv[2:]:
    tag, path = spec.split('=', 1)
    holds = [h for h in hold_phases(path)[0]['phases'] if h['end'] - h['start'] >= 15]
    wins = [f"{h['hand']}:{h['object']}:{h['start']}-{h['end']}" for h in holds]
    out = subprocess.run([sys.executable, '-I', os.path.join(repo, 'tools/contact_slots.py'), path, '--per', 'frames', *wins],
                         capture_output=True, text=True, check=True).stdout.splitlines()[2:]
    for h, ln in zip(holds, out):
        got = re.search(r'\| digits (.*?) \|', ln).group(1)
        exp = want[(tag, h['hand'][0], h['start'], h['end'])]
        n += 1; bad += got != exp
        if got != exp:
            print('MISMATCH', tag, h['hand'], h['object'], h['start'], h['end'], '\n  got ', got, '\n  want', exp)
print(f'{n} holds compared, {bad} mismatches; digit_shares.txt has {len(want)} holds')
