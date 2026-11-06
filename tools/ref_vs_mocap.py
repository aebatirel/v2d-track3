"""Registered ADD-AUC vs mocap of a REFERENCE parquet's object track (public episodes only; evaluation/diagnostic).

Gate G0 of the oracle twins (docs/research/work/oracle-twins-20261030/PREREG.md): before any training, how close is a
reference's object motion (object_body_position / object_body_wxyz, table frame, our meshes' body frames) to mocap?
The track is written as a 4x4-per-object npz and scored by pipeline/score_registered.py itself (kit registration of
our meshes to the scans, frame-0 scene alignment, declared symmetries), i.e. the same number as the `reference` entry
of a rollout's score_registered_ep<N>.json, available before training. Reads ground truth: never for eval inference.
Usage: python ref_vs_mocap.py EP REF.parquet --meshes DIR [--t3 /content/t3] [--kit KIT] [--out JSON]
"""
import argparse, json, os, subprocess, sys, tempfile
import numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('ep', type=int); p.add_argument('ref'); p.add_argument('--meshes', required=True)
p.add_argument('--t3', default='/content/t3'); p.add_argument('--kit', default='/content/kit/v2d_submission_kit')
p.add_argument('--out', default=None)
a = p.parse_args()
t = pq.read_table(a.ref, columns=['object_body_names', 'object_body_position', 'object_body_wxyz', 'robot_left_wrist_position'])
names = [str(x) for x in t.column('object_body_names')[0].as_py()]; B = len(names)
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
pos = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
wxyz = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)
M = np.repeat(np.eye(4)[None, None], T, 0).repeat(B, 1)
M[..., :3, :3] = Rot.from_quat(wxyz[..., [1, 2, 3, 0]].reshape(-1, 4)).as_matrix().reshape(T, B, 3, 3); M[..., :3, 3] = pos
ep_names = [str(o['name']) for o in pq.read_table(f'{a.t3}/ep{a.ep}.parquet', columns=['observation.objects'])
            .column('observation.objects')[0].as_py()]
if names != ep_names:
    sys.exit(f'reference objects {names} != episode slots {ep_names}')
S = os.path.dirname(os.path.abspath(__file__)) + '/../pipeline/score_registered.py'
with tempfile.TemporaryDirectory() as d:
    np.savez(f'{d}/ref.npz', **{n: M[:, b] for b, n in enumerate(names)})
    r = subprocess.run([sys.executable, S, str(a.ep), f'{d}/ref.npz', '--meshes', a.meshes, '--t3', a.t3, '--kit', a.kit,
                        '--out', f'{d}/s.json'], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'score_registered failed: {r.stderr[-800:]}')
    s = json.load(open(f'{d}/s.json'))
res = dict(episode=a.ep, reference=os.path.abspath(a.ref), frames=T, meshes=a.meshes, registration=s['registration'],
           ref_vs_mocap=s['perception'])
print(json.dumps(res, indent=1))
if a.out:
    json.dump(res, open(a.out, 'w'), indent=1)
