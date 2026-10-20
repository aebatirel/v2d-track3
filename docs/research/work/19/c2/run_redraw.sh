#!/bin/zsh
# macOS exact calls, then Linux aarch64 (docker) exact calls on the same inputs. Logs in c2/logs/.
W=/Users/aebatirel/Documents/Code/v2d-research/work/19
cd $W
venv/bin/python c2/c2_redraw.py run > c2/logs/redraw_mac.log 2>&1
mkdir -p c2/rd/lin
for f in c2/rd/*.npz; do
  b=$(basename $f)
  [ -f c2/rd/lin/$b ] && continue
  docker run --rm --platform linux/arm64 -v $W:/w python:3.12-slim-bookworm python /w/c/c_lincoacd.py /w/c2/rd/$b /w/c2/rd/lin/$b /w/c/xplat/lib_arm64 >> c2/logs/redraw_lin.log 2>&1
done
echo done > c2/logs/redraw.done
