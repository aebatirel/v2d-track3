"""Physical gates G3 (pair-scene contacts under sim=rl, the precheck's contacts.py unchanged) and G4 (hands-off settle:
collcarve's S, gmg.simphys.sink_test, as collcarve calls it) for one rack piece set on one episode, at the precheck's
three gate frames (rs_lib.gate_frames: the precheck's H30 contact frames, filled from R; GATES.md as amended).
G3 is plain MuJoCo, indicative only (FlashCHORD budget.py is the binding contact check). G6 (report): how far the guest
is thrown, the per-copy guest displacement in the G3 pair scene (both objects free, contacts.py's
disp_mm_receiver_guest) and in the G4 S scene (rack fixed).

Usage: phys.py SET OUT.json EP     SET: folder with plastic_dish_rack/piece_*.obj, or 'packed'
"""
import json, sys, time
import numpy as np
from scipy.spatial.transform import Rotation as Rot
import rs_lib as L
from measure import load_set

sys.path.insert(0, f'{L.PRECHECK}/scripts')
import contacts as CT                                                    # noqa: E402 (precheck, unchanged)
sys.path.insert(0, f'{L.REPO}/docs/research/mesh-2026-10-26')
from gmg import simphys as PH, simpieces as SP                           # noqa: E402

S_DISP, S_TILT, DROP_MAX = 0.004, 5.0, 4.0                              # GATES.md G4


def main():
    sset, out, ep = sys.argv[1], sys.argv[2], sys.argv[3]
    t0 = time.time()
    H, _ = load_set(sset)
    gh = L.load_hulls(L.GUEST[ep]['packed'])
    P = L.poses(ep)
    T, ir, ig = P['T'], P['ir'], P['ig']
    fr = L.records(ep)
    top = fr['summary']['support']['top_z']
    opt, cfg_info = CT.sim_rl()
    steps = int(round(CT.SECS / opt['timestep']))
    J = CT.jitters()
    pr, pg = CT.props(H), CT.props(gh)
    gp = SP.props(gh, SP.k_('mass_kg'))
    res = dict(set=sset, ep=ep, n_pieces=len(H), sim_rl=cfg_info['sha256'], frames=[])
    for f in L.gate_frames(ep):
        rows = []
        for j in J:
            Jm = np.eye(4); Jm[:3, :3] = Rot.from_rotvec(j[3:]).as_matrix(); Jm[:3, 3] = j[:3]
            rows.append(CT.count_copy(CT.scene(H, gh, T[f, ir], T[f, ig] @ Jm, top, pr, pg, opt), opt, steps))
        me = [r['max_nefc'] for r in rows]; mc = [r['max_ncon'] for r in rows]
        g3 = dict(max_nefc=int(max(me)), median_max_nefc=float(np.median(me)), max_ncon=int(max(mc)),
                  overflow_copies=int(sum(r['overflow'] for r in rows)), nan_copies=int(sum(r['nan'] for r in rows)),
                  classes_at_max=rows[int(np.argmax(me))]['classes_at_max_nefc'])
        gd = [r['disp_mm_receiver_guest'][1] for r in rows if r['disp_mm_receiver_guest']]
        rd = [r['disp_mm_receiver_guest'][0] for r in rows if r['disp_mm_receiver_guest']]
        g6 = dict(pair_guest_disp_median_mm=float(np.median(gd)), pair_guest_disp_max_mm=float(np.max(gd)),
                  pair_rack_disp_median_mm=float(np.median(rd)))
        g3['pass_'] = bool(g3['overflow_copies'] == 0 and g3['max_nefc'] <= opt['njmax'] and g3['max_ncon'] <= opt['nconmax'])
        s = PH.sink_test(H, gh, T[f, ir], T[f, ig], (np.array([0.0, 0.0, 1.0]), -float(top)), gp, copies=16,
                         secs=2.0, dt=0.002, disp_max=S_DISP, tilt_max=S_TILT)
        pc = s.get('per_copy', [])
        drop = max([c['dz_mm'] for c in pc], default=None)
        g4 = {k: v for k, v in s.items() if k != 'per_copy'}
        g4.update(max_copy_disp_mm=max([c['disp_mm'] for c in pc], default=None), max_copy_drop_mm=drop,
                  max_copy_tilt_deg=max([c['tilt_deg'] for c in pc], default=None),
                  fall_through=bool(drop is None or drop > DROP_MAX))
        g4['pass_'] = bool(s['pass_'] and not g4['fall_through'])
        g6.update(S_guest_disp_median_mm=float(np.median([c['disp_mm'] for c in pc])) if pc else None)
        res['frames'].append(dict(frame=f, G3=g3, G4=g4, G6=g6, G4_per_copy=pc,
                                  G3_per_copy=[{k: r[k] for k in ('max_ncon', 'max_nefc', 'overflow', 'nan',
                                                                  'disp_mm_receiver_guest')} for r in rows]))
        print(ep, f, 'G3', json.dumps(g3), 'G4', json.dumps(g4), 'G6', json.dumps(g6), f'{time.time() - t0:.0f}s',
              flush=True)
    res['G3_pass'] = all(r['G3']['pass_'] for r in res['frames'])
    res['G4_pass'] = all(r['G4']['pass_'] for r in res['frames'])
    res['secs'] = round(time.time() - t0, 1)
    json.dump(res, open(out, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
