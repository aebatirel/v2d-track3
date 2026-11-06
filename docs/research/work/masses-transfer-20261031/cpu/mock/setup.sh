#!/bin/bash
# CPU mock of ops/jobs/mass_check.sh (2026-10-31), after docs/research/work/oracle-twins-20261030/cpu/mock.
# A copy of the repo with /content -> $MR/content, stub GPU programs (grasp lock, ILC, evolutionary search, rollouts,
# FlashCHORD training and the official evaluator, qa, scoring) and REAL make_assets.py, support_fill.py, mass_arm.py,
# mass_verify.py, mass_verdict.py, store.sh and glock_public.sh. The FlashCHORD stubs load references the way FlashCHORD
# does (task.parquet folder -> exactly one .parquet -> object_urdf_paths -> URDF inertials), and the trainer stub writes
# safetensors checkpoints whose metadata holds the resolved config, as FlashCHORD does.
# Fake store: $MR/store/runs/<run>/..., filled from local copies of the real store files (scratchpad carve/refs/store):
#   20261024-ev2-2c1e4dd: refs/perc2mc/ep12, refs/sf/ep12, refs/glockt/ep12 (+ a synthetic results/glock_public/ep12/rest_check.json)
#   20261024-ev3-2c1e4dd: refs/perc2mck/ep2 and E3's refs/glockt/ep2 + refs/sf/ep2 (present in the store; the job must NOT use them)
# Parquet asset paths are rewritten /content/ -> $MR/content/ (the only change; the reference fingerprint excludes them).
# usage: setup.sh MR [REPO_SRC]   (REPO_SRC default: the working tree)
set -e
MR=$1; R=${2:-/home/user/v2d-track3}; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
M=$(cd $(dirname $0) && pwd); PY=$S/map/scoring/venv/bin/python; ST=$S/carve/refs/store/runs
rm -rf "${MR:?}"; mkdir -p $MR/bin $MR/content/v2d-track3/meshes $MR/content/v2d-track3/docs/research $MR/store/runs
for d in ops pipeline tools flashchord_conf; do cp -r $R/$d $MR/content/v2d-track3/; done
cp -r $R/meshes/library_v3 $MR/content/v2d-track3/meshes/; cp -r $R/docs/research/physics-2026-10-30 $MR/content/v2d-track3/docs/research/
find $MR/content/v2d-track3 \( -name '*.sh' -o -name '*.py' \) -exec sed -i "s#/content#$MR/content#g" {} +
FC=$MR/content/v2d/robotic_grounding/flash_chord; mkdir -p $FC/.venv/bin $FC/scripts $FC/src/flash_chord/configs/embodiment
w() { printf '#!/bin/bash\nexec %s -I %s/stub.py %s "$@"\n' $PY $M $2 > $1; chmod +x $1; }
w $MR/bin/python main; w $MR/bin/python3 main; w $FC/.venv/bin/python fc
cat > $MR/bin/hf << EOF
#!/bin/bash
# hf stub: download copies from the fake store; upload is logged (counted by check.py)
echo "hf \$*" >> $MR/hf.log
if [ "\$1" = download ]; then
  inc=; dir=; pos=
  shift; shift                                 # 'download' and the store name
  while [ \$# -gt 0 ]; do case \$1 in --include) inc=\$2; shift 2 ;; --local-dir) dir=\$2; shift 2 ;; --repo-type) shift 2 ;; *) pos=\$1; shift ;; esac; done
  if [ -n "\$inc" ]; then s=\${inc%/\*}; [ -e $MR/store/\$s ] || exit 0; mkdir -p \$dir/\$(dirname \$s); cp -r $MR/store/\$s \$dir/\$(dirname \$s)/
  else [ -f $MR/store/\$pos ] || exit 1; mkdir -p \$dir/\$(dirname \$pos); cp $MR/store/\$pos \$dir/\$pos; fi
fi
exit 0
EOF
printf '#!/bin/bash\necho "{}"\n' > $MR/bin/curl
printf '#!/bin/bash\nexit 0\n' > $MR/bin/pip
printf '#!/bin/bash\necho mocksha0000000\n' > $MR/bin/git
chmod +x $MR/bin/*
# fake store from the local copies of the real store files
rw() {  # $1 src parquet, $2 dst parquet: asset paths /content/ -> $MR/content/
  $PY -I - "$1" "$2" "$MR" << 'PYEOF'
import sys, pyarrow as pa, pyarrow.parquet as pq
src, dst, MR = sys.argv[1:4]; t = pq.read_table(src)
for c in ('object_urdf_paths', 'object_mesh_paths'):
    if c in t.column_names:
        v = [p.replace('/content/', MR + '/content/', 1) for p in t.column(c)[0].as_py()]
        t = t.set_column(t.column_names.index(c), c, pa.array([v], type=t.schema.field(c).type))
pq.write_table(t, dst)
PYEOF
}
cpref() {  # $1 src run dir, $2 sub, $3 dst run dir
  mkdir -p $3/$(dirname $2); cp -r $1/$2 $3/$(dirname $2)/
  find $3/$2 -name '*.parquet' | while read -r f; do rw $f $f.tmp && mv $f.tmp $f; done
}
E2=$MR/store/runs/20261024-ev2-2c1e4dd; E3=$MR/store/runs/20261024-ev3-2c1e4dd
for s in refs/perc2mc/ep12 refs/sf/ep12 refs/glockt/ep12; do cpref $ST/20261024-ev2-2c1e4dd $s $E2; done
mkdir -p $E2/results/glock_public/ep12; echo '{"ok": true, "mock": "synthetic rest check (the real file is not on this machine)"}' > $E2/results/glock_public/ep12/rest_check.json
for s in refs/perc2mck/ep2 refs/glockt/ep2 refs/sf/ep2; do cpref $ST/20261024-e3-e49e83d $s $E3; done
echo "export PATH=$MR/bin:\$PATH HF_STORE=mock/store MOCK_MR=$MR MOCK_PY=$PY RUN_ID=20261031-mass-mocksha" > $MR/env.sh
echo "mock at $MR"
