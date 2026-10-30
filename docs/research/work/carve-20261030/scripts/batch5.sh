#!/bin/bash
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve; RS=$S/scripts/run_settle.sh; D=$S/assets/v3_def
$RS E30 $D 242,0 E30_def; $RS E30 $S/assets/E30_cut 242,0 E30_cut; $RS P31mck $D 269,0 P31mck_def; $RS P31mck $S/assets/P31mck_cut 269,0 P31mck_cut
echo SETTLE5_DONE
