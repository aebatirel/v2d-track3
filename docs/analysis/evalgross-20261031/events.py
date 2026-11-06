#!/usr/bin/env python3
"""List the J (jump) events of screen.py on references and characterise each one (inference side only):
spike (the track comes back within 3 cm of its pre-jump position) or step (it stays away), its duration, the
largest excursion, and the reference-minus-perception distance in the window.
Usage: python3 events.py SCREEN_EVAL.json MANIFEST_EVAL.json OUT.json"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screen  # noqa: E402

S, MAN, OUT = sys.argv[1:4]
scr = json.load(open(S))['items']
man = {(m['ep'], m['kind']): m for m in json.load(open(MAN))}
out = []
for it in scr:
    if it['kind'] != 'ref' or 'error' in it:
        continue
    m = man[(it['ep'], 'ref')]
    n, d, A, tz = screen.load_plane(m)
    names, O = screen.load_ref(m['ref'], A)
    pn, PO = screen.load_perc(m['poses'])
    PO = PO[:, [pn.index(x) for x in names]]
    for b, nm in enumerate(names):
        o = it['objects'][nm]
        if not (o['jump_cm_max'] > 5 or o['jump_deg_max'] > 45):
            continue
        mesh = screen.Mesh(nm, os.path.join(m['meshes'], f'{nm}.glb'))
        c = O[:, b, :3, :3] @ mesh.com + O[:, b, :3, 3]
        pc = PO[:, b, :3, :3] @ mesh.com + PO[:, b, :3, 3]
        st = np.r_[0, np.linalg.norm(np.diff(c, axis=0), axis=1) * 100]
        if nm in screen.CUPS:
            rs = np.r_[0, screen.axis_ang(O[1:, b, :3, :3], O[:-1, b, :3, :3], mesh.axis)]
        else:
            rs = np.r_[0, screen.ang(O[1:, b, :3, :3], O[:-1, b, :3, :3])]
        ev = np.where((st > 5) | (rs > 45))[0]
        T = len(c)
        events = []
        for t in ev:
            pre = c[max(t - 1, 0)]
            dist = np.linalg.norm(c[t:] - pre, axis=1) * 100
            back = np.where(dist < 3)[0]
            dur = int(back[0]) if len(back) else int(T - t)
            w = slice(max(t - 3, 0), min(t + dur + 3, T))
            events.append(dict(frame=int(t), step_cm=round(float(st[t]), 1), rot_deg=round(float(rs[t]), 0),
                               kind='spike' if len(back) else 'step (never returns within 3 cm)',
                               frames_away=dur, max_excursion_cm=round(float(dist[:max(dur, 1)].max()), 1),
                               height_cm_pre=round(float(c[max(t - 1, 0)] @ n + d) * 100, 1),
                               height_cm_at=round(float(c[t] @ n + d) * 100, 1),
                               ref_minus_perc_cm_max=round(float(np.linalg.norm(c[w] - pc[w], axis=1).max() * 100), 1)))
        out.append(dict(ep=it['ep'], obj=nm, T=T, events=events))
        print(it['ep'], nm, json.dumps(events))
json.dump(out, open(OUT, 'w'), indent=1)
