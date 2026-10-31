"""Re-run S6 with the committed pipeline/refine.py code (step_S6, s6_plane, Obj) on the stored eval perception tracks
(the runs behind pack 6 / 7, as eval_screen.inputs), GT-free. Independent of eval_screen.py's own S6 copy.
Usage: python -I s6_committed.py OUT_JSON"""
import sys, json, types, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/screen/scripts')
import refine as R
import eval_screen as E
a = types.SimpleNamespace(s6_hmax_cm=2.0, s6_rmax_deg=10.0, s6_axisym='blue_cup,beige_cup')   # refine.py defaults
res = {}
for ep in E.EV:
    I = E.inputs(ep, False)                       # every path passes refine.assert_inference_input inside
    det = np.load(R.checked(I['det']), allow_pickle=True); names = [str(x) for x in det['names']]
    P = np.load(R.checked(I['poses'])); W = P['world_T_cam'].astype(float)
    objs = [R.Obj(n, f'{E.lib(ep, n, False)}/{n}.glb') for n in names]
    O = [np.einsum('nij,njk->nik', W, P[f'cam_T_{n}'].astype(float)) for n in names]
    d0 = np.repeat(np.repeat(det['depth'].astype(np.float32), 2, 0), 2, 1)     # [::2, ::2] in s6_plane = det's depth
    plane = R.s6_plane(d0, det['K'].astype(float), W[0], None, None, {})
    rec = R.step_S6(a, objs, O, plane)
    res[str(ep)] = dict(frozen=rec['frozen'], W0_dev=float(np.abs(W[0] - np.eye(4)).max()),
                        objects={n: {k: v for k, v in o.items()} for n, o in rec['objects'].items()})
json.dump(res, open(sys.argv[1], 'w'), indent=1)
print({k: v['frozen'] for k, v in res.items()})
