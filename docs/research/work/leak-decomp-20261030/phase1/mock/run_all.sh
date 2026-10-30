#!/bin/bash
# All perc_leak mock scenarios (2026-10-30); outputs in out/. usage: run_all.sh MR
#   box a/b/c  the exact JOBS.txt strings (run id <date>-orcP1{a,b,c}-<sha>), then check.py;
#   b8         box a's push list against a B8 candidate guard (no_oracle.py + perc2scan|perc2gf), mock copy only;
#   faults     a 429 on a depth download (retried), a corrupted hands file (md5 flag), perc2 crashing on one arm, a
#              crash after poses.npz (poses_world_vo.npz rebuilt), a truncated depth cache (episode skipped): job rc 3;
#   refusals   no -orc in the run id, an unknown arm, REPEAT outside EPS, an episode outside inputs.tsv: rc 1, no work;
#              plus a relative LIB, which the job must make absolute (perc2 chdirs before loading the templates).
set -u
MR=$1; M=$(cd "$(dirname "$0")" && pwd); O=$M/out; PY=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/map/scoring/venv/bin/python
bash $M/setup.sh $MR > /dev/null
L='LIB=/content/v2d-track3/meshes/library_v3 bash ops/jobs/perc_leak.sh'
declare -A E=([a]="13 2 26 44 45 41 0" [b]="11 21 31 39 22 42 23" [c]="12 27 24 18 40 43")
declare -A R=([a]="13 2" [b]="11 21 31 39" [c]="12 27 24 18")
for k in a b c; do
  rid=20261030-orcP1$k-mocksha
  bash $M/run_mock.sh $MR $rid "EPS=\"${E[$k]}\" REPEAT=\"${R[$k]}\" ARMS=o,s,o2 $L"
  { echo "MOCK (stub perc2, stub hf): every AUC below is fake; paths, names, md5, guard and push list are real"
    echo "== box $k: EPS=\"${E[$k]}\" REPEAT=\"${R[$k]}\" ARMS=o,s,o2 (run id $rid)"; $PY -I $M/check.py $MR $rid "${E[$k]}" "${R[$k]}"
    echo "check rc=$?"; echo "-- job.log"; sed "s#$MR#<MR>#g" $MR/content/job.log | cut -c1-260; echo "-- push"; cat $MR/push.out; } > $O/mock_box$k.txt 2>&1
  if [ $k = a ]; then
    sed "s/BAD = re.compile(r'oracle|/BAD = re.compile(r'perc2scan|perc2gf|oracle|/" $MR/content/v2d-track3/tools/no_oracle.py > $MR/no_oracle_b8.py
    { echo "== B8 candidate guard on box a's push list: $(grep '^BAD' $MR/no_oracle_b8.py)"
      GUARD=$MR/no_oracle_b8.py $PY -I $M/check.py $MR $rid "${E[$k]}" "${R[$k]}" | grep -a 'guard\|RESULT'; } > $O/mock_b8.txt 2>&1
  fi
done
rid=20261030-orcP1f-mocksha
bash $M/run_mock.sh $MR $rid "EPS=\"11 39 12\" REPEAT=\"11\" ARMS=o,s,o2 $L" MOCK_429=cache/depth/public/ep11/depths_fs0.5.npy \
  MOCK_BADHANDS=runs/20261025-g1-022fece/refs/perc2m/ep39/hands_refined.npz MOCK_FAIL=39:perc2scan MOCK_NOWVO=11:perc2rep MOCK_SHORTDEPTH=12
{ echo "MOCK (stub perc2, stub hf): every AUC below is fake"
  echo "== faults: EPS=\"11 39 12\" REPEAT=\"11\"; 429 on ep11 depth, corrupted ep39 hands_refined, perc2 crash on ep39 perc2scan,"
  echo "   crash after poses.npz on ep11 perc2rep, ep12 depth cache one frame short. job rc $(cat $MR/rc.txt) (expected 3)"
  sed "s#$MR#<MR>#g" $MR/content/job.log | cut -c1-260; echo "-- leak_pull.log"; cat $MR/content/leak_pull.log
  echo "-- hf.log"; sed "s#$MR#<MR>#g" $MR/hf.log
  echo "-- ep11 perc2rep in bundle.json:"; $PY -I -c "import json; a = json.load(open('$MR/content/results/leak_p1/ep11/bundle.json'))['arms']['perc2rep']; print({k: a.get(k) for k in ('rc', 'poses_ok', 'poses_world_vo_written_here', 'world_vo_maxdiff', 'ok')})"
  echo "-- ep39 problems: $($PY -I -c "import json; print(json.load(open('$MR/content/results/leak_p1/ep39/inputs.json'))['problems'])")"
  echo "-- ep12 folder: $(ls $MR/content/results/leak_p1/ep12/ 2> /dev/null | tr '\n' ' '); push: $(tail -2 $MR/push.out | tr '\n' ' ')"; } > $O/mock_faults.txt 2>&1
{ for c in "20261030-p1a-mocksha|EPS=\"11\" $L" "20261030-orcP1x-mocksha|EPS=\"11\" ARMS=o,gf $L" \
           "20261030-orcP1x-mocksha|EPS=\"11\" REPEAT=\"12\" $L" "20261030-orcP1x-mocksha|EPS=\"5\" $L"; do
    bash $M/run_mock.sh $MR "${c%%|*}" "${c#*|}"
    echo "run id ${c%%|*}, job [${c#*|}]: rc $(cat $MR/rc.txt), perc2 runs $(cat $MR/perc2_audit.log 2> /dev/null | wc -l), downloads $(grep -c "\"kind\": \"file\"" $MR/hf.log 2> /dev/null): $(tail -1 $MR/content/job.log | cut -c23-200 | sed "s#$MR#<MR>#g")"
  done; } > $O/mock_refusals.txt 2>&1
bash $M/run_mock.sh $MR 20261030-orcP1r-mocksha 'EPS="44" ARMS=o,s LIB=meshes/library_v3 bash ops/jobs/perc_leak.sh'
echo "relative LIB=meshes/library_v3: rc $(cat $MR/rc.txt); MESH_DIR seen by perc2: $(cut -d, -f3 $MR/perc2_audit.log | sed "s#$MR#<MR>#g" | tr '\n' ' ')" >> $O/mock_refusals.txt
grep -h 'RESULT\|check rc' $O/mock_box?.txt; head -3 $O/mock_faults.txt | tail -1; cat $O/mock_refusals.txt
