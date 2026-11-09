#!/bin/bash
# Colour-camera tracking test (2026-11-09; rule pre-registered in docs/analysis/colourcam-20261109/PREREG.md before any
# run). Three perc2 arms per public episode on one box, same code, same cached depth, today's eval defaults
# (library_v3 meshes for detection, TRACK_GUARD on, REG 5 / TRACK 2, KF_MIN 120 as the 2 Nov tracking tests):
#   C   control: FoundationPose on grey camera c with the library_v3 templates (as every eval reference);
#   CP  grey camera c, templates repainted in grey for this episode from camera c along C's own track (mesh_color.py);
#   AP  colour camera a (TRACK_CAM=a), templates repainted in colour for this episode from camera a along C's own track.
# AP vs CP isolates the camera (same per-episode painting); CP vs C is the repainting alone. Scoring against mocap is
# done afterwards by the agent (score_registered.py); perc2's own result.json score is diagnostic only.
#   ops/vast.sh create <offer> <run> 'bash ops/jobs/perc_colour.sh'
# Output /content/results/pcol/<arm>/ep<N>/ and /content/results/pcol/meshes_<CP|AP>/ep<N>/<obj>.glb.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; O=/content/results/pcol; mkdir -p $O
EPS=${EPS:-"12 0 2 11 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}   # ep12 first: a smoke test of all three arms
ARMS=${ARMS:-"C CP AP"}
LIB=${LIB:-$REPO_DIR/meshes/library_v3}
log "perc_colour code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS], arms [$ARMS], LIB $LIB" >> $J
ensure_gdino $J
pip install -q fast_simplification manifold3d >> $J 2>&1 || true
# depth prefetch: one hf_hub_download per file, all episodes in parallel (as perc_vos.sh)
python - $EPS << 'PYEOF' >> $J 2>&1 || true
import os, sys
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import hf_hub_download
def get(e):
    try:
        f = hf_hub_download(os.environ.get('HF_STORE', 'aebatirel/v2d-store'), f'cache/depth/public/ep{e}/depths_fs0.5.npy', repo_type='dataset',
                            local_dir='/content/hfstore', token=os.environ.get('HF_TOKEN'))
        os.makedirs(f'/content/cache/depth/ep{e}', exist_ok=True)
        d = f'/content/cache/depth/ep{e}/depths_fs0.5.npy'
        if not os.path.exists(d): os.symlink(f, d)
        return f'ep{e} ok'
    except Exception as x:
        return f'ep{e} prefetch failed: {x!r}'[:200]
with ThreadPoolExecutor(6) as ex:
    print('prefetch:', list(ex.map(get, sys.argv[1:])))
PYEOF
run_arm() {   # run_arm <arm> <ep> <env...>
  local name=$1 ep=$2; shift 2; local D=$O/$name/ep$ep; mkdir -p $D
  [ -s $D/poses_world_vo.npz ] && return 0
  [ -s /content/cache/depth/ep$ep/depths_fs0.5.npy ] && [ ! -e $D/depths_fs0.5.npy ] && ln -sf /content/cache/depth/ep$ep/depths_fs0.5.npy $D/
  label "pcol ep$ep $name"; local t0=$(date +%s)
  ( export "$@"; KF_MIN=120 EP=$ep OUT=$D SPLIT=public MESH_DIR=$LIB python $P/perc2.py > $D/log.txt 2>&1 )
  local rc=$?
  log "pcol ep$ep $name rc=$rc $(( $(date +%s) - t0 ))s: $(grep -a 'tracker camera\|^\[.*\] vo  ' $D/log.txt | tail -2 | cut -c1-220 | tr '\n' ' ')" >> $J
  [ $rc = 0 ] || tail -5 $D/log.txt >> $J
  return $rc
}
for ep in $EPS; do
  [ -s /content/cache/depth/ep$ep/depths_fs0.5.npy ] || bash $OPS/store.sh pull-depth $ep public > /dev/null 2>&1 || log "pcol ep$ep: no cached depth (computed here)" >> $J
  run_arm C $ep TRACK_CAM=c || { log "pcol ep$ep: control failed, arms skipped" >> $J; continue; }
  OBJS=$(python -c "import json; print(' '.join(json.load(open('$O/C/ep$ep/result.json'))['objects']))")
  DEP=/content/cache/depth/ep$ep/depths_fs0.5.npy; [ -s $DEP ] || DEP=$O/C/ep$ep/depths_fs0.5.npy
  for o in $OBJS; do                                          # per-episode painting along the control's own track
    mkdir -p $O/meshes_CP/ep$ep $O/meshes_AP/ep$ep
    python $P/mesh_color.py --cam c --mesh $LIB/$o.glb --obj $o --poses $O/C/ep$ep/poses.npz --depth $DEP \
      --video /content/t3/v/ep${ep}_c.mp4 --calib /content/t3/calib.json --out $O/meshes_CP/ep$ep/$o.glb >> $O/meshes_CP/ep$ep/paint.log 2>&1
    python $P/mesh_color.py --cam a --mesh $LIB/$o.glb --obj $o --poses $O/C/ep$ep/poses.npz --depth $DEP \
      --video /content/t3/v/ep${ep}_a.mp4 --calib /content/t3/calib.json --out $O/meshes_AP/ep$ep/$o.glb >> $O/meshes_AP/ep$ep/paint.log 2>&1
  done
  log "pcol ep$ep painted: $(tail -qn1 $O/meshes_AP/ep$ep/paint.log 2>/dev/null | cut -c1-160 | tr '\n' ' ')" >> $J
  case " $ARMS " in *" CP "*) run_arm CP $ep TRACK_CAM=c TRACK_MESH_DIR=$O/meshes_CP/ep$ep ;; esac
  case " $ARMS " in *" AP "*) run_arm AP $ep TRACK_CAM=a TRACK_MESH_DIR=$O/meshes_AP/ep$ep ;; esac
  rm -f $O/*/ep$ep/depths_fs*.npy                              # depth caches never go to the store
  n_done=$(( ${n_done:-0} + 1 )); [ $(( n_done % 5 )) = 1 ] && { bash $OPS/store.sh push-run > /dev/null 2>&1 || true; }
done
log "perc_colour done" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
