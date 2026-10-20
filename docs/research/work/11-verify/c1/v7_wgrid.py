"""Verifier C1: own-metric (v5_anchor) W grid +-1/+-5 and spin-error budget (AUC vs |spin error|) for cup anchors.
Public GT only. usage: python v7_wgrid.py [nverts] [seed]"""
import sys, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/11-verify")
import v5_anchor as V
NV = int(sys.argv[1]) if len(sys.argv) > 1 else 500; SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 0
V.NV, V.SEED = NV, SEED
UPB = {"blue_cup": [0, 0, -1]}; HB = {"blue_cup": [1, 0, 0]}
TW = {12: [13], 13: [12], 21: [22], 22: [21]}
wr = lambda a: (a + 180) % 360 - 180
D = {ep: V.load(ep) for ep in (12, 13, 21, 22)}
yaw = lambda ep: V.yaw_about(D[ep][1][0, D[ep][0].index("blue_cup"), 3:], UPB["blue_cup"], HB["blue_cup"])
G = {}; B = {}
for ep in TW:
    names, P = D[ep]; S = lambda s: V.metrics(V.spin(P, UPB["blue_cup"], s), P, names)
    d = wr(yaw(TW[ep][0]) - yaw(ep))
    for W in (0, 1, 3, 5, 10):
        G.setdefault(W, []).append(np.mean([S(wr(d + w)) for w in ((0,) if W == 0 else (-W, W))], 0))
    for e in (0, 2, 5, 8, 10, 15, 20, 30):
        B.setdefault(e, []).append(np.mean([S(s) for s in ((0,) if e == 0 else (-e, e))], 0))
    print(ep, "prior err", round(d, 2), flush=True)
print(f"NV {NV} seed {SEED}")
for W, L in G.items(): print(f"W+-{W:<2d} AGG AUC/SP/MP/RPE/MPPE", np.round(np.mean(L, 0), 3).tolist())
for e, L in B.items(): print(f"spin err +-{e:<2d} AUC per ep", np.round([l[0] for l in L], 3).tolist(), "mean", round(float(np.mean([l[0] for l in L])), 3), "MP", round(float(np.mean([l[2] for l in L])), 2))
