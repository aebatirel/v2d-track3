#!/bin/bash
# Reproduce the [M] numbers of ../human-hand-models.md (CPU, ~1 min). Usage: run.sh WORKDIR PYTHON
# PYTHON must have mujoco==3.8.1 (the FlashCHORD venv has it). Downloads are read as data; scripts run with -I from this folder.
set -euo pipefail
W=$1; PY=$2; H=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$W/myo" "$W/third"
python3 -m pip download myo-sim==0.2.3 --no-deps -d "$W/myo"   # any pip; PY itself may lack pip (uv venv)
(cd "$W/myo" && unzip -q -o myo_sim-0.2.3-py3-none-any.whl)
A="$W/myo/myo_sim/models/arm"
"$PY" -I "$H/filter_hand.py" "$A"
cat > "$A/wrap_hand.xml" <<'XML'
<mujoco model="wrap">
  <include file="assets/myoarm_r_assets.xml"/>
  <worldbody><include file="assets/myoarm_r_chain.xml"/></worldbody>
  <include file="assets/hand_only_tendon.xml"/>
  <include file="assets/hand_only_muscle.xml"/>
</mujoco>
XML
"$PY" -I "$H/myohand_measure.py" "$A/wrap_hand.xml"
"$PY" -I "$H/myohand_torque.py" "$A/wrap_hand.xml"
curl -sS -o "$W/third/mano_mean_meshcoll.urdf" https://raw.githubusercontent.com/christsa/dgrasp/main/rsc/mano/mano_mean_meshcoll.urdf
curl -sS -o "$W/third/eval_model_tmp.xml" https://raw.githubusercontent.com/hu-hy17/HOIC/main/eval_model_tmp.xml
"$PY" -I "$H/probe_dgrasp_hoic.py" "$W/third/mano_mean_meshcoll.urdf" "$W/third/eval_model_tmp.xml"
