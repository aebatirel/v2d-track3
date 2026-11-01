#!/bin/bash
# Contact budget of one scene: sampled training resets (W x STEPS) and explicit resets at FRAMES, sim=rl, box patch set.
# Usage: budget_run.sh REF.parquet EMB(sharpa_hands_mid|default) OUT_PREFIX "f0,f1,..."   (S = session scratchpad)
REF=$1; EMB=$2; OUT=$3; FR=$4; S=${S:?}; B=$(cd "$(dirname "$0")" && pwd)/budget.py
cd $S/src/video_to_data/robotic_grounding/flash_chord
e=""; [ "$EMB" != default ] && e="EMB=$EMB"
for mode in sampled explicit; do
  fr=""; [ $mode = explicit ] && fr="FRAMES=$FR"
  env USE_COPY=$S/rs/fc_box FC_VOC_INERTIA=1 FC_FDR_OBJ=1 FC_FDR_TIPS=1 $e W=${W:-8} STEPS=${STEPS:-30} $fr \
    timeout 2400 $S/fcvenv/bin/python $B $REF ${OUT}_$mode.json > ${OUT}_$mode.log 2>&1
  echo "$mode exit $? overflow_lines $(grep -ci overflow ${OUT}_$mode.log)"
done
python3 - ${OUT}_sampled.json ${OUT}_explicit.json << 'PY'
import json, sys
for f in sys.argv[1:]:
    d = json.load(open(f))
    print(f.rsplit('_', 1)[1][:-5], d['frames'], '| geoms', d['collision_geoms'], '| contacts/world max', d['max_contacts_per_world'],
          'med', d['median_contacts_per_world'], '| nefc max', d['max_nefc_per_world'], 'med', d['median_nefc'],
          '| share>512', round(d.get('share_steps_nefc_over_njmax', 0), 3))
    print('    top pairs', dict(list(d['max_contacts_per_world_by_pair'].items())[:4]))
    print('    hold window (steps < 20):', d.get('nefc_hold_window'), '| after hold:', d.get('nefc_after_hold'))
PY
