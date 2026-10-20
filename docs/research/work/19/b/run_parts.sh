#!/bin/bash
# usage: run_parts.sh LMAX name [name...]  -> V4_<LMAX>/<name>.npz
cd /Users/aebatirel/Documents/Code/v2d-research/work/19/b; L=$1; shift
for n in "$@"; do [ -f V4_$L/$n.npz ] || ../venv/bin/python b_decomp_parts.py S$L/$n $n V4_$L > logs/V4_${L}_$n.log 2>&1; done
