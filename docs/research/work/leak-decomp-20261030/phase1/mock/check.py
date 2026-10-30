"""Checks of one perc_leak mock run (after run_mock.sh). usage: check.py MR RUN_ID 'EPS' 'REPEAT' [ARMS]
Prints a report and exits 1 if any expectation fails:
  - job exit code 0 (the clean run); every episode's bundle ok; every arm's template kind (scan only for perc2scan),
    MESH_DIR as perc2 saw it (MR/perc2_audit.log: unset for perc2scan, the library for perc2 / perc2rep), KF_MIN 120,
    SPLIT public, HF_HUB_OFFLINE=1, depth cache existed (reused) and its stat unchanged; o2 only for REPEAT episodes;
  - Grounding DINO loaded once, before perc2, online (MR/gdino_tries.txt); every arm's bundle records gdino True;
  - hands md5 = inputs.tsv, depth frame-0 sha256 = inputs.tsv, cameras of the arms identical;
  - store traffic (MR/hf.log): single-file downloads only (no listing), exactly 3 per episode (depth + 2 hands files),
    one upload (the final push-run);
  - push list (MR/content/push/RUN_ID): no depth cache, no symlink, every bundle file present, the download log under
    results/leak_p1/; each bundle tar = its episode folder without result.json / log.txt (mocap scores); sizes;
  - guard: tools/no_oracle.py (run as a script per word) refuses every pushed file by its store path
    runs/RUN_ID/<file>, every bare bundle tar name and every bare P_s path as a tar member has it (ep<N>/perc2scan/...,
    B8); the bare P_o paths (ep<N>/perc2/..., perc2rep/...) are reported."""
import json, os, runpy, sys, io, contextlib
MR, RID, EPS, REP = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split()], {int(x) for x in sys.argv[4].split()}
ARMS = (sys.argv[5] if len(sys.argv) > 5 else 'o,s,o2').split(',')
C = f'{MR}/content'; B = f'{C}/results/leak_p1'; fails = []
FOLD = {'o': 'perc2', 's': 'perc2scan', 'o2': 'perc2rep'}
LIB = f'{C}/v2d-track3/meshes/library_v3'


def need(cond, what):
    if not cond:
        fails.append(what)
    return cond


rc = open(f'{MR}/rc.txt').read().strip(); need(rc == '0', f'job rc {rc}')
print(f'job rc {rc}; last job.log lines:'); print(''.join(open(f'{C}/job.log').readlines()[-6:]).replace(MR, '<MR>'))
aud = [json.loads(l) for l in open(f'{MR}/perc2_audit.log')] if os.path.exists(f'{MR}/perc2_audit.log') else []
hf = [json.loads(l) for l in open(f'{MR}/hf.log')] if os.path.exists(f'{MR}/hf.log') else []
for e in EPS:
    want = [FOLD[a] for a in ARMS if a != 'o2' or e in REP]
    b = json.load(open(f'{B}/ep{e}/bundle.json')); inp = b['inputs']
    need(b['ok'], f'ep{e} bundle not ok: {inp.get("problems")}')
    need(sorted(b['arms']) == sorted(want), f'ep{e} arms {sorted(b["arms"])} != {sorted(want)}')
    need(inp['depth'].get('matches_refine_inputs') is True, f'ep{e} depth frame 0 != refine')
    need(all(inp['hands'][f].get('md5_ok') for f in ('hands.npz', 'hands_refined.npz')), f'ep{e} hands md5')
    for f in want:
        a = b['arms'][f]; au = [x for x in aud if x['ep'] == e and x['folder'] == f]
        need(len(au) == 1, f'ep{e} {f}: {len(au)} perc2 runs'); au = au[-1] if au else {}
        kind = 'scan' if f == 'perc2scan' else 'library'
        need(a['template_kind'] == kind, f'ep{e} {f} template kind {a["template_kind"]}')
        need(au.get('mesh_dir') == ('<unset>' if f == 'perc2scan' else LIB), f'ep{e} {f} MESH_DIR seen by perc2 {au.get("mesh_dir")}')
        need({n: v['path'] for n, v in a['templates'].items()} == au.get('templates'), f'ep{e} {f} bundle templates != perc2 audit')
        need(au.get('kf_min') == '120' and au.get('split') == 'public', f'ep{e} {f} KF_MIN/SPLIT {au.get("kf_min")}/{au.get("split")}')
        need(au.get('hf_hub_offline') == '1', f'ep{e} {f} HF_HUB_OFFLINE seen by perc2 {au.get("hf_hub_offline")}')
        need(a.get('gdino') is True, f'ep{e} {f} gdino {a.get("gdino")}')
        need(au.get('depth_cache_existed') is True and a['depth_reused'], f'ep{e} {f} depth not reused')
        need(a.get('camera_maxdiff_vs_perc2', 0.0) == 0.0, f'ep{e} {f} camera differs')
        need(os.path.isfile(f'{B}/ep{e}/{f}/perc_log_inference.txt') and
             not any(k in open(f'{B}/ep{e}/{f}/perc_log_inference.txt').read() for k in (' AUC ', 'anchor:', 'DONE')),
             f'ep{e} {f} perc_log_inference.txt has scoring lines')
    print(f'ep{e}: bundle ok {b["ok"]}; arms ' + ', '.join(
        f'{f} [{b["arms"][f]["template_kind"]}: ' + ' '.join(os.path.basename(v['path']) for v in b['arms'][f]['templates'].values())
        + f'; depth reused {b["arms"][f]["depth_reused"]}]' for f in want) +
        f'; hands md5 {inp["hands"]["hands.npz"]["md5"][:8]}/{inp["hands"]["hands_refined.npz"]["md5"][:8]} = inputs.tsv; '
        f'depth frame-0 sha {inp["depth"]["frame0_sha256"][:8]} = inputs.tsv')
kinds = [x['kind'] for x in hf]; dl = [x for x in hf if x['kind'] == 'file']
need('LISTING' not in kinds, 'a download listed the repo')
need(len([x for x in dl if x['result'] == 'ok']) == 3 * len(EPS), f'{len(dl)} file downloads for {len(EPS)} episodes')
need(kinds.count('upload') == 1, f'{kinds.count("upload")} uploads')
print(f'store traffic: {len(dl)} single-file downloads ({sum(x["result"] == "429" for x in dl)} answered 429 and retried), '
      f'{kinds.count("LISTING")} listings, {kinds.count("upload")} upload(s): ' +
      '; '.join(f'{x["src"]} -> {x["dst"]}' for x in hf if x['kind'] == 'upload'))
gt = open(f'{MR}/gdino_tries.txt').read().splitlines() if os.path.exists(f'{MR}/gdino_tries.txt') else []
jl = open(f'{C}/job.log').read()
need(gt and all(' offline=None ' in x for x in gt) and gt[-1].endswith(' ok'), f'Grounding DINO load: {gt}')
need(jl.count('Grounding DINO cached (try ') == 1, 'Grounding DINO not cached exactly once before perc2')
need(not aud or all(x.get('hf_hub_offline') == '1' for x in aud), 'a perc2 run without HF_HUB_OFFLINE=1')
print(f'Grounding DINO: {len(gt)} from_pretrained calls before perc2 ({"; ".join(gt)}); '
      f'perc2 runs with HF_HUB_OFFLINE=1: {sum(x.get("hf_hub_offline") == "1" for x in aud)}/{len(aud)}')
S = f'{C}/push/{RID}'; files = []
for r, ds, fs in os.walk(S):
    for f in fs:
        files.append(os.path.relpath(f'{r}/{f}', S))
need(not [f for f in files if os.path.basename(f).startswith('depths_')], 'a depth cache is in the push')
need(not [f for f in files if os.path.islink(f'{S}/{f}')], 'a symlink is in the push')
size = sum(os.path.getsize(f'{S}/{f}') for f in files)
p1 = sorted(f for f in files if f.startswith('results/leak_p1/'))
for e in EPS:
    for f in ['depth0.npy', 'inputs.json', 'bundle.json', 'hands/hands.npz', 'hands/hands_refined.npz'] + \
             [f'{FOLD[a]}/{x}' for a in ARMS if a != 'o2' or e in REP for x in
              ('poses.npz', 'poses_world_vo.npz', 'vo.json', 'log.txt', 'perc_log_inference.txt', 'result.json', 'run.json')]:
        need(f'results/leak_p1/ep{e}/{f}' in p1, f'push lacks results/leak_p1/ep{e}/{f}')
    tf = f'results/leak_p1/bundle_ep{e}_oracle.tar'
    if need(tf in p1, f'push lacks {tf}'):
        import tarfile
        with tarfile.open(f'{S}/{tf}') as t:
            n = sorted(m.name for m in t.getmembers() if m.isfile())
        need(n == sorted(f[len('results/leak_p1/'):] for f in p1 if f.startswith(f'results/leak_p1/ep{e}/')
                         and os.path.basename(f) not in ('result.json', 'log.txt')), f'{tf} != ep{e}/ without result.json, log.txt')
        need(not [m for m in n if os.path.basename(m) in ('result.json', 'log.txt')], f'{tf} holds mocap-score files')
need('results/leak_p1/leak_pull.log' in p1, 'push lacks results/leak_p1/leak_pull.log')
print(f'push list: {len(files)} files, {size / 1e6:.1f} MB; results/leak_p1: {len(p1)} files; other: '
      + ', '.join(sorted(f for f in files if not f.startswith('results/leak_p1/'))))
print('  per episode (first): ' + ', '.join(f[len(f"results/leak_p1/ep{EPS[0]}/"):] for f in p1 if f.startswith(f'results/leak_p1/ep{EPS[0]}/')))
G = os.environ.get('GUARD') or f'{C}/v2d-track3/tools/no_oracle.py'                  # GUARD: a candidate guard instead


def refused(word):
    sys.argv = [G, word]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            runpy.run_path(G, run_name='__main__')
        except SystemExit as x:
            return x.code == 1
    return False


by_store = [refused(f'runs/{RID}/{f}') for f in files]
need(all(by_store), f'guard accepts {sum(not x for x in by_store)} pushed files by store path')
mem = [f[len('results/leak_p1/'):] for f in p1 if f.startswith('results/leak_p1/ep')]     # as tar members: ep<N>/...
bare = {k: [refused(f) for f in mem if f'/{k}/' in f] for k in ('perc2scan', 'perc2', 'perc2rep')}
bare['bundle tar'] = [refused(os.path.basename(f)) for f in p1 if f.endswith('_oracle.tar')]
need(all(bare['bundle tar']), 'guard accepts a bare bundle tar name')
need(bare['perc2scan'] and all(bare['perc2scan']), 'guard accepts a bare perc2scan path (B8)')
print(f'guard ({G.replace(MR, "<MR>")}): refuses {sum(by_store)}/{len(files)} pushed files by store path runs/{RID}/...; bare paths '
      '(ep<N>/<arm>/..., tar names) refused: ' + ', '.join(f'{k} {sum(v)}/{len(v)}' for k, v in bare.items()))
print('RESULT:', 'ALL CHECKS PASS' if not fails else f'{len(fails)} FAILED: {fails[:12]}')
sys.exit(1 if fails else 0)
