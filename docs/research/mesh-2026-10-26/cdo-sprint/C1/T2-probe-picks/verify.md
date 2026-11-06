# C1 / T2 probe picks: adversarial verification (2026-10-31, ~16:55-17:05 UTC)

Verifier: a separate agent that did not build T2. Scope: the T2 result (PREREG `6f71234`, results `9e41d09`): mini
dust pan adopted, water pitcher and beige cup rejected on the add_med gate. Scratch: `SCR/cdo_c1/t2_verify/`
(`SCR = /tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`). Step log: the
`VERIFY` lines in `NOTES.md`.

Labels: [D] public scan or mocap as stand-in, after inference; [M] measured without ground truth; [E] estimate;
[H] hypothesis.

## Verdict
**Confirmed. Nothing blocks adopting the dust pan.**
- Every number the track reports was reproduced from its stored records, or recomputed.
- The mesh, the mesh dirs and the order of events check out.
- My re-runs are byte-identical: one AUC twin (base and single) and the GT-free placement.
- The track left one item open: the packed baseline rows. I checked them, and they match.

There are seven non-blocking findings. The most important is the first: the T2 outcome was already known as a [D]
result before the pre-registration, so it is a replication, not a blind test.

## Checks

| # | check | how | result |
|---|---|---|---|
| 1 | PREREG pushed before any scan read | `git reflog` of `origin/claude/bold-albattani-6qmxsv`; file mtimes in `SCR/cdo_c1/t2/` | PREREG text first pushed 16:23:57 (inside another agent's WIP snapshot `0e64c7f`), then final `6f71234` pushed 16:24:49 (one sentence changed). First scan read: `score_t2.py` started 16:25:01. Parquet download (stage 0): 16:25:11 or later. AUC runs: 16:32-16:33. **OK** |
| 2 | Scripts frozen after PREREG | `git diff 6f71234 HEAD` on `scripts/`, `PREREG.md`, `results/place/`, `auc_prep.json` | no change. **OK** |
| 3 | Construction and choices are GT-free | read and grepped `place.py`, `pack_check.py`, `auc_prep.py`, `scripts/obs_fidelity.py`, `gen/sim3_fit.py` | Inputs: the probe ply, our library_v3 glb, our `obs_all` points, our sweep tracks, the kit packer. No scan, mocap, parquet pose or `*_align.npz`. **OK** |
| 4 | Input is the probe-scored mesh | sha1[:16] of the `sam3d_sim3` plys against `gen-probe/scores.jsonl`; sha256 against `SHA256SUMS` | 96a771df / 6434ba5a / 9eededb8 match. **OK** |
| 5 | Probe pick is GT-free | `gen-probe/selection.json` | dust pan pick = `gen/sam3d/ep39_mini_dust_pan_k297_s42` (GT-free argmin); same for pitcher and beige. **OK** |
| 6 | Scored mesh = adopted mesh = AUC mesh = HF copy | sha256 of git `meshes/`, `SCR/.../place/`, `auc/single_mini_dust_pan/mini_dust_pan.glb`, HF LFS sha256 (`runs/cdo-c1-t2-20261031/place/`); sha1[:16] in `score_t2.jsonl` | All `2fb147b5...7d02`; scored sha `3a0c62f390b4646e`. Pitcher `ba38d409...` and beige `8c6e063d...` also match. **OK** |
| 7 | One scoring per mesh | grepped the three sha1 values over scratch, `docs/` and `results/` | Each appears in one `score_t2.jsonl` record only. **OK** |
| 8 | AUC runs used the intended mesh dirs | `auc/base` against `meshes/library_v3` (sha256, 10 files); `single_mini_dust_pan` against `base`; `meshes` field of each run JSON; looked for `episode_*` subdirs | base = library_v3 exactly. single differs only in `mini_dust_pan.glb`. No subdirs. Every JSON names the intended dir. The dust-pan registration changes (rot 2.4 to 0.85-1.15 deg); every other object's registration is identical. `score_registered.py` exits when `--meshes` lacks a mesh; it falls back to the scan only without `--meshes`. **OK** |
| 9 | Same kit and scans for both scorers | `SCR/loc/kit` against `SCR/kit`; sha256 of the scans | `loc/kit` is a symlink to `kit`. Scans `loc/t3/mesh` = `data/scan` (sha256). **OK** |
| 10 | Tracks | recomputed `world_T_cam @ cam_T_obj` from `data/sweep/ep{18,39,40}/poses.npz` | equal to the track files. **OK** |
| 11 | Twins complete | `cam_T_*` keys of all 20 public sweep episodes | dust pan appears only in 18, 39 and 40. **OK** |
| 12 | Gate constants and verdicts | recomputed from `score_t2.jsonl` and `baseline_library.jsonl` | Dust pan: CD-O thr 0.331 - 0.02 = 0.311. Probe 0.2619 / 0.2592 and the placed copy's own 0.2587 / 0.2601 all pass. add_med6 4.83 (seeds 19000158, 38000114, 11, 22, 33, 44) <= 5.65 + 2 = 7.65. Flips 0 of 32. Pitcher add_med6 28.405 > 9.97. Beige 15.025 > 8.97. Verdicts as reported. **OK** |
| 13 | AUC guard arithmetic | recomputed dX from the six run JSONs | dAUC -0.0014 / +0.0153 / +0.0233, mean +0.0124, min -0.0014. Mean dMPPE -0.1277 cm, mean dRPE +0.0015 cm, dSP = dMP = 0. **PASS** as reported. |
| 14 | Eval slots | kit `track_3_evaluation_objects.json` | eval 19 = [mini_sweeper, mini_dust_pan] (slot 1); eval 38 = [mini_dust_pan] (slot 0). **OK** |
| 15 | Packed baseline (T2's open item) | pack 4 `results/submissions/20261026-track3d/track3_submission.cd-o.parquet`, rows `t3m_000019_mini_dust_pan_{0,1}` and `t3m_000038_..._{0,1}` (vertices, faces) | Both equal `budget_mesh(meshes/library_v3/mini_dust_pan.glb, 4096, 4096)` exactly, vertices and faces. So 0.331 is the right packed baseline. **Closed** |
| 16 | Board effect | (0.3274 - 0.2619) + (0.334 - 0.2592) = 0.140 over 36 pairs | -0.0039 cm [E]. **OK** |

## Re-runs (verifier, after T2's push; no new mesh scored)
- **AUC twin ep18** (the only twin with a negative dAUC). I ran `pipeline/score_registered.py` for `base` and
  `single_mini_dust_pan`, with the same track, mesh dirs, `t3` and kit, writing to `SCR/cdo_c1/t2_verify/runs/`.
  Both JSONs are **byte-identical** to the track's [D]. These are two scan reads that re-run existing scorings
  unchanged, not new mesh scorings.
- **GT-free placement.** I re-ran `place.py mini_dust_pan` into `SCR/cdo_c1/t2_verify/place/`. The glb sha256 is
  **identical** (`2fb147b5...`), and the JSON matches except for its paths [M]. Best start pca03, residual 2.774 mm,
  scale 0.9963, second distinct start 4.468 mm at 112 deg.

## Findings (none blocking)
1. **The outcome was known before pre-registration, so this is a replication, not a test** (integrity, disclosure).
   - `diag-2026-10-30/sam-placement-verify/m7_kitlike.jsonl` and `m7_summary.md` had already measured the `lib`
     placement of these same s42 SAM 3D meshes, with a kit-like ADD over 3 seeds [D]:

     | object | `lib` placement ADD | library_v3 ADD |
     |---|---|---|
     | dust pan | 4.3 mm | 5.6 mm |
     | pitcher | 23.8 mm | 7.6 mm |
     | beige cup | 16.2 mm | 6.5 mm |

   - T2's results (4.83, 28.4 and 15.0 mm) reproduce these.
   - The diag README also says `lib` was chosen post hoc, from six variants, on [D].
   - T2 discloses that it read the README's statement ("better on the dust pan"), but it calls its expectation a
     "GT-free prediction" [H]. It was a [D]-informed expectation. Both the method and the object that wins were picked
     with public-scan knowledge.
   - Effect: the dust-pan [D] numbers are somewhat optimistic as stand-ins for the hidden scan. The margins are wide,
     though: CD-O 0.26 against 0.311, ADD 4.83 against 7.65 mm, and dAUC +0.012 against -0.005. Selection over 1
     method x 3 objects is unlikely to remove them [H].
   - RESULTS should not count H-T2's survival for the dust pan as independent evidence.
2. **The CD-O gate used the probe's CD-O, not the placed copy's one-shot CD-O.** The brief asks for the latter.
   This was pre-registered, and the placed copy's own values (0.2587 / 0.2601) pass too. No effect.
3. **The beige-cup eval-8 add threshold.** It used library_v3's 6.97 mm (as briefed). Eval 8 packs library_v3x
   (add_med 5.51 mm), so the stricter threshold is 7.51 mm. The beige pick fails either way (15.0 mm). No effect.
4. **ep39 is an in-sample twin.** The SAM 3D mesh came from an ep39 crop (k297), and the probe's point fit used ep39
   points. The two independent twins pass on their own: ep18 -0.0014 and ep40 +0.0233, mean +0.011 [D]. No effect.
5. **The joint run is still open for ep18.** The dust pan shares ep18 with the sweeper. The diag lists sweeper
   candidates (C1 balls, M2, P1). If any sweeper swap enters the same pack, ep18 needs a joint base/swap run before
   both ship.
6. **A better [D] dust pan exists, but it must not be chosen on that basis.** In the probe, `gen/hy21/ep39_mini_dust_pan_k297_s42` scored CD-O 0.2301 / 0.2328 and
   ADD 5.2 mm at its point-fit pose. It was not the GT-free pick. Choosing it now would be a selection on [D]. I list
   it for transparency, not as a recommendation.
7. **Small wording and provenance points.**
   - The observation-fidelity gap is 0.67-2.0 mm, not "0.5-2.0".
   - The adopted mesh inherits library_v3's frame, which is on the provenance denylist. This is disclosed and is the
     owner's call.
   - The PREREG text first reached origin through another agent's WIP snapshot (`0e64c7f`), 52 s before the track's
     own commit. That is harmless: it was still before any scan read.

## What I did not check
- The organisers' hidden scans. All CD-O, ADD and AUC numbers here are public-scan stand-ins [D].
- The probe's generation step itself (SAM 3D inputs and crops). I relied on the gen-probe SHA256SUMS and on its
  earlier verification.
- The sweeper-swap status of the packs being built in parallel (C0b, E0). See finding 5.
