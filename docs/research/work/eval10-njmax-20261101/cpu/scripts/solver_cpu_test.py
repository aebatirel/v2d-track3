"""Solver-level CPU check of the 512 copy (eval-10 njmax diagnostic, BUILD.md section 3.3): the SolverMuJoCo that
FlashCHORD's evaluation path builds (setup_scene + RLEnv, one world, warp device cpu) for e10v seed 43's REAL chosen
checkpoint (stock), a 1024 stand-in of it (tools/e10nj.py cksim 512/256 -> 1024/512, what the diagnostic training stores)
and the 512 copy of that stand-in (cksim 1024/512 -> 512/256), on e10v's REAL stored V4p reference V and the eval-10
assets (library_v3 + meshes/carve/ev10 pieces, make_assets.py; URDF md5 = e10v's arms.json). Test-only edits, made here
and never used elsewhere: the reference copy names the local assets (object_urdf_paths / object_mesh_paths), and the
three checkpoints' task.parquet / reference.parquet name that local reference (paths only; cksim then edits the limits).
Reports per file: stored limits, the evaluator's RLEnvConfig.sim, the built solver's njmax / naconmax / njmax_nnz, nv, and
the bytes of the MuJoCo-Warp Data arrays for one world (-> the GPU-memory estimate of BUILD.md section 6).
Usage: FCPY solver_cpu_test.py --repo REPO --ck E10V_S43.safetensors --ref V.parquet --usda SUPPORT.usda --assets DIR
                               --py MAIN_PY --fc FLASHCHORD_DIR --work DIR --out OUT.json
"""
import argparse, json, os, shutil, struct, subprocess, sys

ap = argparse.ArgumentParser()
for k in ('repo', 'ck', 'ref', 'usda', 'assets', 'py', 'fc', 'work', 'out'):
    ap.add_argument('--' + k, required=True)
A = ap.parse_args()
import pyarrow as pa, pyarrow.parquet as pq                                       # noqa: E402
W = os.path.abspath(A.work); shutil.rmtree(W, ignore_errors=True)
R = f'{W}/ref/ep10'; hive = f'{R}/processed/sequence_id=t3_ep010/robot_name=sharpa_wave'; os.makedirs(hive); os.makedirs(f'{R}/reconstructed_stage')
shutil.copy(A.usda, f'{R}/reconstructed_stage/')
t = pq.read_table(A.ref); cols = {}
for c in ('object_urdf_paths', 'object_mesh_paths'):
    cols[c] = [[p.replace('/content/assets', os.path.abspath(A.assets)) for p in t.column(c)[0].as_py()]]
for c, v in cols.items():
    i = t.column_names.index(c); t = t.set_column(i, c, pa.array(v, type=t.schema.field(c).type))
pq.write_table(t, f'{hive}/ref_gl_ilc.parquet')


def set_paths(src, dst):  # test-only: the stored task / reference parquet -> the local reference (header canonical, buffer copied)
    b = open(src, 'rb').read(); n = struct.unpack('<Q', b[:8])[0]; h = json.loads(b[8:8 + n])
    c = json.loads(h['__metadata__']['user.resolved_config_json']); c['task']['parquet'] = R; c['reference']['parquet'] = R
    h['__metadata__']['user.resolved_config_json'] = json.dumps(c, sort_keys=True, separators=(',', ':'))
    hb = json.dumps(h, separators=(',', ':')).encode(); hb += b' ' * (-len(hb) % 8)
    os.makedirs(os.path.dirname(dst), exist_ok=True); open(dst, 'wb').write(struct.pack('<Q', len(hb)) + hb + b[8 + n:])


ctl = f'{W}/e10v_s43_local/policy.safetensors'; set_paths(A.ck, ctl)
tool = os.path.join(A.repo, 'tools', 'e10nj.py'); stand = f'{W}/standin_1024/policy.safetensors'; cop = f'{W}/copy_512/policy.safetensors'
for src, dst, frm, to in ((ctl, stand, (512, 256), (1024, 512)), (stand, cop, (1024, 512), (512, 256))):
    r = subprocess.run([A.py, '-I', tool, 'cksim', '--src', src, '--dst', dst, '--from', *map(str, frm), '--to', *map(str, to)], capture_output=True, text=True)
    print(r.stdout.strip()[-300:], r.stderr.strip()[-300:], flush=True)
out = f'{W}/solver_check.json'
r = subprocess.run([sys.executable, os.path.join(A.repo, 'tools', 'e10nj_solver_check.py'), '--out', out, '--solver', '--device', 'cpu',
                    f'e10v_s43={ctl}', f'standin_1024={stand}', f'copy_512={cop}'], capture_output=True, text=True, cwd=A.fc)
print(r.stdout[-3000:], r.stderr[-3000:], flush=True)
sc = json.load(open(out)); res = dict(reference_md5_source=__import__('hashlib').md5(open(A.ref, 'rb').read()).hexdigest(), checkpoints={})
for k, v in sc['checkpoints'].items():
    res['checkpoints'][k] = {x: v.get(x) for x in ('stored_sim', 'env_config_sim', 'solver', 'solver_error', 'error')}
s = {k: (v.get('solver') or {}) for k, v in sc['checkpoints'].items()}
want = dict(e10v_s43=(512, 256), standin_1024=(1024, 512), copy_512=(512, 256))
res['ok'] = all(s[k].get('njmax') == want[k][0] and s[k].get('naconmax') == want[k][1] for k in want)
if s.get('standin_1024', {}).get('data_bytes_one_world') and s.get('e10v_s43', {}).get('data_bytes_one_world'):
    d = s['standin_1024']['data_bytes_one_world'] - s['e10v_s43']['data_bytes_one_world']
    res['data_bytes'] = dict(one_world_512=s['e10v_s43']['data_bytes_one_world'], one_world_1024=s['standin_1024']['data_bytes_one_world'],
                             delta_one_world=d, delta_4096_worlds_GB=round(d * 4096 / 1e9, 3),
                             total_4096_worlds_GB_512=round(s['e10v_s43']['data_bytes_one_world'] * 4096 / 1e9, 3),
                             total_4096_worlds_GB_1024=round(s['standin_1024']['data_bytes_one_world'] * 4096 / 1e9, 3))
json.dump(res, open(A.out, 'w'), indent=1)
print('RESULT: ' + ('SOLVER CHECK PASS' if res['ok'] else 'SOLVER CHECK FAILED') + f" :: {json.dumps({k: [s[k].get('njmax'), s[k].get('naconmax')] for k in s})} :: {res.get('data_bytes')}")
sys.exit(0 if res['ok'] else 1)
