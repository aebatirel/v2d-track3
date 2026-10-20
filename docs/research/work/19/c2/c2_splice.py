# Rewrite sections 1-6 of note 19: new head (c2/head_new.md) + the unchanged append-only logs of the current note
# (from the "# Logs (append-only" heading to the end). Asserts that the log part is preserved byte for byte.
import sys
NOTE = '/Users/aebatirel/Documents/Code/SlamDunk/reports/v2d-challenge/research/19-collision-hulls.md'
HEAD = '/Users/aebatirel/Documents/Code/v2d-research/work/19/c2/head_new.md'
s = open(NOTE).read(); h = open(HEAD).read()
assert 'C20_PLACEHOLDER' not in h, 'fill the placeholder first'
k = s.index('# Logs (append-only')
logs = s[k:]
out = h.rstrip('\n') + '\n\n' + logs
open('/Users/aebatirel/Documents/Code/v2d-research/work/19/c2/notes_before_splice.md', 'w').write(s)
open(NOTE, 'w').write(out)
assert open(NOTE).read().endswith(logs) and logs.count('\n- C') >= 21
print('spliced: head', len(h.splitlines()), 'lines; logs', len(logs.splitlines()), 'lines; total', len(out.splitlines()))
