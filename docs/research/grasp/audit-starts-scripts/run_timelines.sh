#!/bin/bash
cd /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
P=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/venv/bin/python
$P -I scripts/start_timeline.py 21 zero ref_gl_ilc 60 > out/tl_ep21_zero.txt 2>&1
$P -I scripts/start_timeline.py 21 zero_r1 ref_gl_r1_ilc 60 > out/tl_ep21_zero_r1.txt 2>&1
$P -I scripts/start_timeline.py 2 zero ref_gl_ilc 120 > out/tl_ep2_zero.txt 2>&1
$P -I scripts/start_timeline.py 2 zero_r1 ref_gl_r1_ilc 120 > out/tl_ep2_zero_r1.txt 2>&1
$P -I scripts/start_timeline.py 26 zero_r1 ref_gl_r1_ilc 80 > out/tl_ep26_zero_r1.txt 2>&1
$P -I scripts/start_timeline.py 26 zero ref_gl_ilc 80 > out/tl_ep26_zero.txt 2>&1
echo DONE > out/tl_done
