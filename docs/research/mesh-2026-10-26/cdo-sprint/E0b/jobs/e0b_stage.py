"""Stage (and optionally upload) the E0b eval box inputs (C0b PREREG section 9 (a), 10). GT-free.

Writes OUTDIR/{plan.json, calib.json, kit/v2dlb/mesh_budget.py, t0_c0b.json, eval/ep<N>/{poses.npz, hands.npz},
pub/<object>/<label>.glb, SHA256SUMS}:
  - eval tracks: scratchpad data/eval/ep<N>/poses.npz (= store run 20261025-evperc-4f596df; sha256 asserted equal to
    E0's inventory plan, cdo-sprint/E0/inputs/plan.json);
  - eval hands: E0's box hands (store run mesh-20261031-e0-b05f001 results/e0/hands/ep<N>/hands.npz, MediaPipe on the
    eval cam_a videos), sha256 asserted equal to E0's box SHA256SUMS;
  - t0_c0b.json: the public C0b box's t0_C0b (frozen for E0b, PREREG 3.3 step 3), sha256 asserted equal to the
    committed copy C0b/results/box/t0_c0b.json;
  - pub/: the C0b public picks and the frame-check reference candidates (PREREG 9 (c)): every eligible C0b public
    candidate of the object whose source episodes do not include the pick's episode, sha256 asserted equal to the
    public box check rows (C0b/results/box/selection.json table);
  - calibration (md5 56c32942...) and the kit's mesh_budget.py (sha256 8f29481d...).
The eval FoundationStereo depth is already in the store (cache/depth/eval/ep<N>/depths_fs0.5.npy); its size and LFS
sha256 go into plan.json and are checked on the box. No scan, mocap, parquet, *_align file or library mesh (asserted).
Usage: python -I e0b_stage.py SCRATCH KIT REPO PUBRESULTS OUTDIR [--upload RUN_ID]
  PUBRESULTS = the pulled public box results folder (runs/mesh-20261031-c0b-00e8584/results/c0b)
"""
import hashlib, json, os, shutil, sys

SCR, KIT, REPO, PUB, OUT = sys.argv[1:6]
up = sys.argv[sys.argv.index('--upload') + 1] if '--upload' in sys.argv else None
MR = f'{REPO}/docs/research/mesh-2026-10-26'
SP = f'{MR}/cdo-sprint'
E0PLAN = json.load(open(f'{SP}/E0/inputs/plan.json'))
E0HANDS = f'{SCR}/cdo_e0/box/dl/runs/mesh-20261031-e0-b05f001/results/e0'
ROSTER = json.load(open(f'{SP}/C0/roster.json'))
# PREREG 9 candidates table: eval episodes per object (beige: section 10)
CAND = {'white_pot': [1, 3, 5, 6, 8, 28], 'white_pot_lid': [1], 'plastic_dish_rack': [14, 15, 16, 28, 30],
        'blue_cup': [10, 14, 20, 32, 33], 'beige_cup': [8, 10]}
PRIM = ('white_pot', 'white_pot_lid', 'plastic_dish_rack')
BOX_R = '/content/results/c0b'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


slots = {}
for x in ROSTER['pairs']:
    slots.setdefault(int(x['eval_episode']), []).append((int(x['slot']), x['object']))
slots = {e: [o for _, o in sorted(v)] for e, v in slots.items()}
for o, el in CAND.items():                       # the PREREG table equals the kit roster's pairs of the object
    assert sorted(e for e, objs in slots.items() if o in objs) == el, (o, el)
EPS = sorted({e for el in CAND.values() for e in el})
e0sums = {l.split()[1].lstrip('./'): l.split()[0] for l in open(f'{E0HANDS}/SHA256SUMS') if l.strip()}

files = {'calib.json': f'{SCR}/data/calib.json', 'kit/v2dlb/mesh_budget.py': f'{KIT}/v2dlb/mesh_budget.py',
         't0_c0b.json': f'{PUB}/t0_c0b.json'}
assert sha(f'{PUB}/t0_c0b.json') == sha(f'{SP}/C0b/results/box/t0_c0b.json'), 't0_c0b.json differs from the committed copy'
assert sha(files['calib.json']).startswith('') and hashlib.md5(open(files['calib.json'], 'rb').read()).hexdigest().startswith('56c32942')
assert sha(files['kit/v2dlb/mesh_budget.py']).startswith('8f29481d')
t0 = json.load(open(f'{PUB}/t0_c0b.json'))
assert t0['fittable'], 't0_C0b not fittable'

plan = dict(schema='e0b-eval-plan/1', split='eval', episodes={}, candidate_eps=CAND, all_set=CAND, marker_objects={},
            t0_c0b_m=t0['t0_m'],
            tracks_source='scratchpad data/eval/ep<N>/poses.npz = store run 20261025-evperc-4f596df (sha256 = E0 plan)',
            hands_source='store run mesh-20261031-e0-b05f001 results/e0/hands/ep<N>/hands.npz (sha256 = E0 box SHA256SUMS)',
            depth_source='store cache/depth/eval/ep<N>/depths_fs0.5.npy (run mesh-20261029-evdepth-92f3d86)',
            t0_source='C0b public box run mesh-20261031-c0b-00e8584 results/c0b/t0_c0b.json (frozen)')
from huggingface_hub import HfApi  # noqa: E402
info = {i.path: i for i in HfApi().get_paths_info('aebatirel/v2d-store', [f'cache/depth/eval/ep{e}/depths_fs0.5.npy'
                                                                       for e in EPS], repo_type='dataset')}
import numpy as np  # noqa: E402
for e in EPS:
    pz = f'{SCR}/data/eval/ep{e}/poses.npz'
    hz = f'{E0HANDS}/hands/ep{e}/hands.npz'
    assert sha(pz) == E0PLAN['episodes'][str(e)]['poses_sha256'], f'eval {e} track differs from E0 inventory'
    assert sha(hz) == e0sums[f'hands/ep{e}/hands.npz'], f'eval {e} hands differ from E0 box'
    P = np.load(pz)
    bodies = [k[6:] for k in P.files if k.startswith('cam_T_')]
    assert sorted(bodies) == sorted(slots[e]), (e, bodies, slots[e])
    files[f'eval/ep{e}/poses.npz'] = pz
    files[f'eval/ep{e}/hands.npz'] = hz
    d = info[f'cache/depth/eval/ep{e}/depths_fs0.5.npy']
    assert int(d.size) == E0PLAN['episodes'][str(e)]['depth_bytes'], f'eval {e} depth size differs from E0 inventory'
    plan['episodes'][str(e)] = dict(objects=slots[e], slot=slots[e], hands=True, frames_poses=int(len(P['world_T_cam'])),
                                    depth_bytes=int(d.size), depth_lfs_sha256=d.lfs.sha256 if d.lfs else None,
                                    poses_sha256=sha(pz), hands_sha256=sha(hz))
for o in PRIM:
    for e in CAND[o]:
        plan['marker_objects'].setdefault(str(e), [])
for e in list(plan['marker_objects']):
    plan['marker_objects'][e] = [o for o in slots[int(e)] if o in PRIM and int(e) in CAND[o]]

# frame-check references (PREREG 9 (c)): the public pick + eligible public candidates from other public episodes
sel = json.load(open(f'{SP}/C0b/results/box/selection.json'))
picks = json.load(open(f'{SP}/C0b/results/picks.json'))['picks']
joint_eps = {}
jj = json.load(open(f'{PUB}/cand/rack/plastic_dish_rack/joint.json'))
joint_eps['plastic_dish_rack'] = sorted(int(x['obs'].split('_')[0][2:]) for x in jj['alignment']['episodes'])
merged_eps = {'blue_cup': [21, 22]}            # C0b public merged cup = ep21 + ep22 points (c0b_tasks derive)
refs = {}
for o, pk in picks.items():
    rows = {r['label']: r for r in sel['table'][o]}
    p = rows[pk['pick']]
    assert p['sha256'] == pk['sha256'] == sha(f'{REPO}/{pk["repo_path"]}'), o
    pick_ep = int(p['episode'])

    def src_eps(r):
        if r['episode'] == 'joint':
            return joint_eps[o]
        if r['episode'] == 'merged':
            return merged_eps[o]
        return [int(r['episode'])]
    R = []
    for lab, r in sorted(rows.items()):
        if lab == pk['pick'] or r['excluded'] is not None or pick_ep in src_eps(r):
            continue
        assert r['path'].startswith(BOX_R + '/'), r['path']
        local = PUB + r['path'][len(BOX_R):]
        assert sha(local) == r['sha256'], lab
        k = f'pub/{o}/{lab.replace("/", "__")}.glb'
        files[k] = local
        R.append(dict(label=lab, episode=r['episode'], source_episodes=src_eps(r), sha256=r['sha256'], input=k))
    refs[o] = dict(pick=pk['pick'], pick_repo_path=pk['repo_path'], pick_sha256=pk['sha256'], pick_episode=pick_ep,
                   references=R, n_references=len(R),
                   rule='eligible C0b public candidates whose source episodes do not include the pick episode '
                        '(rack joint = eps %s, merged cup = eps 21+22)' % joint_eps['plastic_dish_rack'])
plan['frame_refs'] = refs
plan['report_meshes'] = dict(c0b_public={o: v['repo_path'] for o, v in picks.items()})

for k, v in files.items():
    low = (k + ' ' + v).lower()
    assert not any(w in low for w in ('scan', 'mocap', '_align', '.parquet', '/mesh/', 'library_v')), f'forbidden {k} {v}'
os.makedirs(OUT, exist_ok=True)
json.dump(plan, open(f'{OUT}/plan.json', 'w'), indent=1)
lines = [f'{sha(f"{OUT}/plan.json")}  plan.json']
for k, v in sorted(files.items()):
    d = os.path.join(OUT, k); os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copyfile(v, d)
    lines.append(f'{sha(d)}  {k}')
open(os.path.join(OUT, 'SHA256SUMS'), 'w').write('\n'.join(lines) + '\n')
tot = sum(os.path.getsize(os.path.join(OUT, k)) for k in files)
print(f'staged {len(files) + 1} files, {tot / 1e6:.1f} MB in {OUT}; eval episodes {EPS}; depth '
      f'{sum(x["depth_bytes"] for x in plan["episodes"].values()) / 1e9:.2f} GB; marker_objects {plan["marker_objects"]}; '
      f'frame refs {[(o, v["pick"], v["n_references"]) for o, v in refs.items()]}')
if up:
    HfApi().upload_folder(folder_path=OUT, path_in_repo=f'runs/{up}/inputs', repo_id='aebatirel/v2d-store',
                          repo_type='dataset', commit_message=f'E0b eval inputs {up}')
    print(f'uploaded to aebatirel/v2d-store runs/{up}/inputs')
