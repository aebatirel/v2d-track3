#!/bin/bash
# H5 (robustness review §7, 2026-10-29): N official evaluations of every pack-6 checkpoint, scored sim_vs_ref against
# our own reference (qa.py policy; no ground truth). Measures how much of the packed score was a lucky draw and which
# episodes are high-variance. It never packs or uploads a best-of-N rollout: the output is information for the
# pre-registered choice rules (work log 2026-10-29).
#   1) pack_eval.sh with pack 6's exact choices (pack 5's RUNS / PICK / ASSET_PIECES, EP_LIB 8 only) and NO KEEP_RESULTS:
#      pulls every reference / asset / checkpoint and runs draw 1 (results/submission, summary.txt);
#   2) draws 2..N: the same pristine kit evaluator on the same checkpoints JSON, each into results/h5/r<i>;
#   3) results/h5/h5_summary.json: per episode n, mean, sd, min, p20 and the packed draw (pack 6 summary.txt).
# As a job: ops/vast.sh ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run_id> 'N=10 bash ops/jobs/h5_reeval.sh'
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; N=${N:-10}; H=/content/results/h5; mkdir -p $H
C=/content/v2d-track3/meshes/carve
export RUNS="20261026-fr32s46b-5e0e100@refs/glockt/ep32,refs/sf/ep32 20261026-gl10A2-5e0e100@refs/glockt/ep10,refs/glock/ep10 20261026-c25s42-feb0407@refs/perc2mcks 20261026-fr3233s43-6a8a0e2@refs/glockt/ep33,refs/sf/ep33 20261025-evb0810-ee7ba8e@refs/glockt/ep8,refs/sf/ep8 20261025-evb1420-ee7ba8e@refs/glockt/ep14,refs/sf/ep14,refs/glockt/ep20,refs/sf/ep20 20261025-fr3233-043275f@refs/glockt/ep32,refs/sf/ep32 20261025-std0116-ee7ba8e@refs/perc2mcks 20261025-std1928-ee7ba8e@refs/perc2mcks 20261025-std30-ee7ba8e@refs/perc2mcks 20261024-pack-31ef267"
export PICK="3:20261024-seed43-61101f5 5:20261024-seed43-61101f5 15:20261024-seed43-61101f5 16:20261024-seed43-61101f5 1:20261025-std0116-ee7ba8e:final 8:20261025-evb0810-ee7ba8e:final 14:20261025-evb1420-ee7ba8e:final 20:20261025-evb1420-ee7ba8e:final 19:20261025-std1928-ee7ba8e:final 28:20261025-std1928-ee7ba8e:final 25:20261026-c25s42-feb0407:ck=runs/perc2mcks/ep25-s42/policy_250003456.safetensors 30:20261025-std30-ee7ba8e:final 32:20261026-fr32s46b-5e0e100 33:20261026-fr3233s43-6a8a0e2 10:20261026-gl10A2-5e0e100"
export EP_LIB="8:/content/v2d-track3/meshes/library_v3x" ASSET_PIECES="$C/ev25 $C/ev10"
export COMMIT_URL=https://github.com/aebatirel/v2d-track3/commit/$(git -C $REPO_DIR rev-parse HEAD)
label "H5: draw 1 (pack-6 environment)"
bash $REPO_DIR/ops/jobs/pack_eval.sh || { log "h5: pack_eval FAILED" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }
CK=/content/results/final_eval/checkpoints.json; CLEAN=/content/v2d_clean; KIT=/content/kit/v2d_submission_kit
FCV=/content/v2d/robotic_grounding/flash_chord/.venv/bin/python
cp -r /content/results/submission/qa $H/r1
for i in $(seq 2 $N); do
  label "H5: draw $i of $N"
  O=$H/r$i; mkdir -p $O/results
  ( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl \
      XLA_PYTHON_CLIENT_PREALLOCATE=false $FCV $KIT/examples/run_policy_evaluation.py --checkpoints $CK \
      --results $O/results --runtime-root $CLEAN/robotic_grounding/flash_chord ) > $O/eval.log 2>&1 \
    || { log "h5: draw $i evaluation FAILED ($(tail -2 $O/eval.log | tr '\n' ' ' | cut -c1-200))" >> $J; continue; }
  for p in $O/results/episode_*.parquet; do
    e=$((10#$(basename $p .parquet | cut -d_ -f2))); mkdir -p $O/ep$e; cp ${p%.parquet}.* $O/ep$e/
    python $REPO_DIR/pipeline/qa.py policy $O/ep$e $e > /dev/null 2>&1 || true
    rm -f $O/ep$e/*.parquet                                        # keep the scores, not 200 rollout files
  done
  rm -rf $O/results
  log "h5: draw $i done" >> $J
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true            # partial results survive a crash
done
python - $H $N $REPO_DIR/results/submissions/20261026-track3f/summary.txt << 'PYEOF' > $H/h5_summary.txt 2>&1
import glob, json, sys
import numpy as np
H, N, packed_txt = sys.argv[1], int(sys.argv[2]), sys.argv[3]
packed = json.loads(open(packed_txt).readline())
draws = {}
for f in glob.glob(f'{H}/r*/ep*/qa_policy.json'):
    ep = f.split('/ep')[-1].split('/')[0]
    draws.setdefault(ep, []).append(json.load(open(f))['sim_vs_ref'])
out = {}
for ep in sorted(draws, key=int):
    v = np.array(draws[ep])
    out[ep] = dict(n=len(v), mean=round(float(v.mean()), 4), sd=round(float(v.std(ddof=1)) if len(v) > 1 else 0.0, 4),
                   min=round(float(v.min()), 4), p20=round(float(np.percentile(v, 20)), 4), packed=packed.get(ep))
json.dump(out, open(f'{H}/h5_summary.json', 'w'), indent=1)
means = [d['mean'] for d in out.values()]
print(json.dumps(out))
print(f'episodes {len(out)}  mean of means {np.mean(means):.4f}  packed mean {np.mean([float(x) for x in packed.values()]):.4f}')
PYEOF
log "h5: $(tail -1 $H/h5_summary.txt)" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
exit 0
