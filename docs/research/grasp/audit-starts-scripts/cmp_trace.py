"""Compare object motion of traces (displacement from the frame-0 pose, mm / deg) at chosen frames. No GT."""
import sys, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
frames = [int(x) for x in sys.argv[1].split(',')]; tr = sys.argv[2:]
for p in tr:
    Q, L, F = load_trace(p); objs = [l for l in L if l.startswith('track3_')]
    s = p.split('/')[-1][:28].ljust(28)
    for l in objs:
        i = L.index(l); s += f' | {l[7:17]}:' + ' '.join(f'{1000*np.linalg.norm(Q[f,i,:3]-Q[0,i,:3]):.0f}/{rot_deg(Q[f,i,3:7],Q[0,i,3:7]):.0f}' for f in frames if f < len(Q))
    print(s)
