"""ev10-cavsafe gate 2: the precheck's contacts.py pair scene (plain MuJoCo, sim=rl options and limits, 16 jittered
copies x 2 s, 0.3 kg, COM / inertia of the pieces' union) at FIXED frames, so packed ev10 and the candidate are counted
at the same poses. Imports contacts.py unchanged from ../../collcarve2-evalcheck/scripts.

Frames: gate = the precheck's three (f111, f142, f116); report only = f124, f160 (ends of the hands-off nested rest)
and the frames contacts.py's own rule (pick_frames) chooses on this set's evalcheck records.
Usage: python -I contacts_fixed.py CONFIG.json TAG GEO_DIR OUT.json
"""
import json, os, sys, time
import numpy as np
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'collcarve2-evalcheck', 'scripts'))
import contacts as C  # noqa: E402

GATE, REPORT = [111, 142, 116], [124, 160]
cfg, tag, geo, out = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3], sys.argv[4]
opt, cfg_info = C.sim_rl()
import mujoco  # noqa: E402
steps = int(round(C.SECS / opt['timestep']))
J = C.jitters()
fr = json.load(open(os.path.join(geo, f'ep{tag}_frames.json')))
po = np.load(os.path.join(geo, f'ep{tag}_poses.npz'))
T, ir, ig = po['T'], int(po['ir']), int(po['ig'])
names = [str(x) for x in po['names']]
top = fr['summary']['support']['top_z']
ec = cfg['episodes'][tag]
hr, hg = C.load_hulls(ec['objects'][names[ir]]), C.load_hulls(ec['objects'][names[ig]])
pr, pg = C.props(hr), C.props(hg)
sel, info = C.pick_frames(fr['per_frame']['rows'], fr['per_frame']['pair'])
plan = [(f, 'gate') for f in GATE] + [(f, 'report') for f in REPORT] + \
       [(c['frame'], f"report_rule_{c['kind']}_{c['hands']}") for c in sel if c['frame'] not in GATE + REPORT]
res = dict(tag=tag, receiver=names[ir], guest=names[ig], pieces=[len(hr), len(hg)], table_top_z=top, sim_rl=cfg_info,
           options=opt, copies=C.COPIES, secs=C.SECS, steps=steps, mass_kg=C.MASS, mujoco=mujoco.__version__,
           props=dict(receiver=dict(com=pr['com'].tolist(), volume_cm3=pr['volume_cm3']),
                      guest=dict(com=pg['com'].tolist(), volume_cm3=pg['volume_cm3'])),
           rule_pick=dict(selected=sel, info=info), frames=[])
for f, role in plan:
    t0 = time.time()
    rows = []
    for j in J:
        Jm = np.eye(4); Jm[:3, :3] = Rot.from_rotvec(j[3:]).as_matrix(); Jm[:3, 3] = j[:3]
        rows.append(C.count_copy(C.scene(hr, hg, T[f, ir], T[f, ig] @ Jm, top, pr, pg, opt), opt, steps))
    me = [r['max_nefc'] for r in rows]; mc = [r['max_ncon'] for r in rows]
    i = int(np.argmax(me))
    agg = dict(frame=int(f), role=role, max_nefc=int(max(me)), median_max_nefc=float(np.median(me)),
               max_ncon=int(max(mc)), median_max_ncon=float(np.median(mc)),
               nefc0_max=int(max(r['nefc0'] for r in rows)), ncon0_max=int(max(r['ncon0'] for r in rows)),
               overflow_copies=int(sum(r['overflow'] for r in rows)), nan_copies=int(sum(r['nan'] for r in rows)),
               step_max_nefc=rows[i]['step_max_nefc'], classes_at_max_nefc=rows[i]['classes_at_max_nefc'],
               disp_mm_median=[float(np.median([r['disp_mm_receiver_guest'][k] for r in rows
                                                if r['disp_mm_receiver_guest']])) for k in range(2)],
               pair_at_frame={k: fr['per_frame']['pair'][f][k] for k in ('V_packed', 'dist_packed_mm', 'V_faithful')},
               secs=round(time.time() - t0, 1), per_copy=rows)
    res['frames'].append(agg)
    print(f"{tag} f{f} ({role}): max nefc {agg['max_nefc']} ncon {agg['max_ncon']} step0 nefc {agg['nefc0_max']} "
          f"overflow {agg['overflow_copies']}/{C.COPIES} classes {agg['classes_at_max_nefc']} "
          f"disp {agg['disp_mm_median']} {agg['secs']} s", flush=True)
g = [a for a in res['frames'] if a['role'] == 'gate']
res['gate2'] = dict(frames=GATE, max_nefc=max(a['max_nefc'] for a in g), max_ncon=max(a['max_ncon'] for a in g),
                    overflow_copies=sum(a['overflow_copies'] for a in g))
res['gate2']['pass'] = bool(res['gate2']['overflow_copies'] == 0 and res['gate2']['max_nefc'] <= 512
                            and res['gate2']['max_ncon'] <= 256)
json.dump(res, open(out, 'w'), indent=1, default=float)
print('gate2', json.dumps(res['gate2']))
