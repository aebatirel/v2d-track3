"""G2 stage 2 (C4 PREREG s7 + s10): per object the 4 lowest stage-1 CD-O medians [D] (why "cdo_top4"), plus (s10, rule C
extension) the 2 lowest stage-1 ADD medians among G2 meshes whose stage-1 CD-O median is <= the shipped 50-seed CD-O
median + 0.005, those of the 2 not already among the 4 (why "add_ext"; read literally: no replacement when one of the 2
is already in the top 4) -> GT-free placement in the library_v3
frame (C1/T2 place.py, unchanged) -> optional GT-free T3 fit copy (C1/T3 fit.py + cfg_frozen.json, unchanged) of each
placed mesh -> C4-audit/candidates_g2.json (role g2_candidate, needs_place false).

The SELECTION is GT-informed: best-of-N by public-scan CD-O (stage 1, 6 seeds). Placement and fit read only the
candidate, library_v3 and our observed points (no scan, mocap, parquet pose or *_align).
Usage: stage2.py SCREEN.jsonl SIM3_DIR STAGE2_DIR CANDIDATES_OUT.json [--no-fit]
  SIM3_DIR holds <model>_sim3/<tag>.ply as generated (the screened files, checked against SHA256SUMS).
"""
import argparse, hashlib, json, os, subprocess, sys

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
PY = f'{S}/venv/bin/python'
PLACE = f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint/C1/T2-probe-picks/scripts/place.py'
FIT = f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint/C1/T3-gen-fit/scripts/fit.py'
CFG = f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint/C1/T3-gen-fit/cfg_frozen.json'
SUMS = f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint/G2/results/SHA256SUMS'
OBJECTS = ('white_pot', 'blue_cup', 'plastic_dish_rack', 'water_pitcher')
K = 4
K_ADD = 2
SHIPPED_CDO = dict(white_pot=0.3107, blue_cup=0.2646, plastic_dish_rack=0.4182, water_pitcher=0.3713)  # 50-seed medians (C4 audit)


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('screen'); ap.add_argument('sim3_dir'); ap.add_argument('out_dir'); ap.add_argument('cands')
    ap.add_argument('--no-fit', action='store_true')
    a = ap.parse_args()
    sums = {}
    for l in open(SUMS):
        h, p = l.split()
        sums[p] = h
    recs = [json.loads(l) for l in open(a.screen) if l.strip()]
    os.makedirs(a.out_dir, exist_ok=True)
    picks, cands = [], []
    for obj in OBJECTS:
        rows = [r for r in recs if r['object'] == obj and 'screen' in r]
        rows.sort(key=lambda r: (r['screen']['summary']['cdo_med'], r['screen']['summary']['cdo_mean'], r['label']))
        sel = [(r, 'cdo_top4', rank) for rank, r in enumerate(rows[:K], 1)]
        top = {r['label'] for r in rows[:K]}
        elig = [r for r in rows if r['screen']['summary']['cdo_med'] <= SHIPPED_CDO[obj] + 0.005]
        elig.sort(key=lambda r: (r['screen']['summary']['add_med'], r['screen']['summary']['cdo_med'], r['label']))
        sel += [(r, 'add_ext', rank) for rank, r in enumerate(elig[:K_ADD], 1) if r['label'] not in top]
        print(f'{obj}: {len(rows)} screened, {len(elig)} with CD-O <= {SHIPPED_CDO[obj] + 0.005:.4f}; add_ext lowest 2: '
              f"{[(r['label'], r['screen']['summary']['add_med']) for r in elig[:K_ADD]]}", flush=True)
        for r, why, rank in sel:
            model, tag = r['label'].split('/')[1:3]               # g2/<model>/<tag>
            rel = f'gen/{model}_sim3/{tag}.ply'
            src = os.path.join(a.sim3_dir, f'{model}_sim3', f'{tag}.ply')
            assert sha256(src) == sums[rel], f'hash mismatch {src}'
            ep = tag.split('_')[0]
            stem = os.path.join(a.out_dir, f'{obj}_g2_{model}_{tag.replace(obj + "_", "")}_lib')
            if not os.path.exists(stem + '.glb'):
                subprocess.run([PY, '-I', PLACE, obj, src, f'{REPO}/meshes/library_v3/{obj}.glb', stem], check=True,
                               stdout=subprocess.DEVNULL, cwd=a.out_dir)
            pl = json.load(open(stem + '.json'))
            s1 = r['screen']['summary']
            pick = dict(object=obj, why=why, rank=rank, label=r['label'], model=model, tag=tag, episode=ep, source=rel,
                        source_sha256=sums[rel], stage1=s1, placed=stem + '.glb', placed_md5=md5(stem + '.glb'),
                        place_residual_mm=pl['residual_mm'], place_best_start=pl['best_start'],
                        place_second_distinct_residual_mm=pl['second_distinct_residual_mm'])
            cands.append(dict(object=obj, label=f'G2/{obj}/{model}/{tag}/placed', path=stem + '.glb',
                              md5=md5(stem + '.glb'), role='g2_candidate', needs_place=False, cdo_rec=s1['cdo_med'],
                              stage1_label=r['label'], kind='placed', why=why))
            if not a.no_fit:
                fd = stem + '_t3fit'
                obs = f'{S}/obs_all/{ep}_{obj}.npz'
                if not os.path.exists(os.path.join(fd, 'fit.glb')):
                    rc = subprocess.run(['nice', '-n', '5', PY, '-I', FIT, '--mesh', stem + '.glb', '--obs', obs, '--out', fd,
                                         '--cfg', CFG], stdout=open(fd + '.out', 'w'), stderr=subprocess.STDOUT).returncode
                    pick['fit_rc'] = rc
                if os.path.exists(os.path.join(fd, 'fit.glb')):
                    fg = fd + '.glb'
                    if not os.path.exists(fg):
                        import shutil
                        shutil.copyfile(os.path.join(fd, 'fit.glb'), fg)
                    d = json.load(open(os.path.join(fd, 'diag.json')))
                    st = {x['tag']: x for x in d['stages']}
                    pick.update(fit=fg, fit_md5=md5(fg), fit_obs=obs,
                                fit_held_tmean90_in=st['input']['held_o2m']['tmean90_mm'],
                                fit_held_tmean90_fit=st.get('stage_0', {}).get('held_o2m', {}).get('tmean90_mm'),
                                fit_faces=d['final']['faces'], fit_watertight=d['final']['watertight'])
                    cands.append(dict(object=obj, label=f'G2/{obj}/{model}/{tag}/t3fit', path=fg, md5=md5(fg),
                                      role='g2_candidate', needs_place=False, cdo_rec=s1['cdo_med'],
                                      stage1_label=r['label'], kind='t3fit', why=why))
            picks.append(pick)
            print(json.dumps({k: v for k, v in pick.items() if k != 'stage1'}), flush=True)
    json.dump(picks, open(os.path.join(a.out_dir, 'picks.json'), 'w'), indent=1)
    json.dump(cands, open(a.cands, 'w'), indent=1)
    print(f'{len(picks)} picks, {len(cands)} candidates -> {a.cands}')


if __name__ == '__main__':
    main()
