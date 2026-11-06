"""Re-track mock (2026-10-31): Phase 1's stub perc2 (docs/research/work/leak-decomp-20261030/phase1/mock/stub.py) with
ONE change: the track depends on the template BYTES. For arms perc2 / perc2rep, an object whose template file (as perc2
resolves it through MESH_DIR, links followed) differs in md5 from meshes/library_v3/<obj>.glb gets an extra y offset
of 1-5 mm derived from that md5, so a different mesh gives a different track and a byte copy of library_v3 gives
exactly P_o's track. The audit log also records each template's md5. Everything below is the Phase-1 stub.
Stub dispatcher of the perc_leak CPU mock. argv[1] = role (main), then the real command line. Only perc2.py is
stubbed; everything else (tools/leak_p1.py, tools/no_oracle.py, inline python) runs for real.
The perc2 stub does what the job depends on, with perc2's own logic where it matters:
  - templates: tools/leak_p1.templates() on the mock repo's perc2.py (its D / MESH_DIR / scan_path / mesh_path) with
    the environment it received, i.e. the files real perc2 would load; recorded in MR/perc2_audit.log with KF_MIN,
    SPLIT and the depth cache it found;
  - depth: perc2's rule (perc2.py:97-103): OUT/depths_fs0.5.npy is loaded when it exists, else 'computed' and written;
  - outputs: the refine inputs' real perception of the episode (poses.npz, poses_world_vo.npz, vo.json, det_f0.npz,
    masks_f0.jpg, track_guard.json); object poses get a small arm-specific offset for perc2scan / perc2rep (GPU noise
    stand-in), the camera does not; result.json and log.txt carry MOCK scores in perc2's format.
  - grounding: logs perc2's 'grounding unavailable (term off)' line when Grounding DINO is not cached (MR/gdino_cached,
    written by the stub transformers of setup.sh); HF_HUB_OFFLINE is recorded in the audit log.
Fault injection: MOCK_FAIL=<ep>:<folder> exits 1 before any track; MOCK_NOWVO=<ep>:<folder> writes poses.npz and
exits 1 before poses_world_vo.npz (a crash in perc2's scoring block); MOCK_NOGDINO=<ep>:<folder> logs the grounding
line for that arm only."""
import hashlib, json, os, shutil, sys
md5f = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()
role, argv = sys.argv[1], sys.argv[2:]
MR, IN, PY = os.environ['MOCK_MR'], os.environ['MOCK_IN'], os.environ['MOCK_PY']
script = argv[0] if argv else ''
if os.path.basename(script) != 'perc2.py':
    os.execv(PY, [PY] + argv)
import numpy as np                                                       # noqa: E402

ep, out = int(os.environ['EP']), os.environ['OUT']; folder = os.path.basename(out); os.makedirs(out, exist_ok=True)
repo = os.path.dirname(os.path.dirname(os.path.abspath(script)))
sys.path.insert(0, f'{repo}/tools'); from leak_p1 import templates     # noqa: E402
tsv = f'{repo}/docs/research/work/leak-decomp-20261030/phase1/inputs.tsv'
names = [l.split('\t')[2] for l in open(tsv).read().splitlines()[1:] if l.split('\t')[0] == str(ep)][0].split(',')
D, tp = templates(script, os.environ.get('MESH_DIR'), names)
dc = f'{out}/depths_fs0.5.npy'; had = os.path.exists(dc)
with open(f'{MR}/perc2_audit.log', 'a') as f:
    f.write(json.dumps(dict(ep=ep, folder=folder, mesh_dir=os.environ.get('MESH_DIR', '<unset>'), templates=tp,
                            kf_min=os.environ.get('KF_MIN'), split=os.environ.get('SPLIT'), depth_cache=os.path.realpath(dc),
                            depth_cache_existed=had, hf_hub_offline=os.environ.get('HF_HUB_OFFLINE'),
                            template_md5={n: md5f(p) for n, p in tp.items()})) + '\n')
print(f'[    0.2s] episode {ep} public objects {names}')
if had:
    Dp = np.load(dc, mmap_mode='r'); print(f'[    1.0s] depth ready {len(Dp)}')
else:
    np.save(dc, np.zeros((1, 2, 2), np.float32)); print('[  180.0s] depth ready 1 (COMPUTED by the stub: no cache)')
if os.environ.get('MOCK_FAIL') == f'{ep}:{folder}':
    print('Traceback (most recent call last):\nRuntimeError: mock perc2 failure'); sys.exit(1)
print('[   14.0s] vo keyframes 4 fails 0 median inliers 179 min 124')
if not os.path.exists(f'{MR}/gdino_cached') or os.environ.get('MOCK_NOGDINO') == f'{ep}:{folder}':   # perc2.py:283-291
    print("[   20.0s] grounding unavailable (term off): OSError('not in the local cache (HF_HUB_OFFLINE, mock)')")
for f in ('vo.json', 'det_f0.npz', 'masks_f0.jpg', 'track_guard.json'):
    if os.path.exists(f'{IN}/ep{ep}/{f}'):
        shutil.copyfile(os.path.realpath(f'{IN}/ep{ep}/{f}'), f'{out}/{f}')
z = dict(np.load(os.path.realpath(f'{IN}/ep{ep}/poses.npz')))
d = {'perc2': 0.0, 'perc2scan': 0.004, 'perc2rep': 0.0005}[folder]       # object offset (m); camera unchanged
for n in names:
    z[f'cam_T_{n}'] = z[f'cam_T_{n}'].copy(); z[f'cam_T_{n}'][:, 0, 3] += np.float32(d)
    m, ml = md5f(tp[n]), md5f(f'{repo}/meshes/library_v3/{n}.glb')
    if folder != 'perc2scan' and m != ml:                                # re-track mock: template-dependent track
        z[f'cam_T_{n}'][:, 1, 3] += np.float32(0.001 + 0.004 * int(m[:4], 16) / 65535)
np.savez(f'{out}/poses.npz', **z)
for i, n in enumerate(names):
    print(f'[   {50 + 10 * i}.0s] tracked {n} sec 7.0 guard {{}}')
if os.environ.get('MOCK_NOWVO') == f'{ep}:{folder}':
    print('Traceback (most recent call last):\nValueError: mock crash in the scoring block'); sys.exit(1)
W = z['world_T_cam']
np.savez(f'{out}/poses_world_vo.npz', **{n: np.stack([W[i] @ z[f'cam_T_{n}'][i] for i in range(len(W))]) for n in names})
auc = round(0.80 + 0.2 * int(hashlib.md5(f'{ep}{folder}'.encode()).hexdigest()[:6], 16) / 2 ** 24, 3)
json.dump({'episode': ep, 'objects': names, 'mock': True, 'vo': {'AUC': auc}}, open(f'{out}/result.json', 'w'))
print(f'[   61.0s] vo                           AUC {auc:.3f} SP 1.00 MP 1.00 MPPE 1.00 RPE 1.00 (MOCK)')
print(f'[   61.5s] anchor:{names[0]}  AUC 0.500 (MOCK)')
print('[   62.0s] DONE')
