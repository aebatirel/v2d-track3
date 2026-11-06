"""E0 select and package (CD-O sprint). GT-free; reads only our files.

1. Re-applies PREREG.md section 4 (exclusions, then the pick) and section 6 (recommendation) independently of
   jobs/e0_select.py, from the box's raw rows: results/e0/candidates.json, fid/*/*.jsonl (obs_fidelity.py),
   check/*/*.json (C0 frame_check.py), with inputs/thresholds.json. Recomputes no fidelity and no check: it stops if
   one is missing. Asserts that the pick, eligible set, exclusions and recommendation equal the box's selection.json,
   and that each pick's local bytes match the check's sha256 and the box SHA256SUMS.
2. Packages: E0/meshes/<pick>.glb (+ build record), meshes/library_e0 = meshes/library_c0 with blue_cup.glb from
   meshes/library_v3 and every object recommended E0 replaced by its E0 pick; meshes/library_e0x = the same over
   meshes/library_c0x / library_v3x (eval 8). Refuses to overwrite an existing library or pick that differs.
3. Writes E0/MANIFEST.json (36 pairs from ../C0/roster.json) and E0/selection_final.json.

Usage (run with python -I; R is downloaded data):
  python -I e0_package.py --results R --repo REPO --run_id RUN --run_info JSON
"""
import argparse, glob, hashlib, json, os, shutil

SHORT = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup'}
BOX_R = '/content/results/e0'
BUDGET_MAX = 4096


def digest(path, algo):
    d = hashlib.new(algo)
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            d.update(b)
    return d.hexdigest()


def local(R, box_path):
    assert box_path.startswith(BOX_R + '/'), box_path
    return R + box_path[len(BOX_R):]


def load_fid(R):
    fid = {}
    for f in sorted(glob.glob(f'{R}/fid/*/*.jsonl')):
        lab, s = os.path.basename(f)[:-6].replace('__', '/').rsplit('@', 1)
        rows = [json.loads(l) for l in open(f) if l.startswith('{')]
        assert len(rows) <= 1, f
        if rows:
            fid[(lab, s)] = rows[0]
    return fid


def apply_rule(o, cands, fid, R, th, sums):
    """PREREG section 4, written from the PREREG text (not from e0_select.py)."""
    rows = []
    for c in cands:
        if c['object'] != o:
            continue
        lab = c['label']
        r = dict(label=lab, kind=c['kind'], episode=c['episode'], variant=c['variant'], box_path=c['path'])
        fa = fid.get((lab, 'all'))
        r['fid_all'] = fa
        r['fid_ep'] = {s: v['sum_mm'] for (l, s), v in fid.items() if l == lab and s != 'all'}
        excl = []
        if c['kind'] != 'library_v3':
            ck = f"{R}/check/{SHORT[o]}/{lab.replace('/', '__')}.json"
            if not os.path.exists(ck):
                excl.append('no check (kit budget_mesh raised or check crashed)')
            else:
                k = json.load(open(ck))['results'][o]
                b = k['budget_new']
                r.update(sha256=k['new']['sha256'], faces_raw=k['new']['faces_raw'],
                         watertight_raw=k['new']['watertight_raw'], bodies_raw=k['new']['bodies_raw'], budget=b,
                         centroid_offset_mm=k['centroid_offset_mm'],
                         surf_symmetric_median_mm=k['surf_symmetric_median_mm'], axis_angle_deg=k['axis_angle_deg'])
                if c['kind'] == 'e0':
                    lp = local(R, c['path'])
                    assert digest(lp, 'sha256') == k['new']['sha256'], ('check sha mismatch', lab)
                    rel = './' + os.path.relpath(lp, R)
                    assert sums.get(rel) == k['new']['sha256'], ('SHA256SUMS mismatch', lab)
                if not k['new']['watertight_raw']:
                    excl.append('raw mesh not watertight')
                if not (b['faces'] <= BUDGET_MAX and b['vertices'] <= BUDGET_MAX and b['faces_ok'] and b['vertices_ok']):
                    excl.append('kit budget_mesh leaves > 4096 faces or vertices')
                if k['centroid_offset_mm'] > th['max_centroid_offset_mm']:
                    excl.append('frame: centroid offset beyond 3x C0')
                if k['surf_symmetric_median_mm'] > th['max_surf_symmetric_median_mm']:
                    excl.append('frame: median surface distance beyond 3x C0')
                for i, (ang, mx) in enumerate(zip(k['axis_angle_deg'], th['max_axis_angle_deg'])):
                    if mx is not None and ang > mx:
                        excl.append(f'frame: axis {i} angle beyond 3x C0')
        if fa is None:
            excl.append('no fidelity on ALL')
        r['excluded'] = excl
        rows.append(r)
    e0 = [r for r in rows if r['kind'] == 'e0']
    ok = sorted([r for r in e0 if not r['excluded']],
                key=lambda r: (r['fid_all']['sum_mm'], r['faces_raw'], r['label']))
    c0 = [r for r in rows if r['kind'] == 'C0']
    lib = [r for r in rows if r['kind'] == 'library_v3']
    assert len(c0) == 1 and len(lib) == 1
    return rows, e0, ok, c0[0], lib[0]


def recommend(o, ok, c0, lib):
    """PREREG section 6."""
    flags = []
    if not ok:
        return ('library_v3' if o == 'blue_cup' else 'C0'), ['no eligible E0 candidate'], None, None
    p = ok[0]['fid_all']['sum_mm']
    rc0 = c0['fid_all']['sum_mm'] / p
    rlib = lib['fid_all']['sum_mm'] / p
    if o == 'blue_cup':
        rec = 'E0'
        if rlib < 0.85:
            rec = 'library_v3'; flags.append('library_v3 beats the E0 pick by > 15 % (fidelity)')
        if rc0 < 0.85:
            flags.append('C0 cup (held back) beats the E0 pick by > 15 % (report only)')
    else:
        rec = 'E0'
        if rc0 < 0.85:
            rec = 'C0'; flags.append('C0 beats the E0 pick by > 15 % (fidelity): owner flag')
    return rec, flags, rc0, rlib


def fid_brief(fa):
    return None if fa is None else dict(sum_mm=fa['sum_mm'], obs_to_mesh_mm=fa['obs_to_mesh_mm'],
                                        mesh_to_obs_mm=fa['mesh_to_obs_mm'])


def pick_name(o, r):
    ep, var = r['episode'], r['variant']
    return f'{o}_eval{ep}_{var}' if str(ep).isdigit() else f'{o}_eval_{ep}_{var}'


def build_record(R, o, r):
    """Small sidecar files of the pick's build (paths on the box -> local)."""
    lp = local(R, r['box_path'])
    out = []
    for cand in (lp[:-4] + '.json', lp[:-4] + '.lathe.json'):
        if os.path.exists(cand):
            out.append(cand)
    if o == 'plastic_dish_rack':
        d = os.path.dirname(lp)
        ep = r['episode']
        out.append(os.path.join(d, 'joint.json' if not str(ep).isdigit() else f'ep{ep}.json'))
    if o == 'white_pot':
        out.append(f"{R}/axis/ep{r['episode']}_white_pot.json")
    return [p for p in out if os.path.exists(p)]


def safe_copy(src, dst):
    if os.path.exists(dst):
        assert digest(src, 'sha256') == digest(dst, 'sha256'), f'refusing to overwrite differing {dst}'
        return
    shutil.copyfile(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True); ap.add_argument('--repo', required=True)
    ap.add_argument('--run_id', required=True); ap.add_argument('--run_info', required=True)
    a = ap.parse_args()
    R, REPO = a.results, a.repo
    E0 = f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint/E0'
    C0 = f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint/C0'
    TH = json.load(open(f'{E0}/inputs/thresholds.json'))['objects']
    plan = json.load(open(f'{E0}/inputs/plan.json'))
    roster = json.load(open(f'{C0}/roster.json'))
    c0man = json.load(open(f'{C0}/MANIFEST.json'))
    cands = json.load(open(f'{R}/candidates.json'))
    box_sel = json.load(open(f'{R}/selection.json'))
    sums = {}
    for l in open(f'{R}/SHA256SUMS'):
        h, p = l.rstrip('\n').split('  ', 1)
        sums[p] = h
    fid = load_fid(R)

    # ---- 1. rule ----
    sel = {}
    for o in plan['objects']:
        rows, e0, ok, c0, lib = apply_rule(o, cands, fid, R, TH[o], sums)
        rec, flags, rc0, rlib = recommend(o, ok, c0, lib)
        pick = ok[0] if ok else None
        runner = ok[1] if len(ok) > 1 else None
        runner_distinct = next((r for r in ok[1:] if r['sha256'] != pick['sha256']), None) if pick else None
        # cross-check against the box selection.json
        b = box_sel[o]
        assert (b['pick']['label'] if b['pick'] else None) == (pick['label'] if pick else None), o
        assert b['recommendation'] == rec and b['flags'] == flags, o
        assert b['n_eligible'] == len(ok) and b['n_candidates'] == len(e0), o
        bex = {r['label']: bool(r['excluded']) for r in b['table']}
        assert bex == {r['label']: bool(r['excluded']) for r in rows}, o

        def brief(r):
            if r is None:
                return None
            return dict(label=r['label'], fid_all=fid_brief(r['fid_all']), faces_raw=r.get('faces_raw'),
                        sha256=r.get('sha256'))
        sel[o] = dict(
            eval_episodes=plan['episodes_by_object'][o], n_candidates=len(e0), n_eligible=len(ok),
            excluded={r['label']: r['excluded'] for r in e0 if r['excluded']},
            ranking=[dict(label=r['label'], fid_all_sum_mm=r['fid_all']['sum_mm'], faces_raw=r['faces_raw'],
                          sha256_16=r['sha256'][:16]) for r in ok],
            pick=dict(brief(pick), episode=pick['episode'], variant=pick['variant'], box_path=pick['box_path'],
                      fid_ep=pick['fid_ep'], watertight_raw=pick['watertight_raw'], bodies_raw=pick['bodies_raw'],
                      budget=pick['budget'], centroid_offset_mm=pick['centroid_offset_mm'],
                      surf_symmetric_median_mm=pick['surf_symmetric_median_mm'],
                      axis_angle_deg=pick['axis_angle_deg']) if pick else None,
            runner_up=brief(runner),
            runner_up_note=(None if runner is None or runner_distinct is None or runner is runner_distinct else
                            f"{runner['label']} is byte-identical to the pick (same sha256); the first different "
                            f"mesh is {runner_distinct['label']}"),
            runner_up_distinct=brief(runner_distinct),
            c0=dict(label=c0['label'], fid_all=fid_brief(c0['fid_all']), fid_ep=c0['fid_ep']),
            library_v3=dict(label=lib['label'], fid_all=fid_brief(lib['fid_all']), fid_ep=lib['fid_ep']),
            c0_over_pick=rc0, library_v3_over_pick=rlib, recommendation=rec, rule_flags=flags,
            per_episode=b['per_episode'],
            box_selection_agrees=True)

    # ---- 2. package ----
    os.makedirs(f'{E0}/meshes', exist_ok=True)
    picks = {}
    for o, s in sel.items():
        if s['recommendation'] != 'E0':
            continue
        name = pick_name(o, s['pick'])
        src = local(R, s['pick']['box_path'])
        dst = f'{E0}/meshes/{name}.glb'
        safe_copy(src, dst)
        recs = []
        for rp in build_record(R, o, s['pick']):
            bn = os.path.basename(rp)
            tag = 'axis' if '/axis/' in rp else ('lathe' if bn.endswith('.lathe.json') else 'build')
            d2 = f'{E0}/meshes/{name}.{tag}.json'
            safe_copy(rp, d2)
            recs.append(os.path.relpath(d2, REPO))
        picks[o] = dict(path=os.path.relpath(dst, REPO), sha256=digest(dst, 'sha256'), md5=digest(dst, 'md5'),
                        bytes=os.path.getsize(dst), build_records=recs,
                        box_path=s['pick']['box_path'].replace(BOX_R, f'runs/{a.run_id}/results/e0'))
        assert picks[o]['sha256'] == s['pick']['sha256']

    libs = {}
    for c0lib, v3lib, e0lib in (('library_c0', 'library_v3', 'library_e0'), ('library_c0x', 'library_v3x', 'library_e0x')):
        srcd, v3d, dstd = f'{REPO}/meshes/{c0lib}', f'{REPO}/meshes/{v3lib}', f'{REPO}/meshes/{e0lib}'
        os.makedirs(dstd, exist_ok=True)
        plan_files = {}
        for f in sorted(os.listdir(srcd)):
            if f == 'README.md':
                continue
            plan_files[f] = (f'{srcd}/{f}', f'meshes/{c0lib}/{f}')
        plan_files['blue_cup.glb'] = (f'{v3d}/blue_cup.glb', f'meshes/{v3lib}/blue_cup.glb')
        for o in picks:
            plan_files[f'{o}.glb'] = (f'{REPO}/{picks[o]["path"]}', picks[o]['path'])
        files = {}
        for f, (src, srel) in plan_files.items():
            safe_copy(src, f'{dstd}/{f}')
            fp = f'{dstd}/{f}'
            files[f] = dict(sha256=digest(fp, 'sha256'), md5=digest(fp, 'md5'), bytes=os.path.getsize(fp), source=srel,
                            same_as_c0=os.path.exists(f'{srcd}/{f}') and digest(f'{srcd}/{f}', 'sha256') == digest(fp, 'sha256'),
                            same_as_v3=os.path.exists(f'{v3d}/{f}') and digest(f'{v3d}/{f}', 'sha256') == digest(fp, 'sha256'))
        extra = set(os.listdir(dstd)) - set(files) - {'README.md'}
        assert not extra, f'unexpected files in {dstd}: {extra}'
        # every glb that is not an E0 swap equals library_v3(x)
        for f, v in files.items():
            if f.endswith('.glb') and f[:-4] not in picks:
                assert v['same_as_v3'], (e0lib, f)
        libs[e0lib] = dict(base=f'meshes/{c0lib}', blue_cup_from=f'meshes/{v3lib}/blue_cup.glb',
                           swapped_by_e0=sorted(picks), files=files)

    # ---- 3. manifest ----
    run_info = json.loads(a.run_info)
    MARKER = ("MARKER BALLS: the frozen prim_potlid.py (sha1 c2627630; markers_from is also used by prim_rack.py) "
              "falls back to a fixed ball radius MK_R0 = 7 mm and accepts a free sphere fit only inside 5-9.5 mm; both "
              "values are SCAN-DERIVED (same flag as C0, verify_0 B1; work log 27 Oct ~17:20 UTC). E0 used the frozen "
              "public code unchanged, so this mesh carries the prior. In this mesh's build record: {}.")
    THICK = ("THICKNESS: {} = 2.5 mm is the grid midpoint of the public clean-up round (passed at 1.5 / 2.5 / 4.0 mm); "
             "it equals the value that once leaked from scan measurements; not chosen by any eval number (our points "
             "cannot measure it).")
    INSAMPLE = ("IN-SAMPLE PICK: chosen by obs_fidelity on the same eval points it was fitted to (PREREG 7); C0 and "
                "library_v3 are out-of-sample there. Fidelity is not CD-O (public Spearman 0.85 over 32 pot "
                "candidates, 0.5 over 5 cup candidates). No eval ground truth exists: E0 is not scored.")
    QUAL = ("METHOD QUALIFIER: the object set and each object's method come from C0, which was chosen with public-scan "
            "[D] scores; within that, the E0 pick is GT-free under PREREG.md (pre-registered before any eval candidate).")

    def marker_note(o):
        recp = [p for p in picks[o]['build_records'] if p.endswith('.build.json')]
        if not recp:
            return 'no build record'
        j = json.load(open(f'{REPO}/{recp[0]}'))
        mk = j.get('markers') if 'markers' in j else (j.get('info') or {}).get('markers')
        if not mk:
            return 'no markers recorded'
        acc = [m for m in mk if not m.get('rejected')]
        return (f"{len(acc)} ball(s) kept by the build: " + ', '.join(f"{m.get('mode')} r {m.get('r_mm')} mm"
                                                         + (f" (free fit {m.get('free_r_mm')} mm)" if m.get('mode') == 'prior' else '')
                                                         for m in acc) + f"; {len(mk) - len(acc)} cluster(s) rejected")

    obj_flags, obj_method = {}, {}
    for o in picks:
        s = sel[o]; p = s['pick']; fl = []
        if o in ('white_pot', 'white_pot_lid', 'plastic_dish_rack'):
            fl.append(MARKER.format(marker_note(o)))
        if o == 'white_pot_lid':
            fl.append(THICK.format('T_LID (PRIM_T_LID=0.0025)'))
        if o == 'plastic_dish_rack':
            fl.append(THICK.format('T_WALL (PRIM_T_WALL=0.0025)'))
        fl.append(INSAMPLE)
        if s['c0_over_pick'] < 1:
            fl.append(f"DOES NOT BEAT C0 EVEN IN-SAMPLE: C0 {s['c0']['fid_all']['sum_mm']} mm vs pick "
                      f"{p['fid_all']['sum_mm']} mm on ALL (C0/pick {s['c0_over_pick']:.3f}); within the 15 % margin, "
                      f"so E0 by PREREG 6.")
        if s['library_v3_over_pick'] < 1:
            better = [e for e, v in s['per_episode'].items() if v['library_v3_fid'] < v['pick_fid']]
            allf = [r['fid_all_sum_mm'] for r in s['ranking']] + [s['c0']['fid_all']['sum_mm']]
            lowest = all(s['library_v3']['fid_all']['sum_mm'] < v for v in allf) and s['n_eligible'] == s['n_candidates']
            fl.append(f"LIBRARY_V3 LOWER FIDELITY: library_v3 {s['library_v3']['fid_all']['sum_mm']} mm vs pick "
                      f"{p['fid_all']['sum_mm']} mm on ALL"
                      + (f" (lowest of all {s['n_candidates'] + 2} meshes of this object)" if lowest else '') + " "
                      f"and lower on {', '.join(better)}; PREREG 6 compares only C0 for this object, so this is a "
                      f"reviewer note, not a rule flag.")
        if o == 'blue_cup':
            fl.append(f"FRAME (GT-free check vs library_v3, no registration): centroid {p['centroid_offset_mm']:.1f} mm, "
                      f"median surface distance {p['surf_symmetric_median_mm']:.2f} mm, major-axis angle "
                      f"{p['axis_angle_deg'][0]:.1f} deg (middle/minor axes ill-defined for a lathe, not checked).")
            worst = max(s['per_episode'], key=lambda e: s['per_episode'][e]['pick_fid'])
            fl.append("EVAL 10: the blue cup nests the beige cup with a ~5 mm track offset in nest frames (work log "
                      f"31 Oct 13:55); the pick's worst per-episode fidelity is on {worst} "
                      f"({s['per_episode'][worst]['pick_fid']} mm; own-episode best there "
                      f"{s['per_episode'][worst]['own_best']} {s['per_episode'][worst]['own_best_fid']} mm).")
        if not p['budget']['watertight']:
            fl.append(f"after the kit budget_mesh the mesh is not watertight ({p['budget']['bodies']} bodies); the kit "
                      f"never checks watertightness")
        fl.append(QUAL)
        obj_flags[o] = fl
    obj_method['white_pot'] = ("kit-of-parts primitive assembly, `prim_potlid.py pot obs/ep{e}_white_pot.npz OUT --variant {v} "
                               "--lib meshes/library_v3/white_pot.glb --axis_cache axis/ep{e}_white_pot.json`")
    obj_method['white_pot_lid'] = ("kit-of-parts, `PRIM_T_LID=0.0025 prim_potlid.py lid obs/ep{e}_white_pot_lid.npz OUT "
                                   "--variant {v2} --lib meshes/library_v3/white_pot_lid.glb`")
    obj_method['plastic_dish_rack'] = ("kit-of-parts, `PRIM_T_WALL=0.0025 PRIM_CUP_LEAN=1 prim_rack.py run --obs_dir obs "
                                       "--out cand/rack/t2.5_lean1 --episodes 14,15,16,28,30`, variant {v}")
    obj_method['blue_cup'] = ("observed-point lathe, `lathe_obs.py obs/ep{e}_blue_cup.npz OUT` (all defaults = g1: hollow "
                              "lathe + observed appendages)")
    common = (". Frozen public code of commit 2971a10 (E0/jobs/frozen, SHA1SUMS) on Vast run {run} (code commit {c}); "
              "observed points: obs_points.py (public prep_obs.sh command: stride 2, --hands from MediaPipe hands_mp.py "
              "on eval cam_a video, --others = the episode's other library_v3 bodies, --roi library_v3) on our "
              "library_v3-anchored eval tracks and FoundationStereo eval depth (no scan, mocap, parquet pose or "
              "_align file).")

    def method_for(o, p):
        v = p['variant']
        m = obj_method[o].format(e=p['episode'], v=v, v2=v.split('_', 1)[-1])
        if o == 'plastic_dish_rack' and not str(p['episode']).isdigit():
            j = json.load(open(f"{REPO}/{[q for q in picks[o]['build_records'] if q.endswith('.build.json')][0]}"))
            mem = [e['obs'].split('_')[0] for e in j['alignment']['episodes']]
            m += (f"; joint fit over {', '.join(mem)} (episodes whose own full fit is within JOINT_TOL 1.25 of the "
                  f"best, rigidly aligned on their points, moved to the mean frame)")
        else:
            m += f", fitted to eval {p['episode']} observed points"
        return m + common.format(run=a.run_id, c=run_info.get('commit', '?'))

    pairs = []
    for rp in roster['pairs']:
        o, e = rp['object'], rp['eval_episode']
        x = 'library_v3x' in rp['pack7_mesh']
        lib = 'library_e0x' if x else 'library_e0'
        c0lib = 'library_c0x' if x else 'library_c0'
        f = libs[lib]['files'][f'{o}.glb']
        c0p = next(q for q in c0man['pairs'] if q['eval_episode'] == e and q['slot'] == rp['slot'])
        assert c0p['object'] == o
        c0sha = digest(f'{REPO}/meshes/{c0lib}/{o}.glb', 'sha256')
        ent = dict(eval_episode=e, slot=rp['slot'], object=o, mesh=f'meshes/{lib}/{o}.glb', sha256=f['sha256'],
                   md5=f['md5'], bytes=f['bytes'])
        if o in picks:
            s = sel[o]; p = s['pick']; ep = f'ep{e}'
            ent.update(
                e0_swapped=True, source=picks[o]['path'], source_box=picks[o]['box_path'], e0_label=p['label'],
                method=method_for(o, p),
                selection=(f"PREREG.md section 4 (exclusions, then lowest obs_fidelity sum_mm on ALL eval points of the "
                           f"object): pick of {s['n_eligible']} eligible / {s['n_candidates']} candidates; runner-up "
                           f"{(s['runner_up_distinct'] or {}).get('label')}; recommendation {s['recommendation']} by "
                           f"section 6"),
                fidelity=dict(set_all=p['fid_all'], this_episode=dict(
                    e0_pick_sum_mm=s['per_episode'][ep]['pick_fid'], c0_sum_mm=s['per_episode'][ep]['c0_fid'],
                    library_v3_sum_mm=s['per_episode'][ep]['library_v3_fid'],
                    own_episode_best=s['per_episode'][ep]['own_best'],
                    own_episode_best_sum_mm=s['per_episode'][ep]['own_best_fid']),
                    c0_all_sum_mm=s['c0']['fid_all']['sum_mm'], library_v3_all_sum_mm=s['library_v3']['fid_all']['sum_mm'],
                    note='obs_fidelity.py defaults (trim 0.9), mm; GT-free; in-sample for E0 [M]'),
                flags=obj_flags[o], rule_flags=s['rule_flags'])
        else:
            ent.update(e0_swapped=False, source=f"meshes/{c0lib}/{o}.glb (byte-identical to {rp['pack7_mesh']})",
                       method='unchanged from library_c0 / pack 7 (not an E0 object)', fidelity=None,
                       flags=[], rule_flags=[])
            assert f['sha256'] == rp['pack7_sha256'], (o, e)
        ent.update(c0_mesh=f'meshes/{c0lib}/{o}.glb', c0_sha256=c0sha, differs_from_c0=f['sha256'] != c0sha,
                   pack7_mesh=rp['pack7_mesh'], pack7_sha256=rp['pack7_sha256'],
                   differs_from_pack7=f['sha256'] != rp['pack7_sha256'], c0_in_pack_9a=c0p.get('in_pack_9a'))
        pairs.append(ent)
    assert len(pairs) == roster['n_pairs'] == 36

    man = dict(
        candidate='E0',
        description=("C0's mesh methods (kit-of-parts pot, lid, rack; observed-point lathe blue cup) rebuilt with the "
                     "same frozen public settings on each EVAL episode where the object appears; one mesh per object "
                     "picked GT-free by the pre-registered rule (PREREG.md) and shipped for every eval pair of it."),
        status=("packaged; not scored (no eval ground truth exists). Recommendation by PREREG section 6: "
                + ', '.join(f"{o} {sel[o]['recommendation']}" for o in sel) + '. Owner decides what ships.'),
        prereg=dict(path='docs/research/mesh-2026-10-26/cdo-sprint/E0/PREREG.md',
                    sha256=digest(f'{E0}/PREREG.md', 'sha256')),
        run=dict(run_id=a.run_id, **run_info,
                 results_store=f'aebatirel/v2d-store runs/{a.run_id}/results/e0/',
                 report='docs/research/mesh-2026-10-26/cdo-sprint/E0/BOX.md'),
        rule='packed mesh only; simulator copies and rollouts unchanged (as C0)',
        libraries={k: dict(v, path=f'meshes/{k}') for k, v in libs.items()},
        library_use=('meshes/library_e0 for every eval pair except eval 8; meshes/library_e0x for eval 8 '
                     '(as library_v3 / library_v3x and library_c0 / library_c0x)'),
        selection={o: {k: v for k, v in s.items() if k not in ('per_episode',)} for o, s in sel.items()},
        picks=picks,
        n_pairs=len(pairs),
        n_e0_swapped=sum(p['e0_swapped'] for p in pairs),
        n_differs_from_c0=sum(p['differs_from_c0'] for p in pairs),
        n_differs_from_pack7=sum(p['differs_from_pack7'] for p in pairs),
        pairs=pairs,
        integrity=("Inference inputs: our eval tracks, eval stereo depth, eval videos, calibration, kit mesh_budget, "
                   "library_v3 meshes (ROI / others / frame check). Nothing read a scan, mocap, a parquet pose field or "
                   "an *_align file (jobs/e0_stage_inputs.py asserted the upload). No setting was tuned on eval."),
    )
    json.dump(man, open(f'{E0}/MANIFEST.json', 'w'), indent=1)
    json.dump(sel, open(f'{E0}/selection_final.json', 'w'), indent=1)
    for o, s in sel.items():
        print(json.dumps(dict(object=o, pick=s['pick']['label'] if s['pick'] else None,
                              pick_fid=s['pick']['fid_all']['sum_mm'] if s['pick'] else None,
                              runner_up=(s['runner_up'] or {}).get('label'),
                              runner_up_distinct=(s['runner_up_distinct'] or {}).get('label'),
                              runner_up_distinct_fid=((s['runner_up_distinct'] or {}).get('fid_all') or {}).get('sum_mm'),
                              c0=s['c0']['fid_all']['sum_mm'], lib=s['library_v3']['fid_all']['sum_mm'],
                              rec=s['recommendation'], flags=s['rule_flags'],
                              eligible=f"{s['n_eligible']}/{s['n_candidates']}",
                              excluded=s['excluded'])))
    for o, p in picks.items():
        print(o, p['path'], 'md5', p['md5'], 'sha256', p['sha256'][:16])
    for k, v in libs.items():
        print(k, {f: d['md5'] for f, d in v['files'].items() if f.endswith('.glb')})


if __name__ == '__main__':
    main()
