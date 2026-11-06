"""Fixture tests of tools/e10cs.py choose / gate / verdict (PREREG sections 3.3-5; BUILD.md section 7). Synthetic result
folders (no scores of any real run): labels, the training-box gate, the binding +0.02 inclusion bar on V and P, the overflow
label, the lift clause, INCOMPLETE / INVALID paths. Usage: python -I verdict_tests.py --repo R --work DIR --out J"""
import argparse, json, os, shutil, subprocess, sys

ap = argparse.ArgumentParser(); ap.add_argument('--repo', required=True); ap.add_argument('--work', required=True); ap.add_argument('--out', required=True)
A = ap.parse_args(); sys.path.insert(0, os.path.join(A.repo, 'tools'))
import e10cs                                   # noqa: E402
TOOL = os.path.join(A.repo, 'tools', 'e10cs.py'); SHA = 'c' * 64; rows = []


def need(ok, what):
    rows.append(dict(ok=bool(ok), what=what)); print(('PASS ' if ok else 'FAIL ') + what)


def rollout(draw, v, p, rpe_v=15.0, rpe_p=15.0, sha=SHA):
    def vs(s, rpe):
        return dict(sim_vs_ref=s, RPE=rpe, MPPE=rpe / 2, AUC=s, audit_fail=rpe > 5,
                    objects={'blue_cup': dict(AUC=s, sim_travel_cm=1.0, ref_travel_cm=1.5), 'beige_cup': dict(AUC=s, sim_travel_cm=1.0, ref_travel_cm=23.5)})
    return dict(draw=draw, scored=True, vs=dict(V=vs(v, rpe_v), P=vs(p, rpe_p)), own_ref_check=dict(ok=True), checkpoint_sha256=sha)


def cellrow(s, mean, n=10, status='VERIFIED', sd=0.01):
    return dict(status=status, n=n, mean=round(mean, 4), mean_raw=mean, sd=sd, sha256=SHA if s == '43' else 'd' * 64,
                checkpoint=f'/c/results/perc2e10css{s}_glock_public/ep10/best/policy.safetensors', results=f'/c/results/perc2e10css{s}_glock_public/ep10', failures=[])


def make(name, cells, conf=None, packed_v=0.4632, packed_p=0.4525, nconf=10, ovf=(0, 0), lift=(0.3, 0.2), verify_ok=True, stopped=None,
         old=(0.4717, 0.4563)):
    G = os.path.join(A.work, name); shutil.rmtree(G, ignore_errors=True); os.makedirs(G)
    w = lambda f, d: json.dump(d, open(os.path.join(G, f), 'w'))
    w('pieces.json', dict(ok=True, set='ev10cs5', md5sums_md5=e10cs.SETS['ev10cs5']['md5sums'], manifest=['x'] * 50, pinned=e10cs.SETS['ev10cs5']))
    w('assets.json', dict(ok=True, urdfs={'blue_cup': dict(urdf_md5='a', mass=0.3, com_mm=[0, 0, 19.05], inertia={}, collisions=24)}))
    w('cells.json', dict(seeds=cells))
    ch, st, inv, thin = e10cs.choose(cells, ['42', '43'])
    w('choice.json', dict(status=st, chosen=ch, sha256=cells[ch]['sha256'] if ch else None, checkpoint=cells[ch]['checkpoint'] if ch else None,
                          invalid_seeds=inv, incomplete_seeds=thin, seeds=cells))
    g = e10cs.gate(cells); w('gate.json', g)
    w('verify.json', dict(ok=verify_ok, failures=[] if verify_ok else ['x'], confirmation={}))
    w('overflow.json', dict(groups={f'train_s{s}': dict(files=1, dropped=o, counts=dict(nefc=o)) for s, o in zip(('42', '43'), ovf)}))
    for s, l in zip(('42', '43'), lift):
        w(f'lift_s{s}.json', dict(L=l >= 5.0 - 1e-9, carried_lift_r1_max_cm=l, checkpoints=[], controls={}))
    if stopped:
        open(os.path.join(G, 'STOPPED'), 'w').write(stopped)
    sets = dict(packed=dict(own='P', rollouts=[rollout(i + 1, packed_v + (0.001 if i % 2 else -0.001), packed_p + (0.001 if i % 2 else -0.001),
                                                       sha=e10cs.PACKED_SHA) for i in range(10)]),
                old=dict(own='P', rollouts=[rollout(1, old[0], old[1], sha=e10cs.PACKED_SHA)]))
    sha_ch = cells[ch]['sha256'] if ch else SHA
    if conf is not None:
        sets['conf'] = dict(own='V', rollouts=[rollout(i + 1, conf[0], conf[1], *(conf[2:] or (15.0, 15.0)), sha=sha_ch) for i in range(nconf)])
    for s in ('42', '43'):
        sets[f'train{s}'] = dict(own='V', rollouts=[rollout(i + 1, cells[s].get('mean_raw') or 0.45, 0.44) for i in range(10)])
    w('score.json', dict(refs=dict(V=dict(md5='v' * 32), P=dict(md5=e10cs.PACKED_REF_MD5)), sets=sets))
    r = subprocess.run([sys.executable, '-I', TOOL, 'verdict', '--dir', G, '--score', os.path.join(G, 'score.json'), '--out', os.path.join(G, 'summary.json')],
                       capture_output=True, text=True)
    s = json.load(open(os.path.join(G, 'summary.json'))) if os.path.exists(os.path.join(G, 'summary.json')) else {}
    return s, (r.stdout + r.stderr).strip()


C = lambda m42, m43, **k: {'42': cellrow('42', m42, **k.get('k42', {})), '43': cellrow('43', m43, **k.get('k43', {}))}
s, o = make('gate_not_met', C(0.4524, 0.4512))
need(s.get('label') == 'NO-SWAP' and 'training-box gate not met' in s['why'][0] and not s['pack10_inclusion']['include_in_pack10'], f'e10v-like seeds (0.4524 / 0.4512) -> NO-SWAP, gate not met :: {o[:160]}')
s, o = make('gate_at_bar', C(0.4632, 0.4500))
need(s.get('label') == 'NO-SWAP' and not s['training_box_gate']['met'], 'a seed mean exactly at the bar 0.4632 does not meet the gate (strict)')
s, o = make('gate_thin', C(0.70, 0.45, k42=dict(n=7)))
need(s.get('label') == 'INCOMPLETE' and not s['training_box_gate']['seeds']['42']['above'], 'a thin seed (n 7) -> INCOMPLETE and does not count for the gate')
s, o = make('gate_invalid', C(0.70, 0.45, k42=dict(status='INVALID')))
need(s.get('label') == 'INVALID' and not s['training_box_gate']['met'], 'an INVALID cell -> INVALID (no single-seed fallback), and does not count for the gate')
s, o = make('missing', C(0.70, 0.45, k43=dict(status='MISSING', n=0)))
need(s.get('label') == 'INCOMPLETE', 'a missing seed -> INCOMPLETE')
s, o = make('include', C(0.55, 0.60), conf=(0.50, 0.49))
need(s.get('label') == 'SWAP-ELIGIBLE' and s['pack10_inclusion']['include_in_pack10'] and s['choice']['chosen'] == '43',
     f'gate met, conf 0.50 / 0.49 vs packed 0.4632 / 0.4525 -> SWAP-ELIGIBLE, INCLUDE (gain {s["pack10_inclusion"]["gain"]}) :: {o[:200]}')
s, o = make('below_bar_P', C(0.55, 0.60), conf=(0.50, 0.46))
need(s.get('label') == 'SWAP-ELIGIBLE' and not s['pack10_inclusion']['include_in_pack10'],
     f'SWAP-ELIGIBLE with gain V +0.037, P +0.0075 -> NOT included (bar 0.02 on both) :: {s["pack10_inclusion"]["reading"]}')
s, o = make('at_bar', C(0.55, 0.60), conf=(0.4832, 0.4725))
need(s.get('label') == 'SWAP-ELIGIBLE' and s['pack10_inclusion']['include_in_pack10'], f'gain exactly +0.02 on both -> included (>=) {s["pack10_inclusion"]["gain"]}')
s, o = make('below_bar_both', C(0.55, 0.60), conf=(0.4652, 0.4545))
need(s.get('label') == 'SWAP-ELIGIBLE' and not s['pack10_inclusion']['include_in_pack10'], 'SWAP-ELIGIBLE at +0.002 (pack 9b-like) -> NOT included')
s, o = make('noswap_aP', C(0.55, 0.60), conf=(0.50, 0.44))
need(s.get('label') == 'NO-SWAP' and not s['clauses']['a_P']['holds'] and s['clauses']['a_V']['holds'], 'clause a holds on V, fails on P -> NO-SWAP')
s, o = make('noswap_c', C(0.55, 0.60), conf=(0.50, 0.49, 16.5, 15.0))
need(s.get('label') == 'NO-SWAP' and not s['clauses']['c_V']['holds'], 'median RPE vs V worse -> NO-SWAP (c_V)')
s, o = make('incomplete_conf', C(0.55, 0.60), conf=(0.50, 0.49), nconf=9)
need(s.get('label') == 'INCOMPLETE', '9 scored confirmation draws -> INCOMPLETE')
s, o = make('verify_bad', C(0.55, 0.60), conf=(0.50, 0.49), verify_ok=False)
need(s.get('label') == 'INVALID', 'verify not ok -> INVALID')
s, o = make('stopped', C(0.55, 0.60), stopped='piece set check FAILED')
need(s.get('label') == 'INVALID' and 'job stopped' in s['why'][0], 'STOPPED -> INVALID')
s, o = make('unclean', C(0.55, 0.60), conf=(0.50, 0.49), ovf=(1001, 0))
need(s.get('label') == 'SWAP-ELIGIBLE' and 'pieces not clean in training' in s['labels_attached'] and s['pack10_inclusion']['include_in_pack10'],
     '1,001 overflow lines in one training log -> "pieces not clean in training" attached; the rule still applies')
s, o = make('clean_at_bar', C(0.55, 0.60), conf=(0.50, 0.49), ovf=(1000, 1000))
need('pieces not clean in training' not in s['labels_attached'], '1,000 lines -> no label (> 1,000 is the bar)')
s, o = make('lift', C(0.4524, 0.4512), lift=(5.0, 0.2))
need(s['lift']['holds_any_seed'] and s['lift']['per_seed']['42']['holds'] and not s['lift']['per_seed']['43']['holds'], 'beige r1 lift 5.0 cm holds, 0.2 cm does not (reported clause)')
s, o = make('floor', C(0.55, 0.60), conf=(0.47, 0.46, 15.0, 15.0))
need(s.get('label') == 'SWAP-ELIGIBLE' and 'EQUAL FLOOR' in s['labels_attached'] and not s['pack10_inclusion']['include_in_pack10'],
     'both fail every draw, conf +0.007 -> SWAP-ELIGIBLE [EQUAL FLOOR], not included')
st = {'42': dict(n=10, mean=0.5000, sd=0.02), '43': dict(n=10, mean=0.5040, sd=0.03)}
need(e10cs.rule2_e10v(st, ['42', '43']) == '42', 'choose: means within 0.005 -> the lower sd (42)')
st = {'42': dict(n=10, mean=0.5000, sd=0.02), '43': dict(n=10, mean=0.5060, sd=0.03)}
need(e10cs.rule2_e10v(st, ['42', '43']) == '43', 'choose: 0.006 apart -> the higher mean (43)')
st = {'42': dict(n=10, mean=0.5000, sd=0.02), '43': dict(n=10, mean=0.5000, sd=0.02)}
need(e10cs.rule2_e10v(st, ['42', '43']) == '42', 'choose: full tie -> seed 42')
out = dict(ok=all(r['ok'] for r in rows), n=len(rows), passed=sum(r['ok'] for r in rows), cases=rows)
json.dump(out, open(A.out, 'w'), indent=1)
print(f"RESULT: {out['passed']}/{out['n']} pass"); sys.exit(0 if out['ok'] else 1)
