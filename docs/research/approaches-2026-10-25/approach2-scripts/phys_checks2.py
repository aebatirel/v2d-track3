#!/usr/bin/env python
"""P1b (rock-to-flat certificate for a flat-based lathe), P2b (nest violation profile), P3b (lid lift to clear the pot).
GT-free: our meshes, our lathe fits, our own references."""
import sys, json, numpy as np, trimesh
sys.path.insert(0, '.')
import refpose
from phys_checks import load, world, surf_com
L = '/home/user/v2d-track3/meshes/'; A = 'out/'
res = {}
# P1b: COM (surface-uniform, as our URDFs) projected along world vertical onto the base plane, inside the base disc?
for key, slot, lab in [('ev10', 1, 'beige_cup_v3x'), ('ev10', 1, 'beige_cup_v3'), ('ev10', 0, 'blue_cup'), ('ep21', 0, 'blue_cup')]:
    nm, pos, q = refpose.load(key)
    z = np.load(A + f'lathe2/{lab}_profile.npz'); c0, d = z['c0'], z['d']
    hb = float(z['hb_plane']); rb = float(z['prof_r'][0])
    body = load(A + f'lathe2/{lab}_body.glb'); com = surf_com(body)
    R = refpose.R_of(q[0, slot]); dw = R @ d; up = np.array([0, 0, 1.0])
    base_c = c0 + hb * d                                       # base centre (object frame)
    # base normal pointing out of the object at the base: sign so that (base_c - com).n > 0
    n = d if (base_c - com) @ d > 0 else -d
    nw = R @ n
    tilt = float(np.degrees(np.arccos(np.clip(-nw @ up, -1, 1))))  # base normal should point down
    # project COM along world vertical onto the base plane
    comw = R @ com + pos[0, slot]; bw = R @ base_c + pos[0, slot]
    t = ((bw - comw) @ nw) / (up @ nw) if abs(up @ nw) > 1e-6 else np.nan
    pt = comw + t * up
    radial = np.linalg.norm((pt - bw) - ((pt - bw) @ nw) * nw)
    res[f'P1b {key} f0 {lab} lathe'] = dict(base_r_mm=round(rb * 1e3, 1), base_tilt_deg=round(tilt, 1), com_offset_mm=round(radial * 1e3, 1),
                                         margin_mm=round((rb - radial) * 1e3, 1), stands_after_rocking=bool(radial < rb - 0.003 and tilt < 90))
# P2b: nest constraint at eval-10 last frame: beige outer surface vs blue inner (cavity) radius
nm, pos, q = refpose.load('ev10'); f = len(pos) - 1
zb = np.load(A + 'lathe2/blue_cup_profile.npz'); zg = np.load(A + 'lathe2/beige_cup_v3x_profile.npz')
beige = load(A + 'lathe2/beige_cup_v3x_body.glb')
P = beige.sample(20000)
Pw = P @ refpose.R_of(q[f, 1]).T + pos[f, 1]
Pb = refpose.to_obj(Pw, pos[f, 0], q[f, 0])                    # beige points in the blue cup's frame
c0, d = zb['c0'], zb['d']; Q = Pb - c0; h = Q @ d; r = np.linalg.norm(Q - np.outer(h, d), axis=1)
ph, pr, t = zb['prof_h'], zb['prof_r'], float(zb['t'])
o = np.argsort(ph); r_in = np.interp(h, ph[o], pr[o] - t)
hmin, hmax = min(zb['hb_plane'], zb['hm_plane']), max(zb['hb_plane'], zb['hm_plane'])
inside_range = (h > hmin) & (h < hmax)
viol = (r - r_in)[inside_range & (r < np.interp(h, ph[o], pr[o]) + 0.01)]
# axis misalignment of the two cups at the stacked pose
dg_w = refpose.R_of(q[f, 1]) @ zg['d']; db_w = refpose.R_of(q[f, 0]) @ d
res['P2b ev10 last frame nest'] = dict(axis_angle_deg=round(float(np.degrees(np.arccos(abs(dg_w @ db_w)))), 1),
                                       beige_pts_in_blue_height_range=int(inside_range.sum()),
                                       viol_p50_mm=round(float(np.percentile(viol, 50)) * 1e3, 1) if len(viol) else None,
                                       viol_p95_mm=round(float(np.percentile(viol, 95)) * 1e3, 1) if len(viol) else None,
                                       viol_max_mm=round(float(viol.max()) * 1e3, 1) if len(viol) else None,
                                       frac_viol_pos=round(float((viol > 0).mean()), 3) if len(viol) else None,
                                       blue_wall_t_mm=round(t * 1e3, 1), beige_wall_t_mm=round(float(zg['t']) * 1e3, 1))
# P3b: lift of the lid along world z needed to clear the pot (overlap < 0.05 cm3), library vs lathe pot body
for key in ['ep2', 'ev1']:
    nm, pos, q = refpose.load(key)
    lid0 = world(load(L + 'library_v3/white_pot_lid.glb'), pos[0, 1], q[0, 1])
    for lab, pp in [('library pot', L + 'library_v3/white_pot.glb'), ('lathe2 pot body', A + 'lathe2/white_pot_body.glb')]:
        pot = world(load(pp), pos[0, 0], q[0, 0])
        lo, hi = 0.0, 0.03
        for _ in range(12):
            mid = 0.5 * (lo + hi); lid = lid0.copy(); lid.apply_translation([0, 0, mid])
            v = pot.intersection(lid, engine='manifold').volume * 1e6
            if v > 0.05: lo = mid
            else: hi = mid
        res[f'P3b {key} f0 lid lift to clear {lab}'] = dict(lift_mm=round(hi * 1e3, 1))
json.dump(res, open(A + 'phys_checks2.json', 'w'), indent=1)
for k, v in res.items(): print(k, v)
