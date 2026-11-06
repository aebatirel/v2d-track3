#!/bin/bash
# Eval 10's S12 V4p track for the eval-10 retrain (2026-10-31; docs/research/work/perception-sprint-20261031/ev10retrain/
# PREREG.md section 3.1), from ONE input folder with the committed code. GROUND-TRUTH-FREE (eval: none exists): refine.py
# and nest_physics.py check every input path (refine.assert_inference_input). The exact mask10 eval-10 commands
# (perception-sprint-20261031/mask10/eval10/logs/logs_{pre4,phys4,V4p}.log; tools/e11g_tracks.sh arm T):
#   refine.py --steps S12 --s12_mode support                                  -> OUT/pre
#   nest_physics.py --mode inner --pieces meshes/carve/ev10 --hands <hands>   -> OUT/phys   (physics venv, MuJoCo)
#   refine.py --steps S2 --hands <hands_refined> --depth <depth0>             -> OUT/V/ep10 (V4p)
# IN must hold poses.npz, vo.json (eval 10's stored perc2 track), depth0.npy (perc2's own frame-0 depth: det_f0 'depth'
# as float32 repeated 2x2) and hands_refined.npz; like mask10's input folder it has no poses_world_vo.npz. PY runs
# refine.py (numpy, scipy, trimesh, rtree), FPY nest_physics.py (+ mujoco).
# Output: OUT/{pre,phys,V/ep10}, OUT/logs/*.log, OUT/tracks.json (md5 of every poses file, package versions, code sha256,
# S12 window and settle). Exit 1 if a step fails or writes a non-finite pose (refine's checks.finite).
# Usage: e10v_track.sh IN OUT [PY] [FPY]   (defaults: python, /content/v2d/robotic_grounding/flash_chord/.venv/bin/python)
set -u
IN=$1; OUT=$2; PY=${3:-python}; FPY=${4:-/content/v2d/robotic_grounding/flash_chord/.venv/bin/python}
REPO=$(cd "$(dirname "$0")/.." && pwd); PCS=$REPO/meshes/carve/ev10
for f in poses.npz vo.json depth0.npy hands_refined.npz; do
  [ -s $IN/$f ] || { echo "e10v_track: $IN/$f missing" >&2; exit 1; }
done
[ -e $IN/poses_world_vo.npz ] && { echo "e10v_track: $IN/poses_world_vo.npz present (mask10's input had none)" >&2; exit 1; }
mkdir -p $OUT/logs $OUT/V
H=$(readlink -f $IN/hands_refined.npz); D=$(readlink -f $IN/depth0.npy); RF="$PY -I $REPO/pipeline/refine.py"; rc=0
$RF --in $IN --out $OUT/pre --steps S12 --s12_mode support > $OUT/logs/S12.log 2>&1 || { echo "e10v_track: refine S12 FAILED" >&2; rc=1; }
$FPY -I $REPO/tools/nest_physics.py --in $OUT/pre --popt $OUT/pre/pose_opt.json --pieces $PCS --hands $H --mode inner \
  --out $OUT/phys > $OUT/logs/phys.log 2>&1 || { echo "e10v_track: nest_physics FAILED" >&2; rc=1; }
$RF --in $OUT/phys --out $OUT/V/ep10 --steps S2 --hands $H --depth $D > $OUT/logs/S2.log 2>&1 \
  || { echo "e10v_track: refine S2 FAILED" >&2; rc=1; }
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
def popt(d):
    try:
        return json.load(open(f'{d}/pose_opt.json'))
    except Exception:
        return {}
res = dict(inputs={f: md5(os.path.join(inp, f)) for f in ('poses.npz', 'vo.json', 'depth0.npy', 'hands_refined.npz')},
           tracks={'V': {f: md5(f'{out}/V/ep10/{f}') for f in ('poses.npz', 'poses_world_vo.npz')}},
           stages={s: md5(f'{out}/{s}/poses.npz') for s in ('pre', 'phys')},
           finite={'pre': popt(f'{out}/pre').get('checks', {}).get('finite'), 'V': popt(f'{out}/V/ep10').get('checks', {}).get('finite')},
           code={f: sha(os.path.join(repo, f)) for f in ('pipeline/refine.py', 'pipeline/nest.py', 'pipeline/offsetfix.py', 'tools/nest_physics.py')},
           versions=dict(refine_python=vers(py, ['numpy', 'scipy', 'trimesh']), physics_python=vers(fpy, ['numpy', 'scipy', 'trimesh', 'mujoco'])))
try:
    w = popt(f'{out}/pre')['steps']['S12']['windows'][0]
    res['s12'] = {k: w.get(k) for k in ('outer', 'inner', 'start', 'end', 'pre_frame', 'hold_end', 'released_by', 'applied')}
except Exception as e:
    res['s12'] = dict(error=repr(e)[:200])
try:
    res['nest_physics'] = {k: json.load(open(f'{out}/phys/nest_physics.json'))['windows'][0].get(k) for k in ('window', 'frames_settled', 'runs', 'dz_cm')}
except Exception as e:
    res['nest_physics'] = dict(error=repr(e)[:200])
res['ok'] = bool(res['tracks']['V']['poses.npz']) and all(x is True for x in res['finite'].values())
print(json.dumps(res, indent=1))
sys.exit(0 if res['ok'] else 1)
EOF
grep -h "S12 window\|nest_physics inner" $OUT/logs/S12.log $OUT/logs/phys.log | cut -c1-240
exit $rc
