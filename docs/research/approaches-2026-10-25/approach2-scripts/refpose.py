"""Our own reference poses (perception output; GT-free)."""
import numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
SCR = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
REFS = {
    'ep24': SCR + '/evo/dl24/runs/20261023-glockpub-0f7e3a7/refs/perc2mcs/ep24/processed/sequence_id=t3_ep024/robot_name=sharpa_wave/a53cdb5b5f2c4c41987b6e1ff96bba60-0.parquet',
    'ev25': SCR + '/arcfoot/eval/ep25/ref_sf.parquet', 'ev1': SCR + '/arcfoot/eval/ep1/ref_sf.parquet',
    'ev10': SCR + '/arcfoot/eval/ep10/ref_sf.parquet', 'ev20': SCR + '/arcfoot/eval/ep20/ref_sf.parquet',
    'ep2': SCR + '/evo/sync/runs/20261024-e3-e49e83d/refs/glock/ep2/processed/sequence_id=t3_ep002/robot_name=sharpa_wave/ref_gl.parquet',
    'ep21': SCR + '/arcfoot/ep21/ref_sf.parquet'}
def load(key):
    d = pq.read_table(REFS[key], columns=['object_body_names', 'object_body_position', 'object_body_wxyz']).to_pylist()[0]
    pos = np.array(d['object_body_position']); q = np.array(d['object_body_wxyz'])
    return d['object_body_names'], pos, q
def R_of(qwxyz):
    return Rot.from_quat(np.r_[qwxyz[1:], qwxyz[0]]).as_matrix()
def to_world(X, pos, q):
    return X @ R_of(q).T + pos
def to_obj(X, pos, q):
    return (X - pos) @ R_of(q)
