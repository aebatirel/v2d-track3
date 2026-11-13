"""Collect the P1 runs of this folder into result.json (and print the tables used in RESULT.md).
Usage: aggregate.py P1EP24_DIR"""
import glob, hashlib, json, os, sys

import numpy as np

P = sys.argv[1]
R = f'{P}/runs'
NAMES = ('wooden_piece_1', 'wooden_piece_2')
HOST, GUEST = 'wooden_piece_1', 'wooden_piece_2'


def load(n):
    return json.load(open(f'{R}/{n}.json'))


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def per_copy(d):
    rows = []
    for i, c in enumerate(d['copies']):
        if c['nan']:
            rows.append(dict(copy=i + 1, nan=True, nan_at_step=c['nan_at_step'])); continue
        rows.append(dict(copy=i + 1, nan=False,
                         host_drift_cm=c[HOST]['drift_cm'], host_tilt_deg=c[HOST]['tilt_deg'],
                         guest_drift_cm=c[GUEST]['drift_cm'], guest_tilt_deg=c[GUEST]['tilt_deg'],
                         rel_sink_mm=c['rel_sink_mm'], rel_change_cm=c['rel_change']['cm'], rel_change_deg=c['rel_change']['deg'],
                         host_low_start_mm=c[HOST]['low_start_mm'], host_low_end_mm=c[HOST]['low_end_mm'],
                         guest_low_start_mm=c[GUEST]['low_start_mm'], guest_low_end_mm=c[GUEST]['low_end_mm'],
                         guest_on_table_end=c['guest_on_table_end'], guest_below_host_lowest_end=c['guest_below_host_lowest_end']))
    return rows


def verdict(s, crit):
    gap = round(s['host']['low_start_mm'] - s['guest']['low_start_mm'], 1)
    return dict(
        host_drift=dict(value_cm=s['host']['drift_cm'], threshold_cm=1.0, pass_=crit['host_drift']),
        guest_drift=dict(value_cm=s['guest']['drift_cm'], threshold_cm=1.0, pass_=crit['guest_drift']),
        host_tilt=dict(value_deg=s['host']['tilt_deg'], threshold_deg=5.0, pass_=crit['host_tilt']),
        guest_tilt=dict(value_deg=s['guest']['tilt_deg'], threshold_deg=5.0, pass_=crit['guest_tilt']),
        rel_sink=dict(value_mm=s['rel_sink_mm'], threshold_mm=4.0, signed=True, pass_=crit['rel_sink']),
        no_nan=dict(nan_copies=s['nan'], pass_=crit['no_nan']),
        fall_through_reading_A=dict(applies=False, pass_=True,
                                    why=f'at the start pose the guest is not on top of the host: its lowest point is {gap} mm '
                                        'below the host lowest point (both boards stand on edge in a cross), so the clause '
                                        '"when P_sim has it on the host" is read as not applicable'),
        fall_through_reading_B=dict(applies=True, copies_guest_on_table=s['guest_on_table_end'],
                                    copies_guest_below_host_lowest=s['guest_below_host_lowest_end'],
                                    pass_=(s['guest_on_table_end'] == 0 and s['guest_below_host_lowest_end'] == 0),
                                    why='conservative: P_sim has the guest off the table and engaged in the host, so a '
                                        'guest ending on the table (lowest point <= 2 mm above the top) or below the host '
                                        'lowest point counts'),
        P1_pass_reading_A=bool(all(crit.values())),
        P1_pass_reading_B=bool(all(crit.values()) and s['guest_on_table_end'] == 0 and s['guest_below_host_lowest_end'] == 0))


def block(n):
    d = load(n)
    return dict(run=n, frame=d['info']['frame'], assets=d['info']['assets'], snap_mm=d['info']['snap_mm'],
                sim=d['info']['sim'], hydra_overrides=d['info']['hydra_overrides'], sim_sec=d['sim_sec'],
                buffers={k: v for k, v in d['buffers'].items() if k != 'contacts_series'},
                summary=d['summary'], criteria=verdict(d['summary'], d['criteria_excl_fallthrough']),
                nominal_unjittered=d['nominal'], per_copy=per_copy(d))


def asis_block(v, cfg):
    fs = sorted(glob.glob(f'{R}/asis/f246_{v}_{cfg}_c*.json'))
    rows = []
    for f in fs:
        d = json.load(open(f)); c = d['copies'][0]; nm = os.path.basename(f)[:-5]
        log = f'{P}/logs/asis/{nm}.log'
        ov = sum(1 for ln in open(log) if 'overflow' in ln.lower()) if os.path.exists(log) else None
        r = dict(copy=d['only_copy'], overflow_lines=ov, max_nefc=d['buffers']['max_nefc_any_world'], nan=c['nan'])
        if not c['nan']:
            r.update(host_drift_cm=c[HOST]['drift_cm'], host_tilt_deg=c[HOST]['tilt_deg'], guest_drift_cm=c[GUEST]['drift_cm'],
                     guest_tilt_deg=c[GUEST]['tilt_deg'], rel_sink_mm=c['rel_sink_mm'], guest_low_end_mm=c[GUEST]['low_end_mm'],
                     host_low_end_mm=c[HOST]['low_end_mm'])
        rows.append(r)
    ok = [r for r in rows if not r['nan']]
    m = lambda k: round(float(np.mean([r[k] for r in ok])), 3) if ok else None  # noqa: E731
    return dict(copies=len(rows), nan=len(rows) - len(ok), copies_with_overflow=sum(1 for r in rows if r['overflow_lines']),
                mean=dict(host_drift_cm=m('host_drift_cm'), host_tilt_deg=m('host_tilt_deg'), guest_drift_cm=m('guest_drift_cm'),
                          guest_tilt_deg=m('guest_tilt_deg'), rel_sink_mm=m('rel_sink_mm')),
                copies_guest_below_table_10mm=sum(1 for r in ok if r['guest_low_end_mm'] < -10),
                min_guest_low_end_mm=min(r['guest_low_end_mm'] for r in ok) if ok else None, per_copy=rows)


S0 = '/tmp/claude-0/-home-user-v2d-track3/9bee9e08-a3b0-5c25-ae4f-3db987cc25f2/scratchpad'
R0 = f'{P}/src/docs/research/mesh-2026-10-26/gmg/build/I/results/slot2-ep24/fi4o/r0'
REF = f'{P}/store/runs/20261030-physS1-6a814df/refs/glockt/ep24/processed/sequence_id=t3_ep024/robot_name=sharpa_wave/ref_gl_ilc.parquet'
SUP = f'{P}/store/runs/20261030-physS1-6a814df/refs/glockt/ep24/reconstructed_stage/t3_ep024_support.usda'
prim = {c: block(f'f246_lit_{c}') for c in ('carved', 'default', 'default_inertia')}
coll = {c: load(f'f246_lit_{c}')['info']['collision'] for c in ('carved', 'default', 'default_inertia')}
alt = {f'f{F}_{v}_{c}': block(f'f{F}_{v}_{c}') for F in (246, 258, 270) for v in ('lit', 'snap1')
       for c in ('carved', 'default', 'default_inertia') if not (F == 246 and v == 'lit')}
asis = {f'f246_{v}_{c}': asis_block(v, c) for v in ('lit', 'snap1') for c in ('carved', 'default')}
fo = json.load(open(f'{R}/frames_overlap.json'))
res = dict(
    what="P1 settle (INTERLOCK 6.2) on gmg r0 (public ep24 boards), our reference poses, FlashCHORD scene on CPU",
    requested_by='bold-albattani (mesh session), run by a determined-wright helper agent, 2026-10-31 ~21:33-22:15 UTC',
    machine='this cloud container (Linux, 4 CPU, no GPU); CPU Warp / MuJoCo-Warp; no rental, cost $0',
    code=dict(repo_head_read_only='1511616a7f34b565a1f202d46430ae8ecfde8882 (claude/determined-wright-3joens, clean, not modified)',
              make_assets_py_md5=md5('/home/user/v2d-track3/pipeline/make_assets.py'),
              settle_at_py_md5=md5('/home/user/v2d-track3/docs/research/work/carve-20261030/scripts/settle_at.py'),
              settle_p1_py_md5=md5(f'{P}/scripts/settle_p1.py'),
              flashchord=f'{S0}/src/video_to_data/robotic_grounding/flash_chord at video_to_data commit 8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef',
              venv=f'{S0}/fcvenv (newton 1.2.0, warp 1.14.0, mujoco 3.8.1)', embodiment='EMB=sharpa_hands_mid'),
    inputs=dict(r0=dict(branch='origin/claude/bold-albattani-6qmxsv', commit='cdc8b4016a207653fad83f0d21fe55b406d52d99',
                        path='docs/research/mesh-2026-10-26/gmg/build/I/results/slot2-ep24/fi4o/r0',
                        manifest_sha256=sha(f'{R0}/manifest.json'), props_gmg_sha256=sha(f'{R0}/props_gmg.json'),
                        note='<obj>/<obj>.glb is not in git (gitignored); make_assets takes the visual from meshes/library_v3, which does not affect collisions'),
                reference=dict(store='aebatirel/v2d-store', path='runs/20261030-physS1-6a814df/refs/glockt/ep24/processed/sequence_id=t3_ep024/robot_name=sharpa_wave/ref_gl_ilc.parquet',
                               md5=md5(REF), md5_expected='699fe4266a0a965aaf4472a1bfcc8828', support_usda_md5=md5(SUP),
                               relation_to_P_sel='object poses = the gmg P_sel tracks (poses.npz sha256 e694dae3..., same file as the r0 manifest p_sim) mapped by table_frame.npz T_table_from_world plus a constant world-z shift per object: +12.904 mm board 1, +10.989 mm board 2 (checked: max residual 0.0 mm, 0.0 deg over 275 frames). Relative pose therefore differs from P_sim by 1.92 mm along world z (board 1 higher), i.e. along the insertion direction.')),
    roles=dict(host=HOST, guest=GUEST,
               why=['gmg pair key "wooden_piece_1|wooden_piece_2" (report.json pairs) = (target o = host, partner p = guest); their own P1 pre-check used host = wooden_piece_1',
                    'our reference: board 2 descends onto board 1 over the run (board 2 lowest point 150 mm at f160 -> 27 mm at f218 while board 1 stays at 26-37 mm); insertion direction d = (0.04, -1.00, -0.05) in board 1 frame = world down at assembly']),
    frames=dict(primary=246,
                why='INSERTION run (decisions.json: run 164-274, travel 122 mm, straightness 0.91) -> P1 frame = median frame of the assembled stretch. The gmg assembled stretch on P_sim (= P_sel, flag sim_pose_fallback) is f218-274 (29 frames at stride 2) for both ordered pairs; median = asm[len//2] = 246, the frame the gmg used for P2 and its P1 pre-check. On our reference with the gmg rule (_static_stretches, < 2 mm/frame, >= 5 frames): ordered pair board2<-board1 gives 218-274 (median 246); board1<-board2 splits at 238->240 (2.018 mm/frame vs 1.995 on P_sel, caused by the per-object z shift) -> 240-274, median 258; stride 1 -> 265-274, median 270. Frame 0 is not used: the boards are 30 cm apart there.',
                alternatives_run=[258, 270], assembled_stretch_check=fo),
    collision_shapes_loaded=coll,
    p1_spec_frame246=prim,
    alternatives=alt,
    asis_recipe_buffers_1world=asis,
    intrusion_guest_in_host_cm3=fo['overlap'],
    deviations=[
        'Contact buffers: sim.nconmax=4096, sim.njmax=16384 per world (FlashCHORD SimConfig defaults, configs/sim/replay.yaml) instead of the training config sim=rl (256 / 512). Needed: with 256 / 512 the carved scene overflows the broadphase (MuJoCo-Warp asks for 500-670) and contacts are dropped (asis runs). Buffer size only; 0 overflow lines in every reported run.',
        '17 worlds per env (world 0 nominal, 1..16 jittered) instead of settle_at.py\'s 1 world; worlds are independent (copies 1 and 7 re-run in 1 world gave identical numbers).',
        'Jitter on both objects\' start poses (task instruction; the gmg plain-MuJoCo pre-check jitters the guest only). Draws: default_rng(0).normal((16, 2, 6)), 0.5 mm per axis, 0.005 rad rotation vector per axis, same draws for every configuration (common random numbers).',
        'Drift and tilt are measured from each copy\'s own start pose (as gmg simphys.settle); drift_vs_ref (from the unjittered pose) is also stored and differs by at most 0.13 cm (the jitter itself). Tilt = full rotation angle of R0^T R1 (gmg convention).',
        'Relative sink is signed (positive = guest moves down relative to the host), as gmg simphys.settle; negative values mean the host dropped further than the guest.',
        'Default control: r0/_default has no inertia.json, so make_assets.py --pieces r0/_default keeps the COM / inertia of the library_v3 mesh surface (COM 3-4 mm from the pieces\' solid). Run both: "default" (literal build) and "default_inertia" (exact uniform-solid COM / inertia of the default pieces, scripts/piece_props.py, 0.3 kg).',
        'Snapped variant (snap1, diagnostic only, not the spec): each copy\'s pair moved rigidly along z so its lowest collision vertex is 1 mm above the table top; relative pose unchanged.',
        'Fall-through: two readings reported (A: clause not applicable; B: conservative).'],
)
def short(b):
    s_ = b['summary']; c = b['criteria']
    return dict(host_drift_cm=s_['host']['drift_cm'], host_tilt_deg=s_['host']['tilt_deg'], guest_drift_cm=s_['guest']['drift_cm'],
                guest_tilt_deg=s_['guest']['tilt_deg'], rel_sink_mm=s_['rel_sink_mm'], nan=s_['nan'],
                guest_on_table=s_['guest_on_table_end'], guest_below_host_lowest=s_['guest_below_host_lowest_end'],
                fails=[k for k in ('host_drift', 'guest_drift', 'host_tilt', 'guest_tilt', 'rel_sink', 'no_nan') if not c[k]['pass_']])
res['verdict'] = dict(
    P1_as_specified_frame246={c: dict(**short(prim[c]), P1='PASS' if prim[c]['criteria']['P1_pass_reading_A'] else 'FAIL',
                                      P1_conservative_fallthrough='PASS' if prim[c]['criteria']['P1_pass_reading_B'] else 'FAIL')
                              for c in prim},
    alternatives={k: dict(**short(v)) for k, v in alt.items()},
    asis_recipe_buffers_1world={k: dict(copies_with_overflow=v['copies_with_overflow'], mean=v['mean'],
                                        copies_guest_more_than_10mm_below_table=v['copies_guest_below_table_10mm'])
                                for k, v in asis.items()},
    reading=('P1 as specified FAILS for the carved pieces (mean drift of both boards > 1 cm) and also for the default '
             'control (drift and tilt). The drift is the fall of the whole cross: at the assembled frames our reference '
             'holds both boards about 3 cm above the table (lowest points 30.7 / 35.0 mm at f246) with no hand within '
             '9 cm, so every copy drops about 3 cm. Tilt, relative sink and NaN pass for the carved pieces; the default '
             'fails tilt (13-14 deg host). With the pair lowered rigidly onto the table (diagnostic, not the spec) the '
             'carved pieces pass every numeric P1 criterion at f246, f258 and f270 and the default fails tilt. With the '
             'training sim config buffers (nconmax 256, njmax 512; settle_at.py as is, 1 world) the carved scene overflows '
             'the broadphase in 16/16 copies and both boards fall through the table; the default does not overflow.'))
json.dump(res, open(f'{P}/result.json', 'w'), indent=1)
print('wrote', f'{P}/result.json')
