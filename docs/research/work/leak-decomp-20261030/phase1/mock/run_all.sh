#!/bin/bash
# All perc_leak mock scenarios (2026-10-30); outputs in out/. usage: run_all.sh MR
#   box a/b/c  the exact JOBS.txt strings (run id <date>-orcP1{a,b,c}-<sha>), then check.py;
#   b8         box a's push list against the real tools/no_oracle.py (B8 landed: perc2scan|perc2gf in BAD), plus
#              bare perc2gf paths;
#   faults     a 429 on a depth download (retried), a corrupted hands file (md5 flag), perc2 crashing on one arm, a
#              crash after poses.npz (poses_world_vo.npz rebuilt), a truncated depth cache (episode skipped): job rc 3;
#   gdino      (mechanics review F1) the first Grounding DINO download fails and is retried (rc 0, bundles ok), one
#              injected 'grounding unavailable' arm (NOT OK, NO-GDINO, rc 0); every download fails (NO-GDINO, rc 0);
#   data       (mechanics review F2) a missing public video: fetch_data.sh re-run once (here it fails: the stub hf
#              refuses its listing) -> rc 1, no download, no perc2; the same with a fetch_data.sh that restores it ->
#              rc 0; a missing scan -> rc 1;
#   refusals   a run id that tools/no_oracle.py does not refuse (no -orc; '-orc' without the date; no trailing '-'),
#              an unknown arm, REPEAT outside EPS, an episode outside inputs.tsv: rc 1, no work; plus a relative LIB,
#              which the job must make absolute (perc2 chdirs before loading the templates).
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
    G=$MR/content/v2d-track3/tools/no_oracle.py
    { echo "== B8 in the real guard (tools/no_oracle.py, no candidate copy):"; grep -A3 '^BAD' $G
      $PY -I $M/check.py $MR $rid "${E[$k]}" "${R[$k]}" | grep -a 'guard\|RESULT'
      for f in ep13/perc2gf/poses.npz perc2gf/ep13/vo.json ep13/perc2scan/poses_world_vo.npz ep13/perc2/poses.npz; do
        $PY -I $G $f > /dev/null 2>&1 && echo "bare $f: accepted" || echo "bare $f: REFUSED"; done; } > $O/mock_b8.txt 2>&1
  fi
done
rid=20261030-orcP1f-mocksha
bash $M/run_mock.sh $MR $rid "EPS=\"11 39 12\" REPEAT=\"11\" ARMS=o,s,o2 $L" MOCK_429=cache/depth/public/ep11/depths_fs0.5.npy \
  MOCK_BADHANDS=runs/20261025-g1-022fece/refs/perc2m/ep39/hands_refined.npz MOCK_FAIL=39:perc2scan MOCK_NOWVO=11:perc2rep MOCK_SHORTDEPTH=12
{ echo "MOCK (stub perc2, stub hf): every AUC below is fake"
  echo "== faults: EPS=\"11 39 12\" REPEAT=\"11\"; 429 on ep11 depth, corrupted ep39 hands_refined, perc2 crash on ep39 perc2scan,"
  echo "   crash after poses.npz on ep11 perc2rep, ep12 depth cache one frame short. job rc $(cat $MR/rc.txt) (expected 3)"
  sed "s#$MR#<MR>#g" $MR/content/job.log | cut -c1-260; echo "-- results/leak_p1/leak_pull.log"; cat $MR/content/results/leak_p1/leak_pull.log
  echo "-- hf.log"; sed "s#$MR#<MR>#g" $MR/hf.log
  echo "-- ep11 perc2rep in bundle.json:"; $PY -I -c "import json; a = json.load(open('$MR/content/results/leak_p1/ep11/bundle.json'))['arms']['perc2rep']; print({k: a.get(k) for k in ('rc', 'poses_ok', 'poses_world_vo_written_here', 'world_vo_maxdiff', 'ok')})"
  echo "-- ep39 problems: $($PY -I -c "import json; print(json.load(open('$MR/content/results/leak_p1/ep39/inputs.json'))['problems'])")"
  echo "-- ep12 folder: $(ls $MR/content/results/leak_p1/ep12/ 2> /dev/null | tr '\n' ' '); push: $(tail -2 $MR/push.out | tr '\n' ' ')"; } > $O/mock_faults.txt 2>&1
# gdino (F1): G1 first download 429 then ok + an injected 'grounding unavailable' on ep12 perc2; G2 every download 429
bundle_line() { $PY -I -c "import json, sys; s = json.load(open('$MR/content/results/leak_p1/summary.json'))
for k, v in s['episodes'].items(): print(' ', k, 'ok', v['ok'], {a: (x['ok'], x['gdino']) for a, x in v['arms'].items()})"; }
bash $M/run_mock.sh $MR 20261030-orcP1g-mocksha "EPS=\"11 12\" REPEAT=\"11\" ARMS=o,s,o2 $L" MOCK_GDINO_FAIL1=1 MOCK_NOGDINO=12:perc2
{ echo "MOCK (stub perc2, stub hf, stub transformers): every AUC below is fake"
  echo "== G1: first Grounding DINO download fails (429), retried; ep12 perc2 logs 'grounding unavailable'. job rc $(cat $MR/rc.txt) (expected 0)"
  echo "-- from_pretrained calls (MR/gdino_tries.txt):"; cat $MR/gdino_tries.txt
  echo "-- perc2 runs: $(wc -l < $MR/perc2_audit.log), with HF_HUB_OFFLINE=1: $(grep -c '"hf_hub_offline": "1"' $MR/perc2_audit.log)"
  echo "-- job.log (Grounding DINO, bundles, RESULT):"; grep -a 'Grounding\|bundle\|RESULT' $MR/content/job.log | sed "s#$MR#<MR>#g" | cut -c1-260
  echo "-- summary.json per arm (ok, gdino):"; bundle_line; } > $O/mock_gdino.txt 2>&1
bash $M/run_mock.sh $MR 20261030-orcP1g-mocksha "EPS=\"44\" ARMS=o,s $L" MOCK_GDINO_FAILALL=1
{ echo "== G2: every Grounding DINO download fails. job rc $(cat $MR/rc.txt) (expected 0; the bundles are NOT OK)"
  echo "-- from_pretrained calls:"; cat $MR/gdino_tries.txt
  echo "-- job.log (Grounding DINO, RESULT):"; grep -a 'Grounding\|RESULT' $MR/content/job.log | sed "s#$MR#<MR>#g" | cut -c1-260
  echo "-- summary.json per arm (ok, gdino):"; bundle_line; } >> $O/mock_gdino.txt 2>&1
# data (F2): D1 ep44_a.mp4 missing, the real fetch_data.sh re-run fails (stub hf refuses its dataset listing); D2 the
# same with a fetch_data.sh that restores the file; D3 a missing scan (t3/mesh replaced by a link farm without white_pot)
T3=$MR/content/t3; FD=$MR/content/v2d-track3/pipeline/fetch_data.sh; cp $FD $MR/fetch_data.real.sh
data_line() { echo "$1: rc $(cat $MR/rc.txt), perc2 runs $(cat $MR/perc2_audit.log 2> /dev/null | wc -l), store downloads $(grep -c '"kind": "file"' $MR/hf.log 2> /dev/null), dataset listings $(grep -c 'video_to_data_challenge' $MR/hf.log 2> /dev/null)"
  grep -a 'public data' $MR/content/job.log | cut -c23-300 | sed "s#$MR#<MR>#g"; }
{ rm $T3/v/ep44_a.mp4
  bash $M/run_mock.sh $MR 20261030-orcP1d-mocksha "EPS=\"44\" ARMS=o,s $L"; data_line "D1 ep44_a.mp4 missing, fetch_data.sh fails (expected rc 1, 0, 0)"
  printf '#!/bin/bash\necho "mock fetch_data.sh: restoring ep44_a.mp4"; echo x > %s/v/ep44_a.mp4\n' $T3 > $FD
  bash $M/run_mock.sh $MR 20261030-orcP1d-mocksha "EPS=\"44\" ARMS=o,s $L"; data_line "D2 ep44_a.mp4 missing, fetch_data.sh restores it (expected rc 0, 2 runs)"
  cp $MR/fetch_data.real.sh $FD; [ -s $T3/v/ep44_a.mp4 ] || echo x > $T3/v/ep44_a.mp4
  mv $T3/mesh $T3/mesh.real; mkdir $T3/mesh; for d in $T3/mesh.real/*; do [ $(basename $d) = white_pot ] || ln -s $d $T3/mesh/; done
  bash $M/run_mock.sh $MR 20261030-orcP1d-mocksha "EPS=\"44\" ARMS=o,s $L"; data_line "D3 scan white_pot missing (expected rc 1, 0, 0)"
  rm -rf $T3/mesh; mv $T3/mesh.real $T3/mesh; } > $O/mock_data.txt 2>&1
{ for c in "20261030-p1a-mocksha|EPS=\"11\" $L" "P1-orc-mocksha|EPS=\"11\" $L" "x20261030-orcP1a|EPS=\"11\" $L" \
           "20261030-orcP1x-mocksha|EPS=\"11\" ARMS=o,gf $L" \
           "20261030-orcP1x-mocksha|EPS=\"11\" REPEAT=\"12\" $L" "20261030-orcP1x-mocksha|EPS=\"5\" $L"; do
    bash $M/run_mock.sh $MR "${c%%|*}" "${c#*|}"
    echo "run id ${c%%|*}, job [${c#*|}]: rc $(cat $MR/rc.txt), perc2 runs $(cat $MR/perc2_audit.log 2> /dev/null | wc -l), downloads $(grep -c "\"kind\": \"file\"" $MR/hf.log 2> /dev/null): $(tail -1 $MR/content/job.log | cut -c23-200 | sed "s#$MR#<MR>#g")"
  done; } > $O/mock_refusals.txt 2>&1
bash $M/run_mock.sh $MR 20261030-orcP1r-mocksha 'EPS="44" ARMS=o,s LIB=meshes/library_v3 bash ops/jobs/perc_leak.sh'
echo "relative LIB=meshes/library_v3: rc $(cat $MR/rc.txt); MESH_DIR seen by perc2: $(cut -d, -f3 $MR/perc2_audit.log | sed "s#$MR#<MR>#g" | tr '\n' ' ')" >> $O/mock_refusals.txt
grep -h 'RESULT\|check rc' $O/mock_box?.txt; head -3 $O/mock_faults.txt | tail -1; grep -h '^==' $O/mock_gdino.txt
grep -h '^D[123]' $O/mock_data.txt; cat $O/mock_refusals.txt
