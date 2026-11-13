"""PUBOWN MANIFEST.json from the box results (GT-free; no scoring): public episode -> object -> mesh.
For every object in each public episode's slot list: the PUBOWN pick (store path, sha256, md5, bytes, method,
candidate label, build command line with box paths made relative, own-point fidelity, runner-up), or library_v3 with
the reason (no PUBOWN method, or no eligible candidate with each candidate's exclusion).
Reads: RESULTS/{selection.json, manifest.tsv, plan.json, params.json, commands/build.txt, SHA256SUMS,
candidates.json}, the repo's meshes/library_v3, and optionally the frame/kit check json.
Optional: the frame/kit check json (pubown_frame_kit.py) and the report-only E0-gate json (pubown_gate_alt.py); with
the latter, each pair also carries the E0 frame-gate reading of the PUBOWN pick and the alternative E0-gated pick
(store path, sha256, md5), clearly separate from the PUBOWN pick.
Usage: python -I pubown_manifest.py REPO RESULTS RUN_ID OUT.json [frame_kit.json [gate_alt.json]]
"""
import csv, hashlib, json, os, re, sys

REPO, R, RUN, OUT = sys.argv[1:5]
FK = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else None
GA = json.load(open(sys.argv[6])) if len(sys.argv) > 6 else None
STORE = 'aebatirel/v2d-store'
SRES = f'runs/{RUN}/results/pubown'
METHOD = {
    'white_pot': 'prim_potlid.py pot --c0b (C0b kit-of-parts pot; own pass-B points, own thickness chain, own-episode marker balls)',
    'white_pot_lid': 'prim_potlid.py lid --c0b',
    'plastic_dish_rack': 'PRIM_CUP_LEAN=1 prim_rack.py run --episodes <e> (one run per episode: own floor depth, own wall thickness or t0_C0b, own marker balls)',
    'blue_cup': 'lathe_obs.py with C0b lathe flags on the own pass-B points',
    'beige_cup': 'lathe_obs.py with C0b lathe flags on the M_sep(own) separated-frame points (C0b PREREG item 10, C1/T1 rule)'}


def h(p, a='sha256'):
    return hashlib.new(a, open(p, 'rb').read()).hexdigest()


def rel(cmd):
    cmd = cmd.replace('/content/results/pubown/', '').replace('/content/pubw/code/', '<code@00e8584>/')
    return cmd.replace('/content/pubw/', '<work>/')


sel = json.load(open(f'{R}/selection.json'))
plan = json.load(open(f'{R}/plan.json'))
params = json.load(open(f'{R}/params.json'))['targets']
sums = {}
for line in open(f'{R}/SHA256SUMS'):
    s, p = line.split(None, 1)
    sums[p.strip().lstrip('*')[2:] if p.strip().lstrip('*').startswith('./') else p.strip().lstrip('*')] = s
build = [l for l in open(f'{R}/commands/build.txt').read().splitlines() if l.strip()]


def build_line(label):
    lab = label.replace('/', '__')
    for l in build:
        if f'logs/build/{lab}.log' in l:
            m = re.search(r'\( (.*) \) > logs/build/', l)
            return dict(label=label, log=f'logs/build/{lab}.log', command=rel(m.group(1) if m else l))
    return None


eps = {}
n_pub = n_lib = 0
for row in csv.DictReader(open(f'{R}/manifest.tsv'), delimiter='\t'):
    e, o = row['episode'], row['object']
    pair = f'ep{e}/{o}'
    if row['source'] == 'pubown':
        s = sel['selection'][pair]
        p = f'{R}/{s["mesh"]}'
        sha = h(p)
        assert sha == s['sha256'] == row['sha256'] == sums.get(s['mesh']), (pair, sha, s['sha256'], sums.get(s['mesh']))
        lab = s['pick']
        bl = build_line(lab) or build_line('/'.join(lab.split('/')[:2]))     # rack: one run per episode
        tgt = {k: v for k, v in params.items() if k.startswith(f'{lab.split("/")[0]}/ep{e}')}
        d = dict(source='pubown', store_repo=STORE, store_path=f'{SRES}/{s["mesh"]}', sha256=sha, md5=h(p, 'md5'),
                 bytes=os.path.getsize(p), method=METHOD[o], candidate=lab, variant=s['variant'],
                 candidate_src=s['src'], build=bl, params={k: {kk: vv for kk, vv in v.items() if kk != 'obs'}
                                                           for k, v in tgt.items()},
                 fid_own_sum_mm=s['fid_own_sum_mm'], faces_raw=s['faces_raw'], n_candidates=s['n_candidates'],
                 n_eligible=s['n_eligible'], runner_up=s['runner_up'], runner_up_fid_mm=s['runner_up_fid'],
                 ties_at_3_decimals=s['ties_at_3_decimals'], excluded=s['excluded'])
        if FK and pair in FK['pairs']:
            f, k = FK['pairs'][pair]['frame'], FK['pairs'][pair]['kit']
            d['frame_vs_library_v3'] = dict(
                centroid_offset_mm=round(f['centroid_offset_mm'], 3), axis_angle_deg=f['axis_angle_deg'],
                surf_sym_median_mm=round(f['surf_sym_median_mm'], 3), icp_rot_deg=round(f['icp_rot_deg'], 3),
                icp_centroid_motion_mm=round(f['icp_centroid_motion_mm'], 3),
                icp_symaxis_tilt_deg=round(f['icp_symaxis_tilt_deg'], 3) if 'icp_symaxis_tilt_deg' in f else None,
                icp_med_before_after_mm=[round(f['icp_med_before_mm'], 3), round(f['icp_med_after_mm'], 3)])
            d['kit_budget'] = dict(nonpad_faces=k['nonpad_faces'], vertices=k['vertices_used'], watertight=k['watertight'],
                                   bodies=k['bodies'], quality_flags=k['quality_flags'], payload_chars=k['payload_chars'])
        if GA:
            c = GA['cands'][lab]
            d['e0_frame_gate'] = dict(pass_=c['gate_pass'], reading=c['gate'], extent_mm=c['extent_mm'], bodies=c['bodies'],
                                      main_body_extent_mm=c['main_extent_mm'], main_body_area_frac=c['main_area_frac'],
                                      largest_other_body_mm=c['largest_other_mm'], farthest_other_body_mm=c['farthest_other_mm'])
            d['e0_frame_gate']['pass'] = d['e0_frame_gate'].pop('pass_')
            a = GA['pairs'][pair]
            alt = a['alt_pick']
            if alt is None:
                d['alt_e0_gated'] = dict(source='library_v3', repo_path=f'meshes/library_v3/{o}.glb', reason=a['alt'])
            elif alt == lab:
                d['alt_e0_gated'] = dict(source='pubown', same_as_pick=True)
            else:
                cand = next(r for r in sel['table'][pair] if r['label'] == alt)
                rp = os.path.relpath(cand['path'], '/content/results/pubown')
                ap = f'{R}/{rp}'
                assert h(ap) == cand['sha256'] == sums.get(rp), (pair, alt)
                d['alt_e0_gated'] = dict(source='pubown_candidate', candidate=alt, store_path=f'{SRES}/{rp}', sha256=h(ap),
                                         md5=h(ap, 'md5'), bytes=os.path.getsize(ap), fid_own_sum_mm=cand['fid_own_sum_mm'],
                                         build=build_line(alt) or build_line('/'.join(alt.split('/')[:2])))
        n_pub += 1
    else:
        lp = f'{REPO}/meshes/library_v3/{o}.glb'
        d = dict(source='library_v3', repo_path=f'meshes/library_v3/{o}.glb', sha256=h(lp), md5=h(lp, 'md5'),
                 bytes=os.path.getsize(lp), reason=row['note'])
        s = sel['selection'].get(pair)
        if s:
            d['excluded'] = s.get('excluded')
            d['n_candidates'] = s.get('n_candidates')
        n_lib += 1
    eps.setdefault(f'ep{e}', {})[o] = d

man = dict(
    candidate='PUBOWN',
    description='One clean mesh per public (episode, object) pair, built only from that episode\'s own observed points '
                'with C0b\'s scan-free constants and picked within the episode (C0b PREREG s5 with ALL = own points). '
                'For the score session\'s perception re-track test (perc2 with these meshes as templates). Not scored here.',
    plan='docs/research/mesh-2026-10-26/cdo-sprint/PUBOWN/PLAN.md', box_report='docs/research/mesh-2026-10-26/cdo-sprint/PUBOWN/BOX.md',
    run=dict(run_id=RUN, store=f'{STORE} runs/{RUN}/', results=f'{SRES}/', c0b_run=plan['c0b_run'],
             c0b_code_commit=plan['c0b_code_commit']),
    frame='object frame of the library_v3-seeded sweep track, as fitted (no alignment); same frame as meshes/library_v3',
    gt_free='inputs: sweep tracks, C0b pass-B observed points (FoundationStereo depth), C0b thickness/sigma/markers, '
            't0_C0b; never scans, mocap, parquet poses, *_align or scan-derived constants',
    counts=dict(pairs=n_pub + n_lib, pubown=n_pub, library_v3=n_lib),
    e0_frame_gate=None if not GA else dict(
        note='REPORT ONLY. PUBOWN\'s rule (C0b s5) has no frame gate and its picks are unchanged. The E0 PREREG s4 identity '
             'frame gate (3x the C0 public mesh value vs library_v3; E0 inputs/thresholds.json, fixed before PUBOWN) is '
             'applied here as a reading, and alt_e0_gated is C0b s5 re-applied to the candidates that also pass it '
             '(library_v3 when none does). beige_cup has no E0 threshold: not gated.',
        thresholds=GA['thresholds'], script='docs/research/mesh-2026-10-26/cdo-sprint/PUBOWN/scripts/pubown_gate_alt.py'),
    episodes=dict(sorted(eps.items(), key=lambda kv: int(kv[0][2:]))))
json.dump(man, open(OUT, 'w'), indent=1)
print(json.dumps(man['counts']))
