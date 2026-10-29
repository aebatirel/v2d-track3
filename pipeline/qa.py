"""Automatic quality checks for the per-episode pipeline (inference only: no ground truth is read).

  qa.py ref REF_SUMMARY_JSON      robot-reference quality from mkref's ref_summary.json: per tracked hand the robot
                                  wrist IK error (hand_C_MC p95) and the largest wrist step. Fails if p95 > IK_P95_MM
                                  or max step > STEP_CM (the 2026-10-21 failures: ep18 right p95 289 mm with the
                                  default wrist cost, 77 mm with wrist cost 3.0).
  qa.py policy RES_DIR EP          the official evaluator's rollout (RES/episode_XXXXXX.parquet holds the simulated
                                  object poses and the reference they were asked to track) scored against OUR reference
                                  with the kit's own metric functions, next to the reference's static floor (objects
                                  held at their frame-0 poses). verdict: harmful (sim < floor), weak (sim < floor +
                                  MARGIN or < MIN_AUC), ok. Same yardstick for every variant of one episode, because
                                  the object trajectory of the reference comes from perception, not from the variant.
Both print one JSON object (and write it next to the input as qa_ref.json / qa_policy.json).
"""
import json, os, sys
import numpy as np

KIT = os.environ.get('KIT', '/content/kit/v2d_submission_kit')
IK_P95_MM, STEP_CM = 60.0, 10.0
MARGIN, MIN_AUC = 0.05, 0.5


def qa_ref(path):
    s = json.load(open(path)); out = dict(kind='ref', reasons=[], wrist_p95_mm={}, max_step_cm={})
    for side in ('left', 'right'):
        if s.get('hands', {}).get(side, {}).get('mode') != 'tracked':
            continue
        p95 = s['ik'][side][f'{side}_hand_C_MC']['p95_mm']; step = s['wrist'][side]['max_step_cm']
        out['wrist_p95_mm'][side] = round(p95, 1); out['max_step_cm'][side] = round(step, 1)
        if p95 > IK_P95_MM:
            out['reasons'].append(f'{side} wrist IK p95 {p95:.0f} mm > {IK_P95_MM:.0f}')
        if step > STEP_CM:
            out['reasons'].append(f'{side} wrist step {step:.1f} cm > {STEP_CM:.0f}')
    out['pass'] = not out['reasons']
    out['score'] = max(out['wrist_p95_mm'].values(), default=0.0)       # lower is better (retry choice)
    json.dump(out, open(os.path.join(os.path.dirname(path), 'qa_ref.json'), 'w'), indent=1)
    return out


def qa_policy(res, ep):
    sys.path.insert(0, KIT); sys.path.insert(0, f'{KIT}/metric_code/track_3')
    import importlib
    from v2dlb.submission_parquet import read_trajectory
    A = importlib.import_module('AUC')
    tr = read_trajectory(os.path.join(res, f'episode_{ep:06d}.parquet'))
    w0 = tr.world_index == tr.world_index.min()
    frames = np.unique(tr.frame_index[w0]); B = int(tr.object_slot.max()) + 1
    def grid(P):
        G = np.full((len(frames), B, 7), np.nan)
        for f, s, p in zip(tr.frame_index[w0], tr.object_slot[w0], P[w0]):
            G[np.searchsorted(frames, f), s] = p
        return G
    sim, ref = grid(tr.pose_xyzw), grid(tr.reference_xyzw)
    # ADD points: 500 on a 5 cm-radius sphere per object (no mesh needed; the same yardstick for every variant)
    rng = np.random.default_rng(0); pts = rng.normal(size=(500, 3)); pts = 0.05 * pts / np.linalg.norm(pts, axis=1, keepdims=True)
    V = np.repeat(pts[None], B, 0)
    def auc(a, r):
        a, r = a[:, None], r[:, None]
        a = A._warp_to_reference_start(a, r)
        return float(A._add_auc(A._object_add(a, r, V)))
    out = dict(kind='policy', ep=ep, sim_vs_ref=round(auc(sim, ref), 4),
               floor_vs_ref=round(auc(np.repeat(ref[:1], len(ref), 0), ref), 4))
    out['verdict'] = ('harmful' if out['sim_vs_ref'] < out['floor_vs_ref'] else
                      'weak' if out['sim_vs_ref'] < max(out['floor_vs_ref'] + MARGIN, MIN_AUC) else 'ok')
    json.dump(out, open(os.path.join(res, 'qa_policy.json'), 'w'), indent=1)
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'ref':
        print(json.dumps(qa_ref(sys.argv[2])))
    elif sys.argv[1] == 'policy':
        print(json.dumps(qa_policy(sys.argv[2], int(sys.argv[3]))))
    else:
        raise SystemExit(__doc__)
