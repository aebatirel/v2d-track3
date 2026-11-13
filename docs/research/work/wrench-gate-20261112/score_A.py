#!/usr/bin/env python3
"""Test A of the wrench-feasibility gate, as amended: official evaluator rollouts of trained policies on 8 public episodes.

Rules (docs/work-log.md):
  "2026-11-12 ~22:20 UTC … PRE-REGISTRATION"            score, label (> 2 cm vs our reference), bars, bootstrap
  "2026-11-13 ~02:30 UTC" and "~03:00 UTC … AMENDMENT"  8 episodes (ep12, ep40, ep23, ep18, ep2, ep24, ep21, ep31);
                                                        informative = AUROC >= 0.75 and >= 4 of the 8 episodes with
                                                        positives; falsified = AUROC < 0.65; the 10-90% share rule;
                                                        the tree runs leave-one-episode-out over the same 8 episodes
  "~04:10 UTC" D1-D3                                    D2: the label rollout is
                                                        results/hard_ab/ep<N>/s-s42/r1/episode_<E6>.parquet
  gate       pipeline/wrench_gate.py frozen at 61c0b6ad, on the ORIGINAL refsweep perc2 references (kit assets)
  label      per (object, frame) in the gate's held windows: |achieved - our reference| object position > 0.02 m, the
             rollout row of environment_id = min matched by reference_frame; no row, environment_valid False or a
             non-finite pose counts as positive
  pairing    the training copy refs/perc2s/ep<N>/processed/<x>.parquet must be byte-identical (sha256) to the gate's
             input, and the rollout's reference poses must match our reference within 1 mm on every row; else refuse
  stats      pooled AUROC (mid-ranks); 2,000 episode-bootstrap resamples, seed 20261112, percentile CI
  verdict    share outside [0.10, 0.90] -> inconclusive; else AUROC < 0.65 -> falsified; AUROC >= 0.75 and >= 4 episodes
             with positives -> informative; else inconclusive
Subcommands
  manifest GATE_STORE A_STORE KIT OUT.json   the 8-episode manifest; GATE_STORE / A_STORE = local mirrors of the store
                                  (runs/... paths) holding the gate inputs and the test A files; KIT = kit assets
  pair MANIFEST OUT.json          pairing checks only: reads the rollouts' reference columns, never the achieved poses
  features FEATURES.csv OUT.csv   the blob-feature rows of the 8 episodes (input of tools/blob_tree.py)
  score MANIFEST OUT_DIR          the test: results_A.json, labels_A.csv (episode, object, frame, label)
  selftest                        end-to-end on SYNTHETIC rollouts built from the 8 references (no real outcome read)
Manifest: {"assets": KIT, "episodes": [{"ep", "ref" (gate input), "ref_copy" (refs/perc2s copy), "rollout" (r1
           parquet), "rollout_json", "store": {...}}]}"""
import csv, hashlib, json, os, subprocess, sys, tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'pipeline')); sys.path.insert(0, HERE)
from score_gate import auroc, episode_bootstrap, spearman, BAR_INFORMATIVE, BAR_FALSIFIED  # noqa: E402

EPISODES = (12, 40, 23, 18, 2, 24, 21, 31)                        # amendment 03:00 UTC
MIN_POS_EPISODES, SHARE_LO, SHARE_HI, LABEL_M, ALIGN_M, FROZEN = 4, 0.10, 0.90, 0.02, 1e-3, '61c0b6ad'
REF_COLS = ['environment_id', 'reference_frame', 'object_body_name', 'environment_valid',
            'reference_position_x', 'reference_position_y', 'reference_position_z']
ACH_COLS = ['achieved_position_x', 'achieved_position_y', 'achieved_position_z']
PROV_KEYS = ('checkpoint', 'checkpoint_sha256', 'environment_steps', 'motion_start_frame', 'motion_end_frame', 'parquet')


def verdict_a(a, n_pos_eps, share):
    if a is None:
        return 'inconclusive (one class only)'
    if share < SHARE_LO or share > SHARE_HI:
        return f'inconclusive (positive share {share:.3f} outside [{SHARE_LO}, {SHARE_HI}])'
    if a < BAR_FALSIFIED:
        return 'falsified'
    if a >= BAR_INFORMATIVE and n_pos_eps >= MIN_POS_EPISODES:
        return 'informative'
    return 'inconclusive'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read_rollout(path, achieved):
    """The rollout rows of environment_id = min; the achieved columns only when `achieved` is True."""
    import pyarrow.parquet as pq
    t = pq.read_table(path, columns=REF_COLS + (ACH_COLS if achieved else []))
    md = {k.decode(): v.decode() for k, v in (pq.read_schema(path).metadata or {}).items() if k.startswith(b'flash_chord.')}
    d = t.to_pydict(); env = np.array(d['environment_id']); keep = env == env.min()
    out = dict(frame=np.array(d['reference_frame'])[keep], name=np.array(d['object_body_name'])[keep],
               valid=np.array(d['environment_valid'])[keep].astype(bool),
               ref=np.stack([np.array(d[f'reference_position_{c}'], float)[keep] for c in 'xyz'], 1), meta=md,
               envs=sorted(set(env.tolist())))
    if achieved:
        out['ach'] = np.stack([np.array(d[f'achieved_position_{c}'], float)[keep] for c in 'xyz'], 1)
    return out


def pairing(e):
    """sha256 of the training copy vs the gate input; rollout reference poses vs our reference (reference columns only)."""
    from task_wrench import object_tracks
    names, P, _ = object_tracks(e['ref']); T = len(P); r = read_rollout(e['rollout'], achieved=False)
    s_ref, s_copy = sha256(e['ref']), sha256(e['ref_copy']) if e.get('ref_copy') else None
    worst, per_obj, cover = 0.0, {}, {}
    for j, n in enumerate(names):
        sel = r['name'] == n; fr = r['frame'][sel]
        if not sel.any() or fr.min() < 0 or fr.max() >= T:
            return dict(ok=False, why=f'object {n}: no rows or frames outside the reference')
        d = float(np.linalg.norm(r['ref'][sel] - P[fr, j], axis=1).max()); per_obj[n] = round(d * 1000, 4); worst = max(worst, d)
        cover[n] = dict(rows=int(sel.sum()), frames_unique=int(len(np.unique(fr))), frame_min=int(fr.min()), frame_max=int(fr.max()))
    prov = {}
    if e.get('rollout_json') and os.path.exists(e['rollout_json']):
        js = json.load(open(e['rollout_json'])); prov = {k: js.get(k) for k in PROV_KEYS}   # provenance only, no metrics
    ok = worst < ALIGN_M and (s_copy is None or s_copy == s_ref)
    return dict(ok=ok, max_ref_diff_mm=round(worst * 1000, 4), per_object_max_mm=per_obj, frames_ref=T, coverage=cover,
                sha256_gate_input=s_ref, sha256_training_copy=s_copy, copy_identical=None if s_copy is None else s_copy == s_ref,
                rollout_reference_parquet=r['meta'].get('flash_chord.reference_parquet'),
                rollout_step_count=r['meta'].get('flash_chord.step_count'), rollout_envs=r['envs'], provenance=prov)


RUNS = {12: '20261113-gA1b-25cb421', 31: '20261113-gA1b-25cb421', 40: '20261113-gA2-25cb421', 21: '20261113-gA2-25cb421',
        23: '20261113-gA3-25cb421', 2: '20261113-gA3-25cb421', 18: '20261113-gA4-25cb421', 24: '20261113-gA4-25cb421'}
GATE_INPUT = 'runs/20261020-refsweep-ea14fdf/refs/perc2/ep{ep}/processed/sequence_id=t3_ep{ep:03d}/robot_name=sharpa_wave'


def cmd_manifest(gate_store, a_store, kit, out):
    """D2 label rollout and the refs/perc2s training copy per episode; the gate input is the refsweep perc2 parquet."""
    import glob
    eps = []
    for ep, run in sorted(RUNS.items()):
        g = glob.glob(os.path.join(gate_store, GATE_INPUT.format(ep=ep), '*.parquet'))
        if len(g) != 1:
            raise SystemExit(f'ep{ep}: {len(g)} gate-input parquets under {gate_store}')
        name = os.path.basename(g[0]); sub = GATE_INPUT.format(ep=ep).split('/processed/')[1]
        copy = f'runs/{run}/refs/perc2s/ep{ep}/processed/{sub}/{name}'
        roll = f'runs/{run}/results/hard_ab/ep{ep}/s-s42/r1/episode_{ep:06d}.parquet'
        eps.append(dict(ep=ep, ref=g[0], ref_copy=os.path.join(a_store, copy), rollout=os.path.join(a_store, roll),
                        rollout_json=os.path.join(a_store, roll[:-8] + '.json'),
                        store=dict(gate_input=os.path.relpath(g[0], gate_store), ref_copy=copy, rollout=roll, rollout_json=roll[:-8] + '.json')))
    json.dump(dict(test='A', assets=kit, episodes=eps), open(out, 'w'), indent=1)
    print({e['ep']: dict(ref_copy=os.path.exists(e['ref_copy']), rollout=os.path.exists(e['rollout'])) for e in eps})


def cmd_pair(man_path, out):
    man = json.load(open(man_path)); res = {str(e['ep']): pairing(e) for e in sorted(man['episodes'], key=lambda x: x['ep'])}
    json.dump(res, open(out, 'w'), indent=1)
    for k, v in res.items():
        print(f"ep{k}: ok {v['ok']}, max |ref - ours| {v.get('max_ref_diff_mm')} mm, copy identical {v.get('copy_identical')}, "
              f"frames {v.get('frames_ref')}, rollout ref file {os.path.basename(v.get('rollout_reference_parquet') or '')}")
    return 0 if all(v['ok'] for v in res.values()) else 2


def cmd_features(feat_csv, out_csv):
    keep = {f'ep{e}' for e in EPISODES}; rows = list(csv.DictReader(open(feat_csv)))
    sel = [r for r in rows if r['episode'] in keep]
    with open(out_csv, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(sel)
    print(f'{len(sel)} of {len(rows)} feature rows kept ({sorted(keep)})')


def cmd_score(man_path, out_dir, frozen_check=True):
    from task_wrench import object_tracks
    from wrench_gate import gate, INFEASIBLE
    man = json.load(open(man_path)); eps = sorted(man['episodes'], key=lambda x: x['ep'])
    os.makedirs(out_dir, exist_ok=True)
    if frozen_check and subprocess.run(['git', '-C', REPO, 'diff', '--quiet', FROZEN, '--', 'pipeline/wrench_gate.py']).returncode:
        raise SystemExit(f'pipeline/wrench_gate.py differs from the frozen {FROZEN}; refusing')
    got = sorted(e['ep'] for e in eps)
    if got != sorted(EPISODES) and not man.get('synthetic'):
        res = dict(status='blocked', why='manifest does not hold exactly the 8 amended episodes',
                   missing=sorted(set(EPISODES) - set(got)), extra=sorted(set(got) - set(EPISODES)))
        json.dump(res, open(os.path.join(out_dir, 'results_A.json'), 'w'), indent=1); print(json.dumps(res)); return 2
    prov = {str(e['ep']): pairing(e) for e in eps}
    if not all(p['ok'] for p in prov.values()):
        res = dict(status='blocked', why='pairing check failed', pairing=prov)
        json.dump(res, open(os.path.join(out_dir, 'results_A.json'), 'w'), indent=1); print(json.dumps(res)[:2000]); return 2
    per_ep, table, rows_csv = [], [], []
    for e in eps:
        g = gate(e['ref'], man.get('assets')); names, P, _ = object_tracks(e['ref']); T = len(P)
        r = read_rollout(e['rollout'], achieved=True); err = {}
        for j, n in enumerate(names):
            v = np.full(T, np.nan); sel = r['name'] == n
            for f, a, ok in zip(r['frame'][sel], r['ach'][sel], r['valid'][sel]):
                if ok and np.isfinite(a).all():
                    v[f] = np.linalg.norm(a - P[f, j])
            err[n] = v
        s = np.array([x['score'] for x in g['rows']]); ev = np.array([err[x['object']][x['frame']] for x in g['rows']])
        y = ~np.isfinite(ev) | (np.nan_to_num(ev, nan=np.inf) > LABEL_M); obj = np.array([x['object'] for x in g['rows']])
        rows_csv += [(f"ep{e['ep']}", x['object'], int(x['frame']), int(lab)) for x, lab in zip(g['rows'], y)]
        allerr = np.concatenate(list(err.values())); a_in = auroc(s, y); per_ep.append((s, y))
        table.append(dict(ep=e['ep'], held_units=int(len(s)), positives=int(y.sum()),
                          positive_share=round(float(y.mean()), 4) if len(s) else None, missing_or_invalid=int((~np.isfinite(ev)).sum()),
                          share_infeasible=round(float((s > INFEASIBLE).mean()), 4) if len(s) else None,
                          mean_err_held_cm=round(float(np.nanmean(ev)) * 100, 3) if np.isfinite(ev).any() else None,
                          mean_err_all_cm=round(float(np.nanmean(allerr)) * 100, 3) if np.isfinite(allerr).any() else None,
                          auroc_within=None if a_in is None else round(a_in, 4),
                          objects={n: dict(held=o['held_frames'], share_infeasible=o['share_infeasible'], positives=int(y[obj == n].sum()))
                                   for n, o in g['objects'].items() if o['held_frames']}))
    S = np.concatenate([p[0] for p in per_ep]); Y = np.concatenate([p[1] for p in per_ep])
    a = auroc(S, Y); npos = sum(int(p[1].any()) for p in per_ep); share = float(Y.mean())
    sec = [x for x in table if x['mean_err_held_cm'] is not None and x['held_units']]
    res = dict(status='run', test='A (official evaluator rollouts, 8-episode amendment)', synthetic=bool(man.get('synthetic')),
               episodes=len(per_ep), units=int(len(S)), positives=int(Y.sum()), positive_share=round(share, 4),
               auroc=None if a is None else round(a, 4), bootstrap=episode_bootstrap(per_ep), episodes_with_positives=npos,
               verdict=verdict_a(a, npos, share),
               bars=dict(informative=f'AUROC >= {BAR_INFORMATIVE} and >= {MIN_POS_EPISODES} of 8 episodes with positives',
                         falsified=f'AUROC < {BAR_FALSIFIED}', share_rule=f'inconclusive if positive share < {SHARE_LO} or > {SHARE_HI}'),
               secondary=dict(spearman_share_infeasible_vs_mean_err_held=spearman([x['share_infeasible'] for x in sec], [x['mean_err_held_cm'] for x in sec]),
                              spearman_share_infeasible_vs_mean_err_all=spearman([x['share_infeasible'] for x in sec], [x['mean_err_all_cm'] for x in sec]),
                              note='descriptive only'),
               per_episode=table, pairing=prov, gate_frozen_at=FROZEN)
    json.dump(res, open(os.path.join(out_dir, 'results_A.json'), 'w'), indent=1)
    with open(os.path.join(out_dir, 'labels_A.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['episode', 'object', 'frame', 'label']); w.writerows(rows_csv)
    print(json.dumps({k: v for k, v in res.items() if k not in ('per_episode', 'pairing')}, indent=1))
    return 0


# ------------------------------------------------------------------ self-test on synthetic rollouts
def synth_rollout(ref, path, offset_fn, ref_shift=0.0, drop=()):
    """Evaluator-schema rollout built from OUR reference: achieved = reference + offset_fn(object, frame) (m, along z)."""
    import pyarrow as pa, pyarrow.parquet as pq
    from task_wrench import object_tracks
    names, P, Q = object_tracks(ref); T = len(P); cols = {k: [] for k in ['environment_id', 'step', 'reference_frame', 'object_body_name', 'environment_valid']
                                                         + [f'{a}_position_{c}' for a in ('achieved', 'reference') for c in 'xyz']}
    for f in range(T):
        for j, n in enumerate(names):
            if (n, f) in drop:
                continue
            cols['environment_id'].append(0); cols['step'].append(f); cols['reference_frame'].append(f)
            cols['object_body_name'].append(n); cols['environment_valid'].append(True)
            for k, c in enumerate('xyz'):
                ref_c = float(P[f, j, k]) + (ref_shift if c == 'x' else 0.0)
                cols[f'reference_position_{c}'].append(ref_c); cols[f'achieved_position_{c}'].append(ref_c + (offset_fn(n, f) if c == 'z' else 0.0))
    pq.write_table(pa.table(cols), path)


def cmd_selftest(man_path):
    """Synthetic rollouts for the 8 references: positives exactly where the gate score > 0.5 (expect AUROC 1, informative),
    then all positive (share rule), then a 5 mm reference shift (pairing refusal), then dropped rows (count as positive)."""
    from wrench_gate import gate
    man = json.load(open(man_path)); td = tempfile.mkdtemp(prefix='selftestA_', dir=os.path.dirname(os.path.abspath(man_path))); ok = True; eps = []
    rows = {e['ep']: gate(e['ref'], man.get('assets'))['rows'] for e in man['episodes']}
    for e in man['episodes']:
        bad = {(x['object'], x['frame']) for x in rows[e['ep']] if x['score'] > 0.5}
        p = os.path.join(td, f"episode_{e['ep']:06d}.parquet")
        synth_rollout(e['ref'], p, lambda n, f, bad=bad: 0.03 if (n, f) in bad else 0.005)
        eps.append(dict(ep=e['ep'], ref=e['ref'], ref_copy=e.get('ref_copy'), rollout=p))
    m1 = os.path.join(td, 'm1.json'); json.dump(dict(assets=man.get('assets'), synthetic=True, episodes=eps), open(m1, 'w'))
    cmd_score(m1, os.path.join(td, 'o1')); r = json.load(open(os.path.join(td, 'o1', 'results_A.json')))
    exp_pos = sum(x['score'] > 0.5 for v in rows.values() for x in v); n = sum(len(v) for v in rows.values())
    lab = list(csv.DictReader(open(os.path.join(td, 'o1', 'labels_A.csv'))))
    c1 = r['auroc'] == 1.0 and r['positives'] == exp_pos and len(lab) == n
    print(f"{'PASS' if c1 else 'FAIL'} gate-shaped labels: AUROC {r['auroc']} (want 1.0), positives {r['positives']} (want {exp_pos}), "
          f"rows {len(lab)} (want {n}), share {r['positive_share']}, verdict {r['verdict']}"); ok &= c1
    want_v = verdict_a(1.0, r['episodes_with_positives'], r['positive_share'])
    c1b = r['verdict'] == want_v; ok &= c1b; print(f"{'PASS' if c1b else 'FAIL'} verdict consistent: {r['verdict']}")
    for e in eps:                                                   # every frame 3 cm off -> share 1.0 -> inconclusive
        synth_rollout(e['ref'], e['rollout'], lambda n_, f: 0.03)
    cmd_score(m1, os.path.join(td, 'o2')); r2 = json.load(open(os.path.join(td, 'o2', 'results_A.json')))
    c2 = r2['positive_share'] == 1.0 and r2['verdict'].startswith('inconclusive'); ok &= c2
    print(f"{'PASS' if c2 else 'FAIL'} all positive -> {r2['verdict']}")
    e0 = eps[0]; synth_rollout(e0['ref'], e0['rollout'], lambda n_, f: 0.0, ref_shift=0.005)   # pairing must refuse
    rc = cmd_score(m1, os.path.join(td, 'o3')); r3 = json.load(open(os.path.join(td, 'o3', 'results_A.json')))
    c3 = rc == 2 and r3['status'] == 'blocked'; ok &= c3; print(f"{'PASS' if c3 else 'FAIL'} 5 mm reference shift -> {r3['status']}")
    held = [(x['object'], x['frame']) for x in rows[e0['ep']]][:5]      # 5 held rows missing, the rest exact
    synth_rollout(e0['ref'], e0['rollout'], lambda n_, f: 0.0, drop=set(held))
    for e in eps[1:]:
        synth_rollout(e['ref'], e['rollout'], lambda n_, f: 0.0)
    cmd_score(m1, os.path.join(td, 'o4')); r4 = json.load(open(os.path.join(td, 'o4', 'results_A.json')))
    c4 = r4['positives'] == 5 and r4['per_episode'][[x['ep'] for x in r4['per_episode']].index(e0['ep'])]['missing_or_invalid'] == 5
    ok &= c4; print(f"{'PASS' if c4 else 'FAIL'} 5 dropped rows count as positive: positives {r4['positives']}")
    for v, nn, sh, want in ((0.80, 4, 0.5, 'informative'), (0.80, 3, 0.5, 'inconclusive'), (0.60, 8, 0.5, 'falsified'),
                            (0.90, 8, 0.95, 'inconclusive'), (0.90, 8, 0.05, 'inconclusive'), (0.70, 8, 0.5, 'inconclusive')):
        got = verdict_a(v, nn, sh); good = got.startswith(want); ok &= good
        print(f"{'PASS' if good else 'FAIL'} verdict_a({v}, {nn}, {sh}) = {got}")
    print('SELFTEST_A', 'OK' if ok else 'FAILED', td)
    return 0 if ok else 1


def main():
    a = sys.argv[1:]
    if a[:1] == ['manifest']:
        return cmd_manifest(a[1], a[2], a[3], a[4])
    if a[:1] == ['pair']:
        return cmd_pair(a[1], a[2])
    if a[:1] == ['features']:
        return cmd_features(a[1], a[2])
    if a[:1] == ['score']:
        return cmd_score(a[1], a[2])
    if a[:1] == ['selftest']:
        return cmd_selftest(a[1])
    raise SystemExit(__doc__)


if __name__ == '__main__':
    sys.exit(main() or 0)
