"""ep0 phase table (phases from mocap: oracle diagnostic): per arm and object, mean ADD (cm) under the kit's scene
alignment and under the independent world transform G, mean rotation error, and the per-frame AUC share."""
import numpy as np
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
d = np.load(f'{S}/leak/diag_ep0/out/perframe.npz'); N = 373
vp, vl = d['mocap_speed_white_pot'], d['mocap_speed_white_pot_lid']; hp = d['hand_white_pot']; rel = d['lid_rel_d']
mp = vp > 3; ml = vl > 3
def runs(m):
    r = []; i = 0
    while i < N:
        if m[i]:
            j = i
            while j < N and m[j]: j += 1
            if j - i >= 4: r.append((i, j - 1))
            i = j
        else: i += 1
    return r
print('pot moving runs', runs(mp)); print('lid moving runs', runs(ml)); print('hand<=1.5cm of pot runs', runs(hp <= 1.5)); print('lid off pot (>1 cm) runs', runs(rel > 1))
PH = [('A rest, hands free', 0, 37), ('B pot handle grasped, static', 38, 52), ('C lid lifted to table', 53, 85),
      ('D lid on table, pot held', 86, 107), ('E pot carried (25-49 cm/s)', 108, 206), ('F pot held static', 207, 239),
      ('G lid back onto pot', 240, 266), ('H rest, lid on pot', 267, 372)]
thr = np.arange(1, 10); w = np.r_[0.5, np.ones(7), 0.5] / 8
share = lambda a: ((a[..., None] < thr) * w).sum(-1)
arms = [a for a in ('Ps', 'Po', 'Pr') if f'{a}_add_white_pot' in d.files]
for n in ('white_pot', 'white_pot_lid'):
    print(f'\n{n}: per phase  [kit ADD cm / G ADD cm / G rot deg / kit AUC share]')
    print('| phase | frames | ' + ' | '.join(f'{a} kit ADD | {a} G ADD | {a} G rot | {a} share' for a in arms) + ' |')
    for nm, a0, a1 in PH:
        sl = slice(a0, a1 + 1); row = f'| {nm} | {a0}-{a1} |'
        for a in arms:
            ka = d[f'{a}_add_{n}'][sl]; ga = d[f'{a}_ind_add_cm_{n}'][sl]
            gr = d[f'{a}_ind_rot_sym_deg_{n}'][sl] if f'{a}_ind_rot_sym_deg_{n}' in d.files else d[f'{a}_ind_rot_deg_{n}'][sl]
            row += f' {ka.mean():.1f} | {ga.mean():.1f} | {gr.mean():.1f} | {share(ka).mean():.2f} |'
        print(row)
