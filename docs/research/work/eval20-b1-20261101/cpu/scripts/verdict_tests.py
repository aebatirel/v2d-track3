"""Fixture tests of tools/e20b1.py choose / gate / verdict (PREREG sections 3.3-5; BUILD.md section 7). Synthetic result
folders (no scores of any real run): labels, the training-box gate at 0.8933, the swap rule on P (a / b / c / s), the binding
+0.02 inclusion bar, the overflow label, INCOMPLETE / INVALID paths, the seed choice. The packed side here is a synthetic set
shaped like the real H5p7 eval-20 draws (mean 0.8933, 0 fails, median RPE ~1.67 cm).
Usage: python -I verdict_tests.py --repo R --work DIR --out J"""
import argparse, json, os, shutil, subprocess, sys

ap = argparse.ArgumentParser(); ap.add_argument('--repo', required=True); ap.add_argument('--work', required=True); ap.add_argument('--out', required=True)
A = ap.parse_args(); sys.path.insert(0, os.path.join(A.repo, 'tools'))
import e10cs, e20b1                            # noqa: E402
TOOL = os.path.join(A.repo, 'tools', 'e20b1.py'); SHA = 'c' * 64; rows = []
PK = [0.8968, 0.9112, 0.9146, 0.8945, 0.8193, 0.9058, 0.9076, 0.8922, 0.8815, 0.9100]   # shaped like H5p7 (mean 0.8933)
PR = [1.96, 1.87, 1.73, 1.56, 4.10, 1.37, 1.51, 1.61, 1.99, 1.31]                       # RPE cm (0 fails, median 1.67)


def need(ok, what):
    rows.append(dict(ok=bool(ok), what=what)); print(('PASS ' if ok else 'FAIL ') + what)


def rollout(draw, s, rpe, sha=SHA):
    return dict(draw=draw, scored=True, own_ref_check=dict(ok=True), checkpoint_sha256=sha,
                vs=dict(P=dict(sim_vs_ref=s, RPE=rpe, MPPE=rpe / 2, AUC=s, audit_fail=rpe > 5,
                               objects={'blue_cup': dict(AUC=s), 'water_pitcher': dict(AUC=s)})))


def cellrow(s, mean, n=10, status='VERIFIED', sd=0.01):
    return dict(status=status, n=n, mean=round(mean, 4), mean_raw=mean, sd=sd, sha256=SHA if s == '43' else 'd' * 64,
                checkpoint=f'/c/results/e20b1s{s}_glock_public/ep20/best/policy.safetensors', results=f'/c/results/e20b1s{s}_glock_public/ep20', failures=[])


def make(name, cells, conf=None, nconf=10, ovf=(0, 0), verify_ok=True, stopped=None, old=0.8948, d1=None, ref_md5=e20b1.REF_MD5, pk_sha=e20b1.PACKED_SHA):
    """conf: (mean sim_vs_ref, list of RPE per draw or one RPE)"""
    G = os.path.join(A.work, name); shutil.rmtree(G, ignore_errors=True); os.makedirs(G)
    w = lambda f, d: json.dump(d, open(os.path.join(G, f), 'w'))
    w('pieces.json', dict(ok=True, set='ev20b1', md5sums_md5=e20b1.PIECES['md5sums'], frozen_md5=e20b1.PIECES['frozen'], manifest=['x'] * 41))
    w('assets.json', dict(ok=True, urdfs={'water_pitcher': dict(packed_md5=e20b1.URDF_PACKED['water_pitcher'], md5=e20b1.URDF_B1['water_pitcher'],
                                                               collisions_packed=9, collisions=41, inertial_equal=True, visual_equal=True)}))
    w('cells.json', dict(seeds=cells))
    ch, st, inv, thin = e10cs.choose(cells, ['42', '43'])
    w('choice.json', dict(status=st, chosen=ch, sha256=cells[ch]['sha256'] if ch else None, checkpoint=cells[ch]['checkpoint'] if ch else None,
                          invalid_seeds=inv, incomplete_seeds=thin, seeds=cells))
    w('gate.json', e20b1.gate(cells)); w('verify.json', dict(ok=verify_ok, failures=[] if verify_ok else ['x'], confirmation={}))
    w('overflow.json', dict(groups={f'train_s{s}': dict(files=1, dropped=o, counts=dict(nefc=o)) for s, o in zip(('42', '43'), ovf)}))
    if stopped:
        open(os.path.join(G, 'STOPPED'), 'w').write(stopped)
    sets = dict(packed=dict(own='P', rollouts=[rollout(i + 1, PK[i], PR[i], sha=pk_sha) for i in range(10)]),
                old=dict(own='P', rollouts=[rollout(1, old, 1.30, sha=e20b1.PACKED_SHA)]))
    sha_ch = cells[ch]['sha256'] if ch else SHA
    if conf is not None:
        m, rp = conf; rp = rp if isinstance(rp, list) else [rp] * nconf
        sets['conf'] = dict(own='P', rollouts=[rollout(i + 1, (d1 if (i == 0 and d1 is not None) else m + (0.001 if i % 2 else -0.001)), rp[i], sha=sha_ch)
                                               for i in range(nconf)])
    for s in ('42', '43'):
        sets[f'train{s}'] = dict(own='P', rollouts=[rollout(i + 1, cells[s].get('mean_raw') or 0.85, 1.5) for i in range(10)])
    w('score.json', dict(refs=dict(P=dict(md5=ref_md5)), sets=sets))
    r = subprocess.run([sys.executable, '-I', TOOL, 'verdict', '--dir', G, '--score', os.path.join(G, 'score.json'), '--out', os.path.join(G, 'summary.json')],
                       capture_output=True, text=True)
    s = json.load(open(os.path.join(G, 'summary.json'))) if os.path.exists(os.path.join(G, 'summary.json')) else {}
    return s, (r.stdout + r.stderr).strip()


C = lambda m42, m43, **k: {'42': cellrow('42', m42, **k.get('k42', {})), '43': cellrow('43', m43, **k.get('k43', {}))}
s, o = make('gate_not_met', C(0.8892, 0.8701))
need(s.get('label') == 'NO-SWAP' and 'training-box gate not met' in s['why'][0] and not s['pack10_inclusion']['include_in_pack10'],
     f'seeds 0.8892 / 0.8701 (packed-like) -> NO-SWAP, gate not met :: {o[:160]}')
s, o = make('gate_at_bar', C(0.8933, 0.85))
need(s.get('label') == 'NO-SWAP' and not s['training_box_gate']['met'], 'a seed mean exactly at the bar 0.8933 does not meet the gate (strict)')
s, o = make('gate_thin', C(0.95, 0.85, k42=dict(n=7)))
need(s.get('label') == 'INCOMPLETE' and not s['training_box_gate']['seeds']['42']['above'], 'a thin seed (n 7) -> INCOMPLETE and does not count for the gate')
s, o = make('gate_invalid', C(0.95, 0.85, k42=dict(status='INVALID')))
need(s.get('label') == 'INVALID' and not s['training_box_gate']['met'], 'an INVALID cell -> INVALID (no single-seed fallback), not counted for the gate')
s, o = make('missing', C(0.95, 0.85, k43=dict(status='MISSING', n=0)))
need(s.get('label') == 'INCOMPLETE', 'a missing seed -> INCOMPLETE')
s, o = make('include', C(0.90, 0.93), conf=(0.92, 1.4))
need(s.get('label') == 'SWAP-ELIGIBLE' and s['pack10_inclusion']['include_in_pack10'] and s['choice']['chosen'] == '43',
     f'conf 0.92, 0 fails, RPE 1.4 vs packed 0.8933 -> SWAP-ELIGIBLE, INCLUDE (gain {s["pack10_inclusion"]["gain"]}) :: {o[:220]}')
s, o = make('below_bar', C(0.90, 0.93), conf=(0.905, 1.4))
need(s.get('label') == 'SWAP-ELIGIBLE' and not s['pack10_inclusion']['include_in_pack10'],
     f'SWAP-ELIGIBLE at gain {s["pack10_inclusion"]["gain"]} -> NOT included :: {s["pack10_inclusion"]["reading"]}')
s, o = make('at_bar', C(0.90, 0.93), conf=(0.91335, 1.4))
need(s.get('label') == 'SWAP-ELIGIBLE' and s['pack10_inclusion']['include_in_pack10'], f'gain exactly +0.02 over the raw packed mean 0.89335 -> included (>=) {s["pack10_inclusion"]["gain"]}')
s, o = make('just_below_bar', C(0.90, 0.93), conf=(0.91325, 1.4))
need(s.get('label') == 'SWAP-ELIGIBLE' and not s['pack10_inclusion']['include_in_pack10'], f'gain +0.0199 -> NOT included {s["pack10_inclusion"]["gain"]}')
s, o = make('noswap_a', C(0.90, 0.93), conf=(0.890, 1.4))
need(s.get('label') == 'NO-SWAP' and not s['clauses']['a']['holds'], 'mean below the packed 0.8933 -> NO-SWAP (a)')
s, o = make('noswap_b', C(0.90, 0.93), conf=(0.93, [1.4] * 9 + [5.5]))
need(s.get('label') == 'NO-SWAP' and not s['clauses']['b']['holds'] and s['clauses']['a']['holds'],
     'one draw with RPE > 5 cm against the packed 0 / 10 -> NO-SWAP (b), even with a higher mean')
s, o = make('noswap_c', C(0.90, 0.93), conf=(0.93, 1.8))
need(s.get('label') == 'NO-SWAP' and not s['clauses']['c']['holds'], 'median RPE 1.8 cm vs packed 1.67 -> NO-SWAP (c)')
s, o = make('noswap_s', C(0.90, 0.93), conf=(0.93, 1.4), d1=0.84)
need(s.get('label') == 'NO-SWAP' and not s['clauses']['s']['holds'] and s['clauses']['s']['bar'] == 0.8448,
     'draw 1 at 0.84 < old 0.8948 - 0.05 = 0.8448 -> NO-SWAP (s)')
s, o = make('incomplete_conf', C(0.90, 0.93), conf=(0.92, 1.4), nconf=9)
need(s.get('label') == 'INCOMPLETE', '9 scored confirmation draws -> INCOMPLETE')
s, o = make('bad_ref', C(0.90, 0.93), conf=(0.92, 1.4), ref_md5='e' * 32)
need(s.get('label') == 'INVALID', 'a score file whose P is not the packed reference -> INVALID')
s, o = make('bad_packed_sha', C(0.90, 0.93), conf=(0.92, 1.4), pk_sha='f' * 64)
need(s.get('label') == 'INVALID', 'a packed-side rollout naming another checkpoint -> INVALID')
s, o = make('verify_bad', C(0.90, 0.93), conf=(0.92, 1.4), verify_ok=False)
need(s.get('label') == 'INVALID', 'verify not ok -> INVALID')
s, o = make('stopped', C(0.90, 0.93), stopped='piece set check FAILED')
need(s.get('label') == 'INVALID' and 'job stopped' in s['why'][0], 'STOPPED -> INVALID')
s, o = make('unclean', C(0.90, 0.93), conf=(0.92, 1.4), ovf=(1001, 0))
need(s.get('label') == 'SWAP-ELIGIBLE' and 'pieces not clean in training' in s['labels_attached'] and s['pack10_inclusion']['include_in_pack10'],
     '1,001 overflow lines in one training log -> "pieces not clean in training" attached; the rule still applies')
s, o = make('clean_at_bar', C(0.90, 0.93), conf=(0.92, 1.4), ovf=(1000, 1000))
need('pieces not clean in training' not in s['labels_attached'], '1,000 lines -> no label (> 1,000 is the bar)')
st = {'42': dict(n=10, mean=0.9000, sd=0.02), '43': dict(n=10, mean=0.9040, sd=0.03)}
need(e10cs.rule2_e10v(st, ['42', '43']) == '42', 'choose: means within 0.005 -> the lower sd (42)')
st = {'42': dict(n=10, mean=0.9000, sd=0.02), '43': dict(n=10, mean=0.9060, sd=0.03)}
need(e10cs.rule2_e10v(st, ['42', '43']) == '43', 'choose: 0.006 apart -> the higher mean (43)')
st = {'42': dict(n=10, mean=0.9000, sd=0.02), '43': dict(n=10, mean=0.9000, sd=0.02)}
need(e10cs.rule2_e10v(st, ['42', '43']) == '42', 'choose: full tie -> seed 42')
out = dict(ok=all(r['ok'] for r in rows), n=len(rows), passed=sum(r['ok'] for r in rows), cases=rows)
json.dump(out, open(A.out, 'w'), indent=1)
print(f"RESULT: {out['passed']}/{out['n']} pass"); sys.exit(0 if out['ok'] else 1)
