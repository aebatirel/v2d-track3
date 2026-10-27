"""Tables for README.md from the part-4 outputs (run_part4.sh): f0/, meshswap_seeds/, regflip/reg_flip.json, sens3/.
Usage: python -I summarise_part4.py SCORER_DIR > part4_tables.md
Registration distances are 'symmetric': cups ignore any spin about the scan's symmetry axis (only the axis tilt counts),
the lid ignores a 180 deg turn about its normal; D = R1 R2^T is the change of the scored body frame (scan frame).
"""
import glob, json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
D = sys.argv[1]
CUPS = ('blue_cup', 'beige_cup')


def symdist(q1, q2, obj, ax):
    Dm = Rot.from_quat(q1).as_matrix() @ Rot.from_quat(q2).as_matrix().T
    if obj in CUPS:
        return float(np.degrees(np.arccos(np.clip((Dm @ ax) @ ax, -1, 1))))
    ang = float(np.degrees(Rot.from_matrix(Dm).magnitude()))
    if obj == 'white_pot_lid':
        alt = Dm @ Rot.from_rotvec(np.pi * ax).as_matrix()
        ang = min(ang, float(np.degrees(Rot.from_matrix(alt).magnitude())))
    return ang


out = []
P = print
# ---- f0
rows = []
for f in sorted(glob.glob(f'{D}/f0/ep*.json')):
    r = json.load(open(f)); v = r['variants']
    b, x = v['base']['sim'], v['f0ref']['sim']
    rows.append((r['episode'], os.path.basename(f)[:-5].split('_')[1], r['objects'], b, x))
if rows:
    P('### f0: rollout frame 0 replaced by its reference frame 0 (sim trajectory, registered vs public mocap)\n')
    P('| ep | rollout | objects | AUC base | AUC f0ref | dAUC | per-object dAUC | SP/MP base -> f0ref |')
    P('|---|---|---|---|---|---|---|---|')
    for ep, rr, objs, b, x in sorted(rows, key=lambda t: (t[0], t[1])):
        po = ', '.join(f"{n} {x['per_obj_AUC'][n] - b['per_obj_AUC'][n]:+.3f}" for n in objs)
        P(f"| {ep} | {rr} | {' + '.join(objs)} | {b['AUC']:.4f} | {x['AUC']:.4f} | {x['AUC'] - b['AUC']:+.4f} | {po} | "
          f"{b['SP_SR']:.0f}/{b['MP_SR']:.0f} -> {x['SP_SR']:.0f}/{x['MP_SR']:.0f} |")
    d = [x['AUC'] - b['AUC'] for *_, b, x in rows]
    P(f'\nmean dAUC {np.mean(d):+.4f}, mean |dAUC| {np.mean(np.abs(d)):.4f}, n = {len(d)}\n')
# ---- meshswap
ms = {}
for f in sorted(glob.glob(f'{D}/meshswap_seeds/ep21_*.json')):
    _, r, lib = os.path.basename(f)[:-5].split('_', 2)
    ms[(r, lib)] = json.load(open(f))
if ms:
    P('### Pitcher swap (library_v3 -> library_v3p) on the ep21 twin, same rollouts, per scoring variant\n')
    rs = sorted({k[0] for k in ms})
    var = list(next(iter(ms.values()))['variants'])
    hdr = ' | '.join(f'{r} v3 | {r} v3p | {r} d' for r in rs)
    P(f'| variant | {hdr} | mean d | pitcher reg. rot v3 / v3p (deg) |')
    P('|---|' + '---|' * (3 * len(rs) + 2))
    allds = {}
    for vn in var:
        cells, ds = [], []
        for r in rs:
            if (r, 'library_v3') in ms and (r, 'library_v3p') in ms and vn in ms[(r, 'library_v3p')]['variants']:
                a3 = ms[(r, 'library_v3')]['variants'][vn]['sim']['AUC']; ap = ms[(r, 'library_v3p')]['variants'][vn]['sim']['AUC']
                cells += [f'{a3:.4f}', f'{ap:.4f}', f'{ap - a3:+.4f}']; ds.append(ap - a3)
            else:
                cells += ['', '', '']
        g = lambda lib: next(iter(m['variants'][vn]['registration']['water_pitcher']['rot_deg'] for (r, l), m in ms.items()
                                  if l == lib and vn in m['variants']))
        allds[vn] = ds
        P(f"| {vn} | {' | '.join(cells)} | {np.mean(ds):+.4f} | {g('library_v3'):.2f} / {g('library_v3p'):.2f} |")
    seeds = [d for vn in var if vn.startswith('seed') for d in allds[vn]]
    P(f'\npublic-seed draws (seed0..4, both rollouts): swap d mean {np.mean(seeds):+.4f}, min {min(seeds):+.4f}, '
      f'max {max(seeds):+.4f}, n = {len(seeds)}\n')
    # registration change of the pitcher between the twin's seed and Kaggle's eval-20 seed
    for lib in ('library_v3', 'library_v3p'):
        m = next(m for (r, l), m in ms.items() if l == lib)
        q0 = m['variants']['seed0']['registration']['water_pitcher']['quat_xyzw']
        for vn in var:
            q = m['variants'][vn]['registration']['water_pitcher']['quat_xyzw']
            P(f"- {lib} pitcher: {vn} vs seed0 body-frame change {symdist(q, q0, 'water_pitcher', None):.2f} deg, "
              f"cand anchor {m['variants'][vn]['registration']['water_pitcher']['cand_anchor_cm']} cm")
    P()
# ---- regflip
f = f'{D}/regflip/reg_flip.json'
if os.path.exists(f):
    rf = json.load(open(f))
    sys.path.insert(0, os.environ.get('KIT', ''))
    import trimesh
    T3 = os.environ['T3']
    from v2dlb.object_mesh import _surface_moments
    from v2dlb.mesh_common import _sample_mesh_surface
    AX = {}

    def axis(n):
        if n not in AX:
            q = f'{T3}/mesh/{n}/{n}.glb'
            m = trimesh.load(q if os.path.exists(q) else f'{T3}/mesh/{n}/{n}_visual.glb', force='mesh')
            v, fc = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
            c, _ = _surface_moments(v, fc)
            ps = _sample_mesh_surface(v, fc, 1000, 7) - c
            w, U = np.linalg.eigh(np.cov(ps.T))
            AX[n] = U[:, 0] if n == 'white_pot_lid' else U[:, int(np.argmax([abs(w[i] - np.mean(np.delete(w, i)))
                                                                              for i in range(3)]))]
        return AX[n]
    groups = {}
    for r in rf['results']:
        groups.setdefault((r['lib'], r['obj']), []).append(r)
    P('### Registration of the submitted meshes at Kaggle\'s eval seeds (GT-free; host = public scan)\n')
    P('Mode = the registration with most neighbours within 5 deg over all seeds and hosts. "dev" = symmetric body-frame '
      'distance from the mode; "ident" = symmetric distance from identity (a correct registration of a mesh built in '
      'the scan frame is a few degrees; > 90 = flip).\n')
    P('| mesh | host faces | eval seeds (ep/slot) | eval dev from mode (deg) | eval ident (deg) | public seeds | public dev max | public flips | eval flips |')
    P('|---|---|---|---|---|---|---|---|---|')
    for (lib, obj), L in groups.items():
        ax = axis(obj)
        Q = [r['quat_xyzw'] for r in L]
        nb = [sum(symdist(q, q2, obj, ax) < 5 for q2 in Q) for q in Q]
        mode = Q[int(np.argmax(nb))]
        for h in rf['faces']:
            hk = h or 'full'
            E = [r for r in L if r['host_faces'] == hk and r['kind'] == 'eval']
            Pb = [r for r in L if r['host_faces'] == hk and r['kind'] == 'public']
            ide = lambda r: symdist(r['quat_xyzw'], [0, 0, 0, 1], obj, ax)
            dev = lambda r: symdist(r['quat_xyzw'], mode, obj, ax)
            P(f"| {lib}/{obj} | {hk} | {', '.join(str(r['ep']) + '/' + str(r['slot']) for r in E)} | "
              f"{', '.join(f'{dev(r):.1f}' for r in E)} | {', '.join(f'{ide(r):.1f}' for r in E)} | {len(Pb)} | "
              f"{max([dev(r) for r in Pb] or [0]):.1f} | {sum(ide(r) > 90 for r in Pb)} | {sum(ide(r) > 90 for r in E)} |")
    P()
# ---- sens3
if glob.glob(f'{D}/sens3/ep*.json'):
    P('### Host-scan resolution (welded, then decimated; registration only)\n')
    sys.stdout.flush()
    os.system(f'{sys.executable} -I {D}/summarise.py {D}/sens3 perception')
# ---- regseeds (part 5): seed spread at the eval-20 pitcher seed and the 29 following seeds
fs = sorted(glob.glob(f'{D}/regseeds/*.json'))
if fs:
    P('\n### Pitcher registration over 30 seeds (from Kaggle\'s eval-20 seed 20000161), host = public scan (GT-free)\n')
    P('Distance = body-frame rotation from identity (our meshes are built in the scan frame). Yaw is about the scan z.\n')
    P('| mesh | host faces | yaw min / median / max (deg) | rot from identity median / max (deg) | seeds > 5 deg from the median pose | eval seed yaw / rot |')
    P('|---|---|---|---|---|---|')
    for f in fs:
        r = json.load(open(f)); lib = os.path.basename(f)[:-5].replace(f"{r['obj']}_", '')
        for h in r['faces']:
            L = [x for x in r['runs'] if x['host_faces'] == (h or 'full')]
            yaw = np.array([x['yaw'] for x in L]); rot = np.array([x['rot_deg'] for x in L])
            Qs = [x['quat_xyzw'] for x in L]
            med = Rot.from_quat(Qs).mean().as_quat()
            far = sum(symdist(q, med, r['obj'], None) > 5 for q in Qs)
            e = next(x for x in L if x['seed'] == r['base_seed'])
            P(f"| {lib}/{r['obj']} | {h or 'full'} | {yaw.min():.1f} / {np.median(yaw):.1f} / {yaw.max():.1f} | "
              f"{np.median(rot):.1f} / {rot.max():.1f} | {far} of {len(L)} | {e['yaw']:.1f} / {e['rot_deg']:.1f} |")
# ---- reghosts (part 6): fixed eval seed, many host resolutions
fs = sorted(glob.glob(f'{D}/reghosts/*.json'))
if fs:
    P('\n### Fixed Kaggle eval seed, host = public scan welded + decimated to N faces (GT-free)\n')
    P('Cell = body-frame rotation from identity (deg); **bold** = flip (> 90 deg).\n')
    faces = json.load(open(fs[0]))['faces']
    P('| mesh | eval seed | ' + ' | '.join(str(h or 'full') for h in faces) + ' |')
    P('|---|---|' + '---|' * len(faces))
    for f in fs:
        r = json.load(open(f)); lib = r['glb'].split('/')[-2]
        cells = []
        for h in faces:
            x = next(x for x in r['runs'] if x['host_faces'] == (h or 'full'))
            cells.append(f"**{x['rot_deg']:.0f}**" if x['rot_deg'] > 90 else f"{x['rot_deg']:.1f}")
        P(f"| {lib}/{r['obj']} | {r['base_seed']} | " + ' | '.join(cells) + ' |')
