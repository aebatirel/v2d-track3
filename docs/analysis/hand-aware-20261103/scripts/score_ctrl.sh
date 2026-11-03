#!/bin/bash
cd /home/user/work; . venv/bin/activate; M=m14p/meshes/m14p_public; mkdir -p ho
for e in 2 12 22 23 24 26 27 31 39 40 42 44 45; do for c in C Cr; do
  python score_registered.py $e ctrlC/$c/ep$e/poses_world_vo.npz --meshes $M --t3 t3 --kit kit/v2d_submission_kit --reg_seeds 10 --scores_only --out ho/${c}_ep$e.json > /dev/null 2>&1 || echo "FAIL $c $e"
done; done; echo CTRL-DONE
