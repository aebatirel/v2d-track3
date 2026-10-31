"""E0 step 1 (local, GT-free): inventory of the eval pairs of the four C0 objects and of every box input.

Reads only: the kit eval roster (object names + slot order), our eval tracks (scratchpad data/eval/ep<N>/poses.npz,
result.json = store run 20261025-evperc-4f596df, the pack's poses), the eval cam_a videos (size only), the
calibration file, the store listing of cache/depth/eval (sizes only). No scan, mocap, parquet or *_align file.
Writes plan.json (pairs, per-episode objects, frame counts, depth sizes, input hashes).
Usage: python -I e0_inventory.py SCRATCH KIT OUT_plan.json
"""
import hashlib, json, os, sys
import numpy as np

SCR, KIT, OUT = sys.argv[1:4]
OBJS = ['white_pot', 'white_pot_lid', 'plastic_dish_rack', 'blue_cup']
roster = json.load(open(f'{KIT}/data/track_3_evaluation_objects.json'))


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


# roster format: list or dict of episodes -> objects (slot order)
eps = {}
items = roster["episodes"].items()
for k, v in items:
    objs = v if isinstance(v, list) else v.get('objects', v.get('object_names'))
    eps[int(str(k).replace('episode_', '').replace('ep', ''))] = list(objs)
pairs = [dict(eval_episode=e, slot=i, object=o) for e in sorted(eps) for i, o in enumerate(eps[e]) if o in OBJS]
need = sorted({p['eval_episode'] for p in pairs})
depth_sizes = {}
try:
    from huggingface_hub import HfApi
    for f in HfApi().list_repo_tree('aebatirel/v2d-store', repo_type='dataset', path_in_repo='cache/depth/eval',
                                    recursive=True):
        if f.path.endswith('depths_fs0.5.npy'):
            depth_sizes[int(f.path.split('/')[-2][2:])] = int(f.size)
except Exception as ex:  # noqa: BLE001
    print('store listing failed:', ex)
episodes = {}
for e in need:
    d = f'{SCR}/data/eval/ep{e}'
    P = np.load(f'{d}/poses.npz')
    res = json.load(open(f'{d}/result.json'))
    T = int(P['world_T_cam'].shape[0])
    keys = sorted(k[6:] for k in P.files if k.startswith('cam_T_'))
    ds = depth_sizes.get(e)
    nd = (ds - 128) // (1600 * 1000 * 4) if ds else None
    vid = f'{SCR}/data/eval/ep{e}_a.mp4'
    episodes[e] = dict(objects=eps[e], track_bodies=keys, result_objects=res.get('objects'), frames_poses=T,
                       frames_result=res.get('frames'), depth_bytes=ds, depth_frames=nd,
                       depth_covers_poses=(nd is not None and nd >= T),
                       poses_sha256=sha(f'{d}/poses.npz'), result_sha256=sha(f'{d}/result.json'),
                       video_a=os.path.basename(vid), video_bytes=os.path.getsize(vid), video_sha256=sha(vid),
                       roster_matches_track=(sorted(eps[e]) == keys == sorted(res.get('objects', []))))
by_obj = {o: [p['eval_episode'] for p in pairs if p['object'] == o] for o in OBJS}
plan = dict(objects=OBJS, pairs=pairs, n_pairs=len(pairs), episodes_by_object=by_obj,
            episodes=episodes, calib_sha256=sha(f'{SCR}/data/calib.json'),
            tracks_source='scratchpad data/eval/ep<N>/{poses.npz,result.json} = HF store runs/20261025-evperc-4f596df/'
                          'results/evalperc/ep<N>/ (the pack poses; eval_perc_check.sh, LIB=meshes/library_v3)',
            depth_source='HF store cache/depth/eval/ep<N>/depths_fs0.5.npy (run mesh-20261029-evdepth-92f3d86)')
json.dump(plan, open(OUT, 'w'), indent=1)
print(json.dumps(by_obj), len(pairs), 'pairs;', len(need), 'episodes')
for e in need:
    x = episodes[e]
    print(e, x['objects'], 'T', x['frames_poses'], 'depth', x['depth_frames'], 'ok' if x['depth_covers_poses'] else 'DEPTH-SHORT',
          'roster=track' if x['roster_matches_track'] else 'ROSTER-MISMATCH', round(x['depth_bytes'] / 1e9, 2) if x['depth_bytes'] else None)
