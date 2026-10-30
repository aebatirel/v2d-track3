"""Leak decomposition, CPU test (f) of PLAN.md §7 for B8 tools/no_oracle.py (the eval-pack leak guard), as the oracle
twins tested it (PREREG §2.4): it must refuse every oracle / leak-study / scan-geometry input and still pass all 20
pack-7 checkpoints. Runs the guard as the pack scripts do (python -I tools/no_oracle.py WORDS, from the repo root).
  1 accept: the 20 pack-7 checkpoints (local copies, sha256 = checkpoints.json) as a kit JSON and as words, the stored
    pack-7 / pack-8 checkpoint JSONs, pack 6/7's RUNS / PICK / EP_LIB / ASSET_PIECES words (h5_reeval.sh), the mesh
    libraries and carve pieces, and look-alike words (highThreshold, leaky_relu, our spoon in t3/mesh, ...);
  2 refuse, as before: an -orc id, an oracle path, the renamed oracle-trained checkpoint of the oracle-twin test;
  3 refuse, new (B8): scanlib, perc2scan / perc2gf, hT, leak_p1 / leak_cells, leak run ids, public scan paths,
    ASSET_SRC=public runs; by content, under NEUTRAL names (FIX, deleted afterwards): a symlink farm onto the scans (as
    physics_arms.sh builds scanlib), renamed byte copies of scans (as a file, a directory, EP:DIR), a neutral link onto
    a perc2scan folder, and renamed checkpoints whose stored config names a perc2scan / hT / scanlib reference;
  4 the store listing (store_files.txt): which store paths the old and the new rule refuse, none of a pack run;
  5 the Phase-1 mock (phase1/mock, box a, real perc_leak.sh): every pushed file by its store path, every bare
    perc2scan path and bundle tar; the bare P_o folders (ep<N>/perc2, perc2rep) stay accepted: perc2 is the eval
    pipeline's own folder name and P_o reads no ground truth (their store paths carry the -orc run id).
Usage: python -I guard_test.py --repo REPO --scratch SCRATCH --fix NEUTRAL_DIR --mr MOCK_ROOT --out guard_test.json
"""
import argparse, glob, hashlib, importlib.util, json, os, re, shutil, struct, subprocess, sys

ap = argparse.ArgumentParser()
for k in ('repo', 'scratch', 'fix', 'mr', 'out'):
    ap.add_argument('--' + k, required=True)
A = ap.parse_args()
R, S = A.repo, A.scratch
GUARD = f'{R}/tools/no_oracle.py'
OLD = re.compile(r'oracle|\d{8}-orc[A-Za-z0-9]*-')                         # the rule before B8 (oracle twins)
spec = importlib.util.spec_from_file_location('no_oracle', GUARD); G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
res, fails = {}, []


def need(ok, what):
    print(('PASS ' if ok else 'FAIL ') + what)
    if not ok:
        fails.append(what)
    return ok


def guard(*words):
    p = subprocess.run([sys.executable, '-I', GUARD, *words], capture_output=True, text=True, cwd=R)
    return p.returncode, (p.stdout + p.stderr).strip()


# ------------------------------------------------------------------ 1 accept
ck = json.load(open(f'{R}/results/submissions/20261030-track3g-candidate/checkpoints.json'))
have = glob.glob(f'{S}/**/*.safetensors', recursive=True)
local = {}
for ep, v in ck.items():
    m = [c for c in have if c.endswith(v['checkpoint']) and hashlib.sha256(open(c, 'rb').read()).hexdigest() == v['sha256']]
    if m:
        local[ep] = m[0]
need(len(local) == 20, f'pack 7: {len(local)}/20 checkpoints found locally with sha256 = checkpoints.json')
os.makedirs(A.fix, exist_ok=True)
json.dump(local, open(f'{A.fix}/pack7_local.json', 'w'), indent=1)
rc, out = guard(f'{A.fix}/pack7_local.json'); need(rc == 0, f'pack 7: kit checkpoints JSON of the 20 local copies: rc {rc} ({out[:120]})')
bad = [ep for ep, p in local.items() if guard(p)[0] != 0]
need(not bad, f'pack 7: each of the 20 checkpoints as a word: refused {bad}')
cfg_hits = {ep: [c for c in G.ckpt_config(p) if G.BAD.search(c)] for ep, p in local.items()}
need(not any(cfg_hits.values()) and all(G.ckpt_config(p) for p in local.values()),
     f'pack 7: every stored training config read ({sum(len(G.ckpt_config(p)) for p in local.values())} strings), none matches')
for f in ('20261030-track3g-candidate/checkpoints.json', '20261030-track3h-candidate/checkpoints_box.json',
          '20261026-track3f/checkpoints.json'):
    if os.path.exists(f'{R}/results/submissions/{f}'):
        rc, out = guard(f'results/submissions/{f}'); need(rc == 0, f'stored {f}: rc {rc}')
h5 = open(f'{R}/ops/jobs/h5_reeval.sh').read()
words = []
for var in ('RUNS', 'PICK'):
    words += re.search(rf'export {var}="([^"]*)"', h5).group(1).replace(' ${PICK_EXTRA:-}', '').split()
words += ['8:/content/v2d-track3/meshes/library_v3x', '8:meshes/library_v3x', 'meshes/carve/ev25', 'meshes/carve/ev10',
          'meshes/carve/ev01', 'meshes/library_v3', f'{R}/meshes/library_v3', 'meshes/library_v3x', 'meshes/library_v4',
          '20261030-c01s43-328139c', '20261029-rcB-34bf6ae', '20261026-pack6-5203d42']
rc, out = guard(*words); need(rc == 0, f'pack 6/7 words of h5_reeval.sh + libraries + carve pieces ({len(words)} words): rc {rc} {out[:200]}')
look = ['highThreshold', 'rightThumb', 'leaky_relu', 'scan_path', 'track3', 'v2d-track3', '/content/t3/mesh/wooden_spoon/wooden_spoon.glb',
        '/content/t3/urdf/wooden_spoon_rigid.urdf', '/content/t3/calib.json', 'robot_name=sharpa_wave', 'hTx', 'HT', 'leakage',
        '/content/assets', 'refs/glockt/ep11', 'refs/perc2mcks/ep25', '/content/perc2/ep11', 'perc2rep', 'refs/sf/ep32']
acc = {w: guard(w)[0] for w in look}
need(all(v == 0 for v in acc.values()), f'look-alikes accepted: {[w for w, v in acc.items() if v]} refused')
res['accept'] = dict(pack7=local, words=len(words), look_alikes=acc)

# ------------------------------------------------------------------ 2 refuse, as before
old = ['20261030-orcB-38234d1', '11:20261030-orcB-38234d1', 'refs/oracle_glockt/ep11', '/content/oracle/ep11',
       'results/hard_ab/ep31/oracle_mcks-s42']
r2 = {w: guard(w)[0] for w in old}
gt = f'{S}/guardtest/ck.json'
if os.path.exists(gt):
    r2['renamed oracle checkpoint (guardtest/ck.json)'] = guard(gt)[0]
need(all(v == 1 for v in r2.values()), f'oracle-twin refusals kept: {r2}')

# ------------------------------------------------------------------ 3 refuse, new (B8)
new = ['/content/scanlib', '/content/scanlib/blue_cup.glb', '/content/assets_scanlib', '8:/content/ScanLib',
       'runs/20261030-orcP1a-38234d1/results/leak_p1/ep11/perc2scan/poses.npz', 'results/leak_p1/ep11/perc2scan/poses.npz',
       'results/leak_p1/ep11/perc2/poses.npz', '/content/perc2scan/ep11', '/content/perc2gf/ep18', 'refs/perc2scanmck/ep11',
       'refs/glockt_hT/ep11', '/content/hands_hT/ep11/hands.npz', 'refs/c7-hT/ep2', 'hT', 'results/leak_cells/ep11/c6/s42',
       'docs/research/work/leak-decomp-20261030/tierA/xstar_trk.json', '20261031-orcL11s42-abc1234',
       '11:20261031-orcL11s42-abc1234', '20261031-orcP1b-abc1234@results/leak_p1', '/content/t3/mesh/blue_cup/blue_cup.glb',
       '/content/t3/mesh/mini_sweeper/mini_sweeper_collision.glb', '/content/t3/urdf/blue_cup_rigid.urdf',
       'track_3/public/mesh/white_pot/white_pot.glb', '20261022-r5ks-72ecb2f', '24:20261022-r5ks43-72ecb2f']
r3 = {w: guard(w)[0] for w in new}
need(all(v == 1 for v in r3.values()), f'B8 name refusals ({len(new)}): accepted {[w for w, v in r3.items() if v != 1]}')
scans = sorted(glob.glob(f'{S}/hfds/track_3/public/mesh/*/*.glb'))
F = A.fix
for d in ('farm', 'copies', 'onefile', 'ck', 'trk'):
    shutil.rmtree(f'{F}/{d}', ignore_errors=True); os.makedirs(f'{F}/{d}')
for p in scans:                                                    # as physics_arms.sh builds /content/scanlib
    n = os.path.basename(os.path.dirname(p)); os.symlink(p, f'{F}/farm/{n}.glb') if not os.path.lexists(f'{F}/farm/{n}.glb') else None
for i, p in enumerate(scans[:3]):
    shutil.copy(p, f'{F}/copies/obj{i}.glb')
shutil.copy(scans[1], f'{F}/onefile/mesh_a.glb')
os.makedirs(f'{F}/trk/perc2scan/ep11', exist_ok=True); os.symlink(f'{F}/trk/perc2scan/ep11', f'{F}/trk/tracks11')
open(f'{F}/trk/perc2scan/ep11/poses.npz', 'w').write('stub')
need(not any(G.BAD.search(x) for x in (F, f'{F}/farm', f'{F}/copies/obj0.glb', f'{F}/trk/tracks11')),
     f'fixtures sit under neutral names ({F}), so the refusals below are by content')


def renamed(src, dst, old, new):  # a copy of a pack checkpoint whose stored training config names another reference
    with open(src, 'rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]; h = json.loads(f.read(n)); data = f.read()
    m = h['__metadata__']; c = m['user.resolved_config_json']
    assert old in c, (old, src); m['user.resolved_config_json'] = c.replace(old, new)
    b = json.dumps(h).encode(); b += b' ' * (-len(b) % 8)
    with open(dst, 'wb') as f:
        f.write(struct.pack('<Q', len(b)) + b + data)


renamed(local['3'], f'{F}/ck/policy_a.safetensors', '/workspace/refs/glockt/ep3', '/workspace/refs/perc2scan_glockt/ep3')
renamed(local['3'], f'{F}/ck/policy_b.safetensors', '/workspace/refs/glockt/ep3', '/workspace/refs/glockt_hT/ep3')
renamed(local['25'], f'{F}/ck/policy_c.safetensors', '/workspace/refs/perc2mcks/ep25', '/content/scanlib_refs/perc2mcks/ep25')
json.dump({'3': f'{F}/ck/policy_a.safetensors'}, open(f'{F}/ck/checkpoints.json', 'w'))
content = {'symlink farm onto the scans (dir)': f'{F}/farm', 'one farm link': f'{F}/farm/blue_cup.glb',
           'renamed byte copies (dir)': f'{F}/copies', 'renamed byte copies as EP:DIR': f'8:{F}/copies',
           'one renamed byte copy': f'{F}/onefile/mesh_a.glb', 'ASSET_PIECES-style dir holding a copy': f'{F}/onefile',
           'neutral link onto a perc2scan folder': f'{F}/trk/tracks11', 'checkpoint, config -> perc2scan': f'{F}/ck/policy_a.safetensors',
           'checkpoint, config -> hT': f'{F}/ck/policy_b.safetensors', 'checkpoint, config -> scanlib': f'{F}/ck/policy_c.safetensors',
           'kit JSON listing a renamed checkpoint': f'{F}/ck/checkpoints.json', 'dir of renamed checkpoints': f'{F}/ck'}
rc_ = {k: guard(w) for k, w in content.items()}
need(all(v[0] == 1 for v in rc_.values()), 'B8 content refusals: ' + '; '.join(f'{k}: rc {v[0]}' for k, v in rc_.items()))
res['refuse'] = dict(old=r2, names=r3, content={k: [v[0], v[1].splitlines()[-1][:160]] for k, v in rc_.items()})
rc, out = guard(f'{A.fix}/pack7_local.json', f'{F}/copies'); need(rc == 1, 'a pack-7 JSON plus one scan copy: refused')

# ------------------------------------------------------------------ 4 store listing
sf = f'{S}/store_files.txt'
if os.path.exists(sf):
    paths = open(sf).read().split('\n')
    o = {p for p in paths if OLD.search(p)}; nw = {p for p in paths if G.BAD.search(p)}
    run = lambda p: p.split('/')[1] if p.startswith('runs/') else p.split('/')[0]
    added = sorted({run(p) for p in nw - o}); lost = sorted({run(p) for p in o - nw})
    pack = {v['run'] for v in ck.values()} | {w.split('@')[0].split(':')[1] if ':' in w else w.split('@')[0] for w in words
                                              if re.search(r'\d{8}-', w)} | {'20261026-pack6-5203d42', '20261030-c01s43-328139c'}
    hit = sorted({run(p) for p in nw if run(p) in pack})
    need(not lost and not hit, f'store listing ({len(paths)} paths): old rule {len(o)}, new rule {len(nw)}; newly refused '
         f'groups {added}; no longer refused {lost}; pack runs refused {hit}')
    res['store'] = dict(paths=len(paths), old=len(o), new=len(nw), newly_refused=added,
                        examples=sorted(nw - o)[:8], pack_runs_checked=sorted(pack))

# ------------------------------------------------------------------ 5 Phase-1 mock, box a, with this guard
M = f'{R}/docs/research/work/leak-decomp-20261030/phase1/mock'; PY = f'{S}/map/scoring/venv/bin/python'
E, RP, RID = '13 2 26 44 45 41 0', '13 2', '20261030-orcP1a-mocksha'
subprocess.run(['bash', f'{M}/setup.sh', A.mr], capture_output=True, text=True, check=True)
subprocess.run(['bash', f'{M}/run_mock.sh', A.mr, RID, f'EPS="{E}" REPEAT="{RP}" ARMS=o,s,o2 '
                'LIB=/content/v2d-track3/meshes/library_v3 bash ops/jobs/perc_leak.sh'], capture_output=True, text=True)
p = subprocess.run([PY, '-I', f'{M}/check.py', A.mr, RID, E, RP], capture_output=True, text=True,
                   env=dict(os.environ, GUARD=GUARD))
gl = [l for l in p.stdout.splitlines() if l.startswith('guard') or l.startswith('RESULT')]
jl = [l.split('] ', 1)[-1].strip() for l in open(f'{A.mr}/content/job.log') if 'perc_leak: guard' in l]
st = re.search(r'refuses (\d+)/(\d+) pushed files', '\n'.join(gl)); bare = dict(
    (k, (int(a), int(b))) for k, a, b in re.findall(r'(perc2scan|perc2|perc2rep|bundle tar) (\d+)/(\d+)', '\n'.join(gl)))
ok = p.returncode == 0 and st and st.group(1) == st.group(2) and bare['perc2scan'][0] == bare['perc2scan'][1] > 0 \
    and bare['bundle tar'][0] == bare['bundle tar'][1] > 0 and bare['perc2'][0] == 0 and bare['perc2rep'][0] == 0
need(bool(ok) and any('guard refuses the bare perc2scan folder name' in l for l in jl),
     f'Phase-1 mock box a (real perc_leak.sh, this guard): {gl}; perc_leak.sh: {jl}')
res['phase1_mock'] = dict(check=gl, job_log=jl, rc=p.returncode)

shutil.rmtree(F, ignore_errors=True)                               # no renamed scan copies left lying around
res['fails'] = fails
json.dump(res, open(A.out, 'w'), indent=1)
print('RESULT:', 'ALL CHECKS PASS' if not fails else f'{len(fails)} FAILED: {fails}')
sys.exit(1 if fails else 0)
