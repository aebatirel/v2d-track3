#!/bin/bash
# CPU mock of the Masses v2 box job (2026-10-31), after the first check's mock (masses-transfer-20261031/cpu/mock/setup.sh).
# A copy of the repo with /content -> $MR/content, stub GPU programs (stub_v2.py: grasp lock, ILC, search, rollouts, the
# FlashCHORD trainer and official evaluator, qa, scoring) and REAL make_assets.py, mass_arm.py, mass_verify.py,
# mass_verdict.py, store.sh, glock_public.sh, ckpt_curve.sh and mass_check.sh.
# Fake store STORE (shared by every mock box, so a re-run box can pull what an earlier box pushed): the hf stub serves
# single-file downloads from it, logs every call (an --include download = a store LISTING, counted), and an upload copies
# the uploaded folder into it (as the real push does). Populated once (store_v2.py) from the reference files of the
# 4 episodes downloaded from the real store (glockt parquets, URDFs, rest_check.json) plus labelled stand-ins for files
# the stubs do not parse (base processed parquet = the glockt parquet re-pointed at /content/assets, stage .usda, sf .glb
# = library_v3 copies, zero_score.txt, support_fill.json). Parquet asset paths /content/ -> $MR/content/ (the reference
# fingerprint excludes them; their md5 changes, so the mock table in the repo copy carries the md5 of the re-pointed
# files and the REAL table's fingerprints, recorded in STORE/mock_table_diff.json).
# usage: setup_v2.sh MR STORE   (MR is wiped; STORE is kept, and populated if empty)
set -e
MR=$1; STORE=$2; R=/home/user/v2d-track3; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
M=$(cd $(dirname $0) && pwd); PY=$S/map/scoring/venv/bin/python
rm -rf "${MR:?}"; mkdir -p $MR/bin $MR/content/v2d-track3/meshes $MR/content/v2d-track3/docs/research/work/masses-v2-20261031 $STORE
for d in ops pipeline tools flashchord_conf; do cp -r $R/$d $MR/content/v2d-track3/; done
cp -r $R/meshes/library_v3 $MR/content/v2d-track3/meshes/; cp -r $R/docs/research/physics-2026-10-30 $MR/content/v2d-track3/docs/research/
find $MR/content/v2d-track3 \( -name '*.sh' -o -name '*.py' \) -exec sed -i "s#/content#$MR/content#g" {} +
FC=$MR/content/v2d/robotic_grounding/flash_chord; mkdir -p $FC/.venv/bin $FC/scripts $FC/src/flash_chord/configs/embodiment
w() { printf '#!/bin/bash\nexec %s -I %s/stub_v2.py %s "$@"\n' $PY $M $2 > $1; chmod +x $1; }
w $MR/bin/python main; w $MR/bin/python3 main; w $FC/.venv/bin/python fc
cat > $MR/bin/hf << EOF2
#!/bin/bash
# hf stub (Masses v2 mock): single-file download from STORE; --include = a store listing (logged as such); upload -> STORE
echo "hf \$*" >> $MR/hf.log
if [ "\$1" = download ]; then
  inc=; dir=; pos=
  shift; shift
  while [ \$# -gt 0 ]; do case \$1 in --include) inc=\$2; shift 2 ;; --local-dir) dir=\$2; shift 2 ;; --repo-type) shift 2 ;; *) pos=\$1; shift ;; esac; done
  if [ -n "\$inc" ]; then echo "LISTING \$inc" >> $MR/hf.log; s=\${inc%/\*}; [ -e $STORE/\$s ] || exit 0; mkdir -p \$dir/\$(dirname \$s); cp -r $STORE/\$s \$dir/\$(dirname \$s)/
  else [ -f $STORE/\$pos ] || exit 1; mkdir -p \$dir/\$(dirname \$pos); cp $STORE/\$pos \$dir/\$pos; fi
elif [ "\$1" = upload ]; then
  mkdir -p $STORE/\$4; cp -r \$3/. $STORE/\$4/
fi
exit 0
EOF2
printf '#!/bin/bash\necho "{}"\n' > $MR/bin/curl
printf '#!/bin/bash\nexit 0\n' > $MR/bin/pip
printf '#!/bin/bash\necho mocksha0000000\n' > $MR/bin/git
chmod +x $MR/bin/*
[ -f $STORE/.populated ] || $PY -I $M/store_v2.py $STORE $MR
$PY -I - $R/docs/research/work/masses-v2-20261031/refs_v2.json $STORE/mock_table_diff.json $MR/content/v2d-track3/docs/research/work/masses-v2-20261031/refs_v2.json << 'PYEOF'
import json, sys
T = json.load(open(sys.argv[1])); D = json.load(open(sys.argv[2]))
for e, v in D['episodes'].items():
    assert T['episodes'][e]['glockt_fingerprint'] == v['fingerprint'], e      # the PREREG fingerprint, unchanged
    T['episodes'][e]['glockt_md5'] = v['mock_md5']                             # md5 of the path-re-pointed copy
json.dump(T, open(sys.argv[3], 'w'), indent=1)
PYEOF
echo "export PATH=$MR/bin:\$PATH HF_STORE=mock/store MOCK_MR=$MR MOCK_PY=$PY PULL_RETRY_S=1 PULL_TIMEOUT_S=60" > $MR/env.sh
echo "mock at $MR (store $STORE)"
