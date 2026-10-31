"""PREREG F-I5.14 (7), post hoc, report only (decides nothing, never delivered): the hands-off rest / sink test S on the
pieces an F-I5 round folder DELIVERS, for every pair of the episode, including pairs the rule left out of scope (where
F-I5.5 runs no S). Answers "does the delivered simulator copy hold the objects where our track puts them with the hands
off?".

  GMG_MODE=dev python fi5_default_sink.py --run RUN --ep N --bundle BUNDLE_DIR [--tag fi5] [--copies 16]
Per pair: contact frames (bundle contact census); static frames = runs of >= 5 consecutive contact frames in which the
partner's collider centroid moves < 2 mm per frame relative to the object (F-I1.1 static rule); receiver = the object
whose pieces' convex hull holds the larger share of the other's 2 mm collider samples at the median relative pose of
those frames (F-I5.3 (a); tie < 0.1 -> the object that moves less); hands-off = no M1 hand joint within 30 mm of the
guest's collider (F-I5.3 (b)); S frames = the middle frame of the up to 3 longest hands-off static runs; S as F-I5.5
(simphys.sink_test: receiver fixed, guest free, table, 2 s at 2 ms, 16 jittered copies, 0.3 kg placeholder) on the
round folder's _default pieces and, when they differ, its delivered pieces. GT-free: our tracks, hands, pieces.
Writes RUN/fi5png/default_sink_ep<N>.json.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402
from gmg import interlock as IL, collcarve as CC, simphys as PH, simpieces as SP  # noqa: E402
from scipy.spatial import ConvexHull  # noqa: E402


def load_pieces(d):
    import trimesh
    fs = sorted(glob.glob(os.path.join(d, 'piece_*.obj')))
    return [np.asarray(trimesh.load(f, force='mesh').vertices) for f in fs] or None


def runs_of(frames, minlen):
    out, cur = [], []
    for f in sorted(frames):
        if cur and f != cur[-1] + 1:
            if len(cur) >= minlen:
                out.append(cur)
            cur = []
        cur.append(f)
    if len(cur) >= minlen:
        out.append(cur)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--ep', type=int, required=True)
    ap.add_argument('--bundle', required=True); ap.add_argument('--tag', default='fi5')
    ap.add_argument('--copies', type=int, default=16)
    a = ap.parse_args()
    guard.set_run(a.run)
    r0 = os.path.join(a.run, 'sim', 'public', f'ep{a.ep}-{a.tag}', 'r0')
    b = IL.load_bundle_any(a.bundle)
    hands = dict(guard.load_npz(os.path.join(a.run, 'in', f'hands{a.ep}', 'hands.npz'), 'own'))
    objs = b.objects
    dflt = {o: load_pieces(os.path.join(r0, '_default', o)) for o in objs}
    dlv = {o: load_pieces(os.path.join(r0, o)) for o in objs}
    Xs = {o: CC.collider_samples(dflt[o]) for o in objs}
    tb = b.meta.get('table')
    out = dict(ep=a.ep, note='post hoc, report only (PREREG F-I5.14 (7)); decides nothing', pairs={})
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            o, p = objs[i], objs[j]
            cf = sorted(int(f) for f in b.contact(o, p)['contact'])
            cg = Xs[p].mean(0)
            pos = {f: IL.rel_pose(b.poses, o, p, f)[:3, :3] @ cg + IL.rel_pose(b.poses, o, p, f)[:3, 3] for f in cf}
            stat = [f for f in cf if f - 1 in pos and np.linalg.norm(pos[f] - pos[f - 1]) < 0.002]
            sruns = runs_of(stat, 5)
            sfr = [f for r in sruns for f in r]
            row = dict(contact_frames=len(cf), static_runs=[[r[0], r[-1]] for r in sruns])
            if not sfr:
                row['why'] = 'no static contact run of >= 5 frames'
                out['pairs'][f'{o}|{p}'] = row
                continue
            T = IL.mean_pose([IL.rel_pose(b.poses, o, p, f) for f in sfr])
            ho = ConvexHull(np.vstack(dflt[o])).equations
            hp = ConvexHull(np.vstack(dflt[p])).equations
            s_o = float(np.mean(np.all((Xs[p] @ T[:3, :3].T + T[:3, 3]) @ ho[:, :3].T + ho[:, 3] <= 1e-9, axis=1)))
            Ti = np.linalg.inv(T)
            s_p = float(np.mean(np.all((Xs[o] @ Ti[:3, :3].T + Ti[:3, 3]) @ hp[:, :3].T + hp[:, 3] <= 1e-9, axis=1)))
            if abs(s_o - s_p) >= 0.1:
                recv = o if s_o > s_p else p
            else:
                spd = {}
                for x in (o, p):
                    W = np.array([CC._world(b, x, f)[:3, 3] for f in sfr])
                    spd[x] = float(np.median(np.linalg.norm(np.diff(W, axis=0), axis=1))) if len(W) > 1 else 0.0
                recv = o if spd[o] <= spd[p] else p
            guest = p if recv == o else o
            row.update(receiver=recv, guest=guest, containment={o: round(s_o, 4), p: round(s_p, 4)})
            hoff, flags = CC._hands_off(b, guest, sfr, Xs[guest], hands)
            hruns = sorted(runs_of([f for f in sfr if f in hoff], 5), key=lambda r: -len(r))
            S_frames = [r[len(r) // 2] for r in hruns[:3]]
            row.update(hands_off_static=len([f for f in sfr if f in hoff]), s_frames=S_frames, flags=flags)
            if not S_frames or not tb:
                row['why'] = 'no hands-off static run of >= 5 frames' if not S_frames else 'no table plane'
                out['pairs'][f'{o}|{p}'] = row
                continue
            variants = [('default', dflt)]
            if any(dlv[x] is not None and len(dlv[x]) != len(dflt[x]) or
                   (dlv[x] is not None and not all(np.allclose(A, B) for A, B in zip(dlv[x], dflt[x])))
                   for x in (recv, guest)):
                variants.append(('delivered', dlv))
            rows = []
            for f in S_frames:
                Wr = CC._world(b, recv, f)
                Wg = Wr @ IL.rel_pose(b.poses, recv, guest, f)
                rr = dict(frame=int(f))
                for name, H in variants:
                    gp = SP.props(H[guest], SP.k_('mass_kg'))
                    r = PH.sink_test(H[recv], H[guest], Wr, Wg, (np.asarray(tb['n']), float(tb['d'])), gp,
                                     copies=a.copies, secs=CC.k_('s_secs'), dt=CC.k_('s_dt'),
                                     disp_max=CC.k_('s_disp_m'), tilt_max=CC.k_('s_tilt_deg'))
                    rr[name] = {k: v for k, v in r.items() if k != 'per_copy'}
                rows.append(rr)
                print(a.ep, o, p, f, json.dumps(rr, default=IL._jdefault), flush=True)
            row['S'] = rows
            out['pairs'][f'{o}|{p}'] = row
    os.makedirs(os.path.join(a.run, 'fi5png'), exist_ok=True)
    with open(os.path.join(a.run, 'fi5png', f'default_sink_ep{a.ep}.json'), 'w') as fh:
        json.dump(out, fh, indent=1, default=IL._jdefault)
    print('ok', a.ep)


if __name__ == '__main__':
    main()
