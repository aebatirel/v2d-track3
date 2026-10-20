# Stage B re-run: same as b_held.py but writes to out/b2/held_e<ep>.jsonl (leaves the original Stage B outputs untouched).
import sys
src = open('/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts/b_held.py').read()
src = src.replace("OUTF = f'{OUT}/held_e{ep}.jsonl'", "OUTF = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b2/held_e%d.jsonl' % ep")
assert 'out/b2/held_e' in src
exec(compile(src, 'b_held.py', 'exec'))
