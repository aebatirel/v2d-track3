"""Diagnostic (report only, decides nothing; T-I16, 1 Nov): S at the round-2 floor frames of the five public episodes,
on the DELIVERED pieces (the round folder's piece_*.obj, 16 copies) and on the FAITHFUL colliders (the SHELL's 2 mm
boxes, collcarve.Faithful; 4 copies to bound the cost), although every such frame failed the pose precheck, where the
rule runs no S (PREREG F-I5.15 (3)). Same S as the floor (collcarve.sink_test2: receiver fixed at its tracked pose,
guest free, our table plane, 0.3 kg, 2 s at 2 ms, the stored jitters, 4 mm / 5 deg). Inputs: the T-I16 run's round
folders and the shell_t5p36 bodies; GT-free.

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/build/I/fi517_s_diag.py --run <run> --v6 <bundles> --out <json>
"""
import argparse
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
if MR not in sys.path:
    sys.path.insert(0, MR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--v6', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--eps', default='11,12,13,2'); ap.add_argument('--ref-copies', type=int, default=4)
    ap.add_argument('--max-wall-s', type=float, default=900.0)
    a = ap.parse_args()
    import numpy as np
    import trimesh
    from gmg import guard
    guard.set_run(a.run)
    from gmg import interlock as IL, collcarve as CC, cavpieces as CP
    from gmg.tools.interlock_dev import load_mesh
    out = dict(rule='report only (T-I16 diagnostic); S is not required at pose_impossible frames (F-I5.15 (3))',
               episodes={})
    if os.path.exists(a.out):
        out = json.load(open(a.out))
    for ep in [int(x) for x in a.eps.split(',')]:
        r0 = os.path.join(a.run, 'sim', 'public', f'ep{ep}-fi5r2', 'r0')
        floor = json.load(open(os.path.join(r0, 'floor.json')))
        b = IL.load_bundle_any(os.path.join(a.v6, f'ep{ep}'))
        tb = b.meta['table']
        table = (np.asarray(tb['n'], float), float(tb['d']))
        E = out['episodes'].setdefault(str(ep), {})
        for key, P in floor['pairs'].items():
            recv, guest, frames = P.get('receiver'), P.get('guest'), P.get('frames') or []
            if not frames:
                E[key] = dict(flag=P.get('flag') or (P.get('info') or {}).get('flag'), frames=[])
                continue
            pcs = {o: [np.asarray(trimesh.load(f, force='mesh').vertices, float)
                       for f in sorted(glob.glob(os.path.join(r0, o, 'piece_*.obj')))] for o in (recv, guest)}
            bodies = {o: load_mesh(os.path.join(a.run, 'cand', 'public', f'ep{ep}', o, 'shell_t5p36.glb'))
                      for o in (recv, guest)}
            F = {o: CC.Faithful(bodies[o]) for o in (recv, guest)}
            rows = E.setdefault(key, dict(receiver=recv, guest=guest, rows={}))['rows']
            for f in frames:
                if str(f) in rows and rows[str(f)].get('faithful'):
                    continue
                Wr = CC._world(b, recv, f)
                Wg = Wr @ IL.rel_pose(b.poses, recv, guest, f)
                row = dict(frame=f, pieces=dict(delivered=[len(pcs[recv]), len(pcs[guest])],
                                                faithful=[len(F[recv].boxes), len(F[guest].boxes)]))
                t = time.time()
                sd = CC.sink_test2(pcs[recv], pcs[guest], Wr, Wg, table, CP.exact_props(pcs[guest], 0.3),
                                   copies=16, secs=CC.k_('s_secs'), dt=CC.k_('s_dt'),
                                   disp_max=CC.k_('s_disp_m'), tilt_max=CC.k_('s_tilt_deg'))
                sd['sec'] = round(time.time() - t, 1)
                row['delivered'] = {k: v for k, v in sd.items() if k != 'per_copy'}
                t = time.time()
                sr = CC.sink_test2(F[recv].boxes, F[guest].boxes, Wr, Wg, table, CP.exact_props(F[guest].boxes, 0.3),
                                   copies=a.ref_copies, secs=CC.k_('s_secs'), dt=CC.k_('s_dt'),
                                   disp_max=CC.k_('s_disp_m'), tilt_max=CC.k_('s_tilt_deg'), max_wall_s=a.max_wall_s)
                sr['sec'] = round(time.time() - t, 1)
                row['faithful'] = {k: v for k, v in sr.items() if k != 'per_copy'}
                row['faithful_per_copy'] = sr.get('per_copy')
                rows[str(f)] = row
                print(ep, key, f, 'delivered', json.dumps(row['delivered']), 'faithful', json.dumps(row['faithful']),
                      flush=True)
                with open(a.out, 'w') as fh:
                    json.dump(out, fh, indent=1, default=IL._jdefault)
    with open(a.out, 'w') as fh:
        json.dump(out, fh, indent=1, default=IL._jdefault)


if __name__ == '__main__':
    main()
