"""D1 no-flip gate for named objects of a pack (diagnostic [D], public scans as stand-ins): for every eval (episode, slot)
of each object in the kit roster, the kit's _register_object_body of the decoded packed payload against the public scan,
at the kit eval seed 1_000_003·ep + 101·slot and 6 more seeds (the same slot's kit seeds of eps ep+1..ep+3 and seeds
0..2). Rotation (deg), z tilt (deg) and anchor error (mm, scan surface centroid as anchor). Axially symmetric objects
(blue / beige cup) count a flip only on tilt > 90°; others on rotation > 90°.
REF_MODE=raw|budget (the scan raw, or through the kit's budget_mesh(4096, 4096)).
Usage: REF_MODE=.. OUT=x.json d1pairs.py KIT SCANROOT PACK OBJ[,OBJ...]"""
import sys, os, json, numpy as np, pandas as pd, trimesh
sys.path.insert(0, sys.argv[1])
from v2dlb import track3_pose as tp
from v2dlb.mesh_budget import budget_mesh
REF_MODE = os.environ.get('REF_MODE', 'raw')
kit, scanroot, pack, objs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(',')
AXIAL = {'blue_cup', 'beige_cup'}
eps = json.load(open(f'{kit}/data/track_3_evaluation_objects.json'))['episodes']
def ang(R): return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))
def tilt(R): return float(np.degrees(np.arccos(np.clip(R[2, 2], -1, 1))))
def scan(name):
    f = f'{scanroot}/{name}/{name}_visual.glb'
    f = f if os.path.isfile(f) else f'{scanroot}/{name}/{name}.glb'
    if REF_MODE == 'budget':
        v, fc = budget_mesh(f, 4096, 4096); return np.asarray(v, float), tp._mesh_faces(np.asarray(fc, float), len(v))
    m = trimesh.load(f, force='mesh', process=False)
    return np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
d = pd.read_parquet(pack, columns=['row_id', 'object_mesh_b64']).set_index('row_id')['object_mesh_b64']
res, allok = [], True
for name in objs:
    ref = scan(name); rc, _ = tp._surface_moments(*ref)
    unit = 1000.0 if np.ptp(ref[0], axis=0).max() < 5 else 1.0
    for ep, names in sorted(eps.items(), key=lambda x: int(x[0])):
        for slot, n in enumerate(names):
            if n != name: continue
            e = int(ep)
            cand = tp._decode_object_mesh(d[f'track_3/e{e:06d}/w000/f000000/o{slot}'])
            seeds = [('eval', 1_000_003 * e + 101 * slot)] + [(f'ep{e+k}', 1_000_003 * (e + k) + 101 * slot) for k in (1, 2, 3)] + [(f's{k}', k) for k in (0, 1, 2)]
            row = dict(object=name, ep=e, slot=slot, ref_mode=REF_MODE, seeds={})
            for sl, sd in seeds:
                ca, R = tp._register_object_body(cand, ref, rc, sd)
                row['seeds'][sl] = dict(seed=sd, rot=round(ang(R), 2), tilt=round(tilt(R), 2), anchor_mm=round(float(np.linalg.norm(ca - rc)) * unit, 2))
            flip = lambda v: v['tilt'] > 90 if name in AXIAL else v['rot'] > 90
            nf = sum(flip(v) for v in row['seeds'].values()); row['flips'] = nf; row['pass'] = nf == 0
            allok &= row['pass']; res.append(row)
            ev = row['seeds']['eval']
            print(f"{REF_MODE:6s} e{e:02d} o{slot} {name:18s} flips {nf}/{len(seeds)} | eval {ev['rot']:.1f}°/{ev['anchor_mm']:.1f}mm | max rot {max(v['rot'] for v in row['seeds'].values()):.1f}° | anchor {min(v['anchor_mm'] for v in row['seeds'].values()):.1f}-{max(v['anchor_mm'] for v in row['seeds'].values()):.1f}mm", flush=True)
json.dump(dict(pack=os.path.basename(os.path.dirname(pack)), ref_mode=REF_MODE, all_pass=allok, pairs=res), open(os.environ.get('OUT', '/dev/null'), 'w'), indent=1)
print('D1', 'PASS' if allok else 'FAIL', REF_MODE)
