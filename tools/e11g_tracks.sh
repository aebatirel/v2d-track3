#!/bin/bash
# The two refined ep11 tracks of the ep11 rollout gate (2026-10-31; docs/research/work/perception-sprint-20261031/ep11gate/
# PREREG.md section 2.2), built from ONE input folder with the committed code. GROUND-TRUTH-FREE: refine.py and
# nest_physics.py check every input path (refine.assert_inference_input). These are the exact commands of the mask10
# runs (perception-sprint-20261031/mask10/scripts/m10_run.sh: S2 baseline; runs/Po/posthoc_ep11 logs: V4p):
#   C (control, arm e11c)    refine.py --steps S2
#   T (treatment, arm e11t)  refine.py --steps S12 --s12_mode support                       -> T/pre
#                            nest_physics.py --mode inner --pieces meshes/carve/ev10 --hands  -> T/phys   (FlashCHORD venv, MuJoCo)
#                            refine.py --steps S2 --hands <hands_refined> --depth <depth0>   -> T/ep11 (V4p)
# IN must hold poses.npz, poses_world_vo.npz (the P_o track), depth0.npy (frame 0 of the ep11 depth cache) and
# hands_refined.npz. PY runs refine.py (numpy, scipy, trimesh), FPY runs nest_physics.py (+ mujoco).
# Output: OUT/C/ep11, OUT/T/{pre,phys,ep11}, OUT/logs/*.log, OUT/tracks.json (md5 of every poses file, the python
# package versions, the code sha256). Exit 1 if a step fails or writes a non-finite pose (refine's checks.finite).
# Usage: e11g_tracks.sh IN OUT [PY] [FPY]   (defaults: python, /content/v2d/robotic_grounding/flash_chord/.venv/bin/python)
set -u
IN=$1; OUT=$2; PY=${3:-python}; FPY=${4:-/content/v2d/robotic_grounding/flash_chord/.venv/bin/python}
REPO=$(cd "$(dirname "$0")/.." && pwd); PCS=$REPO/meshes/carve/ev10
for f in poses.npz poses_world_vo.npz depth0.npy hands_refined.npz; do
  [ -s $IN/$f ] || { echo "e11g_tracks: $IN/$f missing" >&2; exit 1; }
done
mkdir -p $OUT/logs $OUT/C $OUT/T
H=$(readlink -f $IN/hands_refined.npz); D=$(readlink -f $IN/depth0.npy); RF="$PY -I $REPO/pipeline/refine.py"; rc=0
$RF --in $IN --out $OUT/C/ep11 --steps S2 > $OUT/logs/C_S2.log 2>&1 || { echo "e11g_tracks: C refine S2 FAILED" >&2; rc=1; }
$RF --in $IN --out $OUT/T/pre --steps S12 --s12_mode support > $OUT/logs/T_S12.log 2>&1 || { echo "e11g_tracks: T refine S12 FAILED" >&2; rc=1; }
$FPY -I $REPO/tools/nest_physics.py --in $OUT/T/pre --popt $OUT/T/pre/pose_opt.json --pieces $PCS --hands $H --mode inner \
  --out $OUT/T/phys > $OUT/logs/T_phys.log 2>&1 || { echo "e11g_tracks: T nest_physics FAILED" >&2; rc=1; }
$RF --in $OUT/T/phys --out $OUT/T/ep11 --steps S2 --hands $H --depth $D > $OUT/logs/T_S2.log 2>&1 \
  || { echo "e11g_tracks: T refine S2 FAILED" >&2; rc=1; }
$PY -I - "$OUT" "$IN" "$REPO" "$PY" "$FPY" << 'EOF' > $OUT/tracks.json || rc=1
import hashlib, json, os, subprocess, sys
out, inp, repo, py, fpy = sys.argv[1:6]
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else None
sha = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else None
def vers(p, mods):
    c = 'import importlib, json; print(json.dumps({m: getattr(importlib.import_module(m), "__version__", "?") for m in %r}))' % (mods,)
    try:
        return json.loads(subprocess.run([p, '-I', '-c', c], capture_output=True, text=True, timeout=300).stdout.strip().splitlines()[-1])
    except Exception as e:
        return dict(error=repr(e)[:200])
def finite(d):
    try:
        return json.load(open(f'{d}/pose_opt.json'))['checks']['finite']
    except Exception:
        return None
res = dict(inputs={f: md5(os.path.join(inp, f)) for f in ('poses.npz', 'poses_world_vo.npz', 'depth0.npy', 'hands_refined.npz')},
           tracks={a: {f: md5(f'{out}/{a}/ep11/{f}') for f in ('poses.npz', 'poses_world_vo.npz')} for a in 'CT'},
           T_stages={s: md5(f'{out}/T/{s}/poses.npz') for s in ('pre', 'phys')},
           finite={'C': finite(f'{out}/C/ep11'), 'T_pre': finite(f'{out}/T/pre'), 'T': finite(f'{out}/T/ep11')},
           code={f: sha(os.path.join(repo, f)) for f in ('pipeline/refine.py', 'pipeline/nest.py', 'pipeline/offsetfix.py', 'tools/nest_physics.py')},
           versions=dict(refine_python=vers(py, ['numpy', 'scipy', 'trimesh']), physics_python=vers(fpy, ['numpy', 'scipy', 'trimesh', 'mujoco'])))
try:
    res['nest_physics'] = {k: json.load(open(f'{out}/T/phys/nest_physics.json'))['windows'][0].get(k) for k in ('window', 'frames_settled', 'runs', 'dz_cm')}
except Exception as e:
    res['nest_physics'] = dict(error=repr(e)[:200])
res['ok'] = all(v.get('poses.npz') for v in res['tracks'].values()) and all(x is True for x in res['finite'].values())
print(json.dumps(res, indent=1))
sys.exit(0 if res['ok'] else 1)
EOF
grep -h "S12 window\|nest_physics inner" $OUT/logs/T_S12.log $OUT/logs/T_phys.log | cut -c1-240
exit $rc
