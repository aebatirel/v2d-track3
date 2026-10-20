#!/bin/bash
# V1 = W2 remesh (h 1 mm, delta 0.3, shell 3 mm, passes CoACD manifold check) -> exact FlashCHORD call
cd /Users/aebatirel/Documents/Code/v2d-research/work/19/b
for n in "$@"; do [ -f V1/$n.npz ] || ../venv/bin/python b_decomp.py W2/$n.npz V1/$n.npz > logs/V1_$n.log 2>&1; done
