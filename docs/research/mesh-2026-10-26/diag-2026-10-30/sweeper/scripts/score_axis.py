# [D] replay of mesh_metric.evaluate for ONE mesh + rotation axis of each seed's registration. Counts as one scoring.
import sys, json, math, numpy as np
sys.path.insert(0,'/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts')
import mesh_metric as MM
from scipy.spatial.transform import Rotation as Rot
label, path = sys.argv[1], sys.argv[2]
out = sys.argv[3]
tf = None
if len(sys.argv) > 4:
    tf = np.load(sys.argv[4])['T'] if sys.argv[4].endswith('.npz') else None
rec = MM.evaluate(label, 'mini_sweeper', path, frame_tf=tf, do_amb=True)
# rotation axes
v, f, _ = MM.load_candidate(path)
if tf is not None: v = v @ tf[:3,:3].T + tf[:3,3]
ref = MM.reference('mini_sweeper')
for s in rec['seeds']:
    ca, R = MM.auc._register_object_body((v, f), (ref['v'], ref['f']), ref['anchor'], s['seed'])
    rv = Rot.from_matrix(R).as_rotvec(); ang = np.linalg.norm(rv); ax = rv/ang if ang > 1e-9 else rv
    s['axis'] = np.round(ax, 3).tolist(); s['angle'] = round(math.degrees(ang), 2)
    s['anchor_off_mm'] = np.round((ca - ref['anchor'])*1000, 1).tolist()
json.dump(rec, open(out, 'a')); open(out,'a').write('\n')
print(label, 'cdo_eval %.4f add_med %.2f add_all %.2f flips %d/%d amb %.2f mm (rot %s)'%(rec['cdo_eval'], rec['add_med'], rec['add_all'], rec['flips_all'], rec['n_seeds'], rec['amb_mm'], rec['amb_rot']))
for s in rec['seeds']: print('   ', s['ep'], s['seed'], 'cdo', s['cdo_cm'], 'add', s['add_mm'], 'rot', s['rot_deg'], 'axis', s['axis'], 'anchor_off', s['anchor_off_mm'])
