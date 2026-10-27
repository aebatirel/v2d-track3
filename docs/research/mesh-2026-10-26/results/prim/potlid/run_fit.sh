#!/bin/bash
# Fit every (episode x variant) candidate of family A (prim_potlid.py). Waits for obs_all files from prep_obs.sh.
SCR=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
S=/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts
O=$SCR/prim/potlid; LIB=/home/user/v2d-track3/meshes/library_v3
cd $SCR
run() {  # obj objname ep
  local obj=$1 name=$2 e=$3 f=$SCR/obs_all/ep${3}_$2.npz
  until [ -f $f ] || grep -q PREP-DONE $SCR/obs_all/prep.log; do sleep 20; done
  sleep 5
  [ -f $f ] || { echo "ep$e $name: no obs"; return; }
  for v in fit nostem tsdf thick; do
    out=$O/cand/${name}_ep${e}_$v.glb
    [ -f $out ] && continue
    venv/bin/python -W ignore $S/prim_potlid.py $obj $f $out --variant $v --lib $LIB/$name.glb \
      --axis_cache $O/axis/ep${e}_$name.json > $O/cand/${name}_ep${e}_$v.log 2>&1 \
      && echo "OK ep$e $name $v $(grep -c . $O/cand/${name}_ep${e}_$v.log)" || echo "FAIL ep$e $name $v: $(grep -v -i 'plugin\|libOpenGL' $O/cand/${name}_ep${e}_$v.log | grep . | tail -1)"
  done
}
for e in 2 0; do run lid white_pot_lid $e; done
for e in 41 2 26 44 42 43 45 27; do run pot white_pot $e; done
echo FIT-DONE
