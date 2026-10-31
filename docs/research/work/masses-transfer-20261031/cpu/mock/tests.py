"""Negative and unit tests for the masses transfer check (CPU). usage: tests.py MR OUT.json   (MR = a finished mock)
  T1 mass_verify.py FAILS when an arm loads the wrong mass (mass1's blue cup URDF set back to 0.3 kg; restored after);
  T2 mass_verify.py FAILS when an arm's reference folder holds a second .parquet (FlashCHORD refuses it; restored after);
  T3 mass_verify.py FAILS when an arm's reference is not the source reference (one wrist sample changed; restored after);
  T4 mass_verdict.verdict(): ADOPT / NOT ADOPTED (gain short on one episode) / NOT ADOPTED (one seed drops 0.06 while the
     seed mean passes) / boundary (+0.03 exactly, -0.05 exactly: passes) / INCOMPLETE (7 rollouts) / INVALID;
  T5 mass_arm.set_mass() on make_assets.py's placeholder URDFs gives make_assets.py --physics props_masses_only.json's
     masses, COMs and inertias (library_v3, every object): the arm copy is what MA_ARGS would have built;
  T6 mass_arm.py refuses a source reference whose URDF is not the 0.3 kg placeholder;
  T7 mass_verify.py FAILS when the two arms' saved training configs differ in a setting (a reward weight) (restored).
"""
import glob, json, os, shutil, subprocess, sys, tempfile
import pyarrow as pa, pyarrow.parquet as pq
MR, OUT = sys.argv[1], sys.argv[2]
C = f'{MR}/content'; TOOLS = f'{C}/v2d-track3/tools'; PY = sys.executable
sys.path.insert(0, TOOLS)
import mass_arm, mass_verdict                                   # noqa: E402
PROPS = f'{C}/v2d-track3/docs/research/physics-2026-10-30/props_masses_only.json'
res = {}


def verify():
    out = f'{MR}/tests_verify.json'
    r = subprocess.run([PY, '-I', f'{TOOLS}/mass_verify.py', '--content', C, '--eps', '2 12', '--seeds', '42 43', '--arms',
                        f'mass0:none mass1:{PROPS}', '--steps', '70004736', '--manifests',
                        f'{C}/results/mass_check/arms_ep2.json {C}/results/mass_check/arms_ep12.json', '--out', out],
                       capture_output=True, text=True)
    return r.returncode, json.load(open(out))['failures']


rc, f = verify(); res['T0_baseline_verified'] = dict(ok=rc == 0 and not f, detail=f[:2])
u = glob.glob(f'{C}/refs/mass1_sf/ep12/assets/urdf/blue_cup_rigid.urdf')[0]; keep = open(u).read()
open(u, 'w').write(mass_arm.set_mass(keep, 0.3, 'tamper test'))
rc, f = verify(); open(u, 'w').write(keep)
res['T1_wrong_mass_detected'] = dict(ok=rc != 0 and any('blue_cup loads 0.3' in x for x in f), detail=[x.replace(MR, 'MR') for x in f[:3]])
d = os.path.dirname(glob.glob(f'{C}/refs/mass1s43_glockt/ep2/processed/*/*/ref_gl_ilc.parquet')[0]); extra = f'{d}/extra.parquet'
shutil.copy(f'{d}/ref_gl_ilc.parquet', extra); rc, f = verify(); os.remove(extra)
res['T2_second_parquet_detected'] = dict(ok=rc != 0 and any('2 .parquet files' in x for x in f), detail=[x.replace(MR, 'MR') for x in f[:2]])
p = glob.glob(f'{C}/refs/mass0s42_glockt/ep12/processed/*/*/ref_gl_ilc.parquet')[0]; tmp = p + '.keep'; shutil.copy(p, tmp)
t = pq.read_table(p); w = t.column("robot_left_wrist_position")[0].as_py(); w[0] = [w[0][0] + 0.001] + list(w[0][1:]) if isinstance(w[0], list) else w[0] + 0.001
t = t.set_column(t.column_names.index('robot_left_wrist_position'), 'robot_left_wrist_position',
                 pa.array([w], type=t.schema.field('robot_left_wrist_position').type)); pq.write_table(t, p)
rc, f = verify(); shutil.move(tmp, p)
res['T3_other_reference_detected'] = dict(ok=rc != 0 and any('not the same reference' in x for x in f), detail=[x.replace(MR, 'MR') for x in f[:2]])
import struct                                                                             # noqa: E402
ck = f'{C}/results/mass1s42_glock_public/ep2/best/policy.safetensors'; keep = ck + '.keep'; shutil.copy(ck, keep)
with open(ck, 'rb') as fh:
    nh = struct.unpack('<Q', fh.read(8))[0]; hd = json.loads(fh.read(nh))
cf = json.loads(hd['__metadata__']['user.resolved_config_json']); cf['objective']['force_closure']['weight'] = '7'
hd['__metadata__']['user.resolved_config_json'] = json.dumps(cf); b = json.dumps(hd).encode(); b += b' ' * (-len(b) % 8)
open(ck, 'wb').write(struct.pack('<Q', len(b)) + b); rc, f = verify(); shutil.move(keep, ck)
res['T7_other_training_setting_detected'] = dict(ok=rc != 0 and any('objective.force_closure.weight' in x for x in f), detail=f[:2])
rc, f = verify(); res['T0_restored_verified'] = dict(ok=rc == 0 and not f, detail=f[:2])


def cells(vals, n=10):  # vals[(ep, arm, seed)] = mean -> rows as mass_verdict builds them
    return {k: dict(auc=dict(n=n, mean=v, sd=0.02, min=v - 0.03, max=v + 0.03)) for k, v in vals.items()}


def V(d, n=10, ok=True):
    return mass_verdict.verdict(cells(d, n), [2, 12], ['42', '43'], 'mass0', 'mass1', ok, 8)[0]


base = {(2, 'mass0', '42'): 0.70, (2, 'mass0', '43'): 0.72, (12, 'mass0', '42'): 0.88, (12, 'mass0', '43'): 0.86}
adopt = {**base, **{(2, 'mass1', '42'): 0.75, (2, 'mass1', '43'): 0.76, (12, 'mass1', '42'): 0.92, (12, 'mass1', '43'): 0.90}}
short = {**adopt, **{(12, 'mass1', '42'): 0.90, (12, 'mass1', '43'): 0.88}}                 # ep12 +0.02
drop = {**adopt, **{(2, 'mass1', '42'): 0.64, (2, 'mass1', '43'): 0.88}}                    # ep2 mean +0.05, seed 42 -0.06
edge = {(2, 'mass0', '42'): 0.5, (2, 'mass0', '43'): 0.5, (2, 'mass1', '42'): 0.53, (2, 'mass1', '43'): 0.53,   # ep2 +0.03
        (12, 'mass0', '42'): 0.5, (12, 'mass0', '43'): 0.5, (12, 'mass1', '42'): 0.45, (12, 'mass1', '43'): 0.67}  # seed 42 -0.05
got = dict(adopt=V(adopt), short=V(short), drop=V(drop), edge=V(edge), incomplete=V(adopt, n=7), invalid=V(adopt, ok=False))
want = dict(adopt='ADOPT', short='NOT ADOPTED', drop='NOT ADOPTED', edge='ADOPT', incomplete='INCOMPLETE', invalid='INVALID')
res['T4_verdict_rule'] = dict(ok=got == want, detail=dict(got=got, want=want))
# T5: arm copy == make_assets --physics
tmpd = tempfile.mkdtemp(); lib = f'{C}/v2d-track3/meshes/library_v3'; ma = f'{C}/v2d-track3/pipeline/make_assets.py'
subprocess.run([PY, '-I', ma, lib, f'{tmpd}/a0'], check=True, capture_output=True)
subprocess.run([PY, '-I', ma, lib, f'{tmpd}/a1', '--physics', PROPS], check=True, capture_output=True)
P = json.load(open(PROPS)); worst = {}
for f in sorted(glob.glob(f'{tmpd}/a0/urdf/*.urdf')):
    n = os.path.basename(f)[:-len('_rigid.urdf')]
    mine = mass_arm.read_inertial(mass_arm.set_mass(open(f).read(), P[n]['physics']['mass_kg'], 'test'))
    ref = mass_arm.read_inertial(open(f'{tmpd}/a1/urdf/{n}_rigid.urdf').read())
    worst[n] = dict(mass=(mine[0], ref[0]), com_equal=mine[1] == ref[1],
                    inertia_rel_err=max(abs(mine[2][k] - ref[2][k]) / max(abs(ref[2][k]), 1e-12) for k in ref[2]))
res['T5_equals_make_assets_physics'] = dict(ok=all(v['mass'][0] == v['mass'][1] and v['com_equal'] and v['inertia_rel_err'] < 1e-6
                                                   for v in worst.values()) and len(worst) == 11, detail=worst)
# T6: refuse a non-placeholder source
src = glob.glob(f'{C}/refs/sf/ep12/assets/urdf/blue_cup_rigid.urdf')[0]; keep = open(src).read()
open(src, 'w').write(mass_arm.set_mass(keep, 0.5, 'tamper test'))
r = subprocess.run([PY, '-I', f'{TOOLS}/mass_arm.py', '--content', C, '--ep', '12', '--base', 'mc', '--arms', 'zz0:none',
                    '--seeds', '99', '--out', f'{tmpd}/m.json'], capture_output=True, text=True)
open(src, 'w').write(keep)
res['T6_non_placeholder_source_refused'] = dict(ok=r.returncode != 0 and 'not the 0.3 kg placeholder' in r.stderr,
                                                detail=r.stderr.strip().replace(MR, 'MR')[-200:])
shutil.rmtree(tmpd)
fails = [k for k, v in res.items() if not v['ok']]
json.dump(dict(ok=not fails, failures=fails, tests=res), open(OUT, 'w'), indent=1, default=str)
print(('ALL TESTS PASS' if not fails else f'FAILED: {fails}') + f' ({len(res)} tests)')
sys.exit(0 if not fails else 1)
