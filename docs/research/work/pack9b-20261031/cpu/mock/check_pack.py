"""Assertions on the confirmation box C of a finished run_all.sh mock and on the CPU verdict after it.
usage: check_pack.py MS OUT.json MERGE.json VERDICT.json
  P1 the kit evaluator ran exactly the merge's candidates, N (10) times each (draw 1 in pack_eval.sh, draws 2..10 in
     h5_reeval.sh), nothing else (KEEP_RESULTS kept every unchanged episode);
  P2 each of those evaluations loaded the candidate's checkpoint (sha256 = the merge's), its D reference copy (md5 = the
     packed reference's), the 0.3 kg placeholder for every object from the packed asset copy (grasp lock) or /content/assets
     (std), eval 25 with one <collision> per ev25 piece; no FC_DR_* in any kit evaluation process;
  P3 tools/dr_pack_check.py ran and passed before draw 1 (results/final_eval) and before draws 2..10 (results/h5);
  P4 the 15 unchanged episodes' packed rollouts are byte-identical to pack 6's real files and name pack 7's checkpoint;
  P5 results/h5/r1..r10/ep<N> hold each candidate's rollout parquet (KEEP_ROLLOUTS default) and qa_policy.json;
  P6 the CPU verdict decided every episode (PASS or NO-SWAP) on n 10 vs 10, every scored rollout's own-reference check
     passed, the old packed draw re-scores to pack 7's summary value, and pack9b lists exactly the PASS episodes;
  P7 the job string: DR_EPS = EVAL_ONLY = EPS_ONLY = the candidates, KEEP_RESULTS = pack 7's sources, PICK_EXTRA starts
     with 33:20261029-rcB-34bf6ae, N=10, PACKED_TXT pack 7's.
"""
import glob, hashlib, json, os, re, sys
MS, OUT, MERGE, VERD = sys.argv[1:5]
REPO = '/home/user/v2d-track3'
sys.path.insert(0, f'{REPO}/tools')
from mass_arm import md5   # noqa: E402
REAL = json.load(open(f'{REPO}/docs/research/work/masses-eval-20261031/packed_refs.json'))['episodes']
MOCKT = json.load(open(f'{MS}/tmpl/content/v2d-track3/docs/research/work/masses-eval-20261031/packed_refs.json'))['episodes']
M = json.load(open(MERGE)); VD = json.load(open(VERD))
B = f'{MS}/done_C'; C = f'{B}/content'; CR = f'{MS}/box/content'
res, fails = {}, []


def ok(name, cond, detail=''):
    res[name] = dict(ok=bool(cond), detail=str(detail)[:600])
    if not cond:
        fails.append(f'{name}: {str(detail)[:300]}')


cand = {e: x for e, x in M['episodes'].items() if x['decision'] == 'CANDIDATE'}
kit = [json.loads(x) for x in open(f'{B}/kit_audit.log')]
ep_of = lambda y: str(int(os.path.basename(y['out']).split('_')[1].split('.')[0]))
by = {}
for y in kit:
    by.setdefault(ep_of(y), []).append(y)
ok('P1_only_candidates_evaluated', set(by) == set(cand), (sorted(by, key=int), sorted(cand, key=int)))
ok('P1_N_draws_each', all(len(by.get(e, [])) == M['n'] for e in cand), {e: len(v) for e, v in by.items()})
for e, x in cand.items():
    T, TM = REAL[e], MOCKT[e]
    for k, y in enumerate(by.get(e, [])):
        sha = hashlib.sha256(open(y['ck'].replace(f'{MS}/box/', f'{B}/'), 'rb').read()).hexdigest()
        want_dir = f'{CR}/refs/drs{x["seed"]}_glockt/ep{e}/' if T['mode'] == 'glock' else f'{CR}/refs/perc2mckdr/ep{e}/'
        root = f'{CR}/refs/sf/ep{e}/assets/' if T['mode'] == 'glock' else f'{CR}/assets/'
        rf = y['reference_file'].replace(f'{MS}/box/', f'{B}/')
        good = (sha == x['sha256'] and y['reference_file'].startswith(want_dir) and md5(rf) == TM['md5'] and y['fingerprint'] == T['traj_fingerprint']
                and all(abs(u['mass'] - 0.3) < 1e-9 and u['urdf'].startswith(root) for u in y['loaded'].values()) and not y.get('env'))
        if T.get('pieces'):
            for n, u in y['loaded'].items():
                kp = len(glob.glob(f'{REPO}/{T["pieces"]}/{n}/piece_*.obj'))
                good = good and (not kp or len(re.findall('<collision>', open(u['urdf'].replace(f'{MS}/box/', f'{B}/')).read())) == kp)
        if not good or k == 0:
            ok(f'P2_ep{e}_eval{k}', good, dict(sha=sha[:12], want=str(x['sha256'])[:12], ref=y['reference_file'].replace(MS, 'MS'),
                                                 md5=md5(rf), env=y.get('env')))
    ok(f'P2_ep{e}_all_draws', all(hashlib.sha256(open(y['ck'].replace(f'{MS}/box/', f'{B}/'), 'rb').read()).hexdigest() == x['sha256']
                                  for y in by.get(e, [])))
for f in ('final_eval', 'h5'):
    p = f'{C}/results/{f}/dr_pack_check.json'
    d = json.load(open(p)) if os.path.exists(p) else {}
    ok(f'P3_dr_pack_check_{f}', d.get('ok') and sorted(map(str, d.get('dr_eps', []))) == sorted(cand), (d.get('ok'), d.get('failures'), d.get('dr_eps')))
P6S = f'{MS}/store/runs/20261026-pack6-5203d42/results/submission/results'
kept = [e for e in REAL if e not in cand]
same = {e: all(md5(f'{C}/results/submission/results/episode_{int(e):06d}{x}') == md5(f'{P6S}/episode_{int(e):06d}{x}') for x in ('.json', '.parquet'))
        for e in kept}
ok('P4_unchanged_rollouts_byte_identical', all(same.values()), {e: v for e, v in same.items() if not v})
sha7 = {e: json.load(open(f'{C}/results/submission/results/episode_{int(e):06d}.json')).get('checkpoint_sha256') == REAL[e]['packed_sha256'] for e in kept}
ok('P4_unchanged_name_pack7_checkpoints', all(sha7.values()), {e: v for e, v in sha7.items() if not v})
for e in cand:
    have = [i for i in range(1, M['n'] + 1) if glob.glob(f'{C}/results/h5/r{i}/ep{e}/episode_*.parquet') and os.path.exists(f'{C}/results/h5/r{i}/ep{e}/qa_policy.json')]
    ok(f'P5_ep{e}_rollouts_kept', len(have) == M['n'], have)
h5s = json.load(open(f'{C}/results/h5/h5_summary.json'))
ok('P5_h5_summary_n', all(h5s.get(e, {}).get('n') == M['n'] for e in cand), {e: h5s.get(e, {}).get('n') for e in cand})
labs = {e: x['label'] for e, x in VD['episodes'].items()}
ok('P6_verdict_decided', all(labs.get(e) in ('PASS', 'NO-SWAP') for e in cand), labs)
ok('P6_verdict_n', all(VD['episodes'][e]['sides']['new']['n'] == M['n'] and VD['episodes'][e]['sides']['packed']['n'] == 10 for e in cand),
   {e: (VD['episodes'][e]['sides'].get('new', {}).get('n'), VD['episodes'][e]['sides'].get('packed', {}).get('n')) for e in cand})
ok('P6_old_draw_matches_pack7', all(VD['episodes'][e].get('old_vs_pack7_summary', {}).get('matches') for e in cand),
   {e: VD['episodes'][e].get('old_vs_pack7_summary') for e in cand})
ok('P6_pack9b_is_the_PASS_set', sorted(VD['pack9b'], key=int) == sorted([e for e, l in labs.items() if l == 'PASS'], key=int), VD['pack9b'])
job = M['job']; E = ' '.join(sorted(cand, key=int))
ok('P7_job_string', all(f'{k}="{E}"' in job for k in ('DR_EPS', 'EVAL_ONLY', 'EPS_ONLY')) and 'KEEP_RESULTS="20261026-pack6-5203d42 20261030-c33B-0202139"' in job
   and 'PICK_EXTRA="33:20261029-rcB-34bf6ae ' in job and job.startswith('N=10 ') and 'track3g-candidate/summary.txt' in job, job)
json.dump(dict(n=len(res), passed=sum(v['ok'] for v in res.values()), failures=fails, labels=labs, checks=res), open(OUT, 'w'), indent=1)
print(f'check_pack: {sum(v["ok"] for v in res.values())} / {len(res)} pass; verdict labels {labs}' + ('' if not fails else ' :: FAIL ' + ' | '.join(fails[:8])))
