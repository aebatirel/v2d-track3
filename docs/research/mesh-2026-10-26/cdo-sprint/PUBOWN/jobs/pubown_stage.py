"""Stage (and optionally upload) the PUBOWN box inputs: one C0b-family mesh per public (episode, object) pair, built
from that episode's own observed points (PLAN.md). Writes OUTDIR/{plan.json, roster_public.json, sweep/ep<N>/poses.npz,
kit/v2dlb/mesh_budget.py, SHA256SUMS}.

The C0b public box run (--c0b_run) is the frozen source of the observed points and GT-free measurements: its pass-B
points, thickness rows, sigma, marker detections and t0_C0b are fetched on the box from the store
(runs/<c0b_run>/results/c0b/<rel>) and checked against the sha256 that C0b's own SHA256SUMS lists (copied into
plan.json here). Whatever C0b did not compute for a PUBOWN pair (sigma of pairs outside C0b's candidate pools, the
marker detection of an episode whose prim-object set differs) is recomputed on the box with C0b's code.

No scan, mocap, parquet pose or *_align file (asserted). The tracks are our sweep base tracks (C0b's).
Usage: python -I pubown_stage.py SCRATCH KIT REPO OUTDIR --c0b_run RUN [--c0b_dir DIR] [--eps "11 21"]
                                [--upload RUN_ID]
  --c0b_dir: read C0b's SHA256SUMS / plan.json from a local results/c0b copy instead of the store (dry run)
  --eps:     restrict the pairs to these episodes (dry run)
"""
import argparse, hashlib, json, os, shutil, subprocess, sys

import numpy as np

STORE = 'aebatirel/v2d-store'
OBJ_EPS = {'white_pot': [0, 2, 26, 27, 41, 42, 43, 44, 45], 'white_pot_lid': [0, 2],
           'plastic_dish_rack': [12, 13, 26, 27, 31], 'blue_cup': [11, 12, 13, 21, 22], 'beige_cup': [11]}
PRIM = ('white_pot', 'white_pot_lid', 'plastic_dish_rack')    # objects with a gmg marker detection (C0b 3.2)
C0B_CODE_COMMIT = '00e858434419b3e6bb11508ec8b35e092d76199f'   # the C0b public box's code (C0b NOTES 18:22:58Z)
# the box extracts the code it runs from this commit (pubown_freeze.sh), never from the working tree
FORBID = ('scan', 'mocap', '_align', '.parquet', '/mesh/', 'library_v')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def c0b_file(a, rel):
    """a file of the C0b results folder: local copy (--c0b_dir) or the store"""
    if a.c0b_dir:
        return os.path.join(a.c0b_dir, rel)
    from huggingface_hub import hf_hub_download
    return hf_hub_download(STORE, f'runs/{a.c0b_run}/results/c0b/{rel}', repo_type='dataset')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scr'); ap.add_argument('kit'); ap.add_argument('repo'); ap.add_argument('out')
    ap.add_argument('--c0b_run', required=True); ap.add_argument('--c0b_dir', default=None)
    ap.add_argument('--eps', default=None); ap.add_argument('--upload', default=None)
    a = ap.parse_args()
    MR = f'{a.repo}/docs/research/mesh-2026-10-26'
    roster = json.load(open(f'{MR}/gmg/roster_public.json'))['episodes']
    keep = set(int(e) for e in a.eps.split()) if a.eps else None
    obj_eps = {o: [e for e in el if keep is None or e in keep] for o, el in OBJ_EPS.items()}
    obj_eps = {o: el for o, el in obj_eps.items() if el}
    eps = sorted({e for el in obj_eps.values() for e in el})

    # C0b's frozen outputs: SHA256SUMS + its plan (marker object sets)
    sums = {}
    for line in open(c0b_file(a, 'SHA256SUMS')):
        if line.strip():
            h, f = line.split(None, 1)
            f = f.strip().lstrip('*')
            sums[f[2:] if f.startswith('./') else f] = h
    c0b_plan = json.load(open(c0b_file(a, 'plan.json')))

    plan = dict(schema='pubown-plan/1', c0b_run=a.c0b_run, c0b_code_commit=C0B_CODE_COMMIT,
                rule='one C0b-family mesh per (episode, object), own points only; pick within the episode (PLAN.md)',
                obj_eps=obj_eps, episodes={}, marker_objects={}, reuse={}, recompute=dict(sigma=[], markers=[]),
                tracks_source='store run 20261025-sweep-a894083 results/sweep/base/ep<N>/poses.npz (C0b inputs)')
    files = {'roster_public.json': f'{MR}/gmg/roster_public.json', 'kit/v2dlb/mesh_budget.py': f'{a.kit}/v2dlb/mesh_budget.py'}
    for e in eps:
        pz = f'{a.scr}/data/sweep/ep{e}/poses.npz'
        P = np.load(pz)
        bodies = [k[6:] for k in P.files if k.startswith('cam_T_')]
        slot = list(roster[str(e)])
        assert sorted(bodies) == sorted(slot), (e, bodies, slot)
        assert c0b_plan['episodes'][str(e)]['poses_sha256'] == sha(pz), f'ep{e} poses differ from the C0b inputs'
        files[f'sweep/ep{e}/poses.npz'] = pz
        plan['episodes'][str(e)] = dict(objects=bodies, slot=slot, poses_sha256=sha(pz),
                                        pairs=[o for o in slot if e in obj_eps.get(o, [])])
        mo = [o for o in roster[str(e)] if o in PRIM and e in obj_eps.get(o, [])]
        if mo:
            plan['marker_objects'][str(e)] = mo

    def need(rel, required=True):
        if rel in sums:
            plan['reuse'][rel] = sums[rel]
            return True
        if required:
            sys.exit(f'C0b run {a.c0b_run} lacks {rel}: no PUBOWN staging without it')
        return False

    need('t0_c0b.json')
    for o, el in obj_eps.items():
        for e in el:
            base = f'ep{e}_beige_cup_sep' if o == 'beige_cup' else f'ep{e}_{o}'
            need(f'pts/B/{base}.npz')
            need(f'thick/{base}.npy'); need(f'thick/{base}.json')
            if not need(f'sigma/{base}.json', required=False):
                plan['recompute']['sigma'].append([o, e])
            if o == 'beige_cup':
                need(f'msep_ep{e}.json')
    for e, mo in plan['marker_objects'].items():
        same = c0b_plan.get('marker_objects', {}).get(e) == mo
        if not (same and need(f'markers/ep{e}.json', required=False)):
            plan['recompute']['markers'].append(e)
    fr = subprocess.run(['bash', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pubown_freeze.sh'), a.repo,
                         C0B_CODE_COMMIT, os.path.join(a.out + '.code_check')], capture_output=True, text=True, check=True)
    plan['frozen_code'] = json.loads(fr.stdout.strip().splitlines()[-1])
    shutil.rmtree(a.out + '.code_check', ignore_errors=True)
    for k, v in list(files.items()) + [(r, r) for r in plan['reuse']]:
        low = (k + ' ' + v).lower()
        assert not any(w in low for w in FORBID), f'forbidden input {k} {v}'

    os.makedirs(a.out, exist_ok=True)
    json.dump(plan, open(f'{a.out}/plan.json', 'w'), indent=1)
    lines = [f'{sha(f"{a.out}/plan.json")}  plan.json']
    for k, v in sorted(files.items()):
        d = os.path.join(a.out, k); os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(v, d)
        lines.append(f'{sha(d)}  {k}')
    open(os.path.join(a.out, 'SHA256SUMS'), 'w').write('\n'.join(lines) + '\n')
    npairs = sum(len(v) for v in obj_eps.values())
    print(json.dumps(dict(staged=len(files) + 1, out=a.out, pairs=npairs, episodes=eps, reuse=len(plan['reuse']),
                          recompute=plan['recompute'], marker_objects=plan['marker_objects'])))
    if a.upload:
        from huggingface_hub import HfApi
        HfApi().upload_folder(folder_path=a.out, path_in_repo=f'runs/{a.upload}/inputs', repo_id=STORE,
                              repo_type='dataset', commit_message=f'PUBOWN inputs {a.upload}')
        print(f'uploaded to {STORE} runs/{a.upload}/inputs')


if __name__ == '__main__':
    main()
