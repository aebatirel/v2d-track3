"""G3 stage 2 (C4 PREREG s12 steps 2-3; copy of G2's scripts/stage2.py with G3 objects, Pixal3D-MV sources and the trim
copy): per object the 4 lowest stage-1 CD-O medians [D] (why "cdo_top4"; s12 lists no ADD extension) ->
  placed: GT-free placement in the library_v3 frame (C1/T2 place.py, unchanged; Pixal3D-MV outputs too, as the C4
          audit placed the 29 Oct Pixal3D-MV candidates; place.py includes the identity start);
  t3fit:  GT-free T3 fit copy of the placed mesh (C1/T3 fit.py + cfg_frozen.json, unchanged; the pick's own episode's
          full observed points, as G2);
  trim:   G3/scripts/trim.py copy of the placed mesh: faces whose centroid is > 15 mm from both our observed points of
          the object (union over the episodes of the object's G3 crops / view sets) and the object's 13h mesh are
          deleted; no hole filling.
-> C4-audit/candidates_g3.json (role g3_candidate, needs_place false, kind placed / t3fit / trim).

The SELECTION is GT-informed: best-of-N by public-scan CD-O (stage 1, 6 seeds). Placement, fit and trim read only the
candidate, library_v3, the 13h meshes (ours) and our observed points (no scan, mocap, parquet pose or *_align).
Usage: stage2.py SCREEN.jsonl GEN_DIR STAGE2_DIR CANDIDATES_OUT.json
  GEN_DIR holds <model>_sim3/<tag>.ply and pixal_mv[_1024]/<tag>.ply as generated (checked against SHA256SUMS).
"""
import argparse, hashlib, json, os, shutil, subprocess

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
PY = f'{S}/venv/bin/python'
CS = f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint'
PLACE = f'{CS}/C1/T2-probe-picks/scripts/place.py'
FIT = f'{CS}/C1/T3-gen-fit/scripts/fit.py'
CFG = f'{CS}/C1/T3-gen-fit/cfg_frozen.json'
TRIM = f'{CS}/G3/scripts/trim.py'
SUMS = f'{CS}/G3/results/SHA256SUMS'
K = 4
THR_MM = 15
# the object's G3 crop / view-set episodes (PREREG s12): the trim's observed points
EPS = dict(mini_dust_pan=(18, 39, 40), beige_cup=(11,), white_pot_lid=(0, 2), mini_sweeper=(18, 31),
           wooden_piece_1=(24,), wooden_piece_2=(24,), plastic_dish_rack=(13, 27), white_pot=(0, 2, 26, 27, 42, 45))
# 13h mesh of each object (the trim reference; also the stage-3 baseline)
REF13H = dict(
    white_pot=f'{CS}/C4-audit/meshes_13h/white_pot_g2_sam3d_ep44_k0_s7_lib.glb',
    plastic_dish_rack=f'{CS}/C4-audit/meshes_13h/plastic_dish_rack_g2_hy21_ep31_k282_s123_lib_t3fit.glb',
    mini_dust_pan=f'{CS}/C3/tierB/meshes/mini_dust_pan_hy21_ep39_k297_s42_lib.glb',
    beige_cup=f'{CS}/C1/T1-beige-lathe/meshes/ep11_beige_cup_sep_g1.glb',
    white_pot_lid=f'{REPO}/meshes/library_c0/white_pot_lid.glb',
    mini_sweeper=f'{CS}/C3/tierB/meshes/mini_sweeper_P1_partprog.glb',
    wooden_piece_1=f'{CS}/C3/tierB/meshes/wooden_piece_1_ep24_occ_d2.glb',
    wooden_piece_2=f'{CS}/C3/tierB/meshes/wooden_piece_2_ep24_occ.glb')
OBJECTS = tuple(EPS)


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('screen'); ap.add_argument('gen_dir'); ap.add_argument('out_dir'); ap.add_argument('cands')
    ap.add_argument('--only', default=None, help='comma-separated objects (debug)')
    a = ap.parse_args()
    for p in REF13H.values():
        assert os.path.exists(p), p
    sums = {}
    for l in open(SUMS):
        h, p = l.split()
        sums[p] = h
    recs = [json.loads(l) for l in open(a.screen) if l.strip()]
    os.makedirs(a.out_dir, exist_ok=True)
    picks, cands = [], []
    for obj in OBJECTS:
        if a.only and obj not in a.only.split(','):
            continue
        rows = [r for r in recs if r['object'] == obj and 'screen' in r]
        rows.sort(key=lambda r: (r['screen']['summary']['cdo_med'], r['screen']['summary']['cdo_mean'], r['label']))
        print(f'{obj}: {len(rows)} screened; top {K}: {[(r["label"], r["screen"]["summary"]["cdo_med"]) for r in rows[:K]]}',
              flush=True)
        obs_union = [f'{S}/obs_all/ep{e}_{obj}.npz' for e in EPS[obj]]
        for rank, r in enumerate(rows[:K], 1):
            why = 'cdo_top4'
            model, tag = r['label'].split('/')[1:3]               # g3/<model>/<tag>
            rel = f'gen/{model}/{tag}.ply' if model.startswith('pixal_mv') else f'gen/{model}_sim3/{tag}.ply'
            src = os.path.join(a.gen_dir, rel[len('gen/'):])
            assert sha256(src) == sums[rel], f'hash mismatch {src}'
            ep = tag.split('_')[0]
            short = tag.replace(obj + '_', '')
            stem = os.path.join(a.out_dir, f'{obj}_g3_{model}_{short}_lib')
            if not os.path.exists(stem + '.glb'):
                subprocess.run([PY, '-I', PLACE, obj, src, f'{REPO}/meshes/library_v3/{obj}.glb', stem], check=True,
                               stdout=subprocess.DEVNULL, cwd=a.out_dir)
            pl = json.load(open(stem + '.json'))
            s1 = r['screen']['summary']
            pick = dict(object=obj, why=why, rank=rank, label=r['label'], model=model, tag=tag, episode=ep, source=rel,
                        source_sha256=sums[rel], stage1=s1, placed=stem + '.glb', placed_md5=md5(stem + '.glb'),
                        place_residual_mm=pl['residual_mm'], place_best_start=pl['best_start'],
                        place_identity_residual_mm=pl.get('identity_start_residual_mm'),
                        place_second_distinct_residual_mm=pl['second_distinct_residual_mm'])
            base = dict(object=obj, role='g3_candidate', needs_place=False, cdo_rec=s1['cdo_med'], stage1_label=r['label'],
                        why=why)
            cands.append(dict(base, label=f'G3/{obj}/{model}/{tag}/placed', path=stem + '.glb', md5=md5(stem + '.glb'),
                              kind='placed'))
            # T3 fit copy
            fd = stem + '_t3fit'
            obs = f'{S}/obs_all/{ep}_{obj}.npz'
            if not os.path.exists(os.path.join(fd, 'fit.glb')):
                rc = subprocess.run(['nice', '-n', '5', PY, '-I', FIT, '--mesh', stem + '.glb', '--obs', obs, '--out', fd,
                                     '--cfg', CFG], stdout=open(fd + '.out', 'w'), stderr=subprocess.STDOUT).returncode
                pick['fit_rc'] = rc
            if os.path.exists(os.path.join(fd, 'fit.glb')):
                fg = fd + '.glb'
                if not os.path.exists(fg):
                    shutil.copyfile(os.path.join(fd, 'fit.glb'), fg)
                d = json.load(open(os.path.join(fd, 'diag.json')))
                st = {x['tag']: x for x in d['stages']}
                pick.update(fit=fg, fit_md5=md5(fg), fit_obs=obs,
                            fit_held_tmean90_in=st['input']['held_o2m']['tmean90_mm'],
                            fit_held_tmean90_fit=st.get('stage_0', {}).get('held_o2m', {}).get('tmean90_mm'),
                            fit_faces=d['final']['faces'], fit_watertight=d['final']['watertight'])
                cands.append(dict(base, label=f'G3/{obj}/{model}/{tag}/t3fit', path=fg, md5=md5(fg), kind='t3fit'))
            # trim copy (of the placed mesh)
            tg = stem + '_trim15.glb'
            if not os.path.exists(tg):
                rc = subprocess.run(['nice', '-n', '5', PY, '-I', TRIM, stem + '.glb', REF13H[obj], tg, str(THR_MM)] + obs_union,
                                    stdout=open(stem + '_trim15.out', 'w'), stderr=subprocess.STDOUT).returncode
                pick['trim_rc'] = rc
            if os.path.exists(tg):
                ti = json.load(open(tg + '.json'))
                pick.update(trim=tg, trim_md5=md5(tg), trim_faces_removed=ti['faces_removed'], trim_faces_in=ti['faces_in'],
                            trim_area_removed_frac=ti['area_removed_frac'], trim_ref=REF13H[obj], trim_obs=obs_union)
                cands.append(dict(base, label=f'G3/{obj}/{model}/{tag}/trim', path=tg, md5=md5(tg), kind='trim'))
            picks.append(pick)
            print(json.dumps({k: v for k, v in pick.items() if k not in ('stage1', 'trim_obs')}), flush=True)
    json.dump(picks, open(os.path.join(a.out_dir, 'picks.json'), 'w'), indent=1)
    json.dump(cands, open(a.cands, 'w'), indent=1)
    print(f'{len(picks)} picks, {len(cands)} candidates -> {a.cands}')


if __name__ == '__main__':
    main()
