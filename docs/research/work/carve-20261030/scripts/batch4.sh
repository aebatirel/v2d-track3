#!/bin/bash
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve; RS=$S/scripts/run_settle.sh; D=$S/assets/v3_def
P12A=$(grep "^P12gl " $S/cases.txt | cut -d' ' -f3)
( $RS P12gl $P12A 170 P12gl_def; $RS P12gl $S/assets/P12gl_cut 170 P12gl_cut; $RS P26mck $D 35,0 P26mck_def ) &
( $RS P26mck $S/assets/P26mck_cut 35,0 P26mck_cut; $RS P2mck $D 334,0 P2mck_def; $RS P2mck $S/assets/P2mck_cut 334,0 P2mck_cut ) &
wait; echo SETTLE4_DONE
