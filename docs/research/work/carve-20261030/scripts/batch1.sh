#!/bin/bash
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve; R=/home/user/v2d-track3/meshes/carve; T=$S/twins
P=$S/scripts/run_place.sh
$P E14 plastic_dish_rack blue_cup $R/ev14
( $P E30 plastic_dish_rack mini_sweeper $R/ev30; $P E28 plastic_dish_rack white_pot $R/ev28; $P P12gl plastic_dish_rack blue_cup $T/P12gl; $P P26mck plastic_dish_rack white_pot $T/P26mck ) &
( $P E1 white_pot white_pot_lid $R/ev01; $P P31mck plastic_dish_rack mini_sweeper $T/P31mck; $P P2mck white_pot white_pot_lid $T/P2mck; $P P0 white_pot white_pot_lid $T/P0 ) &
wait; echo PLACE_ALL_DONE
