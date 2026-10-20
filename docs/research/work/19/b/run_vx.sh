#!/bin/bash
# usage: run_vx.sh OUTDIR THRESH PREPMODE name [name...]   (W2 input, diagnostic coacd params)
cd /Users/aebatirel/Documents/Code/v2d-research/work/19/b; O=$1; TH=$2; PM=$3; shift 3; mkdir -p $O
for n in "$@"; do [ -f $O/$n.npz ] || ../venv/bin/python b_decomp.py W2/$n.npz $O/$n.npz $TH $PM > logs/${O}_$n.log 2>&1; done
