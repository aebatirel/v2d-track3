"""Rack round R stage 2 (C4 PREREG s14 steps 2-3; G3/scripts/stage2.py logic, rack only, plus the s13 outer copies).
Sources:
  R-gen : the 6 lowest stage-1 CD-O medians [D] of the R screen (6 seeds 3001-3006; ties: CD-O mean, label), why
          "cdo_top6". Each is placed in the library_v3 frame with the GT-free C1/T2 place.py (unchanged; Pixal3D-MV
          outputs too, as G3).
  R-prim: every R-prim fit (prim_rack.py at its existing settings, never measured; list in PRIM_LIST), why "r_prim".
          Already in our object frame: used as-is (the "placed" copy is a byte copy of the fit).
Copies per source (PREREG s14 step 3):
  placed    : the placed mesh (R-prim: the fit as built);
  t3fit     : C1/T3 fit.py + cfg_frozen.json, unchanged (as G2 / G3 stage2.py), on the placed mesh, with the observed
              points of the source's own episode (R-prim joint fits: the joint's reference episode, from its build record);
  trim      : G3/scripts/trim.py (unchanged) of the placed mesh: faces whose centroid is > 15 mm from BOTH our observed rack
              points of the crop episodes (union of obs_all ep12/13/26/27/31, the R crop / view-set episodes) AND the
              13i rack surface; no hole filling;
  outer     : C4-audit/scripts/outer_shell.py (unchanged, s13) of the placed mesh;
  trim_outer: outer_shell.py of the trim copy.
Skipped, with a note in picks.json: no-op copies (trim removed 0 faces; outer dropped nothing; trim_outer when there is
no trim copy, since it would equal outer), failed fits, and any copy that fails the kit budget_mesh(4096, 4096).
-> C4-audit/candidates_rack_r.json (role rack_r, needs_place false, kind placed / t3fit / trim / outer / trim_outer,
source R-gen / R-prim; candidates_g3.json key order plus "source").

The R-gen SELECTION is GT-informed: best-of-N by public-scan CD-O (stage 1, 6 seeds). Placement, fit, trim and outer read
only the candidate, library_v3, the 13i rack (ours) and our observed points (no scan, mocap, parquet pose or *_align).
R-prim fits are not scored here.
Usage: stage2_r.py SCREEN.jsonl GEN_DIR PRIM_LIST.json STAGE2_DIR CANDIDATES_OUT.json [--only gen|prim] [--merge]
  GEN_DIR holds <model>_sim3/<tag>.ply and pixal_mv[_1024]/<tag>.ply as generated (checked against R/results/SHA256SUMS).
  PRIM_LIST.json: [{"label", "path", "episode" ("12".."31" or "all"), "variant", "obs_episode"}] (R/results/prim/).
"""
import argparse, glob, hashlib, json, os, shutil, subprocess, sys
import numpy as np

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
PY = f'{S}/venv/bin/python'
CS = f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint'
PLACE = f'{CS}/C1/T2-probe-picks/scripts/place.py'
FIT = f'{CS}/C1/T3-gen-fit/scripts/fit.py'
CFG = f'{CS}/C1/T3-gen-fit/cfg_frozen.json'
TRIM = f'{CS}/G3/scripts/trim.py'
OUTER = f'{CS}/C4-audit/scripts/outer_shell.py'
SUMS = f'{CS}/R/results/SHA256SUMS'
OBJ = 'plastic_dish_rack'
K = 6
THR_MM = 15
EPS = (12, 13, 26, 27, 31)                     # R crop / view-set episodes = every public rack episode
REF13I = f'{CS}/C4-audit/meshes_13h/plastic_dish_rack_g2_hy21_ep31_k282_s123_lib_t3fit.glb'   # the 13i rack
KIT = f'{S}/loc/kit/v2d_submission_kit'
KINDS = ('placed', 't3fit', 'trim', 'outer', 'trim_outer')
KEYS = ('object', 'label', 'path', 'md5', 'role', 'needs_place', 'cdo_rec', 'stage1_label', 'kind', 'why', 'source', 'note')


def kit_budget(p):
    """GT-free: does the kit's budget_mesh(4096, 4096) (the packer's simplifier) accept the mesh?"""
    if KIT not in sys.path:
        sys.path.insert(0, KIT)
    from v2dlb.mesh_budget import budget_mesh
    try:
        budget_mesh(p, 4096, 4096)
        return 'ok'
    except Exception as e:
        return 'FAIL: ' + str(e).split(': ')[-1][:120]


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def run(cmd, log):
    return subprocess.run(['nice', '-n', '5', PY, '-I'] + cmd, stdout=open(log, 'w'), stderr=subprocess.STDOUT).returncode


def copies(src_glb, stem, obs_ep, base, pick, cands, skipped, obs_union):
    """placed (src_glb itself), t3fit, trim, outer, trim_outer of one stage-2 source; candidates appended to cands."""
    def add(kind, path, extra=None):
        b = kit_budget(path)
        pick.setdefault('kit_budget', {})[kind] = b
        if b != 'ok':
            skipped.append(dict(label=f'{base["label_root"]}/{kind}', kind=kind, path=path,
                                why=f'kit budget_mesh(4096, 4096) fails ({b[6:]})'))
            return False
        c = {k: v for k, v in base.items() if k != 'label_root'}
        c.update(label=f'{base["label_root"]}/{kind}', path=path, md5=md5(path), kind=kind, **(extra or {}))
        cands.append(c)
        return True

    def skip(kind, why):
        skipped.append(dict(label=f'{base["label_root"]}/{kind}', kind=kind, why=why))
        pick.setdefault('skipped', {})[kind] = why

    add('placed', src_glb)
    # t3fit
    fd = stem + '_t3fit'
    obs = f'{S}/obs_all/ep{obs_ep}_{OBJ}.npz'
    fit_in = src_glb
    work = json.load(open(CFG))['work_faces']
    import trimesh
    m0 = trimesh.load(src_glb, force='mesh', process=True)
    if len(m0.faces) <= work:
        # fit.py (unchanged) first decimates its input to work_faces with fast_simplification, which raises when the input
        # has fewer faces (all R-prim fits: 958-3568). Deviation (R NOTES): such inputs get exact midpoint subdivision
        # (trimesh.remesh.subdivide, same surface) until they exceed work_faces, then go to fit.py unchanged.
        v, f, n = np.asarray(m0.vertices), np.asarray(m0.faces), 0
        while len(f) <= work:
            v, f = trimesh.remesh.subdivide(v, f); n += 1
        fit_in = stem + '_sub.glb'
        if not os.path.exists(fit_in):
            trimesh.Trimesh(v, f, process=False).export(fit_in)
        pick.update(fit_input=fit_in, fit_input_subdiv=n, fit_input_faces=int(len(f)), fit_input_faces_orig=int(len(m0.faces)))
    if not os.path.exists(os.path.join(fd, 'fit.glb')) and not os.path.exists(fd + '.out'):
        pick['fit_rc'] = subprocess.run(['nice', '-n', '5', PY, '-I', FIT, '--mesh', fit_in, '--obs', obs, '--out', fd,
                                         '--cfg', CFG], stdout=open(fd + '.out', 'w'), stderr=subprocess.STDOUT).returncode
    d = json.load(open(os.path.join(fd, 'diag.json'))) if os.path.exists(os.path.join(fd, 'diag.json')) else {}
    if 'final' not in d:                           # fit.py did not finish: no t3fit candidate (G3 deviation 6)
        err = [l.strip() for l in open(fd + '.out')] if os.path.exists(fd + '.out') else ['no fit output']
        pick['fit_failed'] = err[-1][-300:] if err else 'empty fit log'
        skip('t3fit', 'fit failed: ' + pick['fit_failed'][-160:])
    else:
        fg = fd + '.glb'
        if not os.path.exists(fg):
            shutil.copyfile(os.path.join(fd, 'fit.glb'), fg)
        st = {x['tag']: x for x in d['stages']}
        pick.update(fit=fg, fit_md5=md5(fg), fit_obs=obs, fit_held_tmean90_in=st['input']['held_o2m']['tmean90_mm'],
                    fit_held_tmean90_fit=st.get('stage_0', {}).get('held_o2m', {}).get('tmean90_mm'),
                    fit_faces=d['final']['faces'], fit_watertight=d['final']['watertight'])
        add('t3fit', fg)
    # trim
    tg = stem + '_trim15.glb'
    if not os.path.exists(tg + '.json'):
        pick['trim_rc'] = run([TRIM, src_glb, REF13I, tg, str(THR_MM)] + obs_union, stem + '_trim15.out')
    if os.path.exists(tg + '.json'):
        ti = json.load(open(tg + '.json'))
        pick.update(trim_faces_removed=ti['faces_removed'], trim_faces_in=ti['faces_in'],
                    trim_area_removed_frac=ti['area_removed_frac'], trim_ref=REF13I)
        if ti['faces_removed'] == 0:
            skip('trim', 'no-op: trim removed 0 faces')
        else:
            pick.update(trim=tg, trim_md5=md5(tg))
            add('trim', tg)
    else:
        skip('trim', 'trim.py failed (see _trim15.out)')

    # outer of placed, outer of trim
    def outer(src, out, kind):
        rj = out + '.json'
        if not os.path.exists(rj):
            r = subprocess.run(['nice', '-n', '5', PY, '-I', OUTER, src, out], capture_output=True, text=True)
            open(rj, 'w').write(r.stdout.strip() or json.dumps(dict(error=r.stderr[-300:])))
        rep = json.loads(open(rj).read())
        pick[f'{kind}_report'] = dict(n_components=rep.get('n_components'), dropped=rep.get('dropped'),
                                      out_faces=rep.get('out_faces'), error=rep.get('error'),
                                      drops=[c['drop'] for c in rep.get('components', []) if 'drop' in c][:20])
        if rep.get('error'):
            skip(kind, 'outer_shell.py failed: ' + rep['error'][-160:])
        elif not rep.get('out'):
            skip(kind, 'no-op: outer_shell dropped nothing')
        else:
            add(kind, out)
    outer(src_glb, stem + '_outer.glb', 'outer')
    if pick.get('trim_faces_removed', 0) > 0 and os.path.exists(tg):        # outer of the trim (even if the trim copy failed the budget)
        outer(tg, stem + '_trim15_outer.glb', 'trim_outer')
    else:
        skip('trim_outer', 'no trim copy (trim no-op or skipped): outer of the trim would equal the outer copy')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('screen'); ap.add_argument('gen_dir'); ap.add_argument('prim_list'); ap.add_argument('out_dir')
    ap.add_argument('cands'); ap.add_argument('--only', default=None, choices=('gen', 'prim'))
    ap.add_argument('--merge', action='store_true')
    ap.add_argument('--part', default='', help='suffix for parallel --only prim runs over split prim lists')
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    if a.merge:
        picks, cands, skipped = [], [], []
        for f in sorted(glob.glob(os.path.join(a.out_dir, 'picks_*.json'))):     # picks_gen, picks_prim<part>
            sfx = os.path.basename(f)[len('picks'):-len('.json')]
            picks += json.load(open(f))
            cands += json.load(open(a.cands + sfx))
            skipped += json.load(open(os.path.join(a.out_dir, f'skipped{sfx}.json')))
        RUNS = ('base', 'E', 'K', 'Q')                                         # R-prim runs in build order
        picks.sort(key=lambda p: (p['source'] != 'R-gen', p.get('rank', 0),
                                  RUNS.index(p['label'].split('_')[0]) if p['source'] == 'R-prim' else 0, p['label']))
        order = {p['label']: i for i, p in enumerate(picks)}
        cands.sort(key=lambda c: (order[c['stage1_label'] if c['source'] == 'R-gen' else c['label'].split('/')[3]],
                                  KINDS.index(c['kind'])))
        scan_md5 = {md5(f) for f in glob.glob(f'{S}/loc/t3/mesh/*/*.glb')}  # s3 adoptability: no byte copy of a scan
        assert len(scan_md5) >= 10 and not any(c['md5'] in scan_md5 for c in cands), 'candidate equals a scan file'
        print(f'md5 check: none of {len(cands)} candidates equals any of {len(scan_md5)} public scan files')
        meas = json.load(open(os.path.join(a.out_dir, 'measured_rack.json')))     # scripts/measured_rack.py
        hit = [c['label'] for c in cands if c['md5'] in meas['md5'] or
               hashlib.sha1(open(c['path'], 'rb').read()).hexdigest()[:16] in meas['sha1_16']]
        assert not hit, f'candidate equals an already-measured file: {hit}'
        print(f'hash check: none of {len(cands)} candidates equals any already-measured rack file '
              f'({len(meas["sha1_16"])} sha1, {len(meas["md5"])} md5)')
        dup = {}
        for c in cands:
            dup.setdefault(c['md5'], []).append(c['label'])
        dups = {k: v for k, v in dup.items() if len(v) > 1}
        if dups:                                                   # identical files: keep the first, note the rest
            drop = {l for v in dups.values() for l in v[1:]}
            for c in cands:
                if c['label'] in drop:
                    skipped.append(dict(label=c['label'], kind=c['kind'], why='duplicate bytes of ' + dup[c['md5']][0]))
            cands = [c for c in cands if c['label'] not in drop]
        cands = [{k: c[k] for k in KEYS if k in c} for c in cands]
        json.dump(picks, open(os.path.join(a.out_dir, 'picks.json'), 'w'), indent=1)
        json.dump(skipped, open(os.path.join(a.out_dir, 'skipped.json'), 'w'), indent=1)
        json.dump(cands, open(a.cands, 'w'), indent=1)
        n = {k: sum(c['kind'] == k for c in cands) for k in KINDS}
        print(f'merged {len(picks)} sources, {len(cands)} candidates {n}, {len(skipped)} skipped -> {a.cands}')
        return
    assert os.path.exists(REF13I), REF13I
    obs_union = [f'{S}/obs_all/ep{e}_{OBJ}.npz' for e in EPS]
    picks, cands, skipped = [], [], []
    if a.only in (None, 'gen'):
        sums = {}
        for l in open(SUMS):
            h, p = l.split()
            sums[p] = h
        recs = [json.loads(l) for l in open(a.screen) if l.strip()]
        rows = [r for r in recs if r['object'] == OBJ and 'screen' in r]
        rows.sort(key=lambda r: (r['screen']['summary']['cdo_med'], r['screen']['summary']['cdo_mean'], r['label']))
        print(f'{len(rows)} screened; top {K}: {[(r["label"], r["screen"]["summary"]["cdo_med"]) for r in rows[:K]]}',
              flush=True)
        for rank, r in enumerate(rows[:K], 1):
            model, tag = r['label'].split('/')[1:3]               # r/<model>/<tag>
            rel = f'gen/{model}/{tag}.ply' if model.startswith('pixal_mv') else f'gen/{model}_sim3/{tag}.ply'
            src = os.path.join(a.gen_dir, rel[len('gen/'):])
            assert sha256(src) == sums[rel], f'hash mismatch {src}'
            ep = tag.split('_')[0][2:]
            stem = os.path.join(a.out_dir, f'{OBJ}_r_{model}_{tag.replace(OBJ + "_", "")}_lib')
            if not os.path.exists(stem + '.glb'):
                subprocess.run([PY, '-I', PLACE, OBJ, src, f'{REPO}/meshes/library_v3/{OBJ}.glb', stem], check=True,
                               stdout=subprocess.DEVNULL, cwd=a.out_dir)
            pl = json.load(open(stem + '.json'))
            s1 = r['screen']['summary']
            pick = dict(source='R-gen', why='cdo_top6', rank=rank, label=r['label'], model=model, tag=tag, episode=ep,
                        source_file=rel, source_sha256=sums[rel], stage1=s1, placed=stem + '.glb',
                        placed_md5=md5(stem + '.glb'), place_residual_mm=pl['residual_mm'],
                        place_best_start=pl['best_start'], place_identity_residual_mm=pl.get('identity_start_residual_mm'),
                        place_second_distinct_residual_mm=pl['second_distinct_residual_mm'])
            base = dict(object=OBJ, role='rack_r', needs_place=False, cdo_rec=s1['cdo_med'], stage1_label=r['label'],
                        why='cdo_top6', source='R-gen', label_root=f'R/{OBJ}/{model}/{tag}')
            copies(stem + '.glb', stem, ep, base, pick, cands, skipped, obs_union)
            picks.append(pick)
            print(json.dumps({k: v for k, v in pick.items() if k not in ('stage1',)}), flush=True)
    if a.only in (None, 'prim'):
        for p in json.load(open(a.prim_list)):
            stem = os.path.join(a.out_dir, f'{OBJ}_rprim_{p["label"]}')
            if not os.path.exists(stem + '.glb'):
                shutil.copyfile(p['path'], stem + '.glb')
            assert md5(stem + '.glb') == p['md5'], p
            pick = dict(source='R-prim', why='r_prim', label=p['label'], episode=p['episode'], variant=p['variant'],
                        source_file=p['path'], source_md5=p['md5'], placed=stem + '.glb', placed_md5=md5(stem + '.glb'),
                        t3fit_obs_episode=p['obs_episode'])
            base = dict(object=OBJ, role='rack_r', needs_place=False, cdo_rec=None, stage1_label=None, why='r_prim',
                        source='R-prim', label_root=f'R/{OBJ}/prim/{p["label"]}')
            copies(stem + '.glb', stem, p['obs_episode'], base, pick, cands, skipped, obs_union)
            picks.append(pick)
            print(json.dumps(pick), flush=True)
    sfx = f'_{a.only}{a.part}' if a.only else ''
    json.dump(picks, open(os.path.join(a.out_dir, f'picks{sfx}.json'), 'w'), indent=1)
    json.dump(skipped, open(os.path.join(a.out_dir, f'skipped{sfx}.json'), 'w'), indent=1)
    json.dump(cands, open(a.cands + sfx, 'w'), indent=1)
    print(f'{len(picks)} sources, {len(cands)} candidates, {len(skipped)} skipped -> {a.cands + sfx}')


if __name__ == '__main__':
    main()
