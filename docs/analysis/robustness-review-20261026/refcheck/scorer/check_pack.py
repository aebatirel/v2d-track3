"""Audit of the submitted Track 3 file (pack 4) and of the mesh / frame conventions behind it (part 3 of the scorer check).
No ground truth is read (eval episodes have none); this checks bookkeeping only.

A. results/submissions/20261026-track3d/track3_submission.parquet (the uploaded pack 4):
   - row ids == the kit's sample grid; quaternion norms; one mesh payload per (episode, slot) on its first row;
   - every row == the world-0 achieved pose of the rollout pack 4 packed (store runs/20261026-pack4-f7a49a9/results/
     submission/results/episode_*.parquet, read with the kit's read_trajectory), same xyzw order;
   - every payload == budget_mesh(packed glb) and the packed glb is byte-identical to meshes/library_v3/<obj>.glb (v3x
     for eval 8's beige cup, per the pack README).
B. Simulator assets vs packed meshes: for each eval episode, the grasp-lock reference's own assets that pack 4 pulled
   (refs/sf/epN/assets): URDF visual/collision origin + scale, and the geometric distance between the asset mesh and the
   packed mesh (both loaded with trimesh force='mesh'). Standard-learner rollouts (evals 1, 10, 19, 25, 28, 30) used
   /content/assets built on the box by make_assets.py from library_v3 (pack_eval.sh), which is not stored.
C. Frame-0 gap between achieved and reference pose in every rollout (pack 4 and stored public rollouts), next to the
   centre-of-mass offset |c| from the URDF: if the evaluator recorded the COM (inertial) frame instead of the link
   (= mesh) frame, the frame-0 position gap would be ~|c| (the evaluator resets the objects to the reference pose).
Usage: python -I check_pack.py STORE REPO KIT OUT.json
"""
import glob, hashlib, json, os, re, sys
import numpy as np, pandas as pd, trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

STORE, REPO, KIT, OUT = sys.argv[1:5]
sys.path.insert(0, KIT)
from v2dlb.track3_pose import _decode_object_mesh
from v2dlb.mesh_budget import budget_mesh
from v2dlb.submission_parquet import read_trajectory

P4 = f'{STORE}/runs/20261026-pack4-f7a49a9'
SUBF = f'{REPO}/results/submissions/20261026-track3d/track3_submission.parquet'
roster = json.load(open(f'{KIT}/data/track_3_evaluation_objects.json'))['episodes']
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()
out = {'submission_file': SUBF, 'sha256': hashlib.sha256(open(SUBF, 'rb').read()).hexdigest()}

# ---- A
sub = pd.read_parquet(SUBF)
sample = pd.read_parquet(f'{KIT}/data/track_3_sample_submission.parquet', columns=['row_id'])
out['rows'] = len(sub); out['row_ids_equal_sample'] = bool(set(sub.row_id) == set(sample.row_id))
k = sub.row_id.str.extract(r'^track_3/e(\d+)/w(\d+)/f(\d+)/o(\d+)$').astype(int); k.columns = ['e', 'w', 'f', 'o']
POSE = ['pos_x', 'pos_y', 'pos_z', 'quat_x', 'quat_y', 'quat_z', 'quat_w']
Q = sub[POSE].to_numpy()
out['quat_norm_dev_max'] = float(np.abs(np.linalg.norm(Q[:, 3:], axis=1) - 1).max())
out['worlds'] = sorted(k.w.unique().tolist())
per_ep = {}
for e, g in k.groupby('e'):
    names = roster[str(e)]
    rec = {'objects': names, 'frames': int(g.f.nunique())}
    tr = read_trajectory(f'{P4}/results/submission/results/episode_{e:06d}.parquet')
    w0 = tr.world_index == tr.world_index.min()
    lut = {(int(f), int(s)): q for f, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], tr.pose_xyzw[w0])}
    rec['rollout_worlds'] = int(len(np.unique(tr.world_index)))
    rec['rollout_quaternion_order'] = tr.metadata.get('flash_chord.quaternion_order')
    rec['rollout_body_names'] = list(dict.fromkeys([str(x) for x in tr.object_name[w0]]))
    rec['body_names_match_roster'] = rec['rollout_body_names'] == names
    rows = sub.loc[g.index]
    pk = np.stack([lut[(int(f), int(s))] for f, s in zip(g.f, g.o)])
    rec['rows_minus_rollout_maxabs'] = float(np.abs(rows[POSE].to_numpy() - pk).max())
    meshes = {}
    for s, n in enumerate(names):
        enc = rows.loc[g.o == s].sort_values('row_id').object_mesh_b64.fillna('')
        first = rows.loc[(g.o == s) & (g.f == g.f.min())].object_mesh_b64.iloc[0]
        nonempty = int((enc.str.strip() != '').sum())
        v, f = _decode_object_mesh(first)
        glb = f'{P4}/results/submission/meshes/episode_{e:06d}/{n}.glb'
        bv, bf = budget_mesh(glb, 4096, 4096)
        lib = 'library_v3x' if (e == 8 and n == 'beige_cup') else 'library_v3'
        meshes[n] = dict(payloads=nonempty, payload_equals_budget_mesh=bool(np.array_equal(v, bv) and np.array_equal(f, bf)),
                         packed_glb_md5=md5(glb), library=lib,
                         packed_glb_equals_library=md5(glb) == md5(f'{REPO}/meshes/{lib}/{n}.glb'),
                         equals_library_v3=md5(glb) == md5(f'{REPO}/meshes/library_v3/{n}.glb'))
    rec['meshes'] = meshes
    # ---- B: the grasp-lock reference assets pack 4 pulled for this episode
    assets = {}
    for n in names:
        ag = f'{P4}/refs/sf/ep{e}/assets/mesh/{n}/{n}.glb'
        ur = f'{P4}/refs/sf/ep{e}/assets/urdf/{n}_rigid.urdf'
        if not os.path.exists(ag):
            continue
        A = trimesh.load(ag, force='mesh'); Bm = trimesh.load(f'{P4}/results/submission/meshes/episode_{e:06d}/{n}.glb', force='mesh')
        d1 = cKDTree(np.asarray(Bm.vertices)).query(np.asarray(A.vertices))[0]
        d2 = cKDTree(np.asarray(A.vertices)).query(np.asarray(Bm.vertices))[0]
        u = open(ur).read() if os.path.exists(ur) else ''
        vis = re.search(r'<visual>\s*<origin xyz="([^"]*)" rpy="([^"]*)"/>\s*<geometry><mesh filename="([^"]*)" scale="([^"]*)"', u)
        cols = re.findall(r'<collision>\s*<origin xyz="([^"]*)" rpy="([^"]*)"/>\s*<geometry><mesh filename="([^"]*)" scale="([^"]*)"', u)
        com = re.search(r'<inertial>\s*<origin xyz="([^"]*)"', u)
        assets[n] = dict(max_vertex_distance_mm=round(float(max(d1.max(), d2.max()) * 1000), 4),
                         visual=vis.groups() if vis else None,
                         collision_origins_nonzero=[c for c in cols if c[0] != '0 0 0' or c[1] != '0 0 0' or c[3] != '1 1 1'],
                         n_collision=len(cols), com_cm=[round(float(x) * 100, 2) for x in com.group(1).split()] if com else None)
    rec['sim_assets_vs_packed'] = assets
    # ---- C: frame-0 gap achieved vs reference
    if tr.reference_xyzw is not None:
        f0 = w0 & (tr.frame_index == tr.frame_index[w0].min())
        dp = np.linalg.norm(tr.pose_xyzw[f0, :3] - tr.reference_xyzw[f0, :3], axis=1)
        ang = (Rot.from_quat(tr.pose_xyzw[f0, 3:]).inv() * Rot.from_quat(tr.reference_xyzw[f0, 3:])).magnitude()
        rec['frame0_gap'] = {n: dict(pos_mm=round(float(dp[s]) * 1000, 3), rot_deg=round(float(np.degrees(ang[s])), 3))
                             for s, n in enumerate(names)}
    per_ep[int(e)] = rec
out['episodes'] = per_ep
out['all_rows_equal_rollouts'] = bool(all(r['rows_minus_rollout_maxabs'] == 0 for r in per_ep.values()))
out['all_payloads_equal_budget_mesh'] = bool(all(m['payload_equals_budget_mesh'] for r in per_ep.values() for m in r['meshes'].values()))
out['all_packed_glb_equal_library'] = bool(all(m['packed_glb_equals_library'] for r in per_ep.values() for m in r['meshes'].values()))
out['one_payload_each'] = bool(all(m['payloads'] == 1 for r in per_ep.values() for m in r['meshes'].values()))
out['all_body_names_match'] = bool(all(r['body_names_match_roster'] for r in per_ep.values()))

# ---- C on stored public rollouts (frame-0 gap vs COM offset of the assets they were built with)
pub = {}
for ep, rd, ad in [(21, 'runs/20261025-twin21arc-ee7ba8e/results/glock_public/ep21/best', 'runs/20261025-twin21arc-ee7ba8e/refs/sf/ep21/assets'),
                   (11, 'runs/20261025-twin11v3x-0e8aebb/results/glock_public/ep11/best', 'runs/20261025-twin11v3x-0e8aebb/refs/sf/ep11/assets'),
                   (2, 'runs/20261024-e3-e49e83d/results/glock_public/ep2/best', 'runs/20261024-e3-e49e83d/refs/sf/ep2/assets'),
                   (18, 'runs/20261024-ev3-2c1e4dd/results/glock_public/ep18/best', None),
                   (39, 'runs/20261024-ev3-2c1e4dd/results/glock_public/ep39/best', None)]:
    for pq_ in sorted(glob.glob(f'{STORE}/{rd}/r*/episode_{ep:06d}.parquet')):
        tr = read_trajectory(pq_)
        w0 = tr.world_index == tr.world_index.min(); f0 = w0 & (tr.frame_index == tr.frame_index[w0].min())
        names = list(dict.fromkeys([str(x) for x in tr.object_name[w0]]))
        dp = np.linalg.norm(tr.pose_xyzw[f0, :3] - tr.reference_xyzw[f0, :3], axis=1)
        ang = (Rot.from_quat(tr.pose_xyzw[f0, 3:]).inv() * Rot.from_quat(tr.reference_xyzw[f0, 3:])).magnitude()
        # the COM offset rotated into the world at frame 0: what a COM-frame recording would add to the gap
        com = {}
        if ad:
            for s, n in enumerate(names):
                u = open(f'{STORE}/{ad}/urdf/{n}_rigid.urdf').read()
                c = np.array([float(x) for x in re.search(r'<inertial>\s*<origin xyz="([^"]*)"', u).group(1).split()])
                com[n] = round(float(np.linalg.norm(c) * 1000), 2)
        pub[f'ep{ep}/{os.path.basename(os.path.dirname(pq_))}'] = {
            n: dict(pos_mm=round(float(dp[s]) * 1000, 3), rot_deg=round(float(np.degrees(ang[s])), 3), com_offset_mm=com.get(n))
            for s, n in enumerate(names)}
out['public_rollouts_frame0_gap'] = pub
json.dump(out, open(OUT, 'w'), indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k not in ('episodes', 'public_rollouts_frame0_gap')}, indent=1))
for e, r in per_ep.items():
    print(e, r['rows_minus_rollout_maxabs'], {n: (m['payload_equals_budget_mesh'], m['packed_glb_equals_library']) for n, m in r['meshes'].items()},
          {n: (x['max_vertex_distance_mm'], x['visual'], len(x['collision_origins_nonzero']), x['com_cm']) for n, x in r['sim_assets_vs_packed'].items()},
          r.get('frame0_gap'))
for k_, v in pub.items():
    print(k_, v)
