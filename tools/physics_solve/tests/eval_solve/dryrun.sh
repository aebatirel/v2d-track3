#!/bin/bash
# Dry run (2026-10-31) of ops/jobs/eval_solve.sh on CPU in a scratch root: /content is replaced by ROOT (sed), the store by
# a local mirror of REAL store files (pull-files stub: copy; push-run stub: listing), the GPU tools by fcstub.py. Real:
# eval_inputs.py (pull lists, md5 / URDF / stage checks), make_assets.py (eval 10's /content/assets), trace_score.py,
# rest_check.py, eval_solve_summary.py, the job's queue and hand-off. No ground truth is read.
# Usage: S=<scratchpad> MIRROR=<store mirror> bash dryrun.sh ROOT 'ENV=... ' ; prints the job log, labels, stub calls.
set -u
S=${S:?}; MIRROR=${MIRROR:?}; RT=${1:?}; ENVS=${2:-}; REPO=/home/user/v2d-track3; D=$REPO/tools/physics_solve/tests/eval_solve
rm -rf $RT; mkdir -p $RT/v2d-track3/ops/box $RT/bin $RT/v2d/robotic_grounding/flash_chord/.venv/bin $RT/v2d/robotic_grounding/flash_chord/src/flash_chord/configs/embodiment
for x in tools pipeline meshes docs flashchord_conf .git; do ln -s $REPO/$x $RT/v2d-track3/$x; done
ln -s $REPO/ops/jobs $RT/v2d-track3/ops/jobs
sed "s#/content#$RT#g" $REPO/ops/jobs/eval_solve.sh > $RT/job.sh
cat > $RT/v2d-track3/ops/box/lib.sh << LIB
export REPO_DIR=$RT/v2d-track3 PYTHONUNBUFFERED=1 PATH=$RT/bin:\$PATH KIT=$S/dl/kit/x/v2d_submission_kit
OPS=\$REPO_DIR/ops/box; ST=$RT/run_state; mkdir -p \$ST
log() { echo "[\$(date -u +%FT%TZ)] \$*"; }
label() { echo "\$(date -u +%T) \$*" >> $RT/labels.txt; }
LIB
cat > $RT/v2d-track3/ops/box/store.sh << ST
#!/bin/bash
# stub: pull-files copies from the local mirror (STUB_MISSING / STUB_CORRUPT: store paths to fail / to corrupt)
case \$1 in
pull-files) shift; for f in "\$@"; do
  [[ " \${STUB_MISSING:-} " == *" \$f "* ]] && { echo "pull-files: \$f FAILED after 5 tries" >&2; exit 1; }
  [ -s $MIRROR/\$f ] || { echo "pull-files: \$f FAILED after 5 tries" >&2; exit 1; }
  mkdir -p $RT/hfstore/\$(dirname \$f); cp $MIRROR/\$f $RT/hfstore/\$f
  [[ " \${STUB_CORRUPT:-} " == *" \$f "* ]] && echo corrupt >> $RT/hfstore/\$f
  echo "pulled \$f"; done ;;
push-run) ( cd $RT && find refs results -type f | sort ) > $RT/push_listing.txt; echo "push-run stub: \$(wc -l < $RT/push_listing.txt) files" ;;
*) echo "stub store.sh: \$*" >&2; exit 1 ;;
esac
ST
chmod +x $RT/v2d-track3/ops/box/store.sh
printf '#!/bin/bash\nexec %s "$@"\n' $S/venv/bin/python > $RT/bin/python; chmod +x $RT/bin/python
printf '#!/bin/bash\nexec %s -I %s "$@"\n' $S/venv/bin/python $D/fcstub.py > $RT/v2d/robotic_grounding/flash_chord/.venv/bin/python
chmod +x $RT/v2d/robotic_grounding/flash_chord/.venv/bin/python
t0=$(date +%s)
( cd $RT && eval "env RUN_ID=20261101-evsolvetest-dry J=$RT/job.log STUB_LOG=$RT/stub_calls.log $ENVS bash $RT/job.sh" ) > $RT/stdout.txt 2>&1
echo "job exit $? after $(( $(date +%s) - t0 )) s"
