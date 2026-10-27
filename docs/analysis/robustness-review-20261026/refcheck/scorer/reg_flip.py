"""Registration-only stress test: does the kit's _register_object_body flip our SUBMITTED meshes when the host scan is
decimated (the kit decodes the host geometry with a 16 MB limit, so the hidden scans cannot be the ~100k-face public
scans), at the seeds Kaggle will actually use for the eval episodes?

For each library mesh (budget_mesh 4096/4096, as packed) and each host variant (public scan at full resolution, or
welded, then decimated with fast_simplification to N faces), register with the kit function at:
  - the EVAL seeds 1_000_003*ep + 101*slot for every eval (episode, slot) holding that object (roster in the kit);
  - the public-twin seeds for every public episode holding it;
and report the registration rotation (deg) and the tilt of the scan's distinct principal axis under it (for cups the
symmetry axis: a spin about it is harmless, so a cup 'flips' only if the axis tilts > 90 deg). Our library meshes are built in roughly the scan's frame, so a correct
registration is a few degrees; > 90 deg is a flip (the scored body frame is then turned by ~180 deg).
No poses and no ground truth are used. Usage: python -I reg_flip.py T3 KIT REPO OUT.json [faces ...]
"""
import json, os, sys, time
import numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot
T3, KIT, REPO, OUT = sys.argv[1:5]
FACES = [int(x) for x in sys.argv[5:]] or [0, 50000, 20000, 4096]
sys.path.insert(0, KIT)
from v2dlb import track3_pose as T
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
import fast_simplification
import pyarrow.parquet as pq

roster = json.load(open(f'{KIT}/data/track_3_evaluation_objects.json'))['episodes']
PUB = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
pub_slots = {}
for e in PUB:
    names = [str(o['name']) for o in pq.read_table(f'{T3}/ep{e}.parquet').to_pandas()['observation.objects'].iloc[0]]
    for s, n in enumerate(names):
        pub_slots.setdefault(n, []).append((e, s))
MESHES = [('library_v3', n) for n in ['beige_cup', 'blue_cup', 'mini_dust_pan', 'mini_sweeper', 'plastic_dish_rack',
                                       'water_pitcher', 'white_pot', 'white_pot_lid', 'wooden_piece_1', 'wooden_piece_2']]
MESHES += [('library_v2', 'mini_sweeper'), ('library_v3p', 'water_pitcher'), ('library_v3x', 'beige_cup')]


def scan(n):
    q = f'{T3}/mesh/{n}/{n}.glb'
    q = q if os.path.exists(q) else f'{T3}/mesh/{n}/{n}_visual.glb'
    m = trimesh.load(q, force='mesh')
    return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


out = {'faces': FACES, 'results': []}
AX = {}                                                      # the scan's distinct principal axis (cups: symmetry axis)
for _, n in MESHES:
    if n not in AX:
        v, f = scan(n); c, _ = _surface_moments(v, f)
        from v2dlb.mesh_common import _sample_mesh_surface
        ps = _sample_mesh_surface(v, f, 1000, 7) - c
        w, U = np.linalg.eigh(np.cov(ps.T))
        AX[n] = U[:, int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))]
hosts = {}
for lib, n in MESHES:
    cand = budget_mesh(f'{REPO}/meshes/{lib}/{n}.glb', 4096, 4096)
    if n not in hosts:
        v, f = scan(n); anchor, _ = _surface_moments(v, f)
        hosts[n] = {0: (v, f, anchor)}
        for k in FACES:
            if k:
                w = trimesh.Trimesh(v, f, process=True)              # weld first (as budget_mesh); scans are soups
                dv, df = fast_simplification.simplify(np.asarray(w.vertices, np.float64), np.asarray(w.faces, np.int64),
                                                      target_count=k)
                hosts[n][k] = (np.asarray(dv, np.float64), np.asarray(df, np.int64), anchor)
    seeds = [('eval', int(e), s) for e, objs in roster.items() for s, o in enumerate(objs) if o == n]
    seeds += [('public', e, s) for e, s in pub_slots.get(n, [])]
    for k in FACES:
        v, f, anchor = hosts[n][k]
        for kind, e, s in seeds:
            t0 = time.time()
            ca, R = T._register_object_body(cand, (v, f), anchor, 1_000_003 * e + 101 * s)
            ang = float(np.degrees(Rot.from_matrix(R).magnitude()))
            tilt = float(np.degrees(np.arccos(np.clip(abs(R @ AX[n]) @ AX[n] if False else (R @ AX[n]) @ AX[n], -1, 1))))
            # cups: a spin about the symmetry axis is harmless (scored modulo spin); only the axis tilt matters
            flip = (tilt > 90) if n in ('blue_cup', 'beige_cup') else (ang > 90)
            out['results'].append(dict(lib=lib, obj=n, host_faces=k or 'full', kind=kind, ep=e, slot=s,
                                       rot_deg=round(ang, 2), axis_tilt_deg=round(tilt, 2), flip=flip,
                                       anchor_shift_cm=round(float(np.linalg.norm(ca - anchor) * 100), 2)))
            print(lib, n, k or 'full', kind, e, s, round(ang, 2), round(tilt, 2), f'{time.time() - t0:.1f}s', flush=True)
json.dump(out, open(OUT, 'w'), indent=1)
# summary: flips per (mesh, host)
summ = {}
for r in out['results']:
    key = f"{r['lib']}/{r['obj']} host={r['host_faces']}"
    d = summ.setdefault(key, {'eval_flips': [], 'public_flips': [], 'n_eval': 0, 'n_public': 0})
    d[f"n_{r['kind']}"] += 1
    if r['flip']:
        d[f"{r['kind']}_flips"].append(r['ep'])
out['summary'] = summ
json.dump(out, open(OUT, 'w'), indent=1)
for k, d in summ.items():
    print(k, d)
