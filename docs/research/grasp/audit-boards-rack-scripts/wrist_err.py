"""Zero trace: simulated hand C_MC vs reference C_MC (cm), split along world z and horizontal; per hand. No GT."""
import sys, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from refload import load_ref
d = load_ref(sys.argv[1]); z = np.load(sys.argv[2]); L = [str(x) for x in z['labels']]; Q = z['q'].astype(float); fr = [int(x) for x in sys.argv[3].split(',')]
for h in ('left', 'right'):
    ri = d[f'fnames_{h}'].index(f'{h}_hand_C_MC'); ti = L.index(f'{h}_sharpa_wave/{h}_hand_C_MC')
    e = (Q[:, ti, :3] - d[f'frames_{h}'][:len(Q), ri, :3]) * 100
    print(h, ' '.join(f'f{t}:{np.linalg.norm(e[t]):.1f}(dz{e[t,2]:+.1f})' for t in fr))
