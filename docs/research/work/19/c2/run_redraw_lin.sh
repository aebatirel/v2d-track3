#!/bin/zsh
# Linux aarch64 (docker) exact calls on the re-draw inputs; PYTHONPATH carries numpy + coacd (manylinux wheels).
W=/Users/aebatirel/Documents/Code/v2d-research/work/19
cd $W; mkdir -p c2/rd/lin
for f in c2/rd/*.npz; do
  b=$(basename $f)
  [ -f c2/rd/lin/$b ] && continue
  docker run --rm --platform linux/arm64 -e PYTHONPATH=/w/c/xplat/lib_arm64 -v $W:/w python:3.12-slim-bookworm python /w/c/c_lincoacd.py /w/c2/rd/$b /w/c2/rd/lin/$b >> c2/logs/redraw_lin.log 2>&1
done
echo done > c2/logs/redraw_lin.done
