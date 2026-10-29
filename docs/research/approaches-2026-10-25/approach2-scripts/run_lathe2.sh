L=/home/user/v2d-track3/meshes; PY=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/venv/bin/python
cd /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/approach2
for a in blue_cup=$L/library_v3/blue_cup.glb beige_cup_v3=$L/library_v3/beige_cup.glb beige_cup_v3x=$L/library_v3x/beige_cup.glb white_pot=$L/library_v3/white_pot.glb white_pot_lid=$L/library_v3/white_pot_lid.glb water_pitcher=$L/library_v3/water_pitcher.glb; do
  n=${a%%=*}; p=${a#*=}; $PY lathe_fit2.py $n $p out/lathe2/$n > out/lathe2/$n.log 2>&1 &
done; wait; echo done
