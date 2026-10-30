#!/bin/bash
# Object physics study, GPU arm (2026-10-30; owner approved; docs/research/physics-2026-10-30/README.md).
# NVIDIA's public scans as the object meshes (boards and sweeper: their _collision.glb, as the public URDFs use), the
# frozen grasp-lock recipe of the 29 Oct recipe arms (REUSE_REF off: grasp lock, ILC and evolutionary refinement are
# rebuilt under this arm's physics; SF=0: the scans have real undersides), on four public episodes from the stored base
# references of the 24 Oct recipe validation. One box per arm; the arms differ ONLY in the objects' mass, COM, inertia:
#   ARM=S0  placeholder (0.3 kg, shell inertia; make_assets default)        -- control
#   ARM=S1  plausible (docs/research/physics-2026-10-30/props_public_scans.json)
# Scored after inference: sim_vs_ref (our reference) and registered AUC vs mocap (public episodes), NREP evaluations.
#   ops/vast.sh create <offer> <run> 'ARM=S1 bash ops/jobs/physics_arms.sh'
ARM=${ARM:?ARM=S0 or S1}
R=/content/v2d-track3
mkdir -p /content/scanlib
for d in /content/t3/mesh/*/; do
  n=$(basename $d); f=$d/$n.glb; [ -f $f ] || f=$d/${n}_collision.glb
  [ -f $f ] && [ "$n" != wooden_spoon ] && ln -sf $f /content/scanlib/$n.glb
done
echo "[$(date -u +%FT%TZ)] physics_arms ARM $ARM scanlib: $(ls /content/scanlib | tr '\n' ' ')" >> /content/job.log
case $ARM in
  S0) export MA_ARGS= ;;
  S1) export MA_ARGS="--physics $R/docs/research/physics-2026-10-30/props_public_scans.json" ;;
  *) echo "unknown ARM $ARM" >> /content/job.log; exit 1 ;;
esac
export LIB=/content/scanlib SF=0 REUSE_REF=0 REPLAN=0 EVOLVE=1 CURVE_REP=3 NREP=${NREP:-5} SEED=${SEED:-42}
export GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15 --onset_anchor 1"
export PULL_SUB="refs/perc2mck/ep2 refs/perc2mc/ep12 refs/perc2mc/ep18 refs/perc2mc/ep24"
export PAIRS="2:20261024-ev3-2c1e4dd:mck 12:20261024-ev2-2c1e4dd:mc 18:20261024-ev3-2c1e4dd:mc 24:20261024-ev3-2c1e4dd:mc"
bash $R/ops/jobs/glock_public.sh
for c in /content/results/glock_public/ep*/best/policy.safetensors; do
  /content/v2d/robotic_grounding/flash_chord/.venv/bin/python $R/tools/ckpt_meta.py $c
done > /content/results/glock_public/ckpt_meta.txt 2>&1
grep -h mass /content/assets/urdf/*.urdf > /content/results/glock_public/asset_masses.txt 2>&1
