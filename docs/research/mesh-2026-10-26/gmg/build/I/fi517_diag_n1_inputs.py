"""DIAGNOSTIC inputs (post hoc, report only): runs the n1 fixture through FI5R2 without physics and pickles its K
fragments, unclipped K, carved and default pieces to dbg_wall.pkl (cwd) for fi517_diag_n1_carve.py. Run from a scratch dir."""
import os, sys, pickle, time
os.environ.setdefault('GMG_MODE', 'dev')
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26'); sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/gmg/tests')
import numpy as np
from gmg import cavpieces as CP, collcarve as CC
import test_collcarve2 as T2
b, M = T2.nest_case()
objects = T2.routes(b, M, dict(A=T2.AXIS, B=T2.AXIS))
ctx, rep = CC.run_pairs2(b, objects, copies=2, log=T2.log, physics=False, hands=b.hands)
W = ctx.results[('A', 'B')]
pickle.dump(dict(Kfull=W['_Kfull'], Kf=W['_Kf'], carved=W['_carved'], default=objects['A']['hulls'], caps=W.get('caps'), comps=W.get('components'), carve=W.get('carve')), open('dbg_wall.pkl', 'wb'))
print('saved', W.get('caps'))
