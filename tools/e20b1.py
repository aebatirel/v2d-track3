"""Eval-20 retrain on the b1 water-pitcher collision pieces: import, checks, seed choice, gate and verdict of
ops/jobs/ev20_b1.sh (2026-11-01; pre-registered in docs/research/work/eval20-b1-20261101/PREREG.md before any result).
Eval 20 has no ground truth; none is read here. The PACKED eval-20 learner and recipe (grasp lock, glock_public.sh, run
20261025-evb1420-ee7ba8e, its runs/glock/ep20-s42 checkpoint, sha256 61dcd7a6...) on the PACKED reference P (md5 4d06d8d4,
byte copies per seed), seeds 42 and 43, at the stock sim=rl contact limits, with ONE changed input: the water pitcher's
collision copy = the 41 b1 pieces (meshes/carve/ev20b1, pinned by md5), applied as the mesh lane specified:
pipeline/placement_carve.py assets on the packed refs/sf/ep20/assets (the blue cup's 0.5 cm fill, both visual meshes and
both inertials unchanged; NOT make_assets.py --pieces). PACKABLE if it passes: nothing here is oracle- or scan-derived and
no sim limit changes (tools/no_oracle.py must accept every input and the chosen checkpoint).

  import   byte copy of the mesh lane's frozen set (git show <rev>:<path>, file by file; refused without a FROZEN.md that
           lists exactly the copied files with the same md5, or if the destination exists), MD5SUMS, a PROVENANCE.md header.
  pieces   the set folder: MD5SUMS md5 = the pinned one; file set and md5 = MD5SUMS = FROZEN.md; exactly
           water_pitcher/piece_00..40.obj (no inertia.json or any other input: placement_carve.py assets reads only the
           pieces). Exit 1 on failure.
  inputs   before the carve, the pulled packed inputs: the reference P (md5 + trajectory fingerprint, pinned and = the table
           packed_refs.json), its support stage (= refs/perc2mck/ep20's, pinned md5), the packed asset copy refs/sf/ep20/assets
           (URDF and glb md5s pinned: pitcher URDF 6772f954 with 9 <collision> = the glb + 8 arc-foot STLs, blue cup URDF
           31cd001d / glb d2be7e3d with its 0.5 cm fill), the packed checkpoint's sha256, rest_check.json present.
  assets   after `placement_carve.py assets PACKED CARVE_DIR OUT`: OUT keeps every file of PACKED byte for byte except
           urdf/water_pitcher_rigid.urdf; it adds exactly mesh/water_pitcher/col_00..40.obj, each a byte copy of
           piece_NN.obj; the new pitcher URDF has md5 77b395a5 (the lane's route-A URDF), 41 <collision> naming col_00..40
           in order, and outside its <collision> elements it is the packed URDF (visual and inertial unchanged); the blue
           cup URDF and glb are unchanged.
  arms     per seed: refs/e20b1s<seed>_glockt/ep20/<hive>/ref_gl_ilc.parquet = byte copy of P; base link
           refs/e20b1s<seed>mck/ep20 -> refs/perc2mck/ep20; results/e20b1s<seed>_glock_public/ep20/{rest_check.json,
           zero_score.txt, support_fill.json} (glock_public.sh REUSE_REF / REQUIRE_REUSE). P names the b1 asset copy (URDF
           md5s pinned, 0.3 kg).
  cells    per seed (pack 9b PREREG 1.3 style): the chosen checkpoint as the evaluator loads it: saved config -> task.parquet
           -> this seed's copy (md5 = P) -> object_urdf_paths -> URDFs (b1 md5s, 0.3 kg, under refs/sf/ep20/assets) and the
           support stage (pinned md5); every saved-config key = the PACKED eval-20 checkpoint's except output_dir,
           task.parquet, reference.parquet, reset.seed, env.reset.seed, training.seed; sim and env.sim 512 / 256; steps;
           reset.seed; best/ = the curve's choice; the training-box rollouts name the checkpoint (sha256); their sim_vs_ref
           (qa_policy.json, vs the seed copy = P). Status per seed: VERIFIED | INVALID | MISSING.
  choose   pack 9b PREREG section 2 (tools/e10cs.choose, i.e. e10v's rule 2): two VERIFIED seeds with n >= 8; the higher
           mean; within 0.005 (4-decimal means) the lower sd (ddof 1); still tied seed 42. Exit 1 if no seed is chosen.
  gate     the training-box gate: the confirmation runs only if at least one VERIFIED seed (n >= 8) has a training-box mean
           sim_vs_ref vs P above 0.8933 (the packed policy's fresh-draw mean, H5p7 h5_summary.json eval 20; strict, 1e-9 in
           favour of "not met"). Exit 0 met, 3 not met, 1 unreadable.
  verify   pieces, inputs, assets, arms ok; cells without INVALID; the choice = the chosen cell; every confirmation draw
           names the chosen checkpoint; every scored rollout's own-reference check (score json); no_oracle's record of the
           chosen checkpoint when a confirmation ran.
  verdict  the PREREG label (INVALID / INCOMPLETE / NO-SWAP (training-box gate not met) / the pack 9b swap rule on P:
           SWAP-ELIGIBLE / NO-SWAP / INCOMPLETE / INVALID), the binding pack-10 inclusion (SWAP-ELIGIBLE and mean gain on P
           >= 0.02), the overflow label ("pieces not clean in training" if a training log has > 1,000 dropped-row lines),
           the EQUAL FLOOR note, per-object AUC, the b1 zero-action rest check (reported) and the piece manifest.
Usage (box paths): see ops/jobs/ev20_b1.sh.
"""
import argparse, datetime, glob, hashlib, json, math, os, re, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_arm import md5, traj_fingerprint, read_inertial                                       # noqa: E402
from mass_verify import ck_config, resolve_parquet, resolve_asset, flat, eval_timeouts, STEPS_KEY  # noqa: E402
from e11g_verify import urdfs_of, jsonish                                                       # noqa: E402
from e10cs_pieces import md5b, md5f, inputs_of, parse_md5_list, manifest_text, RECORDS          # noqa: E402
import e10cs                                                                                    # noqa: E402
import dr_verdict                                                                               # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP, PRE, BASE, SET, OBJ, NPIECES = 20, 'e20b1', 'mck', 'ev20b1', 'water_pitcher', 41
SRC_RUN = '20261025-evb1420-ee7ba8e'
PLACEHOLDER, STOCK, TOL = 0.3, (512, 256), 1e-9
# the packed eval-20 reference P (refs/glockt/ep20 of evb1420; packed_refs.json) and its support stage [M]
REF_MD5, REF_FP = '4d06d8d42d57d84b1d25a166e8a90adc', 'c1e09fcc24b9ace1c5aee25fa5027c6e'
STAGE_MD5 = '1388703af76a393ff75a4d34fc614f7d'
PACKED_SHA = '61dcd7a6339677ac8cf612a11a3b9bf8cd7939a358a438c111d34e213faea7ff'   # runs/glock/ep20-s42/policy_70004736
# the b1 piece set (meshes/carve/ev20b1/MD5SUMS md5; FROZEN.md md5) [M, import 1 Nov]
PIECES = dict(md5sums='fe9aeca079fdcc7524a06f46fcd0a7ae', frozen='4259a6cf8a4c28dcbc212ff0a77bad5b',
              source='origin/claude/bold-albattani-6qmxsv 83d18d0 (FROZEN.md; the pieces as delivered in 9c0bc0c)')
URDF_PACKED = {'water_pitcher': '6772f95462e0554cfac39de97bdf2253', 'blue_cup': '31cd001d2618ee2972dc922b77109b9f'}
URDF_B1 = {'water_pitcher': '77b395a5aa46b2eeab1f02e20bf04348', 'blue_cup': '31cd001d2618ee2972dc922b77109b9f'}
GLB = {'water_pitcher': 'adb315f3250d90072c385b8dfd8bf49c', 'blue_cup': 'd2be7e3decad003dab41fe0009541912'}
COLL_PACKED, COLL_B1 = {'water_pitcher': 9, 'blue_cup': 1}, {'water_pitcher': NPIECES, 'blue_cup': 1}
MIN_N, MIN_CONF = 8, 10
GATE_P = 0.8933            # the packed eval-20 policy's 10 fresh (H5p7) draws, mean sim_vs_ref vs P: h5_summary.json["20"]["mean"] [M]
OLD_P = 0.8948             # the old packed draw (pack 6's eval-20 rollout, the board pack's): pack 7 summary = dr_score vs P [M]
INCL_BAR = 0.02            # binding pack-10 inclusion: (new confirmation mean - packed fresh-draw mean) >= 0.02 vs P
O_BAR = 1000               # overflow label: > 1,000 dropped-row lines in a training log
REST_PACKED = dict(water_pitcher=dict(max_mm=10.4, max_deg=3.9, until_frame=14, ok=False), blue_cup=dict(max_mm=0.0, max_deg=0.0, ok=True))


def js(f):
    try:
        return json.load(open(f)) if f and os.path.isfile(f) else None
    except Exception:
        return None


def fin(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def box_path(p, C):
    """a reference path (/content/... or /workspace/...) under this box's content root C (regex: the CPU mock's path
    rewrite of literal box roots leaves this alone)"""
    return re.sub(r'^/(?:content|workspace)/', C.rstrip('/') + '/', p)


def tree(root):
    return {os.path.relpath(f, root): md5(f) for f in sorted(glob.glob(f'{root}/**/*', recursive=True)) if os.path.isfile(f)}


def coll_files(txt):
    return re.findall(r'<collision>.*?filename="([^"]+)".*?</collision>', txt, re.S)


def no_coll(txt):
    """the URDF text without its <collision> elements, whitespace-normalised (placement_carve.py's own regex)"""
    return re.sub(r'\s+', ' ', re.sub(r'\s*<collision>.*?</collision>', '', txt, flags=re.S)).strip()


def block(txt, tag):
    m = re.findall(rf'<{tag}>.*?</{tag}>', txt, re.S)
    return [re.sub(r'\s+', ' ', x) for x in m]


# --------------------------------------------------------------------------------------------------------------- import
def check_set(d):
    d = d.rstrip('/'); fails = []; r = dict(dir=os.path.abspath(d), name=os.path.basename(d))
    if not os.path.isfile(f'{d}/MD5SUMS'):
        return dict(r, ok=False, failures=['MD5SUMS missing'])
    man = parse_md5_list(open(f'{d}/MD5SUMS').read()); ins = inputs_of(d); got = {x: md5f(f'{d}/{x}') for x in ins}
    r['md5sums_md5'] = md5f(f'{d}/MD5SUMS')
    if set(man) != set(got):
        fails.append(f'file set differs from MD5SUMS: extra {sorted(set(got) - set(man))[:5]}, missing {sorted(set(man) - set(got))[:5]}')
    bad = sorted(x for x in set(man) & set(got) if man[x] != got[x])
    if bad:
        fails.append(f'md5 differs from MD5SUMS: {bad[:6]}')
    if os.path.isfile(f'{d}/FROZEN.md'):
        fr = parse_md5_list(open(f'{d}/FROZEN.md').read()); r['frozen_md5'] = md5f(f'{d}/FROZEN.md')
        if fr != man:
            fails.append('FROZEN.md lists other files or md5s than MD5SUMS')
    else:
        fails.append('FROZEN.md missing')
    want = [f'{OBJ}/piece_{k:02d}.obj' for k in range(NPIECES)]
    if sorted(got) != want:
        fails.append(f'inputs are not exactly {OBJ}/piece_00..{NPIECES - 1:02d}.obj: extra {sorted(set(got) - set(want))[:4]}, '
                     f'missing {sorted(set(want) - set(got))[:4]}')
    r['pieces'] = len([x for x in got if x.startswith(f'{OBJ}/piece_')])
    r['pieces_md5_of_md5_list'] = md5b(''.join(f'{got[x]}  {os.path.basename(x)}\n' for x in sorted(got)).encode())
    r['piece_vertices'] = {os.path.basename(x): sum(1 for ln in open(f'{d}/{x}') if ln.startswith('v ')) for x in sorted(got)}
    r.update(files=len(ins), ok=not fails, failures=fails)
    return r


def cmd_import(a):
    repo, src, dst = a.repo, a.src.rstrip('/'), a.dst.rstrip('/')
    if os.path.exists(dst):
        sys.exit(f'import: {dst} exists (a piece set is never overwritten; a change is a new folder)')
    full = subprocess.run(['git', '-C', repo, 'rev-parse', a.rev], capture_output=True, text=True, check=True).stdout.strip()
    ls = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', full, src + '/'], capture_output=True, text=True,
                        check=True).stdout.split()
    rels = sorted(os.path.relpath(p, src) for p in ls)
    if 'FROZEN.md' not in rels:
        sys.exit(f'import: {src} at {full[:7]} has no FROZEN.md (only a frozen set is imported)')
    blobs = {r: subprocess.run(['git', '-C', repo, 'show', f'{full}:{src}/{r}'], capture_output=True, check=True).stdout for r in rels}
    frozen = parse_md5_list(blobs['FROZEN.md'].decode()); ins = [r for r in rels if r not in RECORDS]
    got = {r: md5b(blobs[r]) for r in ins}
    if frozen != got:
        sys.exit(f'import: FROZEN.md does not match the copied files ({sorted(set(got) ^ set(frozen))[:6]})')
    for r in rels:
        if r in ('MD5SUMS', 'PROVENANCE.md'):
            continue
        p = os.path.join(dst, r); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'wb').write(blobs[r])
    open(f'{dst}/MD5SUMS', 'w').write(manifest_text(dst, ins))
    tr = subprocess.run(['git', '-C', repo, 'rev-parse', f'{full}:{src}'], capture_output=True, text=True, check=True).stdout.strip()
    same = {}
    for rev in a.also or []:                                             # the pieces at another commit (e.g. the result commit)
        f2 = subprocess.run(['git', '-C', repo, 'rev-parse', rev], capture_output=True, text=True, check=True).stdout.strip()
        same[f2] = all(md5b(subprocess.run(['git', '-C', repo, 'show', f'{f2}:{src}/{r}'], capture_output=True, check=True).stdout) == got[r]
                       for r in ins)
    open(f'{dst}/PROVENANCE.md', 'w').write(
        f'# {os.path.basename(dst)}: provenance (import header; details below it)\n\n'
        f'- Byte copy of `{src}/` at commit `{full}` (git tree `{tr}`), imported '
        f'{datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} by `tools/e20b1.py import`.\n'
        f'- {len(ins)} input files; `MD5SUMS` lists them (md5 of MD5SUMS `{md5b(manifest_text(dst, ins).encode())}`); '
        f'`FROZEN.md` is the source\'s own freeze, byte copy, and lists the same md5s (checked at import).\n'
        + ''.join(f'- The {len(ins)} input files are byte-identical at commit `{k}`: {v}.\n' for k, v in same.items())
        + f'- Check: `python3 tools/e20b1.py pieces --dir {dst} --out /tmp/p.json`.\n')
    r = check_set(dst)
    print(f'IMPORTED {len(ins)} files from {full[:7]}:{src} -> {dst}; MD5SUMS {r.get("md5sums_md5")}, FROZEN.md {r.get("frozen_md5")}; '
          f'also identical at {same}; check ok {r["ok"]} {r["failures"]}')
    sys.exit(0 if r['ok'] else 1)


def cmd_pieces(a):
    r = check_set(a.dir); fails = list(r.get('failures', []))
    if os.path.basename(a.dir.rstrip('/')) != SET:
        fails.append(f'folder {a.dir} is not named {SET}')
    if r.get('md5sums_md5') != PIECES['md5sums']:
        fails.append(f'MD5SUMS md5 {r.get("md5sums_md5")} != pinned {PIECES["md5sums"]}')
    if r.get('frozen_md5') != PIECES['frozen']:
        fails.append(f'FROZEN.md md5 {r.get("frozen_md5")} != pinned {PIECES["frozen"]}')
    r.update(set=SET, pinned=PIECES, ok=not fails, failures=fails,
             manifest=open(f'{a.dir}/MD5SUMS').read().splitlines() if os.path.isfile(f'{a.dir}/MD5SUMS') else None)
    json.dump(r, open(a.out, 'w'), indent=1)
    print(('PIECES OK' if not fails else 'PIECES FAILED: ' + ' | '.join(fails[:4])) + f" :: {SET} {r.get('pieces')} pieces, MD5SUMS "
          f"{r.get('md5sums_md5')}, FROZEN.md {r.get('frozen_md5')}, md5 list {str(r.get('pieces_md5_of_md5_list'))[:8]}")
    sys.exit(0 if not fails else 1)


# --------------------------------------------------------------------------------------------------------------- inputs
def the_ref(C):
    src = glob.glob(f'{C}/refs/glockt/ep{EP}/processed/*/*/ref_gl_ilc.parquet')
    if len(src) != 1:
        raise SystemExit(f'{len(src)} references under {C}/refs/glockt/ep{EP} (one expected: the packed P)')
    return src[0], os.path.relpath(os.path.dirname(src[0]), f'{C}/refs/glockt/ep{EP}')


def stage_md5(d):
    fs = sorted(glob.glob(f'{d}/reconstructed_stage/*.usda'))
    return {os.path.basename(f): md5(f) for f in fs}


def cmd_inputs(a):
    C = a.content.rstrip('/'); fails = []
    import pyarrow.parquet as pq
    src, hive = the_ref(C); t = pq.read_table(src); m5, fp = md5(src), traj_fingerprint(t)
    T = (js(a.table) or {}).get('episodes', {}).get(str(EP), {}) if a.table else {}
    r = dict(reference=src, md5=m5, traj_fingerprint=fp, hive=hive, pinned=dict(md5=REF_MD5, fp=REF_FP, stage=STAGE_MD5, packed_sha=PACKED_SHA),
             table=dict(md5=T.get('md5'), fp=T.get('traj_fingerprint'), packed_sha256=T.get('packed_sha256'), source_run=T.get('source_run')))
    if m5 != REF_MD5 or fp != REF_FP:
        fails.append(f'reference {m5} / {fp} != pinned {REF_MD5} / {REF_FP}')
    if a.table and (T.get('md5') != REF_MD5 or T.get('traj_fingerprint') != REF_FP or T.get('packed_sha256') != PACKED_SHA):
        fails.append(f'packed_refs.json eval 20 {T.get("md5")} / {T.get("traj_fingerprint")} / {str(T.get("packed_sha256"))[:12]} != pinned')
    sg, sp = stage_md5(f'{C}/refs/glockt/ep{EP}'), stage_md5(f'{C}/refs/perc2{BASE}/ep{EP}')
    r['stage'] = dict(glockt=sg, base=sp)
    if list(sg.values()) != [STAGE_MD5] or sg != sp:
        fails.append(f'support stage glockt {sg} / base {sp} != pinned {STAGE_MD5}')
    if not glob.glob(f'{C}/refs/perc2{BASE}/ep{EP}/{hive}/*.parquet'):
        fails.append(f'no base reference under refs/perc2{BASE}/ep{EP}/{hive}')
    for f in ('rest_check.json', 'zero_score.txt', 'support_fill.json'):
        if not os.path.isfile(f'{C}/results/glock_public/ep{EP}/{f}'):
            fails.append(f'results/glock_public/ep{EP}/{f} missing (glock_public.sh REUSE_REF)')
    r['rest_check_packed'] = jsonish(f'{C}/results/glock_public/ep{EP}/rest_check.json') if os.path.isfile(f'{C}/results/glock_public/ep{EP}/rest_check.json') else None
    names = t.column('object_body_names')[0].as_py(); urdfs = [box_path(u, C) for u in t.column('object_urdf_paths')[0].as_py()]
    A = f'{C}/refs/sf/ep{EP}/assets'; r['assets'] = {}
    if sorted(names) != sorted(URDF_PACKED):
        fails.append(f'reference objects {names} != {sorted(URDF_PACKED)}')
    for n, u in zip(names, urdfs):
        row = dict(urdf=u, under_root=os.path.dirname(os.path.dirname(u)) == A)
        if not row['under_root']:
            fails.append(f'{n}: {u} is not under {A}')
        if not os.path.isfile(u):
            fails.append(f'{n}: {u} missing'); r['assets'][n] = row; continue
        txt = open(u).read(); row.update(md5=md5(u), collisions=len(coll_files(txt)), mass=read_inertial(txt)[0])
        g = f'{A}/mesh/{n}/{n}.glb'; row['glb_md5'] = md5(g) if os.path.isfile(g) else None
        if row['md5'] != URDF_PACKED.get(n):
            fails.append(f'{n} URDF md5 {row["md5"]} != packed {URDF_PACKED.get(n)}')
        if row['glb_md5'] != GLB.get(n):
            fails.append(f'{n} glb md5 {row["glb_md5"]} != packed {GLB.get(n)}')
        if row['collisions'] != COLL_PACKED.get(n):
            fails.append(f'{n} {row["collisions"]} <collision> != packed {COLL_PACKED.get(n)}')
        if abs(row['mass'] - PLACEHOLDER) > 1e-9:
            fails.append(f'{n} mass {row["mass"]} != {PLACEHOLDER}')
        r['assets'][n] = row
    if a.packed_ck:
        r['packed_ck_sha256'] = e10cs.sha256(a.packed_ck) if os.path.isfile(a.packed_ck) else None
        if r['packed_ck_sha256'] != PACKED_SHA:
            fails.append(f'packed checkpoint sha256 {str(r["packed_ck_sha256"])[:12]} != {PACKED_SHA[:12]}')
    r['packed_asset_tree'] = tree(A); r['ok'] = not fails; r['failures'] = fails
    json.dump(r, open(a.out, 'w'), indent=1)
    print(('INPUTS OK' if not fails else 'INPUTS FAILED: ' + ' | '.join(fails[:5])) + f' :: P {m5} (fingerprint {fp[:12]}), stage {STAGE_MD5[:8]}, '
          + ', '.join(f"{n} URDF {str(v.get('md5'))[:8]} {v.get('collisions')} collisions glb {str(v.get('glb_md5'))[:8]}" for n, v in r['assets'].items())
          + f", packed checkpoint {str(r.get('packed_ck_sha256'))[:12]}")
    sys.exit(0 if not fails else 1)


# --------------------------------------------------------------------------------------------------------------- assets
def cmd_assets(a):
    Pk, Cv, d = a.packed.rstrip('/'), a.carved.rstrip('/'), a.pieces.rstrip('/'); fails = []
    t0, t1 = tree(Pk), tree(Cv); pcs = sorted(glob.glob(f'{d}/{OBJ}/piece_*.obj'))
    cols = [f'mesh/{OBJ}/col_{k:02d}.obj' for k in range(len(pcs))]
    changed = sorted(x for x in t0 if x in t1 and t0[x] != t1[x]); removed = sorted(x for x in t0 if x not in t1)
    added = sorted(x for x in t1 if x not in t0)
    if changed != [f'urdf/{OBJ}_rigid.urdf']:
        fails.append(f'files changed {changed} (only urdf/{OBJ}_rigid.urdf may change)')
    if removed:
        fails.append(f'files removed {removed[:5]}')
    if added != sorted(cols):
        fails.append(f'files added {added[:4]}... != {len(cols)} mesh/{OBJ}/col_NN.obj')
    copies = [os.path.isfile(f'{Cv}/{c}') and md5(f'{Cv}/{c}') == md5(p) for c, p in zip(cols, pcs)]
    if not all(copies):
        fails.append(f'{copies.count(False)} col_NN.obj are not byte copies of piece_NN.obj')
    out = {}
    for n in URDF_PACKED:
        u0, u1 = f'{Pk}/urdf/{n}_rigid.urdf', f'{Cv}/urdf/{n}_rigid.urdf'
        x0, x1 = open(u0).read(), open(u1).read()
        row = dict(packed_md5=md5(u0), md5=md5(u1), collisions_packed=len(coll_files(x0)), collisions=len(coll_files(x1)),
                   inertial_equal=block(x0, 'inertial') == block(x1, 'inertial'), visual_equal=block(x0, 'visual') == block(x1, 'visual'),
                   non_collision_equal=no_coll(x0) == no_coll(x1), inertial=dict(zip(('mass', 'com', 'inertia'), read_inertial(x1))),
                   glb_md5=md5(f'{Cv}/mesh/{n}/{n}.glb'))
        if row['packed_md5'] != URDF_PACKED[n]:
            fails.append(f'{n}: packed URDF md5 {row["packed_md5"]} != pinned {URDF_PACKED[n]}')
        if row['md5'] != URDF_B1[n]:
            fails.append(f'{n}: URDF md5 {row["md5"]} != pinned b1 {URDF_B1[n]}')
        if row['collisions'] != COLL_B1[n]:
            fails.append(f'{n}: {row["collisions"]} <collision> != {COLL_B1[n]}')
        if not (row['inertial_equal'] and row['visual_equal'] and row['non_collision_equal']):
            fails.append(f'{n}: URDF differs from the packed one outside <collision> (inertial {row["inertial_equal"]}, visual {row["visual_equal"]})')
        if row['glb_md5'] != GLB[n]:
            fails.append(f'{n}: glb {row["glb_md5"]} != {GLB[n]}')
        if n == OBJ and [x.split('mesh/', 1)[-1] for x in coll_files(x1)] != [c.split('mesh/', 1)[-1] for c in cols]:
            fails.append(f'{n}: <collision> files are not col_00..{len(cols) - 1:02d}.obj in order')
        out[n] = row
    r = dict(packed=Pk, carved=Cv, pieces=os.path.abspath(d), n_pieces=len(pcs), changed=changed, removed=removed, added=len(added),
             col_byte_copies=all(copies), urdfs=out, pinned=dict(packed=URDF_PACKED, b1=URDF_B1, glb=GLB), ok=not fails, failures=fails)
    json.dump(r, open(a.out, 'w'), indent=1, default=str)
    print(('ASSETS OK' if not fails else 'ASSETS FAILED: ' + ' | '.join(fails[:4])) + f' :: changed {changed}, added {len(added)}, removed {len(removed)}; '
          + '; '.join(f"{n} URDF {v['packed_md5'][:8]} -> {v['md5'][:8]}, {v['collisions_packed']} -> {v['collisions']} collisions, "
                      f"inertial equal {v['inertial_equal']}, visual equal {v['visual_equal']}, mass {v['inertial']['mass']}" for n, v in out.items()))
    sys.exit(0 if not fails else 1)


# ----------------------------------------------------------------------------------------------------------------- arms
def cmd_arms(a):
    C = a.content.rstrip('/'); fails = []
    src, hive = the_ref(C); R0 = f'{C}/refs/perc2{BASE}/ep{EP}'; res0 = f'{C}/results/glock_public/ep{EP}'
    urd, fp = urdfs_of(src)
    man = dict(episode=EP, prefix=PRE, base=BASE, source_run=SRC_RUN, source_parquet=src, source_md5=md5(src), traj_fingerprint=fp, hive=hive,
               base_dir=R0, urdfs=urd, stage=stage_md5(f'{C}/refs/glockt/ep{EP}'), rest_check_packed=jsonish(f'{res0}/rest_check.json'), seeds={},
               note='rest_check.json / zero_score.txt / support_fill.json are the packed run\'s records (zero-action replay with the '
                    'packed asset copy); copied only because glock_public.sh REUSE_REF requires them; nothing reads their values')
    if man['source_md5'] != REF_MD5 or fp != REF_FP:
        fails.append(f'P {man["source_md5"]} / {fp} != pinned {REF_MD5} / {REF_FP}')
    if list(man['stage'].values()) != [STAGE_MD5]:
        fails.append(f'support stage {man["stage"]} != {STAGE_MD5}')
    if not os.path.isfile(f'{res0}/rest_check.json'):
        fails.append(f'{res0}/rest_check.json missing')
    for n, u in urd.items():
        lu = box_path(u['urdf'], C)
        if u['md5'] is None and os.path.isfile(lu):
            u.update(md5=md5(lu), mass=read_inertial(open(lu).read())[0])
        if u['md5'] is None:
            fails.append(f'{n} URDF {u["urdf"]} missing'); continue
        if abs(u['mass'] - PLACEHOLDER) > 1e-9:
            fails.append(f'{n} mass {u["mass"]} != {PLACEHOLDER}')
        if u['md5'] != URDF_B1.get(n):
            fails.append(f'{n} URDF md5 {u["md5"]} != the b1 asset copy {URDF_B1.get(n)} (is the carve applied?)')
    for s in a.seeds.split():
        pre = f'{PRE}s{s}'; RD = f'{C}/refs/{pre}_glockt/ep{EP}'; dpq = f'{RD}/{hive}/ref_gl_ilc.parquet'
        os.makedirs(os.path.dirname(dpq), exist_ok=True)
        if not (os.path.isfile(dpq) and md5(dpq) == REF_MD5):
            shutil.copyfile(src, dpq)
        n_pq = len(glob.glob(f'{RD}/**/*.parquet', recursive=True))
        if n_pq != 1:
            fails.append(f'{RD} holds {n_pq} parquet files (FlashCHORD needs exactly one)')
        lk = f'{C}/refs/{pre}{BASE}/ep{EP}'; os.makedirs(os.path.dirname(lk), exist_ok=True)
        if os.path.islink(lk):
            os.remove(lk)
        elif os.path.lexists(lk):
            sys.exit(f'arms: {lk} exists and is not a link')
        os.symlink(R0, lk)
        O = f'{C}/results/{pre}_glock_public/ep{EP}'; os.makedirs(O, exist_ok=True)
        for f in ('rest_check.json', 'zero_score.txt', 'support_fill.json'):
            if os.path.exists(f'{res0}/{f}'):
                shutil.copy(f'{res0}/{f}', f'{O}/{f}')
        man['seeds'][s] = dict(parquet=dpq, md5=md5(dpq), base_link=lk, results=O, pair=f'{EP}:local:{BASE}:{pre}')
        if man['seeds'][s]['md5'] != REF_MD5:
            fails.append(f'seed {s}: the copy is not a byte copy of P')
    man['ok'] = not fails; man['failures'] = fails
    json.dump(man, open(a.out, 'w'), indent=1)
    print(('ARMS OK' if not fails else 'ARMS FAILED: ' + ' | '.join(fails[:5])) + f" :: P {man['source_md5']} (fingerprint {fp[:12]}), "
          f"seeds {sorted(man['seeds'])}, " + ', '.join(f"{n} {u['mass']} kg URDF {str(u['md5'])[:8]}" for n, u in urd.items()))
    sys.exit(0 if not fails else 1)


# ---------------------------------------------------------------------------------------------------------------- cells
def cell(C, s, steps, packed_ck):
    O = f'{C}/results/{PRE}s{s}_glock_public/ep{EP}'; ck = f'{O}/best/policy.safetensors'; fails = []
    row = dict(seed=s, results=O, eval_timeouts=eval_timeouts(O))
    if not (os.path.isfile(f'{O}/best/summary.json') and os.path.isfile(ck)):
        return dict(row, status='MISSING', n=0, failures=[])
    try:
        summ = json.load(open(f'{O}/best/summary.json')); row['chosen_by_curve'] = summ.get('checkpoint')
        if row['chosen_by_curve'] and os.path.exists(row['chosen_by_curve']) and md5(row['chosen_by_curve']) != md5(ck):
            fails.append('best/policy.safetensors is not the checkpoint the curve chose')
        row['checkpoint'] = ck; row['sha256'] = e10cs.sha256(ck)
        diff, bad, sim, cfg = e10cs.config_diff(ck, packed_ck); row.update(config_diff_vs_packed=diff, sim_limits=sim)
        if bad:
            fails.append(f'saved config differs from the packed eval-20 checkpoint in {bad[:8]}')
        if [sim[k] for k in e10cs.SIM_KEYS] != [STOCK[0], STOCK[1], STOCK[0], STOCK[1]]:
            fails.append(f'sim limits {sim} are not the stock {STOCK}')
        row['reset_seed'] = (cfg.get('reset') or {}).get('seed'); row['steps'] = flat(cfg).get(STEPS_KEY)
        if str(row['reset_seed']) != str(s):
            fails.append(f'reset.seed {row["reset_seed"]} != {s}')
        if str(row['steps']) != str(steps):
            fails.append(f'{STEPS_KEY} {row["steps"]} != {steps}')
        task = cfg['task']['parquet']; rp = resolve_parquet(task.strip("'")); row.update(task_parquet=task, reference_file=rp, reference_md5=md5(rp))
        want = os.path.realpath(f'{C}/refs/{PRE}s{s}_glockt/ep{EP}') + '/'
        if not os.path.realpath(rp).startswith(want):
            fails.append(f'trained on {rp}, not this seed\'s copy under {want}')
        if row['reference_md5'] != REF_MD5:
            fails.append(f'reference md5 {row["reference_md5"]} != P {REF_MD5}')
        st = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(rp)))), 'reconstructed_stage')   # <RD>/processed/<seq>/<robot>/x.parquet
        row['support_stage'] = {os.path.basename(f): md5(f) for f in sorted(glob.glob(f'{st}/*.usda'))}
        if list(row['support_stage'].values()) != [STAGE_MD5]:
            fails.append(f'support stage {row["support_stage"]} != {STAGE_MD5}')
        urd, fp = urdfs_of(rp); row['loaded_urdfs'] = urd; row['traj_fingerprint'] = fp
        for n, u in urd.items():
            p, how = resolve_asset(u['urdf'])
            if p is None:
                fails.append(f'{n}: {u["urdf"]} {how}'); continue
            u['collisions'] = len(coll_files(open(p).read()))
            if abs(u['mass'] - PLACEHOLDER) > 1e-9:
                fails.append(f'{n} loads {u["mass"]} kg')
            if u['md5'] != URDF_B1.get(n) or u['collisions'] != COLL_B1.get(n):
                fails.append(f'{n} loads URDF md5 {u["md5"]} ({u["collisions"]} collisions), not the b1 copy {URDF_B1.get(n)}')
            if not os.path.realpath(p).startswith(os.path.realpath(f'{C}/refs/sf/ep{EP}/assets') + '/'):
                fails.append(f'{n}: {p} is not under {C}/refs/sf/ep{EP}/assets')
        v, ev = [], 0
        for r in sorted(glob.glob(f'{O}/best/r*/')):
            d = js(f'{r}episode_{EP:06d}.json')
            if d is not None:
                ev += 1
                if 'checkpoint_sha256' in d and d['checkpoint_sha256'] != row['sha256']:
                    fails.append(f'{os.path.basename(r[:-1])} evaluated checkpoint {str(d["checkpoint_sha256"])[:12]} != chosen {row["sha256"][:12]}')
            q = (js(f'{r}qa_policy.json') or {}).get('sim_vs_ref')
            if fin(q):
                v.append(float(q))
        row.update(evaluations_checked=ev, n=len(v), **e10cs.stats(v))
    except Exception as e:
        fails.append(f'{type(e).__name__}: {str(e)[:200]}')
    return dict(row, status='VERIFIED' if not fails else 'INVALID', failures=fails, n=row.get('n', 0))


def cmd_cells(a):
    C = a.content.rstrip('/'); seeds = a.seeds.split()
    cells = {s: cell(C, s, a.steps, a.packed_ck) for s in seeds}
    out = dict(rule='PREREG section 3.2 (pack 9b PREREG 1.3 style)', set=SET, packed_ck=a.packed_ck, packed_sha256=e10cs.sha256(a.packed_ck),
               allowed_config_diff=sorted(e10cs.ALLOWED), seeds=cells)
    if out['packed_sha256'] != PACKED_SHA:
        for c in cells.values():
            if c['status'] == 'VERIFIED':
                c['status'] = 'INVALID'
            c['failures'].append(f'packed checkpoint sha256 {out["packed_sha256"][:12]} != {PACKED_SHA[:12]}')
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    print('CELLS :: ' + ' | '.join(f"s{s} {c['status']} n {c['n']} mean {c.get('mean')} sd {c.get('sd')} min {c.get('min')}"
                                   + (f" FAIL {c['failures'][:3]}" if c['failures'] else '')
                                   + (f" config diff {c.get('config_diff_vs_packed')}" if c.get('config_diff_vs_packed') is not None else '')
                                   for s, c in cells.items()))
    sys.exit(0 if all(c['status'] != 'INVALID' for c in cells.values()) else 1)


def cmd_choose(a):
    cells = json.load(open(a.cells))['seeds']; seeds = a.seeds.split()
    ch, status, inv, thin = e10cs.choose(cells, seeds)
    out = dict(rule='PREREG section 3.3 = pack 9b PREREG section 2 (e10v rule 2): two VERIFIED seeds with n >= 8; the higher mean '
                    'sim_vs_ref vs P; within 0.005 (4-decimal means) the lower sd (ddof 1); still tied seed 42',
               min_n=MIN_N, status=status, invalid_seeds=inv, incomplete_seeds=thin, chosen=ch,
               checkpoint=cells[ch]['checkpoint'] if ch else None, sha256=cells[ch]['sha256'] if ch else None,
               seeds={s: dict(results=cells[s].get('results'), checkpoint=cells[s].get('checkpoint'), sha256=cells[s].get('sha256'), status=cells[s]['status'],
                              **{k: cells[s].get(k) for k in ('n', 'mean', 'sd', 'min', 'max', 'values', 'chosen_by_curve')}) for s in seeds})
    json.dump(out, open(a.out, 'w'), indent=1)
    print((f'CHOSEN seed {ch}' if ch else f'{status}: invalid {inv}, missing / thin {thin}') + ' :: '
          + '; '.join(f"s{s} {c['status']} n {c.get('n')} mean {c.get('mean')} sd {c.get('sd')}" for s, c in out['seeds'].items()))
    sys.exit(0 if ch else 1)


def gate(cells):
    rows = {s: dict(status=c['status'], n=c.get('n', 0), mean=c.get('mean'), mean_raw=c.get('mean_raw'),
                    above=bool(c['status'] == 'VERIFIED' and c.get('n', 0) >= MIN_N and fin(c.get('mean_raw')) and c['mean_raw'] > GATE_P + TOL),
                    margin=round(c['mean_raw'] - GATE_P, 4) if fin(c.get('mean_raw')) else None) for s, c in cells.items()}
    return dict(rule=f'PREREG section 4: >= 1 VERIFIED seed (n >= {MIN_N}) with training-box mean sim_vs_ref vs P > {GATE_P}', bar=GATE_P,
                bar_source='the packed eval-20 policy\'s 10 fresh (H5p7) draws, mean sim_vs_ref vs P: runs/20261031-h5p7-1a7cdff/results/h5/'
                           'h5_summary.json["20"]["mean"] [M] (dr_score.py on the same 10 draws: 0.8933)',
                met=any(r['above'] for r in rows.values()), seeds=rows)


def cmd_gate(a):
    try:
        g = gate(json.load(open(a.cells))['seeds'])
    except Exception as e:
        print(f'GATE UNREADABLE: {type(e).__name__}: {e}'); sys.exit(1)
    json.dump(g, open(a.out, 'w'), indent=1)
    print(('GATE MET' if g['met'] else 'GATE NOT MET (training-box gate not met: no confirmation draws)') + f' (bar > {GATE_P} vs P) :: '
          + '; '.join(f"s{s} {r['status']} n {r['n']} mean {r['mean']} margin {r['margin']}" for s, r in g['seeds'].items()))
    sys.exit(0 if g['met'] else 3)


# --------------------------------------------------------------------------------------------------------------- verify
def cmd_verify(a):
    G = a.dir.rstrip('/'); fails, missing = [], []
    pcs, inp, ast, arms, cells, ch, gt = (js(f'{G}/{x}.json') for x in ('pieces', 'inputs', 'assets', 'arms', 'cells', 'choice', 'gate'))
    for name, d in (('pieces', pcs), ('inputs', inp), ('assets', ast), ('arms', arms)):
        if not d or not d.get('ok'):
            fails.append(f'{name}.json missing or not ok: {(d or {}).get("failures")}')
    if not cells:
        fails.append('cells.json missing')
    else:
        for s, c in cells['seeds'].items():
            if c['status'] == 'INVALID':
                fails.append(f's{s}: {c["failures"][:4]}')
            elif c['status'] == 'MISSING':
                missing.append(f's{s}')
    conf = dict(draws=0, checked=0)
    if ch and ch.get('chosen'):
        conf.update(chosen=ch['chosen'], sha256=ch['sha256'])
        if cells and ch['sha256'] != cells['seeds'][ch['chosen']].get('sha256'):
            fails.append('choice.json names a checkpoint that is not the chosen seed\'s best/policy.safetensors')
        for f in sorted(glob.glob(f'{G}/conf/r*/ep{EP}/episode_{EP:06d}.json')):
            conf['draws'] += 1; d = js(f)
            if d is None:
                continue
            conf['checked'] += 1
            if d.get('checkpoint_sha256') != ch['sha256']:
                fails.append(f'confirmation {os.path.relpath(f, G)}: checkpoint {str(d.get("checkpoint_sha256"))[:12]} != chosen {ch["sha256"][:12]}')
        rcs = [open(f).read().strip() for f in glob.glob(f'{G}/conf/r*/eval_rc.txt')]
        conf['eval_rc'] = {x: rcs.count(x) for x in sorted(set(rcs))}
        if conf['draws'] and not os.path.isfile(f'{G}/no_oracle_choice.txt'):
            fails.append('confirmation draws exist but the no_oracle check of the chosen checkpoint left no record')
    own = {}
    for f in sorted(glob.glob(f'{G}/score*.json')):
        for name, s_ in ((js(f) or {}).get('sets') or {}).items():
            for r in s_.get('rollouts', []):
                if r.get('scored') and s_.get('own') == 'P':
                    c = r.get('own_ref_check') or {}; own[f'{name}/r{r.get("draw")}'] = c.get('ok')
                    if not c.get('ok'):
                        fails.append(f'{os.path.basename(f)} {name} r{r.get("draw")}: own-reference check failed {c}')
    out = dict(ok=not fails, failures=fails, missing=missing, set=(pcs or {}).get('set'), confirmation=conf, own_ref_checks=own,
               gate_met=(gt or {}).get('met'), choice={k: (ch or {}).get(k) for k in ('chosen', 'checkpoint', 'sha256', 'status', 'incomplete_seeds')},
               rule='docs/research/work/eval20-b1-20261101/PREREG.md section 6')
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    print(('VERIFIED' if out['ok'] else f'VERIFY FAILED ({len(fails)}): ' + ' | '.join(fails[:6])) + (f' :: MISSING {missing}' if missing else '')
          + f" :: set {out['set']} :: chosen {out['choice'].get('chosen')} :: confirmation draws {conf.get('draws')} (rc {conf.get('eval_rc')}) :: "
          f"own-reference checks {sum(1 for v in own.values() if v)}/{len(own)}")
    sys.exit(0 if out['ok'] else 1)


# -------------------------------------------------------------------------------------------------------------- verdict
def swap_rule(sets, ch, ref_md5s):
    """(label, why, clauses, sides) of the pack 9b swap rule on P (dr_verdict's clause code)"""
    sha = ch.get('sha256')
    N = dr_verdict.scored((sets.get('conf') or {}).get('rollouts', [])); K = dr_verdict.scored((sets.get('packed') or {}).get('rollouts', []))
    O = dr_verdict.scored((sets.get('old') or {}).get('rollouts', []))
    sides = dict(new=dr_verdict.side(N) if N else None, packed=dr_verdict.side(K) if K else None)
    bad = []
    if ref_md5s.get('P') != {REF_MD5}:
        bad.append(f'reference P md5 across score files {sorted(ref_md5s.get("P") or [])} != the packed reference {REF_MD5}')
    for name, s_ in sets.items():
        want = sha if name == 'conf' else PACKED_SHA if name in ('packed', 'old') else None
        for r in s_.get('rollouts', []):
            if not r.get('scored'):
                continue
            if s_.get('own') != 'P' or not (r.get('own_ref_check') or {}).get('ok'):
                bad.append(f'{name}/r{r.get("draw")}: own-reference check not ok (own {s_.get("own")})')
            if want and r.get('checkpoint_sha256') != want:
                bad.append(f'{name}/r{r.get("draw")}: checkpoint {str(r.get("checkpoint_sha256"))[:12]} != {str(want)[:12]}')
    if bad:
        return 'INVALID', bad[:8], {}, sides
    draw1 = min(N, key=lambda r: r.get('draw', 0), default=None); inc = []
    if len(N) < MIN_CONF:
        inc.append(f'{len(N)} scored confirmation draws (< {MIN_CONF})')
    if len(K) < MIN_CONF:
        inc.append(f'{len(K)} scored packed-policy draws (< {MIN_CONF})')
    if len(O) != 1:
        inc.append(f'old packed draw scored {len(O)} times (1 needed)')
    if draw1 is None:
        inc.append('no scored confirmation draw')
    if inc:
        return 'INCOMPLETE', inc, {}, sides
    cl, err = dr_verdict.clauses_of(sides['new'], sides['packed'], draw1['vs']['P']['sim_vs_ref'], O[0]['vs']['P']['sim_vs_ref'])
    if cl is None:
        return 'INVALID', [err], {}, sides
    cl['s'].update(new_draw1_r=draw1.get('draw'), new_draw1_path=draw1.get('path'))
    failed = [c for c, v in cl.items() if not v['holds']]
    return ('SWAP-ELIGIBLE', ['every clause holds'], cl, sides) if not failed else ('NO-SWAP', [f'fails: {failed}'], cl, sides)


def cmd_verdict(a):
    G = a.dir.rstrip('/'); seeds = a.seeds.split()
    pcs, ast, cells, ch, gt, ver, ov, zr = (js(f'{G}/{x}.json') for x in ('pieces', 'assets', 'cells', 'choice', 'gate', 'verify', 'overflow', 'rest_check_b1'))
    sets, refs_md5 = {}, {}
    for f in a.score or []:
        d_ = js(f) or {}
        for X, info in (d_.get('refs') or {}).items():
            refs_md5.setdefault(X, set()).add(info.get('md5'))
        sets.update(d_.get('sets') or {})
    clauses, sides, why = {}, {}, []
    if os.path.exists(f'{G}/STOPPED'):
        label, why = 'INVALID', [f'job stopped: {open(f"{G}/STOPPED").read().strip()[:300]}']
    elif not ver or not ver.get('ok'):
        label, why = 'INVALID', [f'verify failed: {(ver or {}).get("failures", ["verify.json missing"])[:6]}']
    elif not ch or not ch.get('chosen'):
        st = (ch or {}).get('status'); label = 'INVALID' if st == 'INVALID' else 'INCOMPLETE'
        why = [f'no chosen seed ({st}; invalid {(ch or {}).get("invalid_seeds")}, missing / thin {(ch or {}).get("incomplete_seeds")})']
    elif not gt or not gt.get('met'):
        label = 'NO-SWAP'
        why = [f'training-box gate not met: no seed\'s training-box mean sim_vs_ref vs P above {GATE_P} '
               f'({ {s: r.get("mean") for s, r in ((gt or {}).get("seeds") or {}).items()} }); no confirmation draws']
    else:
        label, why, clauses, sides = swap_rule(sets, ch, refs_md5)
    if not sides or not sides.get('packed'):
        K = dr_verdict.scored((sets.get('packed') or {}).get('rollouts', []))
        sides = dict(sides or {}, packed=dr_verdict.side(K) if K else None)
    nm, km = ((sides.get('new') or {}).get('mean_raw'), (sides.get('packed') or {}).get('mean_raw'))
    gain = (nm - km) if fin(nm) and fin(km) else None
    include = bool(label == 'SWAP-ELIGIBLE' and gain is not None and gain >= INCL_BAR - TOL)
    inclusion = dict(rule=f'binding: a SWAP-ELIGIBLE eval 20 enters pack 10 only if (new confirmation mean - packed fresh-draw mean) '
                          f'sim_vs_ref vs P >= {INCL_BAR}', bar=INCL_BAR, gain=round(gain, 4) if gain is not None else None, include_in_pack10=include,
                     reading=('INCLUDE in pack 10' if include else ('SWAP-ELIGIBLE but below the 0.02 inclusion bar: NOT included in pack 10'
                                                                    if label == 'SWAP-ELIGIBLE' else 'not swap-eligible: not included')))
    tov = e10cs.training_overflow(ov, seeds)
    unclean = [s for s, o in tov.items() if o['dropped'] is not None and o['dropped'] > O_BAR]
    fl = ((sides.get('new') or {}).get('fail_raw'), (sides.get('packed') or {}).get('fail_raw'))
    equal_floor = all(x is not None and x >= 0.9 for x in fl)
    tb = {}
    for s in seeds:
        rows = dr_verdict.scored((sets.get(f'train{s}') or {}).get('rollouts', []))
        tb[s] = dr_verdict.side(rows) if rows else None
    strip = lambda v: {k: x for k, x in (v or {}).items() if not k.endswith('_raw')} if v else None
    out = dict(label=label, why=why, rule='docs/research/work/eval20-b1-20261101/PREREG.md section 5',
               labels_attached=(['pieces not clean in training'] if unclean else []) + (['EQUAL FLOOR'] if equal_floor else []),
               pack10_inclusion=inclusion, clauses=clauses, sides={k: strip(v) for k, v in sides.items()},
               training_box_gate=gt,
               overflow=dict(bar=O_BAR, unclean_seeds=unclean, per_seed=tov,
                             other={k: dict(files=v.get('files'), dropped=v.get('dropped')) for k, v in ((ov or {}).get('groups') or {}).items()
                                    if not k.startswith('train_s')},
                             baseline='determined-wright contact_budget f59c897 (FlashCHORD 32 x 60): b1 0 / 0 lines, sampled max 342, explicit 321 [R]'),
               training_box={s: strip(t) for s, t in tb.items()},
               choice={k: (ch or {}).get(k) for k in ('status', 'chosen', 'checkpoint', 'sha256', 'seeds', 'incomplete_seeds', 'invalid_seeds')},
               rest_check=dict(note='reported, not gating: zero-action replay of P on the b1 asset copy (tools/trace_rollout.py zero + '
                                    'tools/rest_check.py, 5 mm / 2 deg until a hand comes) next to the packed run\'s record', b1=zr,
                               packed=REST_PACKED),
               pieces=dict(set=(pcs or {}).get('set'), dir=(pcs or {}).get('dir'), md5sums_md5=(pcs or {}).get('md5sums_md5'),
                           frozen_md5=(pcs or {}).get('frozen_md5'), manifest=(pcs or {}).get('manifest'), source=PIECES['source']),
               urdfs={n: {k: u.get(k) for k in ('packed_md5', 'md5', 'collisions_packed', 'collisions', 'inertial_equal', 'visual_equal')}
                      for n, u in ((ast or {}).get('urdfs') or {}).items()},
               verify=dict(ok=(ver or {}).get('ok'), failures=(ver or {}).get('failures'), confirmation=(ver or {}).get('confirmation')),
               equal_floor_note=('both policies fail >= 90 % of their draws: the rule compares two floors; expected effect about 0') if equal_floor else None,
               counts={k: dict(own=v.get('own'), n_files=v.get('n_files'), n_scored=v.get('n_scored')) for k, v in sets.items()})
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    s_new, s_k = sides.get('new') or {}, sides.get('packed') or {}
    print(f"{label}{' [' + ', '.join(out['labels_attached']) + ']' if out['labels_attached'] else ''} :: pack 10: {inclusion['reading']} "
          f"(gain vs P {inclusion['gain']}; bar {INCL_BAR}) :: " + '; '.join(why)
          + ' :: ' + ' | '.join(f"{k} {'ok' if v['holds'] else 'FAIL'} margin {v.get('margin')}" for k, v in clauses.items())
          + (f" :: new {(s_new.get('sim_vs_ref') or {}).get('mean')} (n {s_new.get('n')}, fails {s_new.get('fails')}, RPE med {(s_new.get('RPE') or {}).get('median')})" if s_new else '')
          + (f" vs packed {(s_k.get('sim_vs_ref') or {}).get('mean')} (n {s_k.get('n')}, fails {s_k.get('fails')}, RPE med {(s_k.get('RPE') or {}).get('median')})" if s_k else '')
          + f" :: gate {'met' if (gt or {}).get('met') else 'NOT met'} " + str({s: r.get('mean') for s, r in ((gt or {}).get('seeds') or {}).items()})
          + f" :: overflow lines per training log {{{', '.join(f's{s}: {o['dropped']}' for s, o in tov.items())}}} (bar {O_BAR})"
          + f" :: chosen seed {(ch or {}).get('chosen')} :: set {out['pieces']['set']} (MD5SUMS {str(out['pieces']['md5sums_md5'])[:12]})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    i = sp.add_parser('import'); i.add_argument('--rev', required=True); i.add_argument('--src', required=True); i.add_argument('--dst', required=True)
    i.add_argument('--repo', default=REPO); i.add_argument('--also', action='append')
    p = sp.add_parser('pieces'); p.add_argument('--dir', required=True); p.add_argument('--out', required=True)
    n = sp.add_parser('inputs'); n.add_argument('--content', default='/content'); n.add_argument('--table', default='')
    n.add_argument('--packed_ck', default=''); n.add_argument('--out', required=True)
    s = sp.add_parser('assets'); s.add_argument('--packed', required=True); s.add_argument('--carved', required=True)
    s.add_argument('--pieces', required=True); s.add_argument('--out', required=True)
    r = sp.add_parser('arms'); r.add_argument('--content', default='/content'); r.add_argument('--seeds', default='42 43'); r.add_argument('--out', required=True)
    c = sp.add_parser('cells'); c.add_argument('--content', default='/content'); c.add_argument('--seeds', default='42 43')
    c.add_argument('--steps', type=int, required=True); c.add_argument('--packed_ck', required=True); c.add_argument('--out', required=True)
    h = sp.add_parser('choose'); h.add_argument('--cells', required=True); h.add_argument('--seeds', default='42 43'); h.add_argument('--out', required=True)
    g = sp.add_parser('gate'); g.add_argument('--cells', required=True); g.add_argument('--out', required=True)
    v = sp.add_parser('verify'); v.add_argument('--dir', required=True); v.add_argument('--out', required=True)
    d = sp.add_parser('verdict'); d.add_argument('--dir', required=True); d.add_argument('--score', action='append'); d.add_argument('--seeds', default='42 43')
    d.add_argument('--out', required=True)
    a = ap.parse_args()
    dict(pieces=cmd_pieces, inputs=cmd_inputs, assets=cmd_assets, arms=cmd_arms, cells=cmd_cells, choose=cmd_choose, gate=cmd_gate,
         verify=cmd_verify, verdict=cmd_verdict, **{'import': cmd_import})[a.cmd](a)


if __name__ == '__main__':
    main()
