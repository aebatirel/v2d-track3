#!/bin/bash
# C2/R box job (PREREG C2/R-rack sections 4-5): C0b's pinned venv, C0b's rack inputs from the store run, the 8 option
# runs, fidelity, exclusion checks, the pick. Started by ops/box/run_job.sh with SETUP=none (stall watchdog, push of
# /content/results to the HF store runs/<RUN_ID>/, self-destroy). GT-free: inputs are C0b's observed points, markers,
# params and the kit's budget code; never a scan, mocap, parquet pose, *_align file or library_v3 mesh.
# Box:   bash docs/research/mesh-2026-10-26/cdo-sprint/C2/R-rack/scripts/c2r_box.sh       (RUN_ID from ops/vast.sh)
set -u
. /content/v2d-track3/ops/box/lib.sh
: "${RUN_ID:?RUN_ID is not set}"
JOBD=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
C0B_RUN=${C0B_RUN:-mesh-20261031-c0b-00e8584}
R=/content/results/c2r; W=/content/c2rw
mkdir -p $R $W
exec >> $R/c2r_job.log 2>&1
log "C2/R job start: run $RUN_ID commit $(git -C $REPO_DIR rev-parse HEAD) cpus $(nproc) ram $(free -g | awk '/Mem/{print $2}') GB; inputs from $C0B_RUN"
label "C2R setup"
bash $REPO_DIR/docs/research/mesh-2026-10-26/cdo-sprint/C0b/jobs/c0b_setup.sh $W $R/setup.log || { log "C2R-FAIL setup"; exit 1; }
PY=$W/venv/bin/python
label "C2R inputs"
$PY -I $JOBD/c2r_stage.py --run $C0B_RUN --out $W/in > $R/stage.log 2>&1 || { log "C2R-FAIL stage: $(tail -2 $R/stage.log)"; exit 1; }
cp $W/in/STAGED.json $R/
# the kit (budget check) from C0b's store inputs
$PY -I - << EOF >> $R/stage.log 2>&1 || { log "C2R-FAIL kit"; exit 1; }
from huggingface_hub import snapshot_download
import shutil, os
p = snapshot_download('aebatirel/v2d-store', repo_type='dataset', allow_patterns=['runs/$C0B_RUN/inputs/kit/**'],
                      cache_dir='$W/.kc')
shutil.copytree(os.path.join(p, 'runs/$C0B_RUN/inputs/kit'), '$W/kit', dirs_exist_ok=True)
print('kit ok', os.listdir('$W/kit'))
EOF
log "inputs: $(tail -1 $R/stage.log)"
NP=$(nproc); RAM=$(free -g | awk '/Mem/{print $2}'); PAR=$(( RAM / 8 )); [ $PAR -gt 8 ] && PAR=8; [ $PAR -gt $NP ] && PAR=$NP; [ $PAR -lt 1 ] && PAR=1
export GMG_DATA_ROOT=$W GMG_MODE=clean
label "C2R build"
( while sleep 120; do log "alive: $(ls $R/cand/*/plastic_dish_rack/*.glb 2> /dev/null | wc -l) meshes, $(ls $R/fid/*.json 2> /dev/null | wc -l) fid, load $(cut -d' ' -f1 /proc/loadavg)"; done ) &
HB=$!
C2R_PY=$PY bash $JOBD/c2r_build.sh $W/in $R $W/kit $PAR
kill $HB 2> /dev/null
(cd $R && find . -type f ! -name SHA256SUMS ! -name c2r_job.log -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
grep -q C2R-BUILD-DONE $R/c2r_build.log && log "C2R-DONE $(cat $R/logs/select.log | tail -1)" || log "C2R-INCOMPLETE"
