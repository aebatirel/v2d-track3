import numpy as np, pyarrow.parquet as pq
def col(t, c):
    return t.column(c)[0].as_py()
def load_ref(path):
    t = pq.read_table(path)
    names = col(t, 'object_body_names'); B = len(names)
    T = len(np.array(col(t, 'robot_left_wrist_position'), float).reshape(-1, 3))
    d = dict(names=names, T=T)
    d['OP'] = np.array(col(t, 'object_body_position'), float).reshape(T, B, 3)
    d['OQ'] = np.array(col(t, 'object_body_wxyz'), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]  # xyzw
    d['mano_links'] = col(t, 'mano_link_names')
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
