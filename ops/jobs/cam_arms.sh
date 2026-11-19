#!/bin/bash
# Camera-arms test (2026-11-19; rule pre-registered in docs/analysis/camarms-20261119/PREREG.md before any run):
# perc2 on the public episodes with the PUBLIC SCANS as templates (arm S, perc2's own camera = arm C), then NVIDIA ViPE's
# MetricTrail on the same rectified camera-c frames as alternative cameras:
#   VD   mono, known K, DA3METRIC-LARGE keyframe depth (dav3), DPVO window 12        (the owner's recipe; candidate)
#   VD2  VD again (MetricTrail's own noise)           VM  VD with MoGe-2 depth (MetricTrail default)
#   VDH  VD + ViPE dynamic masking (person, hand)     VS  MetricTrail stereo runner on rectified c/b, DA3, window 12
#   SD   perc2 re-run with VD's per-frame DA3 metric depth instead of FoundationStereo depth (mono-depth perception)
# The room-map camera (arm M) comes from the 2 Nov store run. Scoring (tools/cam_arms_score.py) runs last, after every
# inference output exists; it is the only step that reads mocap.
#   ops/vast.sh create <offer> <run> 'bash ops/jobs/cam_arms.sh'
# Output /content/results/camarms/{S,SD}/ep<N>/ (perc2), V/<arm>/ep<N>.{npz,log} (cameras), M/, score.json.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; O=/content/results/camarms; VW=/content/vwork; mkdir -p $O/M $O/V $VW
EPS=${EPS:-"12 0 2 11 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}   # ep12 first: smoke test of every arm
VARMS=${VARMS:-"VD VD2 VM VDH VS"}
VPY=/content/vipe/.venv/bin/python; export TORCH_HOME=/content/torch_home
log "cam_arms code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS], MetricTrail arms [$VARMS], tracks: public scans" >> $J
ensure_gdino $J
pip install -q fast_simplification manifold3d >> $J 2>&1 || true

# 1. ViPE + MetricTrail install, in the background (CPU-heavy compile while perc2 uses the GPU)
( bash $OPS/vipe_setup.sh > $O/vipe_setup.log 2>&1; echo "vipe_setup rc=$?" >> $O/vipe_setup.log ) &
SETUP_PID=$!

# 2. prefetch: cached FoundationStereo depth (as perc_colour.sh) and the 2 Nov room-map cameras (leave-out folds)
python - $EPS << 'PYEOF' >> $J 2>&1 || true
import os, sys, shutil
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import hf_hub_download
S = os.environ.get('HF_STORE', 'aebatirel/v2d-store'); T = os.environ.get('HF_TOKEN')
def get(e):
    out = []
    try:
        f = hf_hub_download(S, f'cache/depth/public/ep{e}/depths_fs0.5.npy', repo_type='dataset', local_dir='/content/hfstore', token=T)
        os.makedirs(f'/content/cache/depth/ep{e}', exist_ok=True)
        d = f'/content/cache/depth/ep{e}/depths_fs0.5.npy'
        if not os.path.exists(d): os.symlink(f, d)
        out.append(f'ep{e} depth ok')
    except Exception as x:
        out.append(f'ep{e} depth prefetch failed: {x!r}'[:200])
    try:
        f = hf_hub_download(S, f'runs/20261102-roommap-6438495/world_T_cam/public/ep{e}.npz', repo_type='dataset', local_dir='/content/hfstore', token=T)
        shutil.copy(f, f'/content/results/camarms/M/ep{e}.npz'); out.append('map ok')
    except Exception as x:
        out.append(f'map failed: {x!r}'[:200])
    return ' '.join(out)
with ThreadPoolExecutor(6) as ex:
    print('prefetch:', list(ex.map(get, sys.argv[1:])))
PYEOF

# 3. frames for MetricTrail (perc2's rectification, 512 x 320), all episodes (CPU)
for ep in $EPS; do
  [ -s $VW/ep$ep/K.json ] || python $P/vipe_prep.py $ep $VW/ep$ep >> $J 2>&1 || log "cam_arms ep$ep: frame prep FAILED" >> $J
done

# 4. arm S: perc2 with the public scans (MESH_DIR unset), today's eval defaults otherwise; MESH_WELD=1 merges the scans'
#    duplicate vertices (same faces; 300k -> 50k vertices) so FoundationPose fits a 32 GB card (19 Nov: OOM without it)
run_perc() {   # run_perc <arm> <ep> <depth file>
  local name=$1 ep=$2 dep=$3 D=$O/$1/ep$2; mkdir -p $D
  [ -s $D/poses.npz ] && return 0
  [ -s "$dep" ] && ln -sf "$dep" $D/depths_fs0.5.npy
  label "camarms ep$ep $name"; local t0=$(date +%s)
  ( unset MESH_DIR TRACK_MESH_DIR; MESH_WELD=1 KF_MIN=120 EP=$ep OUT=$D SPLIT=public TRACK_CAM=c python $P/perc2.py > $D/log.txt 2>&1 )
  local rc=$?
  log "camarms ep$ep $name rc=$rc $(( $(date +%s) - t0 ))s: $(grep -a 'vo keyframes\|^\[.*\] vo  ' $D/log.txt | tail -2 | cut -c1-200 | tr '\n' ' ')" >> $J
  [ $rc = 0 ] || tail -5 $D/log.txt >> $J
  rm -f $D/depths_fs*.npy
  return $rc
}

# 5. MetricTrail arms (on a 96 GB card they start as soon as the install is ready and share the GPU with perc2)
run_vipe() {   # run_vipe <arm> <ep>
  local arm=$1 ep=$2 F=$VW/ep$2 ART=$VW/ep$2/art_$1 L=$O/V/$1/ep$2.log; mkdir -p $O/V/$arm
  [ -s $ART/pose/c.npz ] && return 0
  local K; K=$(python -c "import json; k=json.load(open('$F/K.json')); print(k['fx'], k['fy'], k['cx'], k['cy'])")
  local B; B=$(python -c "import json; print(json.load(open('$F/meta.json'))['baseline_m'])")
  local COMMON=(pipeline=metrictrail streams=frame_dir_stream "streams.base_path=$F/c" pipeline.init.input_raster.policy=unchanged
                "pipeline.optional.intrinsics={path:'$F/K.json'}" "pipeline.output.path=$ART/" pipeline.slam.dpvo.OPTIMIZATION_WINDOW=12)
  local t0=$(date +%s) rc
  case $arm in
    VD|VD2) ( cd /content/vipe && $VPY run.py "${COMMON[@]}" pipeline.slam.keyframe_depth=dav3 ) > $L 2>&1; rc=$? ;;
    VM)     ( cd /content/vipe && $VPY run.py "${COMMON[@]}" ) > $L 2>&1; rc=$? ;;
    VDH)    ( cd /content/vipe && $VPY run.py "${COMMON[@]}" pipeline.slam.keyframe_depth=dav3 \
                "pipeline.init.instance={phrases:[person,hand],add_sky:false}" ) > $L 2>&1; rc=$? ;;
    VS)     sed -e 's/^keyframe_depth: .*/keyframe_depth: dav3/' -e 's/^\(\s*\)OPTIMIZATION_WINDOW: .*/\1OPTIMIZATION_WINDOW: 12/' \
              /content/vipe/vipe/metrictrail/stereo/stereo.yaml > $VW/stereo_dav3_w12.yaml
            ( cd /content/vipe && $VPY -m vipe.metrictrail.stereo --left $F/c --right $F/b --intrinsics $K --baseline $B \
                --output $ART --name c --config $VW/stereo_dav3_w12.yaml ) > $L 2>&1; rc=$? ;;
  esac
  log "camarms ep$ep $arm rc=$rc $(( $(date +%s) - t0 ))s" >> $J
  [ $rc = 0 ] || { tail -8 $L | cut -c1-300 >> $J; }
  find $ART -name '*.zip' -size +1M ! -path "*/depth/*" -delete 2> /dev/null || true
  return $rc
}
vipe_loop() {
  while kill -0 $SETUP_PID 2> /dev/null; do sleep 30; done
  [ -f /content/vipe_ready ] || { log "cam_arms: ViPE setup FAILED: $(tail -5 $O/vipe_setup.log | tr '\n' ' ' | cut -c1-400)" >> $J; return 1; }
  log "cam_arms: ViPE ready" >> $J
  for ep in $EPS; do
    [ -s $VW/ep$ep/K.json ] || continue
    for arm in $VARMS; do run_vipe $arm $ep; done
    rm -rf $VW/ep$ep/art_VD2/depth $VW/ep$ep/art_VM/depth $VW/ep$ep/art_VDH/depth $VW/ep$ep/art_VS/depth   # only VD's depth is used (SD)
  done
  log "cam_arms: MetricTrail arms done" >> $J
}
# a 32 GB card (RTX 5090) runs perc2 and MetricTrail one after the other; a 96 GB card runs them side by side
GPU_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2> /dev/null | head -1)
if [ "${GPU_MB:-0}" -ge 60000 ]; then vipe_loop & VLOOP_PID=$!; log "cam_arms: ${GPU_MB} MiB GPU, MetricTrail alongside perc2" >> $J
else VLOOP_PID=; log "cam_arms: ${GPU_MB} MiB GPU, MetricTrail after perc2" >> $J; fi

for ep in $EPS; do
  [ -s /content/cache/depth/ep$ep/depths_fs0.5.npy ] || bash $OPS/store.sh pull-depth $ep public > /dev/null 2>&1 || log "camarms ep$ep: no cached depth (computed here)" >> $J
  run_perc S $ep /content/cache/depth/ep$ep/depths_fs0.5.npy || log "camarms ep$ep: S failed" >> $J
done
log "cam_arms: S tracks done" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
if [ -n "$VLOOP_PID" ]; then wait $VLOOP_PID; else vipe_loop; fi

# 6. cameras -> perc2 convention; VD depth -> perc2 grid; then arm SD (perc2 on DA3 depth)
for ep in $EPS; do
  N=$(python -c "import json; print(json.load(open('$VW/ep$ep/meta.json'))['frames'])" 2> /dev/null) || continue
  for arm in $VARMS; do
    [ -s $VW/ep$ep/art_$arm/pose/c.npz ] || continue
    $VPY $P/vipe_cam.py pose $VW/ep$ep/art_$arm c $N $O/V/$arm/ep$ep.npz --perc2 $O/S/ep$ep/poses.npz >> $O/V/$arm/ep$ep.log 2>&1 \
      && log "camarms ep$ep $arm camera: $(tail -1 $O/V/$arm/ep$ep.log | cut -c1-260)" >> $J \
      || log "camarms ep$ep $arm camera conversion FAILED" >> $J
  done
  if [ -s $VW/ep$ep/art_VD/depth/c.zip ]; then
    $VPY $P/vipe_cam.py depth $VW/ep$ep/art_VD c $N $VW/ep$ep/da3_depth.npy >> $J 2>&1 \
      && run_perc SD $ep $VW/ep$ep/da3_depth.npy || log "camarms ep$ep: SD failed" >> $J
    rm -f $VW/ep$ep/da3_depth.npy
  fi
done
log "cam_arms: SD done" >> $J

# 7. scoring (reads mocap; every inference output above already exists)
label "camarms scoring"
python $REPO_DIR/tools/cam_arms_score.py $O $O/score.json --map $O/M --eps "$EPS" > $O/score.log 2>&1 \
  && log "cam_arms scored: $(grep -a '"mean_AUC"' -A9 $O/score.log | tr -s ' \n' ' ' | cut -c1-400)" >> $J \
  || { log "cam_arms scoring FAILED" >> $J; tail -5 $O/score.log >> $J; }
log "cam_arms done" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
