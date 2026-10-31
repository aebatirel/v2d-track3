#!/bin/bash
# CPU mock of the pack 9b D arm (2026-10-31; ops/jobs/mass_eval.sh ARM=dr + the confirmation, h5_reeval.sh / pack_eval.sh
# DR_EPS), built on the masses eval-retrain mock (masses-eval-20261031/cpu/mock/setup.sh, unchanged in substance).
# D additions: the template's FlashCHORD tree gets a stand-in src/flash_chord/lifecycle/reset.py holding the anchors the
# ported ops/box/patch_flashchord_dr.py checks (the patch runs for real on it, stub.py); eval 25 / 30 base references
# (refs/perc2mck/ep<N> in c25s42 / std30: the real packed perc2mcks file, of which it is a byte copy) and synthetic
# perception; MR/templates/rollout_ep<N>.parquet = the REAL packed rollouts of 14 / 16 / 25 / 30 (pack 6) and 33 (c33B)
# for the kit stub; the packed policy's H5p7 set runs/20261031-h5p7-1a7cdff/results/h5/r1..r10/ep<N>/ (perturbed copies
# of those real rollouts naming the packed sha256, stub.py mkdraw). Mock scores are synthetic.
# --- masses mock header follows ---
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
# 2026-10-31 (review F7): within every sub-folder a training box pulls, the store holds exactly the files of the table's
# pull_files (the 29 Oct store listing): the real file names; files the mock has no stand-in for are placeholders
# (stage .usda per episode, identical in refs/glockt and refs/perc2mck as on the real store [H]; .parquet = a copy of
# the episode's base parquet; .npz / .json / other small stand-ins), and unlisted synthetic files there are removed.
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
FC=$TC/v2d/robotic_grounding/flash_chord; mkdir -p $FC/.venv/bin $FC/scripts $FC/src/flash_chord/configs/embodiment $FC/src/flash_chord/lifecycle
cat > $FC/src/flash_chord/lifecycle/reset.py << 'RSEOF'
"""stand-in for FlashCHORD lifecycle/reset.py (pack 9b CPU mock): only the anchors ops/box/patch_flashchord_dr.py checks"""
import warp as wp
import newton


class ReferenceResetTable:
    pass


class ReferenceReset:
    def sample(self, reset_mask, curriculum_voc_scale):
        pass

    def prepare_explicit(self, reset_mask, curriculum_voc_scale):
        pass


def reset_worlds(model, table, state, reset_mask=None):
    pass
RSEOF
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
# pack 9b: the real packed rollouts of the five D episodes (kit stub templates)
for e in 14 16 25 30 33; do
  src=20261026-pack6-5203d42; [ $e = 33 ] && src=20261030-c33B-0202139
  cp $S/e1conf/dl_keep/runs/$src/results/submission/results/episode_$(printf %06d $e).parquet $TP/templates/rollout_ep$e.parquet
done

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
synth_np() {  # $1 dir, $2 episode: hands.npz, hands_refined.npz, the episode's support stage (real name, mock content)
  mkdir -p $1/reconstructed_stage; $PY -I -c "import numpy as np, sys; np.savez(sys.argv[1] + '/hands.npz', mock=np.zeros(1)); np.savez(sys.argv[1] + '/hands_refined.npz', mock=np.zeros(1))" $1
  stage $1 $2
}
stage() { mkdir -p $1/reconstructed_stage; echo "#usda 1.0 (mock support stage, eval $2)" > $1/reconstructed_stage/$(printf 't3_ep%03d' $2)_support.usda; }
TAB=$R/docs/research/work/masses-eval-20261031/packed_refs.json
tabv() { $PY -I -c "import json, sys; v = json.load(open(sys.argv[1]))['episodes'][sys.argv[2]][sys.argv[3]]; print(' '.join(v) if isinstance(v, list) else v)" $TAB $1 $2; }
listed() {  # $1 episode, $2 sub-folder prefix: that listed file, relative to the prefix (e.g. the base parquet's real name)
  $PY -I -c "import json, sys; x = json.load(open(sys.argv[1]))['episodes'][sys.argv[2]]; p = 'runs/' + x['source_run'] + '/' + sys.argv[3]; print([f[len(p):] for f in x['pull_files'] if f.startswith(p)][0])" $TAB $1 "$2"
}
# grasp-lock episodes: glockt (real) + sf assets + base (synthetic) + result files, in the episode's source run
for e in 3 5 6 8 10 14 15 16 20 32 33 35 36 37 38; do
  src=$(tabv $e source_run); lib=$(tabv $e lib); root=$(tabv $e asset_root); X=$ST/$src
  f=$(ls $D6/glockt/ep$e/processed/*/*/ref_gl_ilc.parquet); hive=$(dirname ${f#$D6/glockt/ep$e/})
  rw $f $X/refs/glockt/ep$e/$hive/ref_gl_ilc.parquet; stage $X/refs/glockt/ep$e $e
  rw $f $X/refs/perc2mck/ep$e/processed/$(listed $e refs/perc2mck/ep$e/processed/) base; synth_np $X/refs/perc2mck/ep$e $e
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
rw $f $X/refs/perc2mck/ep1/${f#*/refs/perc2mck/ep1/}; synth_np $X/refs/perc2mck/ep1 1
mkdir -p $X/perc2/ep1; $PY -I -c "import numpy as np, sys; np.savez(sys.argv[1], world_T_cam=np.tile(np.eye(4), (335, 1, 1)))" $X/perc2/ep1/poses.npz
echo 'mock perception log' > $X/perc2/ep1/log.txt
# pack 9b: eval 25 / 30 base references (the real packed perc2mcks file, of which the pulled perc2mck one is a byte copy)
# + synthetic hands and perception, in the table's source runs
for x in 25:20261026-c25s42-feb0407 30:20261025-std30-ee7ba8e; do
  e=${x%%:*}; X=$ST/${x#*:}; f=$(ls $D6/perc2mcks/ep$e/processed/*/*/*.parquet)
  rw $f $X/refs/perc2mck/ep$e/processed/$(listed $e refs/perc2mck/ep$e/processed/); synth_np $X/refs/perc2mck/ep$e $e
  mkdir -p $X/perc2/ep$e; $PY -I -c "import numpy as np, sys; np.savez(sys.argv[1], world_T_cam=np.tile(np.eye(4), (400, 1, 1)))" $X/perc2/ep$e/poses.npz
  echo 'mock perception log' > $X/perc2/ep$e/log.txt
done
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
# the pulled sub-folders = the listing (review F7): placeholders for listed files without a stand-in, unlisted files removed
$PY -I - $TAB $MS/store << 'EOF'
import glob, json, os, shutil, sys
import numpy as np
T = json.load(open(sys.argv[1]))['episodes']; ST = sys.argv[2]; made = rm = 0
for e, x in T.items():
    subs = [f'{ST}/runs/{x["source_run"]}/{s}' for s in x['pull']]
    if not all(os.path.isdir(d) for d in subs):
        continue                                                   # an episode the mock never trains (std 19 25 28 30)
    base = glob.glob(f'{ST}/runs/{x["source_run"]}/refs/perc2mck/ep{e}/processed/*/*/*.parquet')[0]
    want = {f'{ST}/{f}' for f in x['pull_files']}
    for f in sorted(want):
        if os.path.exists(f):
            continue
        os.makedirs(os.path.dirname(f), exist_ok=True); made += 1
        if f.endswith('.parquet'):
            shutil.copy(base, f)
        elif f.endswith('.npz'):
            np.savez(f[:-4], mock=np.zeros(1))
        elif f.endswith('.json'):
            json.dump(dict(mock='placeholder for a listed store file'), open(f, 'w'))
        else:
            open(f, 'w').write(f'mock placeholder for {os.path.basename(f)}\n')
    for d in subs:
        for f in glob.glob(f'{d}/**/*', recursive=True):
            if os.path.isfile(f) and f not in want:
                os.remove(f); rm += 1
    assert {f for d in subs for f in glob.glob(f'{d}/**/*', recursive=True) if os.path.isfile(f)} == want, e
print(f'store sub-folders = the listing: {made} placeholders written, {rm} unlisted synthetic files removed')
EOF
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
# pack 9b: the packed policy's H5p7 draws (r1..r10 per D episode; perturbed real packed rollouts naming the packed sha256)
for e in 14 16 25 30 33; do
  sha=$(tabv $e packed_sha256); ref=$(tabv $e reference)
  for i in $(seq 1 10); do
    d=$ST/20261031-h5p7-1a7cdff/results/h5/r$i/ep$e; E6=$(printf %06d $e)
    MOCK_MR=$TP MOCK_PY=$PY $PY -I $M/stub.py mkdraw $TP/templates/rollout_ep$e.parquet $d/episode_$E6.parquet h5p7/$e/$i $sha /workspace/$ref 0.2
    echo "{\"mock\": 1, \"checkpoint_sha256\": \"$sha\"}" > $d/episode_$E6.json
  done
done
echo "export PATH=$B/bin:\$PATH HF_STORE=mock/store MOCK_MR=$B MOCK_PY=$PY" > $TP/env.sh
echo "mock store at $MS/store ($(du -sh $MS/store | cut -f1)), box template $TP"
