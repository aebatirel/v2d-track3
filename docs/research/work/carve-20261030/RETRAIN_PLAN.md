# Placement-carve retraining plan: evals 1, 14 (28, 30) (draft 2026-10-30; nothing rented, no git operation)

Markers: [M] measured (this container, CPU), [E] estimate, [H] hypothesis. GT-free: eval carves and every rule below use
only our meshes, our eval references and official sim_vs_ref. Owner go-ahead is required before any rental (CLAUDE.md).
Verification scripts and outputs: `$S/verify/` (`S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve`).

## 0. Verification verdicts (adversarial pass on the build report)

**(a) No ground truth for eval carves: CONFIRMED [M].**
- `pipeline/placement_carve.py` reads two things only:
  - `ASSETS/mesh/<n>/<n>.glb`;
  - the reference parquet's `object_body_names/position/wxyz`, through `interaction_carve.ref_poses`.
- Its imports (`interaction_carve`, `collision_decomp`) read nothing at import time. The "mocap" in
  `interaction_carve.py` is a MuJoCo kinematic body, not motion capture.
- The eval carves name our references (`carve.json` `ref`), checked by md5:
  - ev01: std0116 perc2mcks/ep1, md5 7f2304663b4e3c55a0a1ad12503174c1;
  - ev14: evb1420 glockt/ep14 ref_gl_ilc, md5 10d5f3ba6b7368ed30dad9d0c9c30df1;
  - ev28: std1928 perc2mcks/ep28, md5 6f57deb27e47abcd7ec2afe739354af1;
  - ev30: std30 perc2mcks/ep30, md5 dd464c96184e84400e62ffcfa17a6ac4.
- Each is byte-identical to the stored source reference a retrain pulls:
  - 20261024-pack-31ef267 refs/perc2mck for ep1 and ep28;
  - 20261024-ev30rp-07eef1a for ep30;
  - for ep14, the same store file.
- Mocap appears only in `twin_gt_score.py` / `gt_poses.py`, which run on P-cases only.

**(b) Independent recompute, E1 and E28: overlap CONFIRMED, settle CONFIRMED only for a fresh first frame [M].**
- My own Monte Carlo test (600k random points, not a grid; `verify/scripts/vgeom.py`) used the hulls read back from the
  BUILT FlashCHORD model.
- Overlap (default → carved, cm³):

  | | f0 | placed | rest max | max increase |
  |---|---|---|---|---|
  | E1 | 44.58 → 0 | 50.07 → 0 | 57.27 → 0 | 0.0 |
  | E28 | 0.39 → 0 | 42.0 → 0 | 46.23 → 0 | 0.0 |
  | E14 (extra) | – | 16.47 → 0 | – | 0.0 |
  | E30 (extra) | – | 13.54 → 0 | – | 0.0 |

  These agree with the build report within 0.6 cm³. In the simulator itself, the reset contacts between guest and host
  at the placed frame go away:
  - E1: 26 lid–pot contacts, the deepest at −17.3 mm → none;
  - E28: 16 rack–pot contacts, the deepest at −26.4 mm → none.
- Settle at the placed frame, run first in a fresh process: reproduced exactly (E1 lid 2.33/14.5 → 1.08/8.1; E28 pot
  2.45/9.0 → 3.31/18.2).
- **But the settle is chaotic.** The same frame re-run in the same process, with only the solver warm start different,
  gives (cm/deg at 2 s):
  - E1 carved f305: 1.08/8.1, 0.64/1.3, 1.29/8.1;
  - E1 carved f0: 1.15/2.6, 0.80/0.6, 0.51/2.5;
  - E28 carved f206: 3.31/18.2, 0.42/1.7, 0.31/0.4;
  - E28 carved f0: 0.12/0.5, 0.41/3.3, 0.16/0.4;
  - E1 default f0: 2.02/5.3, 1.87/10.9, 23.2/126.5 (the lid falls off).
- Consequences:
  - The build report's frame-0 numbers (always the second frame of a run) are single noisy draws and do not reproduce.
    For example, E28 carved f0 was reported as 0.08/1.0, and E1 default f0 as 2.16/12.4.
  - Per draw, the carve still beats the default: E28 guest passes 5 of 6 carved draws vs 2 of 6 default; E1 guest passes
    3 of 6 carved draws vs 0 of 6 default.
  - The pre-registered single-draw criterion 2 is therefore a coin flip near its 1 cm / 5° threshold. Any later
    criterion should use at least 3 draws.

**(c) Loading, contacts, debris, submitted meshes: PASS, with two budget warnings [M].**
- `make_assets.py meshes/library_v3 OUT --pieces meshes/carve/ev01|ev28|ev30` gives:
  - the same set of collision pieces (by md5) as the tested `*_cut` assets;
  - URDF collision counts equal to the piece counts;
  - unchanged `<inertial>`;
  - a visual GLB md5-identical to the default.
- The FlashCHORD scene builds. Every piece stays one shape (collide shapes 53/107, 104/104, 114/90, 32/85), with no
  NaN in any run.
- Every carved-piece vertex lies inside the default hulls (0 outside at 0.2 mm tolerance), so nothing is added outside
  the old collision envelope.
- Smallest new piece: 0.02 cm³, thinnest 0.44 mm (3V/A). The smallest piece overall is an untouched CoACD hull
  (1.9e-11 m³, far above MuJoCo's 1e-15 limit).
- The carve adds 6–22 pieces under 0.1 cm³ per object. They are rigidly attached, so they are not loose debris.
- Contacts: the training env config gives naconmax 256 and njmax 512 per world (not the 4096/16384 in note 19).
  - Reset contacts, hands parked: carved 2–21 vs default 6–46.
  - Peak over 3 s: carved ≤ 54 contacts and 228 constraint rows vs default ≤ 71 and 296.
  - Headroom with hands grasping is unmeasured [E: likely sufficient; falsified by a nacon/nefc log in a zero-action
    replay with hands].
- **Budget warning (note 19 C4: S_A + S_B ≲ 165 shapes per episode at 4096 worlds):**
  - E28 carved 208 shapes and E14 204: over budget, ≈ 1.8× the pair memory [E];
  - E1 160: at the limit;
  - E30 117: within.
- Submitted meshes are untouched:
  - `git status` lists only the untracked new files;
  - `meshes/library_v3` is unchanged (make_assets output md5 = v3_def);
  - only `<collision>` elements change.

**(d) Guest fall-through or sinking: E1, E14 and E28 sink slightly; E30 FAILS (falls through the slot) [M].**
- Free travel of the carved guest before it touches the carved host (MC test), compared with the simulated sink at 3 s:

  | Case | free travel (host frame) | simulated sink at 3 s |
  |---|---|---|
  | E1 lid, f0 and f305 | 6 mm downward | lid 0.6–1.0 cm below its reference relative to the pot, in every carved draw |
  | E28 pot, f206 | 11 mm downward | ≤ 0.5 cm: the table catches it |
  | E14 cup, f150 | 6 mm | cup and rack both drop about 0.9 cm in the world; relative ≈ 0 |
  | E30 sweeper, f242 and f0 | > 40 mm downward | 2.5–3.5 cm drop and 48° tilt in 2 of 2 draws |

- Default E1 instead pushes the lid up 1.2 cm.
- E30: the sweeper drops through the carved rack slot onto the table. The sweeper loses 35 % of its hull volume
  (150 → 98 cm³). Do not train on ev30 v2.
- E14 rack drop: at reset the rack–support contacts are only 3, the deepest at −0.64 mm, and the rack falls about
  0.9–1.2 cm (with default hulls too). This contradicts the build report's [H] that "the rack interpenetrates the
  table": the rack is under-supported in the reference, not inside the table [H]. This drop, not the carve, makes E14
  fail its host criterion.

## 1. Recommendation

None of the four eval carves passed the pre-registered criterion, so retraining any of them is a deviation and needs
the owner's explicit go-ahead.

| Episode | Recommendation | Reasons |
|---|---|---|
| E1 | **retrain** (strongest case) | twin P2mck passes against GT; carved draws beat default in 6 of 6 pairs; H5 0.822 ± 0.239 leaves the most headroom; known cost: the lid sits 0.6–1 cm low |
| E14 | **retrain** (grasp lock, its own sf asset copy, so no pack conflicts) | cup drift is better per draw (2.21/22.5 → 1.48/12.5 and 0.88/3.5); the twin narrowly misses; the remaining failure is the rack's own drop |
| E28 | **do not retrain** | stable (0.931 ± 0.033); the rule needs ≥ 0.961, above every std draw seen (max 0.949); 208 shapes is over budget; its white_pot clashes with E1's carve in the pack |
| E30 | **do not retrain with v2** | the guest falls through; twin P31 is worse against GT (6.38 vs 4.33 cm) |

## 2. Prerequisites (blockers; all before launch, CPU)
1. **Commit and push** `pipeline/placement_carve.py`, `meshes/carve/ev01`, `meshes/carve/ev14` (plus ev28 and ev30
   only if they are used) and this plan. Every launch names that `SHA`.
2. **Per-episode asset root at pack time (code change, not yet written).**
   - `pack_eval.sh` builds ONE `/content/assets` for all standard-learner episodes (1, 10, 19, 25, 28, 30) and merges
     `ASSET_PIECES` per object, first wins.
   - So E1's carved `white_pot` would silently replace eval 28's pot. Likewise a rack carve would hit 28 and 30, and
     ev30's sweeper would hit 19.
   - Fix: build the carved episode's assets in their own root (e.g. `/content/assets_ep1`, make_assets `--pieces`) and
     rewrite only that episode's reference `object_urdf_paths` to it.
   - Test: on CPU, the pack's ep1 URDFs show 53/107 collisions and ep28's show the default 43/31.
   - E14 needs none of this, because grasp-lock references carry `refs/sf/ep14/assets`.
3. **E14 asset path.**
   - The stored glockt reference names `/content/refs/sf/ep14/assets/urdf/*.urdf` [M]. With `REUSE_REF=1`, `PIECES`
     only changes `/content/assets`, so on its own it would silently train on default hulls.
   - The job therefore carves the pulled sf assets in place (`placement_carve.py assets`).
   - That copy survives glock_public's second pull, because `store.sh pull-run` copies with `cp -rn` (no clobber).
   - The sf meshes are geometry-identical to library_v3 (vertices and faces, inertial) [M].
4. **`carve_rerun.sh` with EP=1** would look for `meshes/carve/ev1`, which does not exist, and exit. Pass
   `PIECES=/content/v2d-track3/meshes/carve/ev01`.
5. Ledger `planned` lines; offers ≤ $1.5/h (RTX PRO 6000, on demand); the owner's go-ahead.

## 3. Launch commands (repo root, after `SHA=<pushed sha>`; jobs self-destroy via run_job.sh; stall watchdog as usual)
```bash
SNAP=pt2.11-cu130-py313-20261020; C=${SHA:0:7}; D=$(date -u +%Y%m%d)
# ---- E1: standard learner on the stored reference, carved collision copy (ev25/ev10 pattern, 26 Oct) ----
for SEED in 42 43; do
  python3 ops/ledger.py add planned $D-c01s$SEED-$C 5.5 "eval-1 placement carve ev01, std learner s$SEED"
  ops/vast.sh V2D_COMMIT=$SHA ENV_SNAPSHOT=$SNAP create $OFFER $D-c01s$SEED-$C \
  'PULL_SUB="refs/perc2mck/ep1 perc2/ep1" bash ops/box/store.sh pull-run 20261024-pack-31ef267 >> /content/prepull.log 2>&1
   R=$(ls /content/refs/perc2mck/ep1/processed/*/*/*.parquet | head -1)
   [ "$(md5sum < $R | cut -c1-32)" = 7f2304663b4e3c55a0a1ad12503174c1 ] || { echo "[$(date -u +%FT%TZ)] ep1 ref md5 mismatch" >> /content/job.log; exit 1; }
   EP=1 SRC_RUN=20261024-pack-31ef267 SEED='$SEED' NREP=5 PIECES=/content/v2d-track3/meshes/carve/ev01 bash ops/jobs/carve_rerun.sh'
done
# ---- E14: grasp-lock fine-tune on the stored glockt reference (REUSE_REF), carved sf asset copy + PIECES ----
for SEED in 42 43; do
  python3 ops/ledger.py add planned $D-c14s$SEED-$C 3.5 "eval-14 placement carve ev14, glock REUSE_REF s$SEED"
  ops/vast.sh V2D_COMMIT=$SHA ENV_SNAPSHOT=$SNAP create $OFFER $D-c14s$SEED-$C \
  'export PULL_SUB="refs/perc2mck/ep14 refs/sf/ep14 refs/glockt/ep14 results/glock_public/ep14"
   bash ops/box/store.sh pull-run 20261025-evb1420-ee7ba8e >> /content/prepull.log 2>&1
   R=$(ls /content/refs/glockt/ep14/processed/*/*/ref_gl_ilc.parquet | head -1); A=/content/refs/sf/ep14/assets
   [ "$(md5sum < $R | cut -c1-32)" = 10d5f3ba6b7368ed30dad9d0c9c30df1 ] && [ -f /content/results/glock_public/ep14/rest_check.json ] \
     || { echo "[$(date -u +%FT%TZ)] ep14 stored reference incomplete/mismatch" >> /content/job.log; exit 1; }
   /content/v2d/robotic_grounding/flash_chord/.venv/bin/python pipeline/placement_carve.py assets $A meshes/carve/ev14 /content/sf14_cut \
     && rm -rf $A && mv /content/sf14_cut $A || exit 1
   [ $(grep -c "<collision>" $A/urdf/blue_cup_rigid.urdf) = 114 ] && [ $(grep -c "<collision>" $A/urdf/plastic_dish_rack_rigid.urdf) = 90 ] \
     || { echo "[$(date -u +%FT%TZ)] ep14 carved sf assets wrong" >> /content/job.log; exit 1; }
   export REUSE_REF=1 SF=1 REPLAN=1 EVOLVE=0 CURVE_REP=3 NREP=5 SPLIT=eval SEED='$SEED' LIB=/content/v2d-track3/meshes/library_v3
   export GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"
   PIECES=/content/v2d-track3/meshes/carve/ev14 PAIRS="14:20261025-evb1420-ee7ba8e:mck" bash ops/jobs/glock_public.sh'
done
# ---- NOT recommended (section 1); listed for completeness, same pattern ----
# E28: EP=28 SRC_RUN=20261024-pack-31ef267, md5 6f57deb27e47abcd7ec2afe739354af1, PIECES=.../meshes/carve/ev28 (needs prerequisite 2)
# E30: EP=30 SRC_RUN=20261024-ev30rp-07eef1a, md5 dd464c96184e84400e62ffcfa17a6ac4, PIECES=.../meshes/carve/ev30 (guest falls through: do not run)
```
Notes:
- E14's `REPLAN`, `EVOLVE` and `GL_ARGS` are evb1420's logged values. With `REUSE_REF` the reference stages are skipped,
  so they are only logged. Training is the stored run's recipe at the new SHA.
- [H] Recipe drift between ee7ba8e and the new SHA is confounded with the carve. An optional same-SHA default-hull
  control (E1 s42 without PIECES, ≈ $5) would separate the two. It is not in the costed batch.

## 4. Pre-registered choice rule (written before any result; GT-free)

**Candidates.** For each episode, the candidates are carve s42 and carve s43.
- Each candidate's checkpoint is the one its own job picks (sim_vs_ref curve).
- That checkpoint gets 5 official evaluations (NREP=5).
- From these, compute the mean and the sample sd (ddof=1, as in H5's `h5_summary.json`). Do not use the summary
  json's `std`, which is ddof=0.

**Adoption.** Adopt a candidate only if both conditions hold:

| Episode | mean ≥ (H5 mean + 0.03) | sd ≤ (H5 sd) |
|---|---|---|
| 1 | 0.8519 | 0.2387 |
| 14 | 0.6452 | 0.1989 |
| (28) | 0.9612 | 0.0333 |
| (30) | 0.8284 | 0.2552 |

- If both seeds qualify, the higher mean wins; within 0.005, the lower sd wins.
- If neither qualifies, the packed policy stays, and so does its pack 6 rollout.

**Packing.**
- An adopted policy is packed with ONE fresh official evaluation in the pack. Never pack one of the 5 draws, and never
  pack a best draw.
- Before comparing, check that the scoring reference is the md5 above, so the object trajectory is identical.
- Caveat [E]: with n = 5 and an sd near 0.2, the SE of the mean is ≈ 0.09. The +0.03 margin alone would admit a
  no-better policy about a third of the time, and the sd condition only partly guards against that. Raising NREP to 10
  (parity with H5) costs ≈ +10–15 min per box [E].

## 5. Cost (at ~$1.5/h)
- Durations measured on 26 Oct, 250M steps + curve + 5 evaluations, one episode per box [M]: carve_rerun c25 ≈ 3.0 h,
  c10 ≈ 2.8 h.

| Item | Estimate [E] |
|---|---|
| E1, per seed | 3–4 h (160 shapes vs 32 or 102 before) → $4.5–6 |
| E14, per seed | 1.5–2.5 h (70M steps, curve ×3, 5 evaluations, no reference build) → $2.3–3.8 |
| **Recommended batch** (E1 ×2 + E14 ×2, 4 boxes) | **≈ $14–20** |
| Pack, if a candidate wins | ≈ $0.7–1 |
| E28 + E30, if the owner overrides section 1 | ≈ +$18–24 |

- Session budget: ≤ $45, of which $2.45 is actual and $13.50 planned, so ≈ $29 is left. The recommended batch fits.
- Not done here: STATUS.md and work-log entries, the commit, prerequisite 2's code and its CPU test.
