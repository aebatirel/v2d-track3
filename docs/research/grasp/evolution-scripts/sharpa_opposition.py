# Feix-style (not their exact metric) opposition analysis of the Sharpa Wave right hand, from the URDF only.
# usage: python -I sharpa_opposition.py URDF HANDS_NPZ OUT_JSON
# - segment lengths (robot) and the demonstrator's MANO keypoint segment lengths (human, our perception, median)
# - pad-to-pad opposition volume thumb vs each finger, pad-to-side (lateral pinch) volume thumb pad vs index radial
#   side of the middle phalanx, in a 5 mm voxel grid, opposed normals (dot < -0.8)
import sys, json, xml.etree.ElementTree as ET
import numpy as np

rng = np.random.default_rng(0)
U, H, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
root = ET.parse(U).getroot()
J = {}
for j in root.findall('joint'):
    o = j.find('origin'); l = j.find('limit')
    xyz = np.array([float(v) for v in (o.get('xyz') if o is not None else '0 0 0').split()])
    rpy = np.array([float(v) for v in (o.get('rpy') if o is not None else '0 0 0').split()])
    J[j.find('child').get('link')] = dict(name=j.get('name'), type=j.get('type'), parent=j.find('parent').get('link'),
        xyz=xyz, rpy=rpy, lim=(float(l.get('lower')), float(l.get('upper'))) if l is not None else None)

def rpy_m(r, p, y):
    cr, sr, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    return np.array([[cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr], [sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr], [-sp, cp*sr, cp*cr]])

def chain(link):
    c = []
    while link in J:
        c.append(link); link = J[link]['parent']
    return c[::-1]

def fk(link, q):  # q: dict joint name -> array (N,) ; returns (N,4,4)
    c = chain(link)
    N = len(next(iter(q.values())))
    T = np.tile(np.eye(4), (N, 1, 1))
    for ln in c:
        jd = J[ln]
        To = np.eye(4); To[:3, :3] = rpy_m(*jd['rpy']); To[:3, 3] = jd['xyz']
        T = T @ To
        if jd['type'] == 'revolute':
            a = q.get(jd['name'], np.zeros(N))
            R = np.tile(np.eye(4), (N, 1, 1))
            R[:, 0, 0] = np.cos(a); R[:, 0, 1] = -np.sin(a); R[:, 1, 0] = np.sin(a); R[:, 1, 1] = np.cos(a)
            T = T @ R
    return T

def joints_of(link):
    return [J[l]['name'] for l in chain(link) if J[l]['type'] == 'revolute']

def sample(link, n):
    q = {}
    for l in chain(link):
        if J[l]['type'] == 'revolute':
            lo, hi = J[l]['lim']; q[J[l]['name']] = rng.uniform(lo, hi, n)
    return q

import trimesh, os
MESHDIR = os.path.join(os.path.dirname(U), '..', '..', 'meshes', 'sharpawave', 'right_cvx')
PAD = {}
def pad_local(digit):
    # pad centre and normal in the elastomer frame: faces of the elastomer collision mesh whose normal points the way
    # the tip moves on distal flexion (palmar), area-weighted
    if digit in PAD: return PAD[digit]
    el = 'right_%s_elastomer' % digit
    m = trimesh.load(os.path.join(MESHDIR, 'thumb_elastomer.STL' if digit == 'thumb' else 'elastomer.STL'), force='mesh')
    qz = {jn: np.zeros(1) for jn in joints_of(el)}
    last = [jn for jn in joints_of(el) if jn.endswith('_IP') or jn.endswith('_DIP')][0]
    T0 = fk(el, qz)[0]; q2 = dict(qz); q2[last] = qz[last] + 1e-3
    tl = 'right_%s_fingertip' % digit
    d = (fk(tl, q2)[0, :3, 3] - fk(tl, qz)[0, :3, 3]); d /= np.linalg.norm(d)
    dl = T0[:3, :3].T @ d  # proxy palmar direction in the elastomer frame
    fn = m.face_normals; a = m.area_faces; c = m.triangles_center
    sel = (fn @ dl) > 0.5
    nrm = (fn[sel] * a[sel, None]).sum(0); nrm /= np.linalg.norm(nrm)
    cen = (c[sel] * a[sel, None]).sum(0) / a[sel].sum()
    # pad width: extent of the selected faces across the digit (perpendicular to nrm and to the digit long axis)
    axis = T0[:3, :3].T @ (fk(tl, qz)[0, :3, 3] - fk(el, qz)[0, :3, 3]); axis /= np.linalg.norm(axis) + 1e-12
    side = np.cross(nrm, axis); side /= np.linalg.norm(side) + 1e-12
    w = c[sel] @ side
    PAD[digit] = dict(c=cen, n=nrm, width_mm=float((w.max() - w.min()) * 1000), area_cm2=float(a[sel].sum() * 1e4),
                      proxy_dot=float(nrm @ dl))
    return PAD[digit]

def tip_and_normal(digit, n, eps=1e-3):
    el = 'right_%s_elastomer' % digit
    q = sample(el, n)
    T = fk(el, q)
    pl = pad_local(digit)
    p = T[:, :3, :3] @ pl['c'] + T[:, :3, 3]
    nrm = T[:, :3, :3] @ pl['n']
    return p, nrm, q

def vox(p, h=0.005):
    return np.floor(p / h).astype(np.int64)

def opposed_volume(pa, na, pb, nb, h=0.005, thr=-0.8):
    return {('dot<%.1f' % t): _ov(pa, na, pb, nb, h, t) for t in (-0.6, -0.7, -0.8, -0.9)}

def _ov(pa, na, pb, nb, h, thr):
    ka, kb = vox(pa, h), vox(pb, h)
    da, db = {}, {}
    for k, nv in zip(map(tuple, ka), na): da.setdefault(k, []).append(nv)
    for k, nv in zip(map(tuple, kb), nb): db.setdefault(k, []).append(nv)
    shared = set(da) & set(db)
    good = 0
    best = []
    for k in shared:
        A = np.array(da[k]); B = np.array(db[k])
        m = (A @ B.T).min()
        best.append(m)
        if m < thr: good += 1
    return dict(shared_voxels=len(shared), opposed_voxels=good, opposed_volume_cm3=good * (h * 100) ** 3,
                best_dot=float(min(best)) if best else None)

out = {}
# --- segment lengths, robot
seg = lambda l: float(np.linalg.norm(J[l]['xyz']))
tipoff = lambda d: float(np.linalg.norm(J['right_%s_fingertip' % d]['xyz']))
out['robot_cm'] = {
    'thumb_MC(CMC->MCP)': 100 * seg('right_thumb_MCP_VL'), 'thumb_PP': 100 * seg('right_thumb_DP'), 'thumb_DP(to tip)': 100 * tipoff('thumb'),
    'index_PP': 100 * seg('right_index_MP'), 'index_MP': 100 * seg('right_index_DP'), 'index_DP(to tip)': 100 * tipoff('index'),
}
r = out['robot_cm']
r['thumb_total'] = r['thumb_MC(CMC->MCP)'] + r['thumb_PP'] + r['thumb_DP(to tip)']
r['index_digit_total(MCP->tip)'] = r['index_PP'] + r['index_MP'] + r['index_DP(to tip)']
q0 = {jn: np.zeros(1) for jn in [J[l]['name'] for l in J if J[l]['type'] == 'revolute']}
P = lambda l: fk(l, q0)[0, :3, 3]
r['thumbCMC_to_indexMCP'] = 100 * float(np.linalg.norm(P('right_thumb_CMC_VL') - P('right_index_MCP_VL')))
r['indexMCP_to_pinkyMCP(width)'] = 100 * float(np.linalg.norm(P('right_index_MCP_VL') - P('right_pinky_MCP_VL')))
r['ratio_thumb_total/index_digit'] = r['thumb_total'] / r['index_digit_total(MCP->tip)']

# --- human (MANO keypoints of the demonstrator, our perception; OpenPose order)
d = np.load(H, allow_pickle=False)
hum = {}
for side in ('right', 'left'):
    j = d['joints_%s' % side]; ok = d['valid_%s' % side] & d['measured_%s' % side]
    if ok.sum() < 10: continue
    j = j[ok]
    L = lambda a, b: float(np.median(np.linalg.norm(j[:, a] - j[:, b], axis=1)) * 100)
    h = {'thumb_MC(CMC->MCP)': L(1, 2), 'thumb_PP': L(2, 3), 'thumb_DP(to tip)': L(3, 4),
         'index_PP': L(5, 6), 'index_MP': L(6, 7), 'index_DP(to tip)': L(7, 8),
         'thumbCMC_to_indexMCP': L(1, 5), 'indexMCP_to_pinkyMCP(width)': L(5, 17), 'n_frames': int(ok.sum())}
    h['thumb_total'] = h['thumb_MC(CMC->MCP)'] + h['thumb_PP'] + h['thumb_DP(to tip)']
    h['index_digit_total(MCP->tip)'] = h['index_PP'] + h['index_MP'] + h['index_DP(to tip)']
    h['ratio_thumb_total/index_digit'] = h['thumb_total'] / h['index_digit_total(MCP->tip)']
    hum[side] = h
out['human_mano_cm'] = hum

# --- opposition volumes
N = 60000
pt, nt, qt = tip_and_normal('thumb', N)
opp = {}
for f in ('index', 'middle', 'ring', 'pinky'):
    pf, nf, _ = tip_and_normal(f, 30000)
    opp['pad_to_pad_thumb_%s' % f] = opposed_volume(pt, nt, pf, nf)
# pad-to-side: thumb pad vs the radial side of the index middle phalanx (MP collision-mesh faces facing the thumb)
mpm = trimesh.load(os.path.join(MESHDIR, 'right_MP.STL'), force='mesh')
qz = {jn: np.zeros(1) for jn in joints_of('right_index_MP')}
Tm0 = fk('right_index_MP', qz)[0]
ax = Tm0[:3, :3].T @ (fk('right_index_DP', qz)[0, :3, 3] - Tm0[:3, 3]); ax /= np.linalg.norm(ax)
toward_thumb = P('right_thumb_CMC_VL') - P('right_index_MCP_VL')
rl = Tm0[:3, :3].T @ toward_thumb; rl -= ax * (rl @ ax); rl /= np.linalg.norm(rl)
fn, ar, ce = mpm.face_normals, mpm.area_faces, mpm.triangles_center
sel = (fn @ rl) > 0.7
side_n = (fn[sel] * ar[sel, None]).sum(0); side_n /= np.linalg.norm(side_n)
side_c = ce[sel]  # keep all selected face centres as candidate contact points
n = 30000
q = sample('right_index_MP', n)
Tm = fk('right_index_MP', q)
k = rng.integers(0, len(side_c), n)
pm = np.einsum('nij,nj->ni', Tm[:, :3, :3], side_c[k]) + Tm[:, :3, 3]
nr = Tm[:, :3, :3] @ side_n
out['index_MP_radial_side'] = dict(faces=int(sel.sum()), area_cm2=float(ar[sel].sum() * 1e4))
opp['pad_to_side_thumb_indexMP_radial'] = opposed_volume(pt, nt, pm, nr)
opp['note'] = 'volumes of 5 mm voxels where a thumb-pad sample and a finger-surface sample coexist with normals opposed (dot < -0.8); uniform joint sampling within URDF limits; no collision check'
out['opposition'] = opp
out['pads'] = {k: dict(width_mm=v['width_mm'], area_cm2=v['area_cm2'], normal_vs_flexion_proxy_dot=v['proxy_dot']) for k, v in PAD.items()}
# thumb opposition reach (Kapandji-like): min tip-tip distance with dot < -0.8 among samples
reach = {}
for f in ('index', 'middle', 'ring', 'pinky'):
    pf, nf, _ = tip_and_normal(f, 20000)
    idx = rng.choice(len(pt), 20000, replace=False)
    A, An = pt[idx], nt[idx]
    from scipy.spatial import cKDTree
    tr = cKDTree(pf)
    dd, ii = tr.query(A, k=8)
    best = np.inf
    for kk in range(8):
        ok = (np.einsum('ij,ij->i', An, nf[ii[:, kk]]) < -0.8)
        if ok.any(): best = min(best, dd[ok, kk].min())
    reach['thumb_tip_to_%s_tip_min_mm_opposed' % f] = float(best * 1000)
out['opposition_reach'] = reach
json.dump(out, open(OUT, 'w'), indent=1)
print(json.dumps(out, indent=1))
