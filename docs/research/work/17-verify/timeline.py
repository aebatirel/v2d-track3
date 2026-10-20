"""Verifier: per contiguous segment block (rest/held/carried) median ADD and fix fraction from saved ev17 error arrays.
usage: timeline.py <err.npy> ..."""
import sys, numpy as np
SEG = ['rest', 'held', 'carr']
for fn in sys.argv[1:]:
    a = np.load(fn); et, er, ea, st, sg = a.T; sg = sg.astype(int); st = st.astype(int)
    print(fn.split('/')[-1], f'T {len(ea)}')
    i = 0; out = []
    while i < len(sg):
        j = i
        while j < len(sg) and sg[j] == sg[i]: j += 1
        m = slice(i, j)
        out.append(f'{i}-{j-1} {SEG[sg[i]]} ADD {np.median(ea[m]):.0f} r {np.median(er[m]):.0f} fix>=2 {np.mean(st[m] >= 2):.2f} fix3 {np.mean(st[m] == 3):.2f}')
        i = j
    print('   ' + '\n   '.join(out))
