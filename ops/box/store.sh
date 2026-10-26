#!/bin/bash
# Artifact store: a private Hugging Face dataset repo ($HF_STORE, e.g. <owner>/v2d-store), written with the HF_TOKEN
# from the Vast account env. Written 2026-10-20, not yet run.
# Layout in the store:
#   weights/FoundationStereo/23-51-11/...       weights/FoundationPose/<dated dirs>/...   (mirror of Google Drive)
#   env/<name>/env.tar.zst.part-* + SHA256SUMS  environment snapshot (venvs, built extensions, weights, kit, caches)
#   cache/depth/<public|eval>/ep<N>/depths_fs0.5.npy                                      (FoundationStereo depth)
#   runs/<run_id>/...                           logs, perception outputs, references, latest policy/state, eval results
#
#   store.sh push-run                  stage this run's outputs (hard links) and upload them as one commit
#   store.sh push-depth <ep> [public|eval] [perc_dir]
#   store.sh pull-depth <ep> [public|eval]
#   store.sh pull-run <run_id>         put an earlier run's outputs back under /content (stages skip, training resumes)
#                                      (PULL_SUB="sub/dir ..." limits it to those sub-folders of the run)
#   store.sh mirror-weights            upload FoundationStereo/FoundationPose weights after a Google Drive setup
#   store.sh snapshot-env <name>       tar + zstd + upload the built environment (same image tag required to restore)
#   store.sh restore-env <name>
. /etc/v2d_env 2> /dev/null || true
[ -f /venv/main/bin/activate ] && . /venv/main/bin/activate      # before set -u: activate scripts read unset vars
set -euo pipefail
: "${HF_STORE:?HF_STORE is not set}"
# HF PRO (owner, 2026-10-21): 1 TB private storage included, then pay-as-you-go ($18/TB/month). Refuse uploads once
# the store holds STORE_MAX_GB, so a pruning bug cannot run up a bill (the 100 GB free quota filled once already).
store_gb() { curl -s -m 30 -H "Authorization: Bearer ${HF_TOKEN:-}" "https://huggingface.co/api/datasets/$HF_STORE?expand%5B%5D=usedStorage" \
  | python3 -c "import json,sys; print(int(json.load(sys.stdin).get('usedStorage', 0) / 1e9))" 2> /dev/null || echo 0; }
up() {
  local g; g=$(store_gb)
  [ "$g" -lt "${STORE_MAX_GB:-800}" ] || { echo "store holds $g GB >= STORE_MAX_GB ${STORE_MAX_GB:-800}: not uploading $2" >&2; return 1; }
  hf upload "$HF_STORE" "$1" "$2" --repo-type dataset --commit-message "$3" > /dev/null
}
down() { hf download "$HF_STORE" --repo-type dataset --include "$1" --local-dir "$2" > /dev/null; }
need_zstd() { command -v zstd > /dev/null || apt-get -qq install -y zstd > /dev/null 2>&1; }
SNAP_PATHS="workspace/v2d workspace/FoundationStereo workspace/FoundationPose workspace/ckpt workspace/kit
            workspace/mpvenv workspace/rtvenv venv/main .uv root/.cache/torch/hub"

case ${1:-} in
push-run)
  : "${RUN_ID:?}"; S=/content/push/$RUN_ID; rm -rf $S; mkdir -p $S; cd /content
  for d in perc2 perc2m perc4 oracle refs runs results det; do        # det: detection dumps (ops/jobs/det_dump.sh)
    [ -d $d ] || continue
    find $d -type f ! -name 'depths_*' ! -path '*/dbg/*' ! -path '*/hydra/*/.hydra/*.lock' | while read -r f; do
      mkdir -p "$S/$(dirname "$f")"; ln "$f" "$S/$f" 2> /dev/null || cp "$f" "$S/$f"
    done
  done
  # per run directory (runs/<perc><variant>/ep<N>-s<seed>/): keep every KEEP_EVERY-th policy_* plus the newest
  # (checkpoint choice), and the newest state_* only while training is unfinished (no .done; it is for resuming). The
  # old loop looked one level too high (runs/<perc>/), so every checkpoint was uploaded and the 100 GB store filled up
  # (2026-10-21: 44 GB of state_ files). KEEP_EVERY 25 -> 10 after the HF PRO upgrade (1 TB; policies are 5 MB).
  # 2026-10-26: also keep every checkpoint that an evaluation result names (the sweep's choice can be an earlier
  # checkpoint: eval 10 carve s42 chose 150M, which was pruned, and the box was gone when the pack needed it)
  NAMED=$(find /content/results -name '*.json' -exec grep -hoE 'runs/[^"]*/policy_[0-9]+\.safetensors' {} + 2> /dev/null | sort -u)
  for r in $S/runs/*/*/; do
    [ -d "$r" ] || continue
    rel=runs/${r#$S/runs/}
    { ls -v "$r" | grep '^policy_' || true; } | head -n -1 | awk -v k="${KEEP_EVERY:-10}" 'NR % k != 0' | while read -r x; do
      echo "$NAMED" | grep -qxF "$rel$x" || rm -rf "$r/$x"; done
    if [ -e "$r/.done" ]; then
      rm -rf "$r"/state_*
    else
      { ls -v "$r" | grep '^state_' || true; } | head -n -1 | while read -r x; do rm -rf "$r/$x"; done
    fi
  done
  cp /workspace/run_job.log /content/*.log $S/ 2> /dev/null || true
  cp -r /content/run_state $S/ 2> /dev/null || true
  git -C /content/v2d-track3 rev-parse HEAD > $S/COMMIT
  up $S runs/$RUN_ID "run $RUN_ID: $(date -u +%FT%TZ)"
  echo "pushed runs/$RUN_ID ($(du -sh $S | cut -f1))"
  ;;
push-depth)
  EP=$2; SPLIT=${3:-public}; PD=${4:-/content/perc2}
  up "$(readlink -f $PD/ep$EP/depths_fs0.5.npy)" cache/depth/$SPLIT/ep$EP/depths_fs0.5.npy "depth $SPLIT ep$EP"
  ;;
pull-depth)
  EP=$2; SPLIT=${3:-public}
  down "cache/depth/$SPLIT/ep$EP/*" /content/hfstore
  F=/content/hfstore/cache/depth/$SPLIT/ep$EP/depths_fs0.5.npy
  [ -s $F ] || { echo "no stored depth for $SPLIT ep$EP" >&2; exit 1; }    # never leave a dangling link (perception would read it)
  mkdir -p /content/cache/depth/ep$EP
  ln -sf $F /content/cache/depth/ep$EP/
  ;;
pull-run)
  if [ -n "${PULL_SUB:-}" ]; then   # PULL_SUB="refs/perc2mck/ep8 perc2/ep8 ...": only those sub-folders (2026-10-25: pulling
    for s in $PULL_SUB; do down "runs/$2/$s/*" /content/hfstore; done   # a whole still-running run failed twice on one
  else                                                                 # checkpoint, "File size mismatch")
    down "runs/$2/*" /content/hfstore
  fi
  for d in perc2 perc2m perc4 oracle refs runs results; do
    [ -d /content/hfstore/runs/$2/$d ] && mkdir -p /content/$d && cp -rn /content/hfstore/runs/$2/$d/. /content/$d/
  done
  echo "pulled runs/$2"
  ;;
mirror-weights)
  up /content/FoundationStereo/pretrained_models/23-51-11 weights/FoundationStereo/23-51-11 "FoundationStereo weights"
  up /content/FoundationPose/weights weights/FoundationPose "FoundationPose weights"
  echo "weights mirrored"
  ;;
snapshot-env)
  NAME=$2; need_zstd; O=/content/snap/$NAME; rm -rf $O; mkdir -p $O
  ( . /venv/main/bin/activate 2> /dev/null; pip freeze ) > $O/pip-freeze-main.txt 2> /dev/null || true
  echo "image ${V2D_IMAGE:-unknown}; commit $(git -C /content/v2d-track3 rev-parse HEAD); $(date -u +%FT%TZ)" > $O/README.txt
  # shellcheck disable=SC2086
  tar -C / --exclude='*/__pycache__' -cf - $(cd / && ls -d $SNAP_PATHS 2> /dev/null) | zstd -q -T0 -3 | split -b 8G - $O/env.tar.zst.part-
  (cd $O && sha256sum env.tar.zst.part-* > SHA256SUMS)
  up $O env/$NAME "environment snapshot $NAME"
  echo "snapshot env/$NAME uploaded ($(du -sh $O | cut -f1))"; rm -rf $O
  ;;
restore-env)
  NAME=$2; need_zstd; D=/content/snapdl
  down "env/$NAME/*" $D
  (cd $D/env/$NAME && sha256sum -c --quiet SHA256SUMS)
  cat $D/env/$NAME/env.tar.zst.part-* | zstd -q -d | tar -C / -xf -
  rm -rf $D
  apt-get -qq update > /dev/null 2>&1; apt-get -qq install -y libeigen3-dev libboost-all-dev > /dev/null 2>&1 || true
  echo "ENV-RESTORE-OK $NAME"
  ;;
*) sed -n '2,18p' "$0"; exit 1 ;;
esac
