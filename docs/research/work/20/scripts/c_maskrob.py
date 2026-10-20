"""Robustness of the MC rule to a worse frame-0 mask (motion features re-run with dilated / eroded / shifted masks;
contact features unchanged). usage: c_maskrob.py"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import c_eval2 as E
from c_grid import evaluate, stat
from c_lib import PUB, OUT
for mt in ('t2', 't2dil10', 't2ero6', 't2shx10'):
    if not all(os.path.exists(f'{OUT}/mot_{mt}_p{e}.npz') for e in PUB): print(mt, 'incomplete'); continue
    E.MTAG = mt
    for L in (10, None):
        o = evaluate(2.0, 0.15, L, 120); s = stat(o); eb = np.array([x['eb'] for x in o])
        print(f'{mt:8s} L={L}: late {s[0]} empty {s[1]} n_med {s[2]:.0f} dRmax {s[3]:.2f} dRp90 {s[4]:.2f} shmax {s[5]:.2f} shmean {s[6]:.2f} | '
              f'robust err median {np.median(eb):+.0f} | ' + ' '.join(f'p{x["ep"]}:{x["eb"]:+.0f}' for x in o))
