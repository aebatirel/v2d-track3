"""verify_scorer test 7: the UNMODIFIED official metric files' score() on DataFrames packed by MY code (not the kit packer):
submission rows = world-0 rollout poses (xyzw) + budget_mesh payload on each object's first row; host solution = public
mocap (w-first -> xyzw) + host geometry payload built here. Two host encodings:
  soup64: the public scan as loaded (float64 soup; > 16 MB for 2 objects? -> limit raised for this test only),
  weld32: welded, float32 vertices / int32 faces (what a host might upload; must fit the official 16 MB limit unpatched).
Anchor / points / axis stand-ins as in vs_core.host. Usage: python -I t7_official.py EP RUN_SUBPATH LIB OUT.json"""
import base64, io, json, sys
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_scorer')
import numpy as np, pandas as pd, trimesh
from vs_core import *

ep, subp, lib, out = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
names, G = load_gt(ep)
rn, ach, ref, steps, rf, md = load_rollout(f'{STORE}/{subp}/episode_{ep:06d}.parquet')
assert rn == names
T, B = len(steps), len(names)


def b64npz(**arrs):
    s = io.BytesIO(); np.savez_compressed(s, **arrs); return base64.b64encode(s.getvalue()).decode('ascii')


prov = dict(eval_script_sha256='a' * 64, eval_code_sha256='b' * 64, checkpoint_sha256='c' * 64,
            packer_script_sha256='d' * 64, uploader_script_sha256='e' * 64,
            code_commit_url='https://github.com/example/example/commit/' + '0' * 40)
rows = []
for t in range(T):
    for s in range(B):
        q = ach[t, s]
        rows.append(dict(row_id=f'track_3/e{ep:06d}/w000/f{t:06d}/o{s}', pos_x=q[0], pos_y=q[1], pos_z=q[2], quat_x=q[3],
                         quat_y=q[4], quat_z=q[5], quat_w=q[6], **prov, object_mesh_b64=''))
sub = pd.DataFrame(rows)
for s, n in enumerate(names):
    v, f = budget(f'{LIB}/{lib}/{n}.glb')
    sub.loc[s, 'object_mesh_b64'] = b64npz(vertices=v, faces=f)        # row (f=0, slot s) is row index s
res = dict(ep=ep, rollout=subp, lib=lib, scores={})
for enc in ('weld32', 'soup64'):
    geo = {'names': np.array(names)}
    for i, n in enumerate(names):
        H = host(n, i)
        v, f = load_vf(scan_path(n))
        if enc == 'weld32':
            m = trimesh.Trimesh(v, f, process=False); m.merge_vertices(); m.remove_unreferenced_vertices()
            v, f = np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.int32)
        geo.update({f'v{i}': v, f'f{i}': f, f'anchor{i}': H['anchor'], f'points{i}': H['points'] + H['anchor'],
                    f'axis{i}': H['axis'], f'order{i}': np.int64(H['order'])})
    nbytes = int(sum(np.asarray(x).nbytes for x in geo.values()))
    sol = []
    for t in range(T):
        for s, n in enumerate(names):
            q = G[t, s]
            sol.append(dict(row_id=f'track_3/e{ep:06d}/w000/f{t:06d}/o{s}', episode_index=ep, world_index=0, frame_index=t,
                            object_slot=s, object_name=n, ref_pos_x=q[0], ref_pos_y=q[1], ref_pos_z=q[2], ref_quat_x=q[3],
                            ref_quat_y=q[4], ref_quat_z=q[5], ref_quat_w=q[6], reference_geometry_b64=''))
    sol = pd.DataFrame(sol); sol.loc[0, 'reference_geometry_b64'] = b64npz(**geo)
    r = dict(decoded_bytes=nbytes, limit_patched=nbytes > 16_000_000)
    for name in ('AUC', 'SP-SR', 'MP-SR'):
        mod = official(name)
        if nbytes > 16_000_000:
            o = mod._decode_archive
            mod._decode_archive = lambda text, maximum_bytes=2_000_000, _o=o: _o(text, max(maximum_bytes, 10 ** 9))
        r[name] = round(float(mod.score(sol.copy(), sub.copy(), 'row_id')), 6)
    res['scores'][enc] = r
    print(enc, r, flush=True)
json.dump(res, open(out, 'w'), indent=1)
