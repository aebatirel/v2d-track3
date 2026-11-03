#!/bin/bash
cd /tmp/claude-0/-home-user-v2d-track3/179e384c-3df3-5902-b468-f503474d35e9/scratchpad
for e in $@; do [ -s srpub/ep$e.json ] && continue; nice -n 5 venv/bin/python -I /home/user/v2d-track3/docs/analysis/ptrk-20261102/scripts/sr_public.py $e tracksT/ep$e/poses_world_vo.npz m14pub t3 kit/v2d_submission_kit srpub/ep$e.json > srpub/ep$e.log 2>&1 && echo OK $e || echo FAIL $e; done
