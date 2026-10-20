#!/bin/sh
# waits for the stride-5 reloc batch, then runs VO v2 (ray-exact, unmasked) on all 20 eval clips, 3 workers
cd /Users/aebatirel/Documents/Code/v2d-research/work/18
while kill -0 $(cat c1log/batch_s5.pid) 2>/dev/null; do sleep 10; done
for e in 35 36 25 33 1 3 5 30 38 32 6 19 28 8 20 16 15 10 14 37; do echo $e; done | xargs -P 3 -I{} sh -c "perl -e 'alarm 1200; exec @ARGV' ../../venv/bin/python b3_vo.py evaluation {} c3/vo_e{}.json 0 > c1log/vo_e{}.log 2>&1"
echo VO_DONE
