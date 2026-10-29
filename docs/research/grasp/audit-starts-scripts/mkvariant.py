"""Write a modified copy of a stored grasp-lock reference into a local reference tree for CPU zero-action replays
(no ground truth). The URDF paths are re-pointed to our local copies of the run's own assets (identical md5 to the
box's). Modifications (comma list):
  nohands            both wrists parked 0.6 m above their frame-0 position for the whole episode (objects alone)
  shift:OBJ:dx:dy:dz object OBJ moved by (dx,dy,dz) m in the world for frames < its first hold start + 10 (then the
                     original path; the hand reference is unchanged)
  depen:OBJ:HOST     OBJ moved straight up until its hull samples are out of HOST's hulls (same frame window)
  frames:N           truncate nothing; only recorded for the log
Usage: mkvariant.py EP REFKIND OUTNAME MODS"""
import sys, os, json, glob, shutil, numpy as np, pyarrow as pa, pyarrow.parquet as pq, trimesh
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *

ep, kind, name, mods = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
src = glob.glob(f'{run_dir(ep)}/refs/glockt/ep{ep}{".r1" if "r1" in kind else ""}/processed/*/*/ref_gl_ilc.parquet')[0]
hive = os.path.relpath(os.path.dirname(src), os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(src)))))
tree = f'{W}/sim/ep{ep}/{name}'; os.makedirs(f'{tree}/{hive}', exist_ok=True)
stage = glob.glob(f'{run_dir(ep)}/refs/glock/ep{ep}/reconstructed_stage')[0]
if not os.path.isdir(f'{tree}/reconstructed_stage'):
    shutil.copytree(stage, f'{tree}/reconstructed_stage')
t = pq.read_table(src); names = t.column('object_body_names')[0].as_py(); B = len(names)
T = len(t.column('robot_left_wrist_position')[0].as_py())
urdfs = []
for u in t.column('object_urdf_paths')[0].as_py():
    loc = f'{run_dir(ep)}/refs/sf/ep{ep}/assets/urdf/{os.path.basename(u)}'
    assert os.path.exists(loc), loc
    urdfs.append(loc)
t = t.set_column(t.column_names.index('object_urdf_paths'), 'object_urdf_paths', pa.array([urdfs], type=t.schema.field('object_urdf_paths').type))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
OQw = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)
gl = json.load(open(glob.glob(f'{run_dir(ep)}/refs/glock/ep{ep}/processed/*/*/{kind.replace("_ilc", "")}_grasp_lock.json')[0]))
h0 = {n: min([p['hold_from'] for p in gl['phases'] if p['object'] == n], default=T) for n in names}
log = {}
for m in mods.split(','):
    f = m.split(':')
    if f[0] == 'nohands':
        for s in ('left', 'right'):
            c = f'robot_{s}_wrist_position'; v = np.array(t.column(c)[0].as_py(), float).reshape(T, 3)
            v[:] = v[0] + np.array([0, 0, 0.6])
            t = t.set_column(t.column_names.index(c), c, pa.array([v.tolist()], type=t.schema.field(c).type))
        log['nohands'] = True
    elif f[0] == 'urdf':
        urdfs[names.index(f[1])] = f[2]
        t = t.set_column(t.column_names.index('object_urdf_paths'), 'object_urdf_paths', pa.array([urdfs], type=t.schema.field('object_urdf_paths').type))
        log[f'urdf:{f[1]}'] = f[2]
    elif f[0] == 'setpose':                     # setpose:OBJ:JSONFILE:KEY  (pose from depen6.py output)
        o = f[1]; j = names.index(o); end = min(T, h0[o] + 10); pz = json.load(open(f[2]))[f[3]]['pose']
        OP[:end, j] = pz[:3]; qq = np.array(pz[3:7]); OQw[:end, j] = qq[[3, 0, 1, 2]]
        t = t.set_column(t.column_names.index('object_body_wxyz'), 'object_body_wxyz', pa.array([OQw.tolist()], type=t.schema.field('object_body_wxyz').type))
        log[m] = dict(frames=[0, int(end)], pose=pz)
    elif f[0] in ('shift', 'depen'):
        o = f[1]; j = names.index(o); end = min(T, h0[o] + 10)
        if f[0] == 'shift':
            dlt = np.array([float(x) for x in f[2:5]])
        else:
            host = f[2]; k = names.index(host); Ho = Hulls(hull_path(o)); Hh = Hulls(hull_path(host))
            HS = np.concatenate([trimesh.sample.sample_surface(h, 400, seed=i)[0] for i, h in enumerate(Ho.H)])
            qo = OQw[0, j][[1, 2, 3, 0]]; qh = OQw[0, k][[1, 2, 3, 0]]
            dz = 0.0
            while dz < 0.05:
                P = local_to_world(HS, OP[0, j] + [0, 0, dz], qo)
                dep, _ = Hh.depth(world_to_local(P, OP[0, k], qh))
                if dep.max() < 0.0005:
                    break
                dz += 0.0005
            dlt = np.array([0, 0, dz])
        OP[:end, j] += dlt; log[m] = dict(delta_mm=(1000 * dlt).round(1).tolist(), frames=[0, int(end)])
op = OP.tolist()
t = t.set_column(t.column_names.index('object_body_position'), 'object_body_position', pa.array([op], type=t.schema.field('object_body_position').type))
if 'object_root_position' in t.column_names:
    t = t.set_column(t.column_names.index('object_root_position'), 'object_root_position', pa.array([OP[:, 0].tolist()], type=t.schema.field('object_root_position').type))
out = f'{tree}/{hive}/ref_gl_ilc.parquet'; pq.write_table(t, out)
json.dump(dict(src=src, mods=mods, log=log, hold0=h0), open(f'{tree}/variant.json', 'w'), indent=1)
print(out, json.dumps(log))
