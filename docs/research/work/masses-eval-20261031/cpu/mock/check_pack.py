"""Assertions on the confirmation box of a finished run_all.sh mock (MS/done_C1: ops/jobs/h5_reeval.sh with the joined
strings of the training boxes, KEEP_RESULTS = pack 7's sources). usage: check_pack.py MS OUT.json MERGE.json
  P1 unchanged episodes untouched: every non-candidate episode's packed rollout (results/submission/results/episode_X
     .json + .parquet) is byte-identical to its pack-7 source (pack 6's store copy, the real file), and names pack 7's
     checkpoint sha256 (results/submissions/20261030-track3g-candidate/checkpoints.json);
  P2 the kit evaluator ran exactly the candidates, in draw 1 and in each of draws 2..N, and nothing else;
  P3 each candidate's evaluations loaded its training box's chosen checkpoint (sha256), the packed policy's reference
     (real fingerprint) and the props masses, grasp lock from refs/mass1_sf/ep<N>/, eval 1 from the shared /content/assets
     (with ev01's 53 / 107 pieces): the masses it trained with;
  P4 tools/mass_pack_check.py ran before draw 1 and before draws 2..N and passed;
  P5 h5_summary.json: the candidates with n = N each, packed column = pack 7's summary.txt (PACKED_TXT);
  P6 the pack's checkpoints.json: unchanged episodes = pack 7's checkpoints (sha256), candidates = the PICK_EXTRA ones;
  P7 tools/mass_eval_merge.py: six candidates; eval 1's seed is rule 2 over the two S1 boxes' 10-rollout stats;
  P8 (review F4) tools/mass_eval_rule.py on C1's real outputs: every candidate is read, and with N 3 < 8 rule 4 makes each
     INCOMPLETE (only the confirmation would be repeated); the spoon pilots then have no reading.
"""
import glob, hashlib, json, os, sys
MS, OUT = sys.argv[1], sys.argv[2]
REPO = '/home/user/v2d-track3'
B = f'{MS}/done_C1'; C = f'{B}/content'; CR = f'{MS}/box/content'
fx = lambda p: p.replace(f'{MS}/box/', f'{B}/')
REAL = json.load(open(f'{REPO}/docs/research/work/masses-eval-20261031/packed_refs.json'))['episodes']
P7 = json.load(open(f'{REPO}/results/submissions/20261030-track3g-candidate/checkpoints.json'))
P7S = json.loads(open(f'{REPO}/results/submissions/20261030-track3g-candidate/summary.txt').readline())
props = {n: v['physics']['mass_kg'] for n, v in json.load(open(f'{REPO}/docs/research/physics-2026-10-30/props_masses_only.json')).items()
         if isinstance(v, dict) and 'physics' in v}
BOX = {'20261101-mevG1-mocksha': 'G1', '20261101-mevG2-mocksha': 'G2', '20261101-mevG4-mocksha': 'G4',
       '20261101-mevS1s42-mocksha': 'S1a', '20261101-mevS1s43-mocksha': 'S1b'}
MG = json.load(open(sys.argv[3]))['episodes']                     # tools/mass_eval_merge.py's choices (rule 2 across boxes)
CAND = {e: BOX[x['run']] for e, x in MG.items() if x['decision'] == 'CANDIDATE'}
RID = {b: r for r, b in BOX.items()}
N = 3
res, fails = {}, []


def ok(name, cond, detail=''):
    res[name] = dict(ok=bool(cond), detail=str(detail)[:600])
    if not cond:
        fails.append(f'{name}: {str(detail)[:300]}')


sha = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()
R = f'{C}/results/submission/results'
K6 = f'{MS}/store/runs/20261026-pack6-5203d42/results/submission/results'
for e in sorted(P7, key=int):
    if e in CAND:
        continue
    src = K6 if 'pack6' in P7[e]['rollout'] else f'{MS}/store/runs/20261030-c33B-0202139/results/submission/results'
    same = all(md5(f'{R}/episode_{int(e):06d}{x}') == md5(f'{src}/episode_{int(e):06d}{x}') for x in ('.json', '.parquet'))
    js = json.load(open(f'{R}/episode_{int(e):06d}.json'))
    ok(f'P1_ep{e}_kept_byte_identical', same and js.get('checkpoint_sha256') == P7[e]['sha256'], (same, js.get('checkpoint_sha256', '')[:12]))
kit = [json.loads(x) for x in open(f'{B}/kit_audit.log')]
draws = {}
for x in kit:
    d = 'draw1' if '/results/submission/' in x['out'] else x['out'].split('/results/h5/')[1].split('/')[0]
    draws.setdefault(d, []).append(os.path.basename(x['out']).split('_')[1].split('.')[0].lstrip('0'))
ok('P2_only_candidates_evaluated', sorted(draws) == ['draw1'] + [f'r{i}' for i in range(2, N + 1)]
   and all(sorted(v, key=int) == sorted(CAND, key=int) for v in draws.values()), draws)
for e, box in CAND.items():
    T = REAL[e]; mine = [x for x in kit if os.path.basename(x['out']).startswith(f'episode_{int(e):06d}')]
    tb = f'{MS}/done_{box}/content'; S = json.load(open(f'{tb}/results/mass_eval/summary.json'))['episodes'][e]
    ck_tb = S['seeds'][MG[e]['seed']]['checkpoint'].replace(f'{MS}/box/', f'{MS}/done_{box}/')
    root = f'{CR}/refs/mass1_sf/ep{e}/' if T['mode'] == 'glock' else f'{CR}/assets/'
    bad = [x['out'] for x in mine if sha(fx(x['ck'])) != sha(ck_tb) or x['fingerprint'] != T['traj_fingerprint']
           or {n: v['mass'] for n, v in x['loaded'].items()} != {n: props[n] for n in x['loaded']}
           or not all(v['urdf'].startswith(root) for v in x['loaded'].values())]
    ok(f'P3_ep{e}_evaluated_with_its_training_masses', len(mine) == N and not bad,
       f'{len(mine)} evaluations, {len(bad)} wrong; loads {mine[0]["loaded"] if mine else None}'.replace(MS, 'MS'))
cols = {n: open(f'{C}/assets/urdf/{n}_rigid.urdf').read().count('<collision>') for n in ('white_pot', 'white_pot_lid')}
ok('P3_eval1_pieces', cols == dict(white_pot=53, white_pot_lid=107), cols)
m1, m2 = json.load(open(f'{C}/results/final_eval/mass_pack_check.json')), json.load(open(f'{C}/results/h5/mass_pack_check.json'))
ok('P4_mass_pack_check_draw1_and_later', m1['ok'] and m2['ok'] and sorted(m1['evaluated'], key=int) == sorted(CAND, key=int)
   and sorted(m2['evaluated'], key=int) == sorted(CAND, key=int), (m1['failures'], m2['failures']))
H = json.load(open(f'{C}/results/h5/h5_summary.json'))
ok('P5_h5_summary', sorted(H, key=int) == sorted(CAND, key=int) and all(H[e]['n'] == N and H[e]['packed'] == P7S[e] for e in H),
   {e: (v['n'], v['packed']) for e, v in H.items()})
CK = json.load(open(f'{C}/results/final_eval/checkpoints.json'))
ok('P6_checkpoints', all(sha(fx(CK[e])) == P7[e]['sha256'] for e in P7 if e not in CAND)
   and all(f'/pick/{RID[CAND[e]]}/' in CK[e] for e in CAND), {e: CK[e].split('/pick/')[-1][:60] for e in CK})
s1 = {s: json.load(open(f'{MS}/done_{b}/content/results/mass_eval/summary.json'))['episodes']['1']['seeds'][s]
      for b, s in (('S1a', '42'), ('S1b', '43'))}
sys.path.insert(0, f'{REPO}/tools'); from mass_eval_verify import rule2   # noqa: E402
ok('P7_merge_rule2_across_boxes', sorted(CAND, key=int) == ['1', '8', '10', '15', '20', '33'] and MG['1']['seed'] == rule2(s1, ['42', '43'])
   and CAND['1'] == ('S1a' if MG['1']['seed'] == '42' else 'S1b'), {s: (v['mean'], v['sd']) for s, v in s1.items()})
if len(sys.argv) > 4:
    RU = json.load(open(sys.argv[4]))
    ok('P8_rule_applied_rule4_incomplete', 'refused' not in RU and sorted(RU['episodes'], key=int) == sorted(CAND, key=int)
       and all(x['verdict'] == 'INCOMPLETE' and x['rule'] == '4' and x['confirmation']['n'] == N for x in RU['episodes'].values())
       and RU['spoon_stratum'].startswith('NO READING'), {e: (x['verdict'], x.get('confirmation', {}).get('n')) for e, x in RU.get('episodes', {}).items()})
out = dict(ok=not fails, failures=fails, checks=res, draws=draws, note='mock scores are synthetic (stub.py): plumbing, not masses')
json.dump(out, open(OUT, 'w'), indent=1)
print(('ALL PACK CHECKS PASS' if not fails else f'{len(fails)} FAILED: ' + ' | '.join(fails[:8])) + f' ({len(res)} checks)')
sys.exit(0 if not fails else 1)
