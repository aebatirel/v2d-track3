"""CPU proof for the 512 copy (eval-10 njmax diagnostic, BUILD.md section 3). Run with a FlashCHORD-capable python (the
FlashCHORD source at the evaluator pin on sys.path, plus jax / flax / optax / safetensors for the evaluation imports):
  1. hydra: train_flash_sac composed with and without `sim.njmax=1024 sim.nconmax=512` -> the resolved configs differ in
     exactly sim.njmax, sim.nconmax, env.sim.njmax, env.sim.nconmax (where a training override lands in a checkpoint);
  2. on a REAL checkpoint (stock 512 / 256): tools/e10nj.py cksim 512/256 -> 1024/512 makes the stand-in of a 1024
     checkpoint (what training with the overrides stores, by 1), cksim 1024/512 -> 512/256 makes the copy; the copy must be
     byte-identical to the original; refusals: a wrong --from, a non-canonical header;
  3. FlashCHORD's own readers on all three files (read_checkpoint_metadata, checkpoint_config, _read_checkpoint: manifest
     + every tensor) and the evaluator's config chain (tools/e10nj_solver_check.py without --solver:
     apply_evaluation_composition -> RLEnvConfig.sim): 512/256, 1024/512, 512/256; tensors equal across the three.
Usage: FCPY cksim_test.py --repo REPO --ck REAL.safetensors --py MAIN_PY --fc FLASHCHORD_DIR --work DIR --out OUT.json
"""
import argparse, copy, hashlib, json, os, shutil, subprocess, sys

ap = argparse.ArgumentParser()
for k in ('repo', 'ck', 'py', 'fc', 'work', 'out', 'emb'):
    ap.add_argument('--' + k, required=k != 'emb')
A = ap.parse_args()
os.makedirs(A.work, exist_ok=True); res = dict(checks=[]); fails = []
TOOL = os.path.join(A.repo, 'tools', 'e10nj.py'); SOLV = os.path.join(A.repo, 'tools', 'e10nj_solver_check.py')


def need(ok, what, **kw):
    res['checks'].append(dict(ok=bool(ok), what=what, **kw)); print(('PASS ' if ok else 'FAIL ') + what, flush=True)
    if not ok:
        fails.append(what)


def flat(d, p=''):
    out = {}
    for k, v in d.items():
        q = f'{p}.{k}' if p else k
        out.update(flat(v, q) if isinstance(v, dict) else {q: v})
    return out


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


# ---------------------------------------------------------------- 1. hydra compose: where the training override lands
from hydra import compose, initialize_config_dir                                    # noqa: E402
from omegaconf import OmegaConf                                                     # noqa: E402
cfgdir = os.path.join(A.work, 'configs')
shutil.rmtree(cfgdir, ignore_errors=True); shutil.copytree(os.path.join(A.fc, 'src/flash_chord/configs'), cfgdir)
emb = 'sharpa_hands'
if A.emb and os.path.isfile(A.emb):                                                 # our kp-400 embodiment (the box copies it in)
    shutil.copy(A.emb, os.path.join(cfgdir, 'embodiment', 'sharpa_hands_mid.yaml')); emb = 'sharpa_hands_mid'
base = ['experiment=sharpa_flash_sac', "task.parquet='/content/refs/x/ep10'", f'embodiment={emb}', 'reset.seed=43',
        'training.total_environment_steps=70004736', 'logging.mode=disabled']
cf = {}
for arm, extra in (('stock', []), ('njmax1024', ['sim.njmax=1024', 'sim.nconmax=512'])):
    with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath(cfgdir)):
        cf[arm] = OmegaConf.to_container(compose(config_name='train_flash_sac', overrides=base + extra), resolve=True)
f0, f1 = flat(cf['stock']), flat(cf['njmax1024'])
diff = sorted(k for k in set(f0) | set(f1) if f0.get(k) != f1.get(k))
res['hydra'] = dict(embodiment=emb, keys=len(f1), diff=diff, values={k: [f0.get(k), f1.get(k)] for k in diff})
need(diff == sorted(['sim.njmax', 'sim.nconmax', 'env.sim.njmax', 'env.sim.nconmax'])
     and [f1[k] for k in ('sim.njmax', 'sim.nconmax', 'env.sim.njmax', 'env.sim.nconmax')] == [1024, 512, 1024, 512]
     and [f0[k] for k in ('sim.njmax', 'sim.nconmax')] == [512, 256],
     f'hydra: the training overrides change exactly the four sim limits of the {len(f1)}-key resolved config: {res["hydra"]["values"]}')

# ---------------------------------------------------------------- 2. cksim round trip on a real checkpoint
def cksim(src, dst, frm, to, tag):
    r = subprocess.run([A.py, '-I', TOOL, 'cksim', '--src', src, '--dst', dst, '--from', *map(str, frm), '--to', *map(str, to),
                        '--out', os.path.join(A.work, f'{tag}.json')], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


real = A.ck; stand = os.path.join(A.work, 'standin_1024', 'policy.safetensors'); cop = os.path.join(A.work, 'copy_512', 'policy.safetensors')
for p in (stand, cop):
    if os.path.exists(p):
        os.remove(p)
rc, out = cksim(real, stand, (512, 256), (1024, 512), 'cksim_standin'); need(rc == 0, f'cksim real -> 1024 stand-in: rc {rc}: {out[-300:]}')
rc, out = cksim(stand, cop, (1024, 512), (512, 256), 'cksim_copy'); need(rc == 0, f'cksim stand-in -> 512 copy: rc {rc}: {out[-300:]}')
res['files'] = {k: dict(path=p, sha256=sha(p), bytes=os.path.getsize(p)) for k, p in (('real', real), ('standin_1024', stand), ('copy_512', cop))}
need(open(real, 'rb').read() == open(cop, 'rb').read(), f'round trip: the 512 copy of the 1024 stand-in is byte-identical to the real checkpoint '
     f'(sha256 {res["files"]["real"]["sha256"][:12]} = {res["files"]["copy_512"]["sha256"][:12]})')
cs = json.load(open(os.path.join(A.work, 'cksim_copy.json')))
need(cs['buffer_identical'] and cs['config_diff'] == sorted(['sim.njmax', 'sim.nconmax', 'env.sim.njmax', 'env.sim.nconmax'])
     and not cs['other_header_entries_differ'] and not cs['other_metadata_differ'],
     f'cksim report: buffer identical ({cs["tensors"]} tensors), config diff {cs["config_diff"]}, no other header / metadata entry differs')
rc, out = cksim(real, os.path.join(A.work, 'wrong_from', 'policy.safetensors'), (1024, 512), (512, 256), 'cksim_wrong_from')
need(rc != 0 and not os.path.exists(os.path.join(A.work, 'wrong_from', 'policy.safetensors')), f'refusal: --from 1024 512 on a stock checkpoint: rc {rc} ({out[-160:]})')
b = open(real, 'rb').read(); import struct                                          # noqa: E402
n = struct.unpack('<Q', b[:8])[0]; hdr = b[8:8 + n].replace(b'{"__metadata__":', b'{ "__metadata__":', 1)
bad = os.path.join(A.work, 'noncanon.safetensors'); open(bad, 'wb').write(struct.pack('<Q', len(hdr)) + hdr + b[8 + n:])
rc, out = cksim(bad, os.path.join(A.work, 'noncanon_out', 'policy.safetensors'), (512, 256), (1024, 512), 'cksim_noncanon')
need(rc != 0, f'refusal: a header that does not re-serialise byte for byte: rc {rc} ({out[-160:]})')

# ---------------------------------------------------------------- 3. FlashCHORD's readers and the evaluator's config chain
from flash_chord.training.checkpoint import read_checkpoint_metadata, _read_checkpoint   # noqa: E402
from flash_chord.training.checkpoint_metadata import checkpoint_config                 # noqa: E402
import numpy as np                                                                      # noqa: E402
arrays = {}
for k, p in (('real', real), ('standin_1024', stand), ('copy_512', cop)):
    md = read_checkpoint_metadata(p); c = checkpoint_config(md); man, arr, um = _read_checkpoint(p); arrays[k] = arr
    res['files'][k].update(stored_sim=[c['sim']['njmax'], c['sim']['nconmax'], c['env']['sim']['njmax'], c['env']['sim']['nconmax']],
                           tensors=len(man), user_metadata_keys=len(um))
def same_arr(x, y):  # bytes, dtype and shape (NaN-safe: a learner state may hold NaN / inf placeholders)
    x, y = np.asarray(x), np.asarray(y)
    return x.dtype == y.dtype and x.shape == y.shape and x.tobytes() == y.tobytes()


same = all(set(arrays[k]) == set(arrays['real']) and all(same_arr(arrays[k][t], arrays['real'][t]) for t in arrays['real'])
           for k in ('standin_1024', 'copy_512'))
need(same, f'FlashCHORD _read_checkpoint loads all {len(arrays["real"])} tensors of the three files, identical in dtype, shape and bytes')
out_json = os.path.join(A.work, 'solver_check_config.json')
r = subprocess.run([sys.executable, SOLV, '--out', out_json, f'real={real}', f'standin_1024={stand}', f'copy_512={cop}'],
                   capture_output=True, text=True, cwd=A.fc)
sc = json.load(open(out_json))['checkpoints']; res['evaluator_config_chain'] = {k: v.get('env_config_sim') for k, v in sc.items()}
need(res['evaluator_config_chain'] == dict(real=[512, 256], standin_1024=[1024, 512], copy_512=[512, 256]),
     f'evaluator config chain (read_checkpoint_metadata -> checkpoint_config -> apply_evaluation_composition -> RLEnvConfig.sim): '
     f'{res["evaluator_config_chain"]} ({r.stdout.strip()[-200:]})')
res['ok'] = not fails; res['failures'] = fails
json.dump(res, open(A.out, 'w'), indent=1)
print('RESULT: ' + ('ALL CHECKS PASS' if not fails else f'{len(fails)} FAILED: {fails}'))
sys.exit(0 if not fails else 1)
