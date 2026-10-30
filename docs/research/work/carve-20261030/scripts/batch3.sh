#!/bin/bash
# v2 rest thresholds for the sweeper cases (thin object, reference angular jitter 1.5-2.7 deg/frame at world rest)
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve; P=$S/scripts/run_place.sh
until grep -q PLACE_ALL_DONE $S/blogs/batch1.log; do sleep 10; done
LOGTAG=E30_v2 $P E30 plastic_dish_rack mini_sweeper /home/user/v2d-track3/meshes/carve/ev30 --rest_cm 0.25 --rest_deg 3.0 &
LOGTAG=P31mck_v2 $P P31mck plastic_dish_rack mini_sweeper $S/twins/P31mck --rest_cm 0.25 --rest_deg 3.0 &
wait; echo V2_DONE
