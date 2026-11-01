"""Fixtures for tools/e10nj.py verdict / lift / overflow (eval-10 njmax diagnostic, PREREG section 4). Synthetic inputs
only (not results). Each fixture builds a results/ev10_nj folder and checks the label and the 512 readout status.
Usage: python -I verdict_tests.py --repo REPO --work DIR --out OUT.json"""
import argparse, hashlib, json, os, shutil, subprocess, sys

ap = argparse.ArgumentParser(); ap.add_argument('--repo', required=True); ap.add_argument('--work', required=True); ap.add_argument('--out', required=True)
A = ap.parse_args(); TOOL = os.path.join(A.repo, 'tools', 'e10nj.py'); shutil.rmtree(A.work, ignore_errors=True); os.makedirs(A.work)
import numpy as np, pandas as pd, pyarrow as pa, pyarrow.parquet as pq        # noqa: E402
res, fails = [], []


def need(ok, what, info=''):
    res.append(dict(ok=bool(ok), what=what, info=str(info)[:300])); print(('PASS ' if ok else 'FAIL ') + what + (f'  [{info}]' if info else ''))
    if not ok:
        fails.append(what)


def row(draw, sha, v, own=True, rpe=15.9):
    side = lambda x: dict(sim_vs_ref=x, RPE=rpe, MPPE=8.4, AUC=x, audit_fail=True, fail=rpe > 5,
                          objects={o: dict(AUC=x, MPPE=8.0, frac_kp_over_5cm=0.5, end_kp_cm=10.0, ref_travel_cm=25.0, sim_travel_cm=0.7)
                                   for o in ('blue_cup', 'beige_cup')})
    return dict(path=f'/x/r{draw}/ep10/episode_000010.parquet', draw=draw, scored=True, checkpoint_sha256=sha,
                own_ref_check=dict(ok=own), vs=dict(V=side(v), P=side(v - 0.01)))


def build(name, O=40, L=True, n1024=10, mean1024=0.50, n512=10, mean512=0.45, stopped=None, arms_ok=True, idn_ok=True, ck=True,
          wrong_sha=False, own_fail=False, solver512=(512, 256), json_sha_wrong=False, build_ok=True, built512=(512, 256)):
    G = os.path.join(A.work, name); os.makedirs(G)
    c1, c5 = os.path.join(G, 'ck1024.safetensors'), os.path.join(G, 'ck512', 'policy.safetensors'); os.makedirs(os.path.dirname(c5))
    open(c5, 'wb').write(b'copy512')
    if ck:
        open(c1, 'wb').write(b'ck1024')
    s1 = hashlib.sha256(b'ck1024').hexdigest(); s5 = hashlib.sha256(b'copy512').hexdigest()
    J = lambda f, d: json.dump(d, open(os.path.join(G, f), 'w'))
    if stopped:
        open(os.path.join(G, 'STOPPED'), 'w').write(stopped)
    J('arms.json', dict(ok=arms_ok, failures=[] if arms_ok else ['V md5 differs']))
    J('overflow.json', dict(groups=dict(train=dict(files=1, dropped=O, counts=dict(nefc=O, broadphase=0, narrowphase=0, njmax_nnz=0, ccd=0, newton_contacts=0),
                                                   njmax_requested=dict(n=O, median=1030, p95=1070, max=1080)))))
    J('lift.json', dict(L=L, carried_lift_r1_max_cm=8.0 if L else 0.3, carried_lift_any_repeat_max_cm=8.0 if L else 0.4, checkpoints=[],
                        controls=dict(e10v_s42=dict(carried_lift_r1_max_cm=2.5), e10v_s43=dict(carried_lift_r1_max_cm=0.3))))
    J('identity.json', dict(ok=idn_ok, failures=[] if idn_ok else ['config differs'], config_diff=['output_dir']))
    J('ck512.json', dict(ok=True)); J('guard.json', dict(ok=True, cases=[dict(refused=True)] * 6))
    J('solver_check.json', dict(checkpoints=dict(ck1024=dict(env_config_sim=[1024, 512], solver=None), ck512=dict(env_config_sim=list(solver512), solver=None))))
    if build_ok:                                                     # the solver build (solver_build.json); absent = not done
        J('solver_build.json', dict(checkpoints=dict(ck1024=dict(solver=dict(njmax=1024, naconmax=512)),
                                                    ck512=dict(solver=dict(njmax=built512[0], naconmax=built512[1])))))
    vals = [mean1024 + d for d in np.linspace(-0.01, 0.01, n1024)] if n1024 else []
    rows1 = [row(i + 1, ('0' * 64 if (wrong_sha and i == 3) else s1), v, own=not (own_fail and i == 2)) for i, v in enumerate(vals)]
    rows5 = [row(i + 1, s5, mean512) for i in range(n512)]
    J('score.json', dict(sets=dict(conf1024=dict(own='V', rollouts=rows1), conf512=dict(own='V', rollouts=rows5),
                                   train1024=dict(own='V', rollouts=[row(i + 1, s1, 0.5) for i in range(10)]),
                                   e10vconf=dict(own='V', rollouts=[row(i + 1, 'e' * 64, 0.4593) for i in range(10)]))))
    for name_, n_, sha in (('conf1024', n1024, s1), ('conf512', n512, s5)):
        for i in range(n_):
            d = os.path.join(G, name_, f'r{i + 1}', 'ep10'); os.makedirs(d)
            json.dump(dict(checkpoint_sha256=('f' * 64 if (json_sha_wrong and name_ == 'conf1024' and i == 0) else sha)), open(os.path.join(d, 'episode_000010.json'), 'w'))
            open(os.path.join(G, name_, f'r{i + 1}', 'eval_rc.txt'), 'w').write('0')
    r = subprocess.run([sys.executable, '-I', TOOL, 'verdict', '--dir', G, '--ck1024', c1, '--ck512', c5, '--out', os.path.join(G, 'summary.json')],
                       capture_output=True, text=True)
    s = json.load(open(os.path.join(G, 'summary.json')))
    return s, r.stdout.strip()


cases = [
    ('supported', dict(), 'SUPPORTED', 'VALID'),
    ('O_at_bar_1000', dict(O=1000), 'SUPPORTED', 'VALID'),
    ('O_above_bar_1001', dict(O=1001), 'INCONCLUSIVE', 'VALID'),
    ('inconclusive_beats_falsified', dict(O=5000, L=False), 'INCONCLUSIVE', 'VALID'),
    ('falsified', dict(L=False), 'FALSIFIED', 'VALID'),
    ('falsified_needs_no_draws', dict(L=False, n1024=0, n512=0), 'FALSIFIED', 'MISSING'),
    ('incomplete_9_draws', dict(n1024=9), 'INCOMPLETE', 'VALID'),
    ('partial_mean_equal_bar', dict(mean1024=0.4593), 'PARTIAL', 'VALID'),
    ('supported_just_above', dict(mean1024=0.4594), 'SUPPORTED', 'VALID'),
    ('partial_below', dict(mean1024=0.45), 'PARTIAL', 'VALID'),
    ('invalid_stopped', dict(stopped='identity FAILED'), 'INVALID', 'VALID'),
    ('invalid_arms', dict(arms_ok=False), 'INVALID', 'VALID'),
    ('invalid_identity', dict(idn_ok=False), 'INVALID', 'VALID'),
    ('invalid_no_checkpoint', dict(ck=False), 'INVALID', 'VALID'),
    ('invalid_wrong_sha_scored', dict(wrong_sha=True), 'INVALID', 'VALID'),
    ('invalid_wrong_sha_json', dict(json_sha_wrong=True), 'INVALID', 'VALID'),
    ('invalid_own_ref', dict(own_fail=True), 'INVALID', 'VALID'),
    ('readout512_invalid_does_not_gate', dict(solver512=(1024, 512)), 'SUPPORTED', 'INVALID'),
    ('readout512_built_solver_wrong', dict(built512=(1024, 512)), 'SUPPORTED', 'INVALID'),
    ('readout512_no_solver_build_still_valid', dict(build_ok=False), 'SUPPORTED', 'VALID'),
    ('readout512_missing', dict(n512=0), 'SUPPORTED', 'MISSING'),
]
for name, kw, want, want512 in cases:
    s, out = build(name, **kw)
    need(s['label'] == want and s['readout_512']['status'] == want512, f'{name}: {want} / 512 {want512}', f"{s['label']} / {s['readout_512']['status']} :: {out[:160]}")
s, _ = build('delta512', mean1024=0.50, mean512=0.45)
need(abs(s['readout_512']['delta_vs_1024_V'] - (-0.05)) < 1e-6 and s['readout_512']['mean_V'] == 0.45, '512 readout reports its mean and the delta vs 1024',
     (s['readout_512']['mean_V'], s['readout_512']['delta_vs_1024_V']))

# ---- lift: the 5.0 cm bar on real-format curve parquets (tools/ckpt_curve.sh REP=3 layout)
def curve(dirn, lifts):  # lifts: per checkpoint, per repeat, the beige cup's lift (m)
    for k, reps in enumerate(lifts):
        d = os.path.join(dirn, f'policy_{(k + 1) * 10000000}')
        for r, lift in enumerate(reps):
            e = os.path.join(d, f'r{r + 1}'); os.makedirs(e); rows = []
            for t in range(60):
                for b, n in enumerate(('blue_cup', 'beige_cup')):
                    rz = 0.235 * min(t / 30, 1) if n == 'beige_cup' else 0.0
                    az = (lift if 20 <= t < 40 else 0.0) if n == 'beige_cup' else 0.0
                    rows.append(dict(environment_id=0, step=t, object_body_name=n, achieved_position_x=0.0, achieved_position_y=0.1 * b,
                                     achieved_position_z=0.05 + az, reference_position_x=0.0, reference_position_y=0.1 * b, reference_position_z=0.05 + rz))
            pq.write_table(pa.Table.from_pandas(pd.DataFrame(rows)), os.path.join(e, 'episode_000010.parquet'))
            json.dump(dict(sim_vs_ref=0.45), open(os.path.join(e, 'qa_policy.json'), 'w'))
        json.dump(dict(sim_vs_ref=0.45), open(os.path.join(d, 'qa_policy.json'), 'w'))


ctrl = os.path.join(A.repo, 'docs/research/work/eval10-njmax-20261101/cpu/out/control')
for name, lifts, want_L, want_r1 in (('lift_below', [[0.049, 0.06, 0.0]] + [[0.0] * 3] * 6, False, 4.9),
                                     ('lift_at_bar', [[0.0] * 3] * 6 + [[0.05, 0.0, 0.0]], True, 5.0)):
    d = os.path.join(A.work, name); curve(d, lifts)
    r = subprocess.run([sys.executable, '-I', TOOL, 'lift', '--curve', d, '--control', f'e10v_s42={ctrl}/e10v_s42_curve.json',
                        '--control', f'e10v_s43={ctrl}/e10v_s43_curve.json', '--out', os.path.join(d, 'lift.json')], capture_output=True, text=True)
    L = json.load(open(os.path.join(d, 'lift.json')))
    need(L['L'] == want_L and L['carried_lift_r1_max_cm'] == want_r1 and L['n_checkpoints'] == 7
         and L['controls']['e10v_s42']['carried_lift_r1_max_cm'] == 2.5 and L['controls']['e10v_s43']['carried_lift_r1_max_cm'] == 0.3
         and L['reference_lift_cm']['beige_cup'] == 23.5,
         f'lift {name}: r1 max {want_r1} cm -> L {want_L} (a 6.0 cm lift in repeat 2 alone does not count: r1 only); controls 2.5 / 0.3 cm read',
         (L['L'], L['carried_lift_r1_max_cm'], L['carried_lift_any_repeat_max_cm'], r.stderr[-200:]))

# ---- overflow: counts and the requested-njmax distribution
lg = os.path.join(A.work, 'train.log'); rng = np.random.default_rng(3); req = rng.integers(513, 1058, 5000)
with open(lg, 'w') as f:
    f.write('start\n')
    for i, x in enumerate(req):
        f.write(f'nefc overflow - please increase njmax to {x}\n')
        if i % 1000 == 0:
            f.write('broadphase overflow - please increase nconmax to 300 or naconmax to 1228800\n')
    f.write('narrowphase overflow - please increase nconmax to 300 or naconmax to 1228800\nnjmax_nnz overflow - please increase njmax_nnz to 99999\n'
            'step 100 reward 1.0 (no overflow here)\n')
r = subprocess.run([sys.executable, '-I', TOOL, 'overflow', '--group', f'train={lg}', '--group', f'none={A.work}/absent*.log',
                    '--out', os.path.join(A.work, 'overflow.json')], capture_output=True, text=True)
ov = json.load(open(os.path.join(A.work, 'overflow.json')))['groups']; t = ov['train']; q = t['njmax_requested']
need(t['counts']['nefc'] == 5000 and t['counts']['broadphase'] == 5 and t['counts']['narrowphase'] == 1 and t['counts']['njmax_nnz'] == 1
     and t['dropped'] == 5006 and q['median'] == float(np.percentile(req, 50)) and q['p95'] == float(np.percentile(req, 95)) and q['max'] == int(req.max())
     and ov['none']['files'] == 0 and ov['none']['dropped'] == 0,
     'overflow: counts per kind, O = nefc + broadphase + narrowphase, requested median / p95 / max = numpy\'s; an absent glob counts 0',
     (t['counts'], q))
json.dump(dict(ok=not fails, failures=fails, checks=res), open(A.out, 'w'), indent=1)
print('RESULT: ' + (f'ALL {len(res)} PASS' if not fails else f'{len(fails)} FAILED: {fails}'))
sys.exit(0 if not fails else 1)
