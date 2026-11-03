"""PREREG_srpublic.md: SP-SR / MP-SR per object of a public perception track against mocap (DIAGNOSTIC: reads mocap),
through the same registered path as pipeline/score_registered.py (kit registration, conversion, frame-0 alignment,
symmetry-aware orientation error), over 10 registration seeds.
Usage: python -I sr_public.py EP TRACK_NPZ MESH_DIR T3 KIT OUT_JSON"""
import sys, os, json, numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
EP, TRK, MD, T3D, KIT, OUT = int(sys.argv[1]), *sys.argv[2:7]
sys.path.insert(0, KIT)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
tab = pq.read_table(f'{T3D}/ep{EP}.parquet').to_pandas(); names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]; B = len(names)
P = np.load(TRK); T = min(len(P[names[0]]), len(tab)); fr = np.arange(T)
trk = np.stack([[np.r_[P[n][i][:3, 3], Rot.from_matrix(P[n][i][:3, :3]).as_quat()] for n in names] for i in fr])
gt = np.stack([[(lambda q: np.r_[q[:3], q[4:7], q[3]])(np.array([o for o in tab['observation.objects'].iloc[i] if o['name'] == n][0]['pose'], float)) for n in names] for i in fr])
def scan(n):
    q = f'{T3D}/mesh/{n}/{n}.glb'; return q if os.path.exists(q) else f'{T3D}/mesh/{n}/{n}_visual.glb'
H = []
for s, n in enumerate(names):
    m = trimesh.load(scan(n), force='mesh'); v, f = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64); c, _ = _surface_moments(v, f)
    pts = _sample_mesh_surface(v, f, 1000, 7 + s) - c; w, U = np.linalg.eigh(np.cov(pts.T)); ax, od = np.zeros(3), 0
    if n in SYM:
        if SYM[n] == 'half': ax, od = U[:, 0], 2
        else: k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); ax, od = U[:, k], 360
    H.append(dict(mesh=(v, f), anchor=c, axis=ax, order=od, U=U))
C = [budget_mesh(f'{MD}/{n}.glb', 4096, 4096) for n in names]
axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]
seeds = []
for k in range(10):
    REG = [T3._register_object_body(C[s], H[s]['mesh'], H[s]['anchor'], 1_000_003 * EP + 101 * s + 7919 * k) for s in range(B)]
    ach = trk[:, None].copy(); ref = gt[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    ach = T3._align_registered_scene(ach, ref, axes)
    pos = np.linalg.norm(ach[:, 0, :, :3] - ref[:, 0, :, :3], axis=-1)                    # (T, B) m
    ori = T3._symmetry_orientation_errors(ach, ref, axes, orders)[:, 0]                 # (T, B) rad
    rv = [(Rot.from_quat(ref[:, 0, s, 3:]).inv() * Rot.from_quat(ach[:, 0, s, 3:])).as_rotvec() for s in range(B)]  # body-frame error
    p, o = pos.mean(0), ori.mean(0)
    seeds.append(dict(p=p, o=o, sp=bool(p.mean() <= 0.1 and o.mean() <= 0.5), mp_obj=(p < 0.03) & (o < np.deg2rad(30)), pos=pos, ori=ori, rv=rv))
def ctype(e):
    srt = np.sort(e)[::-1]; n = max(1, int(np.floor(0.25 * len(e))))
    return 'SPAN' if srt[:n].sum() > 0.5 * e.sum() else 'STEADY'
res = dict(episode=EP, objects=names, frames=int(T), SP_pass_rate=float(np.mean([q['sp'] for q in seeds])),
           MP_pass_rate=float(np.mean([q['mp_obj'].all() for q in seeds])),
           SP_mean_p_cm=round(100 * float(np.mean([q['p'].mean() for q in seeds])), 2), SP_mean_o_rad=round(float(np.mean([q['o'].mean() for q in seeds])), 3), per_object={})
s0 = seeds[0]
for s, n in enumerate(names):
    d = dict(p_cm=round(100 * float(np.mean([q['p'][s] for q in seeds])), 2), o_deg=round(float(np.degrees(np.mean([q['o'][s] for q in seeds]))), 1),
             MP_obj_pass_rate=float(np.mean([q['mp_obj'][s] for q in seeds])),
             p_cm_frame0=round(100 * float(s0['pos'][0, s]), 2), o_deg_frame0=round(float(np.degrees(s0['ori'][0, s])), 1),
             p_cm_p90=round(100 * float(np.percentile(s0['pos'][:, s], 90)), 2), o_deg_p90=round(float(np.degrees(np.percentile(s0['ori'][:, s], 90))), 1))
    if d['MP_obj_pass_rate'] < 0.5:
        po, oo = s0['pos'][:, s], s0['ori'][:, s]
        d['dominant'] = 'position' if po.mean() / 0.03 >= oo.mean() / np.deg2rad(30) else 'orientation'
        flipfrac = float((oo > np.deg2rad(135)).mean()); d['flip_frac'] = round(flipfrac, 3)
        d['ori_type'] = 'FLIP' if flipfrac >= 0.2 else ctype(oo); d['pos_type'] = ctype(po)
        rv = s0['rv'][s]; big = np.linalg.norm(rv, axis=1) > np.deg2rad(15)
        if big.any():
            u = rv[big] / np.linalg.norm(rv[big], axis=1, keepdims=True); M = u.T @ u; ev, EV = np.linalg.eigh(M); a_ = EV[:, -1]
            cos = np.abs(H[s]['U'].T @ a_); j = int(np.argmax(cos))
            d['err_axis'] = dict(principal=['thin(min)', 'mid', 'long(max)'][j], angle_deg=round(float(np.degrees(np.arccos(min(1, cos[j])))), 1),
                                 median_err_deg=round(float(np.degrees(np.median(np.linalg.norm(rv[big], axis=1)))), 1), frames=int(big.sum()))
    d['per_seed'] = [dict(p_cm=round(100 * float(q['p'][s]), 2), o_deg=round(float(np.degrees(q['o'][s])), 1), mp=bool(q['mp_obj'][s])) for q in seeds]
    res['per_object'][n] = d
json.dump(res, open(OUT, 'w'), indent=1); np.savez_compressed(OUT.replace('.json', '_pf.npz'), pos=s0['pos'], ori=s0['ori'], names=np.array(names))
print(json.dumps({k: v for k, v in res.items() if k != 'per_object'}), json.dumps(res['per_object']))
