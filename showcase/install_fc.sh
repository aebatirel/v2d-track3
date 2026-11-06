#!/bin/bash
# Install the showcase's generic floating-hand embodiment into a FlashCHORD checkout and its per-robot configs into
# FlashCHORD's embodiment config group (so "embodiment=<robot>" works and checkpoints rebuild in the evaluator).
#   install_fc.sh FLASHCHORD_DIR ROBOTS_DIR      (ROBOTS_DIR = output of showcase/prep_robots.py)
set -e
FC=$1; RD=$2; HERE=$(cd $(dirname $0) && pwd)
cp $HERE/floating_hands.py $FC/src/flash_chord/embodiments/floating_hands.py
for y in $RD/*/emb_*.yaml; do n=$(basename $y .yaml); cp $y $FC/src/flash_chord/configs/embodiment/${n#emb_}.yaml; done
echo "installed floating_hands.py + $(ls $RD/*/emb_*.yaml | wc -l) embodiment configs into $FC"
