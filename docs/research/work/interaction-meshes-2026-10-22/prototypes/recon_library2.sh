#!/bin/bash
# Own-mesh library v1 (2026-10-21, A-lite): each object fused over the public episodes where our tracking holds.
# Lines: object | episodes | extra recon_mesh args. Depth caches are fetched as needed and dropped when no later
# object needs them (disk). Output: /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/library/<obj>.glb (+ .json, .log, _full.glb).
PY=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/venv/bin/python; OUT=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/library; mkdir -p $OUT
MAN=$(cat "$1")
need_later() { echo "$MAN" | sed -n "$(($1 + 1)),\$p" | cut -d'|' -f2 | tr ' ' '\n' | grep -qx "$2"; }
objs_of() { $PY -I -c "import numpy as np; print(' '.join(k[6:] for k in np.load('/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/perc/ep$1/poses.npz').files if k.startswith('cam_T_')))"; }
i=0
echo "$MAN" | while IFS='|' read -r obj eps extra; do
  i=$((i + 1)); P=""; D=""; H=""; O=""; k=0
  for e in $eps; do
    mkdir -p /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/depth/ep$e
    [ -s /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/depth/ep$e/depths_fs0.5.npy ] || curl -sSfL -o /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/depth/ep$e/depths_fs0.5.npy https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main/cache/depth/public/ep$e/depths_fs0.5.npy || echo "depth ep$e download failed"
    oth=""; for o in $(objs_of $e); do [ $o = $obj ] && continue; f=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/t3/mesh/$o/$o.glb; [ -s $f ] || f=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/t3/mesh/$o/${o}_visual.glb; oth="${oth:+$oth,}$o=$f"; done
    P="${P:+$P,}/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/perc/ep$e/poses.npz"; D="${D:+$D,}/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/depth/ep$e/depths_fs0.5.npy"; H="${H:+$H,}/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/refs/ep$e/hands.npz"; if [ $k -eq 0 ]; then O="$oth"; else O="$O;$oth"; fi; k=$((k + 1))
  done
  t0=$(date +%s)
  $PY -I /home/user/v2d-track3/pipeline/recon_mesh.py --poses "$P" --depth "$D" --hands "$H" --others "$O" --calib /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/t3/calib.json --obj $obj --out $OUT/$obj.glb --kit /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/kit/v2d_submission_kit --stride 2 $extra > $OUT/$obj.log 2>&1 < /dev/null     && echo "$obj (eps $eps) done in $(($(date +%s) - t0)) s: $(tail -1 $OUT/$obj.log | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d["extents_cm"], d["closing"], d["unknown_share"])' 2>/dev/null)"     || echo "$obj FAILED: $(tail -2 $OUT/$obj.log)"
  for e in $eps; do need_later $i $e || rm -f /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/depth/ep$e/depths_fs0.5.npy; done
done
echo "LIBRARY-DONE $1"
