#!/bin/bash
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve; RS=$S/scripts/run_settle.sh; D=$S/assets/v3_def
( $RS E28 $D 206,0 E28_def; $RS E28 $S/assets/E28_cut 206,0 E28_cut ) &
( $RS E1 $D 305,0 E1_def; $RS E1 $S/assets/E1_cut 305,0 E1_cut ) &
wait; echo SETTLE2_DONE
