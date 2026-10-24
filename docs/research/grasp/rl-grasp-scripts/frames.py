"""Per-frame hand-object contact geometry for a body trace (tools/trace_rollout.py npz) or a reference parquet.
Usage: frames.py SRC OUT.jsonl --objs name=hulls.npz=mesh.glb ... [--every N] [--ref]
SRC = trace npz (simulated bodies) or, with --ref, a reference parquet (its robot link frames + object poses).
Per frame and object: pose metrics (lift, lowest-point height over the table, tilt, turn, slide), object-object
distance, and for every hand link within NEAR mm: exact distance, contact location in the plate's PCA frame, mesh face
(+axis3 / -axis3 / edge), world approach side (link above / below / beside the surface) and where on the link
(palmar pad / dorsal / radial / ulnar side). Plus joint angles of both hands and palm pose relative to each object."""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as R
from rlgrasp_lib import (TABLE_Z, ObjGeom, hand_points, revolute_joints, joint_angles, link_world, to_obj, rot_deg,
                         load_trace, load_ref, fingertip_offsets, urdf_path)
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser(); p.add_argument('src'); p.add_argument('out'); p.add_argument('--objs', nargs='+', required=True)
p.add_argument('--every', type=int, default=1); p.add_argument('--ref', action='store_true'); p.add_argument('--near_mm', type=float, default=8.0)
p.add_argument('--f0', type=int, default=0); p.add_argument('--f1', type=int, default=10 ** 6)
a = p.parse_args()
NEAR = a.near_mm / 1000
geo = {}
for s in a.objs:
    n, h, g = s.split('='); geo[n] = ObjGeom(h, g)
src = load_ref(a.src) if a.ref else load_trace(a.src)
T = src['T']; objpose = src['obj']; L = src['links']
SIDES = ('left', 'right'); hp = {s: hand_points(s, n=120) for s in SIDES}; js = {s: revolute_joints(s) for s in SIDES}
tips = {s: fingertip_offsets(s) for s in SIDES}

# per-link local frames for 'where on the link': long axis, flexion axis (positive flexion), palmar = flex x long
linkinfo = {}
for s in SIDES:
    child_of = {}
    for name, par, ch, Ro, ax, lo, hi in js[s]:
        child_of.setdefault(par, []).append((name, ch, Ro, ax))
    root = ET.parse(urdf_path(s)).getroot()
    org = {j.get('name'): np.array([float(x) for x in j.find('origin').get('xyz').split()]) for j in root.findall('joint')}
    for ln in hp[s]:
        if ln.endswith('C_MC'):
            continue
        kids = [c for c in child_of.get(ln, []) if not c[0].endswith('_AA')]
        if kids:                            # flexion joint to the next link
            name, ch, Ro, ax = kids[0]; long_ = org[name]; flex = Ro.apply(ax)
            if np.linalg.norm(long_) < 1e-6:   # e.g. MCP_VL -> PP at the same origin: use the PP's own long axis
                long_ = Ro.apply(np.array([1.0, 0, 0]))
        else:                               # distal link: same axes as its own joint (rotation about local z), long = x
            long_ = np.array([1.0, 0, 0]); flex = np.array([0, 0, 1.0])
        long_ = long_ / np.linalg.norm(long_); flex = flex - (flex @ long_) * long_; flex /= np.linalg.norm(flex)
        palmar = np.cross(flex, long_)
        linkinfo[ln] = (long_, flex, palmar)
# palm normal: direction the index fingertip moves when the index MCP flexes, in the C_MC frame
for s in SIDES:
    name, par, ch, Ro, ax, lo, hi = [j for j in js[s] if j[0] == f'{s}_index_MCP_FE'][0]
    pp_long = Ro.apply(np.array([1.0, 0, 0]))   # the PP x axis (AA joint rotates only about the PP's own axes)
    linkinfo[f'{s}_hand_C_MC'] = (pp_long, Ro.apply(ax), np.cross(Ro.apply(ax), pp_long) / np.linalg.norm(np.cross(Ro.apply(ax), pp_long)))
pc_palm = {s: hp[s][f'{s}_hand_C_MC'].mean(0) for s in SIDES}


def region(name, pc):
    x1 = 100 * pc[0]
    if name == 'mini_dust_pan':
        return 'ring' if x1 < -4 else ('neck' if x1 < -2 else 'pan')
    if name == 'mini_sweeper':
        return 'ring' if x1 < -3 else ('neck' if x1 < 1 else 'head')
    return 'body'


def on_link(s, ln, xl, pose_l, thumb_world):
    """Where the contact sits on the link: palmar / dorsal / radial / ulnar (fingers) from the link-local point."""
    long_, flex, palmar = linkinfo[ln]
    if ln.endswith('_VL'):
        return 'knuckle'
    if ln.endswith('C_MC'):
        v = xl - pc_palm[s]; return 'palm-front' if v @ palmar > 0.0 else 'palm-back'
    v = xl - (xl @ long_) * long_
    cp, cf = v @ palmar, v @ flex
    if abs(cp) >= abs(cf):
        return 'pad' if cp > 0 else 'dorsal'
    if 'thumb' in ln:
        return 'side+' if cf > 0 else 'side-'
    fw = R.from_quat(pose_l[3:7]).apply(flex); tow = (thumb_world - pose_l[:3]) @ fw
    return 'radial' if (cf > 0) == (tow > 0) else 'ulnar'


fh = open(a.out, 'w')
names = list(geo)
p0 = {n: objpose[n][0] for n in names}
for f in range(max(0, a.f0), min(T, a.f1), a.every):
    rec = dict(f=f, obj={}, hands={})
    lp = {k: v[f] for k, v in L.items()}
    for s in SIDES:
        ja = joint_angles(lp, js[s])
        rec['hands'][s] = dict(joints={k.split('_', 1)[1]: round(v[0], 3) for k, v in ja.items()},
                               resid_max=round(max((v[1] for v in ja.values()), default=0), 3),
                               palm=[round(x, 4) for x in lp[f'{s}_hand_C_MC'][:3]],
                               palm_normal_world=[round(x, 3) for x in R.from_quat(lp[f'{s}_hand_C_MC'][3:7]).apply(linkinfo[f'{s}_hand_C_MC'][2])])
    for n in names:
        G = geo[n]; P = objpose[n][f]; Rw = R.from_quat(P[3:7])
        hv = Rw.apply(G.hullV) + P[:3]; zlow = hv[:, 2].min(); klow = hv[:, 2] < zlow + 0.002
        ax3 = Rw.apply(G.W[2]); ax1 = Rw.apply(G.W[0])
        o = dict(lift_cm=round(100 * (P[2] - p0[n][2]), 2), low_mm=round(1000 * (zlow - TABLE_Z), 1),
                 low_region=region(n, G.pca(to_obj(P, hv[klow].mean(0)))[0]), low_pca_cm=[round(100 * x, 1) for x in G.pca(to_obj(P, hv[klow].mean(0)))[0]],
                 tilt_deg=round(float(np.degrees(np.arccos(min(1, abs(ax3[2]))))), 1), ax3_z=round(float(ax3[2]), 3), ax1_z=round(float(ax1[2]), 3),
                 turn_deg=round(rot_deg(P[3:7], p0[n][3:7]), 1), slide_mm=round(1000 * float(np.linalg.norm(P[:2] - p0[n][:2])), 1),
                 pos=[round(x, 4) for x in P[:3]], quat=[round(x, 5) for x in P[3:7]], links={})
        # object-object distance
        others = [m for m in names if m != n]
        if others:
            m = others[0]; Pm = objpose[m][f]; Xm = to_obj(P, R.from_quat(Pm[3:7]).apply(geo[m].hullV) + Pm[:3])
            d, _ = G.lb(Xm); k = np.argsort(d)[:6]; de, cp = G.exact(Xm[k]); i = int(np.argmin(de))
            o['objobj_mm'] = round(1000 * float(de[i]), 1); o['objobj_region'] = region(n, G.pca(cp[i])[0])
        cand = []   # (side, link, local samples, candidate sample indices, object-frame points)
        for s in SIDES:
            for ln, Pl in hp[s].items():
                if ln not in lp:
                    continue
                X = to_obj(P, link_world(lp[ln], Pl))
                if np.linalg.norm(X.mean(0) - G.ctr) > G.radius + 0.08:
                    continue
                d, arg = G.lb(X)
                if d.min() > NEAR:
                    continue
                k = np.argsort(d)[:6]; cand.append((s, ln, Pl, k, X[k], arg[k], G.pca(X)))
        if cand:
            DE, CPS = G.exact(np.vstack([c[4] for c in cand]))
        off = 0
        for s, ln, Pl, k, Xk, ak, PX in cand:
            de, cp = DE[off:off + len(k)], CPS[off:off + len(k)]; off += len(k); i = int(np.argmin(de))
            if de[i] > NEAR:
                continue
            thumb_w = lp[f'{s}_thumb_DP'][:3]
            x, c = Xk[i], cp[i]; pc = G.pca(c)[0]; nrm, n3 = G.face(c)
            if de[i] > 1e-4:
                no = (x - c) / np.linalg.norm(x - c)
            else:   # penetrating: outward normal of the deepest piece plane
                E = G.pieces[ak[i]]['E']; no = E[int(np.argmax(x @ E[:, :3].T + E[:, 3])), :3]
            nw = Rw.apply(no)
            side_w = 'above' if nw[2] > 0.5 else ('below' if nw[2] < -0.5 else 'beside')
            o['links'][f'{s[0].upper()}:{ln.split("_", 1)[1]}'] = dict(
                d_mm=round(1000 * float(de[i]), 1), pca_cm=[round(100 * v, 1) for v in pc], region=region(n, pc),
                face='+' if n3[0] > 0.5 else ('-' if n3[0] < -0.5 else 'edge'), world=side_w, nz=round(float(nw[2]), 2),
                on_link=on_link(s, ln, Pl[k[i]], lp[ln], thumb_w), dir3=round(float(no @ G.W[2]), 2),
                cen=[round(100 * v, 1) for v in PX.mean(0)], a3=[round(100 * PX[:, 2].min(), 1), round(100 * PX[:, 2].max(), 1)])
        rec['obj'][n] = o
    fh.write(json.dumps(rec) + '\n'); fh.flush()
fh.close()
print('wrote', a.out)
