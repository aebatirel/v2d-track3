#!/bin/bash
# Mesh v5 library build (docs/mesh-v5-spec-draft.md section 10.2, 2026-10-25) on a box, CPU only: every public episode
# of each object (episode sets in pipeline/mesh_v5.json), along our own-mesh perc2m tracks (G1 run + the 21 Oct runs),
# our MediaPipe hands and our depth caches. Step 1: pass 0 (M0) for every object; step 2: pipeline/ep_mesh.py library
# per object, in parallel (fusion with the other objects' M0, post-pass + gates, F4, selection, support rule,
# decimation, collision pieces). Output /content/results/library_v5/<obj>.glb, <obj>_full.glb, <obj>.json, pieces/,
# README.md, pushed with the run (under results/: store.sh push-run uploads it and the stall watchdog sees its files;
# the 25 Oct run wrote /content/library_v5, outside both, and needed a copier on the box) (the agent copies the result into meshes/library_v5 after review). Tier P1 (owner decision O1).
#   ops/vast.sh create <offer> <run> 'G1RUN=20261025-g1-022fece bash ops/build_library.sh'   [OBJS="..." PAR=6]
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; OUT=/content/results/library_v5; M0=$OUT/m0; mkdir -p $OUT $M0
G1RUN=${G1RUN:?G1RUN (the G1 perc2m run) missing}; OLDRUNS=${OLDRUNS:-"20261021-auto18-966eb96 20261021-auto24-966eb96"}
OBJS=${OBJS:-"white_pot white_pot_lid blue_cup beige_cup plastic_dish_rack water_pitcher mini_sweeper mini_dust_pan wooden_piece_1 wooden_piece_2"}
PAR=${PAR:-6}
log "build_library code $(git -C $REPO_DIR rev-parse --short HEAD), G1 $G1RUN + $OLDRUNS, objects [$OBJS]" >> $J
pip install -q fast_simplification manifold3d open3d==0.20.0 pymeshlab==2025.7.post1 warp-lang >> $J 2>&1 || log "pip install FAILED" >> $J
apt-get install -y -q libopengl0 > /dev/null 2>&1 || true
for r in $G1RUN $OLDRUNS; do bash $OPS/store.sh pull-run $r >> $J 2>&1 || { log "pull-run $r FAILED" >> $J; exit 1; }; done
EPS=$(python -c "import json; d = json.load(open('$P/mesh_v5.json'))['library_episodes']; print(' '.join(sorted({str(e) for v in d.values() for e in v}, key=int)))")
for ep in $EPS; do bash $OPS/store.sh pull-depth $ep public > /dev/null 2>&1 || log "no stored depth for ep$ep" >> $J; done
# the --ep arguments of one object: POSES DEPTH HANDS OTHERS(names of the other library objects of that episode)
epargs() {
  python - "$1" "$P/mesh_v5.json" << 'EOF'
import json, os, sys
obj, lib = sys.argv[1], json.load(open(sys.argv[2]))['library_episodes']
for ep in lib[obj]:
    p, d, h = f'/content/perc2m/ep{ep}/poses.npz', f'/content/cache/depth/ep{ep}/depths_fs0.5.npy', f'/content/refs/perc2m/ep{ep}/hands.npz'
    if not (os.path.exists(p) and os.path.exists(d)):
        print(f'# ep{ep}: missing {"poses" if not os.path.exists(p) else "depth"}', file=sys.stderr); continue
    others = [o for o, e in lib.items() if o != obj and ep in e]
    print(f"--ep {p} {d} {h if os.path.exists(h) else '-'} {','.join(others) if others else '-'}", end=' ')
EOF
}
label "library v5: pass 0"
pids=()
for o in $OBJS; do
  A=$(epargs $o 2>> $J); [ -n "$A" ] || { log "$o: no episodes with tracks and depth" >> $J; continue; }
  python $P/ep_mesh.py m0 $o $M0 --calib /content/t3/calib.json $A >> $M0/$o.log 2>&1 &   # m0 ignores OTHERS
  pids+=($!); [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
done
wait
log "library v5: pass 0 done: $(ls $M0/*_M0.glb 2>/dev/null | wc -l) M0 meshes" >> $J
label "library v5: objects"
pids=()
for o in $OBJS; do
  A=$(epargs $o 2>> $J); [ -n "$A" ] || continue
  ( python $P/ep_mesh.py library $o $OUT --m0_dir $M0 --calib /content/t3/calib.json $A > $OUT/$o.log 2>&1
    log "library v5 $o rc=$?: $(tail -1 $OUT/$o.log | cut -c1-400)" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1 ) &
  pids+=($!); [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
done
wait
python - $OUT << 'EOF' > $OUT/README.md
import glob, json, os, sys
rows = ['# library_v5 build', '', '| object | branch | O G1 cm3 | O G2 | O gates | F4 gates | support | pieces | sec |', '|---|---|---|---|---|---|---|---|---|']
for f in sorted(glob.glob(f'{sys.argv[1]}/*.json')):
    r = json.load(open(f)); o = r.get('O') or {}
    g = lambda d: ' '.join(f'{k}={d[k]}' for k in ('T', 'X', 'C', 'G1', 'G2') if k in (d or {}))  # noqa: E731
    sup = 'changed' if (r.get('support') or {}).get('changed') else (r.get('support') or {}).get('skipped', 'unchanged')
    rows.append(f"| {r['obj']} | {r.get('branch')} | {o.get('g1_seen_free_violation_cm3')} | {o.get('g2_unexplained8')} | {g(r.get('gates_O'))} | "
                f"{g(r.get('gates_F4'))} | {sup} | {(r.get('pieces') or {}).get('n_pieces')} | {(r.get('timings') or {}).get('total')} |")
print('\n'.join(rows))
EOF
log "library v5 done: $(ls $OUT/*.glb 2>/dev/null | grep -vc _full) meshes; README $(wc -l < $OUT/README.md) lines" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
