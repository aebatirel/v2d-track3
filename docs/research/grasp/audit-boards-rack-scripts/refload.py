import os, sys
import numpy as np, pyarrow.parquet as pq
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'tools'))
from contact_slots import slot_names, short  # noqa: E402
def col(t, c):
    return t.column(c)[0].as_py()
def load_ref(path):
    t = pq.read_table(path)
    names = col(t, 'object_body_names'); B = len(names)
    T = len(np.array(col(t, 'robot_left_wrist_position'), float).reshape(-1, 3))
    d = dict(names=names, T=T)
    d['OP'] = np.array(col(t, 'object_body_position'), float).reshape(T, B, 3)
    d['OQ'] = np.array(col(t, 'object_body_wxyz'), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]  # xyzw
    # contact slot labels in mkref's probe order. 2026-10-25: was the mano_link_names column (MANO link order), which
    # does not describe mkref's slots (approach3-grasp-taxonomy.md §9). None when the slot order is unknown.
    try:
        d['slots'] = [short(n) for n in slot_names(t)]
    except ValueError:
        d['slots'] = None
    for s in ('left', 'right'):
        d[f'J_{s}'] = np.array(col(t, f'mano_{s}_joints'), float).reshape(T, 21, 3)
        d[f'cpos_{s}'] = np.array(col(t, f'mano_{s}_link_contact_positions'), float).reshape(T, -1, 3)
        d[f'cn_{s}'] = np.array(col(t, f'mano_{s}_object_contact_normals'), float).reshape(T, -1, 3)
        d[f'cpid_{s}'] = np.array(col(t, f'mano_{s}_object_contact_part_ids')).reshape(T, -1)
        d[f'ocpos_{s}'] = np.array(col(t, f'mano_{s}_object_contact_positions'), float).reshape(T, -1, 3)
        d[f'frames_{s}'] = np.array(col(t, f'robot_{s}_frames'), float).reshape(T, -1, 7)
        d[f'fnames_{s}'] = col(t, f'{s}_robot_frame_names')
        d[f'wpos_{s}'] = np.array(col(t, f'robot_{s}_wrist_position'), float).reshape(T, 3)
        d[f'fj_{s}'] = np.array(col(t, f'robot_{s}_finger_joints'), float).reshape(T, -1)
        d[f'fjn_{s}'] = col(t, f'{s}_robot_finger_joint_names')
    return d
