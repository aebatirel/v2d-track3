"""Stage C (resume), evaluation only: temporal vote for a CONSTANT spin correction. Each fix frame (status >= 2) votes
for its chosen spin hypothesis (weight 2 for 3-marker fixes, 1 for 2-marker), smoothed by a +-15 deg window on the 15 deg
grid; the winner is compared with the correct correction (360 - SPIN). Also the vote restricted to the first 40 frames
(slot-0 anchor use) and the margin (winner score / runner-up outside +-30 deg).
usage: c/spin_vote.py c/trk_<ep>_s<deg>[n<pn>].npz ..."""
import sys, numpy as np
for fn in sys.argv[1:]:
    z = np.load(fn); sp = float(fn.split('_s')[-1].split('.')[0].split('n')[0]); T = int(z['T']); want = (360 - sp) % 360
    s, st = z['spin_0'][:T], z['status_0'][:T]; out = []
    for lab, m in (('all', np.ones(T, bool)), ('t<40', np.arange(T) < 40)):
        fx = (st >= 2) & m; w = np.where(st[fx] == 3, 2.0, 1.0); g = np.arange(0, 360, 15)
        d = lambda a, b: np.abs(((a - b + 180) % 360) - 180)
        sc = np.array([np.sum(w * (d(s[fx], a) <= 15)) for a in g]); k = int(np.argmax(sc)); win = g[k]
        ru = max([sc[i] for i in range(len(g)) if d(g[i], win) > 30] or [0])
        out.append(f'{lab}: n {int(fx.sum())} winner {win} ({"OK" if d(win, want) <= 15 else "WRONG"}) margin {sc[k]:.0f}/{ru:.0f}')
    print(fn, '|', ' | '.join(out))
