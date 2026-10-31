#!/bin/bash
# CPU mock of the masses eval retrain (2026-10-31; ops/jobs/mass_eval.sh + the pack side, h5_reeval.sh / pack_eval.sh).
# usage: setup.sh MS [REPO_SRC]   (REPO_SRC default: the working tree)
# Layout: MS/store = ONE fake HF store shared by every box; MS/tmpl = a box template (repo copy with /content -> the box's
# /content, kit, FlashCHORD dirs, stub programs); newbox.sh makes MS/box from it for each box in turn, so every box sees a
# fresh /content at the SAME path (as the real boxes do) and the boxes talk only through the store.
# Real: every ops/ and tools/ script, make_assets.py, mass_arm.py, mass_eval_verify.py, mass_pack_check.py, no_oracle.py,
# store.sh. Stubs (stub.py): FlashCHORD trainer and evaluators, the kit evaluator and packer, qa, renders (see stub.py).
# Fake store, from local copies of real files (scratchpad; nothing downloaded here):
#   - the 20 packed reference parquets (pack 6's box copies) and their packed checkpoints (headers: real saved configs);
#   - pack 6's and c33B's submitted rollouts (KEEP_RESULTS), pack 7's summary values;
#   - eval 1's real refs/perc2mck/ep1 processed parquet (c01s43's pull of pack-31ef267);
#   - SYNTHETIC (the real files are not on this machine): every refs/sf/ep<N>/assets (make_assets.py, 0.3 kg, the
#     episode's library), the grasp-lock base folders refs/perc2mck/ep<N> (the glockt parquet with /content/assets URDF
#     paths, a stage .usda, hands), perc2/ep1/poses.npz, results/glock_public/ep<N>/{rest_check.json, ...}.
# Parquet asset paths are rewritten /content/ -> MS/box/content/ (the fingerprint ignores them, the md5 changes): the
# mock's copy of packed_refs.json carries the md5 of the rewritten files; its fingerprints stay the real ones, and
# setup asserts every rewritten reference still has its real fingerprint.
set -e
MS=$1; R=${2:-/home/user/v2d-track3}; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
M=$(cd $(dirname $0) && pwd); PY=$S/map/scoring/venv/bin/python; B=$MS/box
D6=$S/daudit/dl_evrefs/runs/20261026-pack6-5203d42/refs; CK=$S/e1conf/dl_ck/runs
rm -rf "${MS:?}"; mkdir -p $MS/store/runs $MS/tmpl
TP=$MS/tmpl; TC=$TP/content; mkdir -p $TP/bin $TC/v2d-track3/meshes $TC/v2d-track3/docs/research/work $TC/v2d-track3/results/submissions
for d in ops pipeline tools flashchord_conf; do cp -r $R/$d $TC/v2d-track3/; done
for d in library_v3 library_v3x carve; do cp -r $R/meshes/$d $TC/v2d-track3/meshes/; done
cp -r $R/docs/research/physics-2026-10-30 $TC/v2d-track3/docs/research/
mkdir -p $TC/v2d-track3/docs/research/work/masses-eval-20261031
cp $R/docs/research/work/masses-eval-20261031/packed_refs.json $TC/v2d-track3/docs/research/work/masses-eval-20261031/
for p in 20261030-track3g-candidate 20261026-track3f; do mkdir -p $TC/v2d-track3/results/submissions/$p; cp $R/results/submissions/$p/summary.txt $TC/v2d-track3/results/submissions/$p/; done
find $TC/v2d-track3 \( -name '*.sh' -o -name '*.py' \) -exec sed -i "s#/content#$B/content#g" {} +
FC=$TC/v2d/robotic_grounding/flash_chord; mkdir -p $FC/.venv/bin $FC/scripts $FC/src/flash_chord/configs/embodiment
mkdir -p $TC/v2d_clean/robotic_grounding/flash_chord $TC/kit/v2d_submission_kit/{data,examples,tools,flash_chord/scripts}
cp $S/pack7_verify_prov/kitzip/v2d_submission_kit/data/track_3_evaluation_objects.json $TC/kit/v2d_submission_kit/data/
touch $TC/kit/v2d_submission_kit/examples/run_policy_evaluation.py $TC/kit/v2d_submission_kit/tools/pack_submission.py \
      $TC/kit/v2d_submission_kit/flash_chord/scripts/evaluate_policy.py $FC/scripts/{train_flash_sac,evaluate_policy,view_policy}.py
w() { printf '#!/bin/bash\nexec %s -I %s/stub.py %s "$@"\n' $PY $M $2 > $1; chmod +x $1; }
w $TP/bin/python main; w $TP/bin/python3 main; w $FC/.venv/bin/python fc
printf '#!/bin/bash\nexec %s -I %s/hfstub.py "$@"\n' $PY $M > $TP/bin/hf
printf '#!/bin/bash\necho "{}"\n' > $TP/bin/curl
printf '#!/bin/bash\nexit 0\n' > $TP/bin/pip
printf '#!/bin/bash\necho mocksha0000000\n' > $TP/bin/git
chmod +x $TP/bin/*
# templates for the stub trainer: the REAL saved configs of a packed grasp-lock (evb1420 ep20) and standard-learner
# (std30 ep30) checkpoint; pack 7's packed draws for real kept rollouts
mkdir -p $TP/templates
$PY -I - $CK/20261025-evb1420-ee7ba8e/results/final_eval/ep20/policy.safetensors $CK/20261025-std30-ee7ba8e/results/final_eval/ep30/policy.safetensors $TP/templates << 'EOF'
import json, struct, sys
for f, k in ((sys.argv[1], 'glock'), (sys.argv[2], 'std')):
    with open(f, 'rb') as fh:
        n = struct.unpack('<Q', fh.read(8))[0]; h = json.loads(fh.read(n))
    json.dump(json.loads(h['__metadata__']['user.resolved_config_json']), open(f'{sys.argv[3]}/{k}.json', 'w'))
EOF
head -1 $R/results/submissions/20261030-track3g-candidate/summary.txt > $TP/packed7.json

# ---------------- fake store ----------------
ST=$MS/store/runs
rw() {  # $1 src parquet, $2 dst parquet, $3 optional: replace the URDF root by /content/assets (synthetic base reference)
  mkdir -p $(dirname $2)
  $PY -I - "$1" "$2" "$B" "${3:-}" << 'PYEOF'
import sys, pyarrow as pa, pyarrow.parquet as pq
src, dst, B, base = sys.argv[1:5]; t = pq.read_table(src)
for c in ('object_urdf_paths', 'object_mesh_paths'):
    if c in t.column_names:
        v = t.column(c)[0].as_py()
        if base and c == 'object_urdf_paths':
            v = ['/content/assets/urdf/' + p.rsplit('/', 1)[1] for p in v]
        v = [p.replace('/content/', B + '/content/', 1) for p in v]
        t = t.set_column(t.column_names.index(c), c, pa.array([v], type=t.schema.field(c).type))
pq.write_table(t, dst)
PYEOF
}
synth_np() {  # $1 dir: hands.npz, hands_refined.npz, a stage .usda (contents unused by the mock)
  mkdir -p $1/reconstructed_stage; $PY -I -c "import numpy as np, sys; np.savez(sys.argv[1] + '/hands.npz', mock=np.zeros(1)); np.savez(sys.argv[1] + '/hands_refined.npz', mock=np.zeros(1))" $1
  echo '#usda 1.0 (mock stage)' > $1/reconstructed_stage/stage.usda
}
TAB=$R/docs/research/work/masses-eval-20261031/packed_refs.json
tabv() { $PY -I -c "import json, sys; v = json.load(open(sys.argv[1]))['episodes'][sys.argv[2]][sys.argv[3]]; print(' '.join(v) if isinstance(v, list) else v)" $TAB $1 $2; }
# grasp-lock episodes: glockt (real) + sf assets + base (synthetic) + result files, in the episode's source run
for e in 3 5 6 8 10 14 15 16 20 32 33 35 36 37 38; do
  src=$(tabv $e source_run); lib=$(tabv $e lib); root=$(tabv $e asset_root); X=$ST/$src
  f=$(ls $D6/glockt/ep$e/processed/*/*/ref_gl_ilc.parquet); hive=$(dirname ${f#$D6/glockt/ep$e/})
  rw $f $X/refs/glockt/ep$e/$hive/ref_gl_ilc.parquet; mkdir -p $X/refs/glockt/ep$e/reconstructed_stage
  echo '#usda 1.0 (mock stage)' > $X/refs/glockt/ep$e/reconstructed_stage/stage.usda
  rw $f $X/refs/perc2mck/ep$e/$hive/base$e-0.parquet base; synth_np $X/refs/perc2mck/ep$e
  if [ "$root" != /content/assets ]; then
    mkdir -p $X/refs/sf/ep$e; $PY -I $TC/v2d-track3/pipeline/make_assets.py $R/meshes/$lib $X/refs/sf/ep$e/assets > /dev/null
  fi
  mkdir -p $X/results/glock_public/ep$e
  echo '{"ok": true, "mock": "synthetic rest check (the real file is in the store)"}' > $X/results/glock_public/ep$e/rest_check.json
  echo 'zero_action: 0.6100 (mock)' > $X/results/glock_public/ep$e/zero_score.txt
  [ $e = 10 ] || echo '{"objects": {}, "mock": 1}' > $X/results/glock_public/ep$e/support_fill.json
done
# eval 1 (standard learner): the real base parquet + synthetic hands / perception
X=$ST/20261024-pack-31ef267; f=$(ls $S/e1conf/dl_c01s43/runs/20261030-c01s43-328139c/refs/perc2mck/ep1/processed/*/*/*.parquet)
rw $f $X/refs/perc2mck/ep1/${f#*/refs/perc2mck/ep1/}; synth_np $X/refs/perc2mck/ep1
mkdir -p $X/perc2/ep1; $PY -I -c "import numpy as np, sys; np.savez(sys.argv[1], world_T_cam=np.tile(np.eye(4), (335, 1, 1)))" $X/perc2/ep1/poses.npz
echo 'mock perception log' > $X/perc2/ep1/log.txt
# packed standard-learner references (refs/perc2mcks, what their checkpoints name) in the runs h5_reeval.sh pulls
for x in 1:20261025-std0116-ee7ba8e 19:20261025-std1928-ee7ba8e 28:20261025-std1928-ee7ba8e 30:20261025-std30-ee7ba8e 25:20261026-c25s42-feb0407; do
  e=${x%%:*}; f=$(ls $D6/perc2mcks/ep$e/processed/*/*/*.parquet); rw $f $ST/${x#*:}/refs/perc2mcks/ep$e/${f#$D6/perc2mcks/ep$e/}
done
# packed checkpoints (real files) at their store paths, the eval-1 recipe checkpoint, the h5 picks
for f in $(cd $CK && find . -name '*.safetensors' | sed 's#^\./##'); do
  mkdir -p $(dirname $ST/$f); cp $CK/$f $ST/$f
done
# pack-31ef267 holds a 24 Oct grasp-lock checkpoint for every roster episode (pack_eval.sh needs all 20 before PICK);
# those the h5 PICK replaces are synthetic placeholders here (never evaluated: replaced, then kept or picked)
for e in 1 3 5 8 10 14 15 16 19 20 25 28 30 32 33; do
  d=$ST/20261024-pack-31ef267/results/glock_public/ep$e/best; mkdir -p $d
  $PY -I -c "import json, struct, sys; h = json.dumps({'__metadata__': {'user.resolved_config_json': '{}', 'mock': 'placeholder, replaced by PICK'}}).encode(); open(sys.argv[1], 'wb').write(struct.pack('<Q', len(h)) + h)" $d/policy.safetensors
done
mkdir -p $ST/20261025-std0116-ee7ba8e/results/final_eval/ep1 $ST/20261026-fr3233s43-6a8a0e2/results/glock_public/ep33/best
cp $S/e1conf/dl_std0116ck/runs/20261025-std0116-ee7ba8e/results/final_eval/ep1/policy.safetensors $ST/20261025-std0116-ee7ba8e/results/final_eval/ep1/
cp $S/e1conf/dlv_fr3233s43/runs/20261026-fr3233s43-6a8a0e2/results/glock_public/ep33/best/policy.safetensors $ST/20261026-fr3233s43-6a8a0e2/results/glock_public/ep33/best/
# kept official rollouts (KEEP_RESULTS): pack 6 and c33B
for x in dl_keep/runs/20261026-pack6-5203d42 dl_keep/runs/20261030-c33B-0202139; do
  d=$ST/$(basename $x)/results/submission/results; mkdir -p $d; cp $S/e1conf/$x/results/submission/results/episode_* $d/
done
# the mock's table: md5 of the rewritten parquets, fingerprints asserted equal to the real ones
$PY -I - $TAB $ST $TC/v2d-track3/docs/research/work/masses-eval-20261031/packed_refs.json $TC/v2d-track3/tools << 'EOF'
import glob, json, sys
tab, st, out, tools = sys.argv[1:5]; sys.path.insert(0, tools)
from mass_arm import md5, traj_fingerprint
import pyarrow.parquet as pq
T = json.load(open(tab)); bad = []
for e, x in T['episodes'].items():
    sub = f'refs/glockt/ep{e}' if x['mode'] == 'glock' else f'refs/perc2mck/ep{e}'
    fs = glob.glob(f'{st}/{x["source_run"]}/{sub}/processed/*/*/*.parquet')
    if len(fs) != 1:
        continue
    if traj_fingerprint(pq.read_table(fs[0])) != x['traj_fingerprint']:
        bad.append(e)
    x['md5_real'] = x['md5']; x['md5'] = md5(fs[0])
json.dump(T, open(out, 'w'), indent=1)
print('mock table: md5 of the rewritten references for', sorted([e for e, x in T['episodes'].items() if 'md5_real' in x], key=int),
      '; real fingerprints', 'ALL MATCH' if not bad else f'MISMATCH {bad}')
sys.exit(1 if bad else 0)
EOF
echo "export PATH=$B/bin:\$PATH HF_STORE=mock/store MOCK_MR=$B MOCK_PY=$PY" > $TP/env.sh
echo "mock store at $MS/store ($(du -sh $MS/store | cut -f1)), box template $TP"
