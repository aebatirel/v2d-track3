"""Reconstructed (not recorded) provenance chain for the eval-10 packed reference ref_gl_ilc.parquet (run
20261026-gl10A2-5e0e100, commit 5e0e100). Built from the run's run_job.log / job.log / COMMIT in the HF store and
ops/jobs/glock_public.sh; hashes only where the file is on this machine. NOT a pipeline/provenance.py manifest."""
import hashlib, json, sys
ref, out = sys.argv[1], sys.argv[2]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
R = 'hf://datasets/aebatirel/v2d-store/runs/20261026-gl10A2-5e0e100'
REPO = '/home/user/v2d-track3'
C, RUN = '5e0e100c5751f54f175c9b4b058cf3c1c9e0553c', '20261026-gl10A2-5e0e100'
lib = {f'{REPO}/meshes/library_v3/{n}.glb': sha(f'{REPO}/meshes/library_v3/{n}.glb') for n in ('blue_cup', 'beige_cup')}
import glob
pcs = {p: sha(p) for n in ('blue_cup', 'beige_cup') for p in sorted(glob.glob(f'{REPO}/meshes/carve/ev10/{n}/piece_*.obj'))}
chain = [
 dict(tool='pipeline/wrist_ilc.py (ops/jobs/glock_public.sh step 3, --iters 4 --hold ref_gl_grasp_lock.json, reconstructed)',
      commit=C, run_id=RUN, artifact=ref, sha256=sha(ref),
      command='EMB=<emb> python pipeline/wrist_ilc.py ref_gl.parquet ref_gl_ilc.parquet --iters ${ILC_ITERS:-4} --device cuda [--hold ...] (reconstructed from glock_public.sh at HEAD, not at 5e0e100)',
      inputs={f'{R}/(box-local, not stored) refs/glockt/ep10/.../ref_gl.parquet': None}),
 dict(tool='pipeline/grasp_lock.py (ops/jobs/glock_public.sh step 2, reconstructed)', commit=C, run_id=RUN,
      artifact=f'{R}/(box-local, not stored) ref_gl.parquet', sha256=None,
      command='python pipeline/grasp_lock.py P0 ref_gl.parquet --single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15 (GL_ARGS from run_job.log)',
      inputs={f'{R}/refs/perc2mck/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave/a865e22731864ebc80e0c4419efc4bfb-0.parquet (base perception mck, not downloaded)': None,
              '/content/assets (pipeline/make_assets.py meshes/library_v3 --pieces meshes/carve/ev10, box-local)': None}),
 dict(tool='pipeline/make_assets.py (glock_public.sh line 61: LIB=meshes/library_v3 PIECES=meshes/carve/ev10)', commit=C, run_id=RUN,
      artifact='/content/assets (box-local, not stored)', sha256=None, command='python pipeline/make_assets.py meshes/library_v3 /content/assets --pieces meshes/carve/ev10',
      inputs={**lib, **pcs}),
]
json.dump(dict(reconstructed=True,
               note='RECONSTRUCTED by ev10_intrusion/scripts/make_prov.py from run_job.log, job.log, COMMIT (HF store) and '
                    'glock_public.sh; not recorded by the run. Repo files are hashed at HEAD 4eb10b1; their git blobs equal '
                    'commit 5e0e100 (checked via the GitHub API). Base perception refs/perc2mck/ep10 and perc2/ep10 not hashed.',
               chain=chain), open(out, 'w'), indent=1)
print('wrote', out, len(chain), 'steps')
