# Tracker fixes from the four public diagnoses (ep0, ep11, ep24, ep31): plan (30 Oct 2026, ~00:30 UTC 31 Oct)

Inputs: `ep0/`, `ep11/`, `ep24/`, `ep31/` DIAG.md here; `../PLAN.md` §2/§4 (LB conversion, acting rules). Labels: [M] measured,
[E] estimate, [H] hypothesis. CPU only, $0, nothing launched or committed. **Every rental below needs the owner's go-ahead.**
Every fix is GT-free and uses our meshes (library_v3) unless the "meshes" column says otherwise. Mocap was read only to diagnose.
LB value [E] = n_eval × Δ / 20 × c, where n_eval is how many eval episodes share the mode, Δ the per-episode rollout gain,
and c ∈ [0.74, 1.0] the transfer [M, refcheck/mapping].

## 0. Owner summary
1. None of the four starting hypotheses held. Three failures (ep0, ep24, ep31) are one frame-0 pose amplified by the kit's
   scene alignment. The fourth (ep11) is the static outer cup's track rising 2.5–5.3 cm while the other cup is nested in it.
2. Fixes with eval value: freeze objects that never travel (eval 10, central +0.007 LB) [E]; a camera (VO) fix (eval 25 and
   any eval with a keyframe burst, +0.004) [E]; occlusion-aware anchor registration (eval 30, +0.003) [E]; a detection size
   gate plus backfill (pot and pitcher evals, +0.03–0.04 per affected eval, but none is known to be affected) [E].
3. Three always-on frame-0/anchor corrections failed their own no-harm rules on 20 public episodes. The gates that rescue
   them were set after seeing the data. So root-cause perc2 changes come first, and post-hoc rules only as detectors.
4. Cost [E]: about $0–1 on CPU, then about $1–2 for one GPU perception box. Rollout gates and eval retrains cost about $12–40
   in total, spent only on fixes that pass their public test and have an eval target.
5. A $0 GT-free screen of the stored eval outputs decides which of the four modes exist on eval at all. It reads the outputs
   and changes nothing.
6. Mesh-session items (registration-safe sweeper, beige cup base, lid template frame) are worth ≤ +0.003 LB, unless the
   host's sweeper scan differs from the public one (then up to +0.017).

## 1. Cross-check: one number per diagnosis, recomputed independently (`plan_check_scripts/spot.py`; jumps: `jumps.py`, `ep18.py`) [M]
| ep | claim in DIAG | recomputed here (own code, Phase-1 tracks) | verdict |
|---|---|---|---|
| 0 | P_s pot guard jump at f64: 5.19 cm, 176.1°; f0–63 wobble 3.2 cm / 20.8° | 5.19 cm, 176.1°; 3.23 cm / 20.8° | agrees |
| 11 | P_o blue cup lift: peak +5.3 cm (f60–69), ≈ 2.4 cm in F, horizontal ≤ 1.0 cm | peak 5.41 cm at f67 (track displacement); F mean 2.21 cm; off-axis ≤ 0.95 cm | agrees |
| 24 | P_o board 2 steps at keyframes f36/38/40/49: 0.41/0.28/0.66/1.05 cm; ≤ 0.48 between | 0.41/0.28/0.66/1.05; 0.48; 2.47 cm off at f110 | agrees |
| 31 | sweeper frame-0 rotation error 9.1° (world, P_o) | 9.8° in the rack's frame (includes the rack's own 1–2°), 1.3 cm | agrees |

Other findings of the cross-check:
- **Unexplained event [M]:** P_o and P_o2 ep18 sweeper jumps 15.6 cm / 80° at f155. No DIAG covers it, and the ep0 claim that "no
  other public track has a re-acquisition" holds only for the 25 Oct refine tracks. ep0 F2 would not fire there (pre-jump motion
  13.8 cm), and ep18 scores 0.917 \*. It goes into test T4b. No other Phase-1 P_o/P_s track jumps by more than 5 cm or 30°,
  apart from ep23 (identity swap, known) and P_s ep0.
- **Wiring [M]:** `pipeline/pipeline_ep.sh` does not call `pipeline/refine.py`, and refine's `DEFAULT_STEPS` still lists S1 and S3,
  which were rejected on 30 Oct. Two DIAGs both name their new step "S6". Here: **S6** = static hold (ep11), **S7** = keyframe-gated
  camera correction (ep24), **S8** = gated frame-0 polish (ep31 F1g), **S9** = backfill (ep0 F2). Proposed order: S0, S7, S6, S9, S8,
  S2. Every public gate runs with `--steps` explicit, on the adopted chain (S2 only), and the eval build must call the same chain.
- **ep24 value arithmetic:** 0.5–1.5 jumped evals × 0.157 / 20 × c gives +0.003 to +0.012. The DIAG's +0.002 to +0.008 (central
  +0.004) assumes smaller jumps outside eval 25. Kept as central, with +0.012 as the upper bound.
- ep31's coverage screen reads the **pre-guard** `det_f0.npz` mask. Its "coverage ≈ 0" on ep0's lid is the guard's re-registration,
  not an error. The eval screen must use the post-guard pose and mask.
- Consistent across files [M]: ep11's static hold on ep31's rack gives lib +0.000 (both files). ep11 Fix 2 is the same code as
  ep31 F2. Pot/pitcher exposure lists agree (1, 3, 5, 6, 8, 20, 28).

## 2. Failure modes → fixes
| mode (twin) | mechanism | fix, where | eval exposure | LB [E] | cost | meshes |
|---|---|---|---|---|---|---|
| **M1 static container lifts under a nested object** (ep11) | [M] jump at the nest (+5.3 cm), offset held; [H] aperture: rim and base hidden | **S6 static hold**: freeze an object whose perceived horizontal travel is < 2 cm (non-axisymmetric objects also need rotation < 10°); `refine.py` | **10**; marginal: 14, 28, 30, 15, 16, 3 | 1 × (0.10–0.24) / 20 × c = **+0.004–0.012, central +0.007**; others ≤ +0.001 | CPU ref; rollout gate $2.6–5.2; eval-10 retrain $2.6 | ours |
| | same | **Mask the other objects** out of the tracker's depth/RGB (render with nvdiffrast) + track frame by frame; `perc2.py` | 10, plus moving containers 32, 33, 5, 1 | duplicates S6 on 10; extra ≤ +0.003 | GPU re-track (shared box) | ours |
| **M2 rotation anchor's frame-0 tilt** from contaminated input (ep31) | [M] 9° tilt fits the fin-contaminated mask better than truth; kit alignment turns it into a 2.8 cm error on the rack | **Occlusion-aware registration**: large objects first, mask occluders, drop mask pixels > 2 cm in front; `perc2.py`. Fallback **S8** = trimmed ICP polish only on a rotation anchor with mask coverage < 0.70 | **30**; 19 low; spoon anchors 32, 33, 35–37 unknown (not added) | 1 × (0.04–0.086) / 20 × c = **+0.0015–0.004, central +0.003**; ≤ +0.0075 with the physics start fix | GPU re-track (shared box); rollout $2.6–5.2 (+$6 std learner) | ours |
| **M3 VO camera jump** at a keyframe burst (ep24) | [M] 2.4 cm common-mode step over f33–51, held to the end; [H] SIFT on moving board and hands | **Robust VO** (match the earliest usable keyframe, mask objects and hands, or vo17 stereo map) + **table-plane constraint** at keyframes; `perc2.py` camera block. Detector/fallback **S7** gated at ≥ 1 cm | **25** (p 0.2–0.5); any eval with a burst (5, 1, 28, 20, 19 candidates) | (0.5–1.5) × 0.157 / 20 × c = **+0.002–0.008, central +0.004**, upper +0.012 | CPU only for the reference (VO re-run, recompose); retrain flagged evals $2.6–7 each | ours |
| **M4 frame-0 detection decoy** (ep0, scan arm) | [M] table-top proposal wins on intensity; anchor registered upside down; scene rotated 180° | **Area gate** (bar proposals > 1.5 × the template's largest silhouette area; `det_rules.py`/`detect()`) + **S9 backfill** after a ≥ 5 cm / 30° guard re-acquisition | pot/pitcher anchors 1, 3, 5, 6, 8, 20, 28 (gate); re-acquisitions 8, 14, 32, 33 (S9) | 0 now (public P_o 0/11 failed); **+0.031–0.041 per flagged eval**; insurance for any re-perception | CPU replay $0; GPU check (shared box) | ours |
| lid offset 1.4–1.8 cm (ep0), beige base +1.8 cm (ep11), sweeper registration flip 25/50 (ep31 L1) | [M] template shape and frame (L1/L2) | mesh session: lid template frame, flat-base cup rule, registration-safe sweeper (0/50 flips) | 1; 10, 8; 30, 19 | ≤ +0.001; ≤ +0.002; 0 if host scan = public, else ≤ +0.017 | mesh session, then re-track | **better meshes** |
| sweeper ejected at the first sim step (ep31 audit) | [M] 11.3° start transient | split rack hulls / depenetrate (physics session) | 30 | with M2 ≤ +0.0075 | rollout | physics |

## 3. Pre-registered public tests (frozen here, before any run; thresholds never tuned on eval)
- **T1 S6 static hold.** Reference, committed code, `refine/in` + Phase-1 P_o/P_s, on top of S2. Pass: the frozen set equals the
  mocap-static set on 20/20 episodes, and no episode Δ < −0.002 (lib or \*). Rollout: ep11 c1 vs c1+S6, seeds 42/43, NREP 10.
  Pass: seed-mean T vs mocap ≥ +0.05 and S ≥ 0.70; otherwise falsified.
- **T2 masking + occlusion-aware registration** (one GPU box, 20 episodes, P_o + repeat, depth caches reused). Pass: ep11 blue
  \* ≥ 0.95, ep31 sweeper f0 error ≤ 4°, ep31 lib ≥ 0.93, no episode down > 0.01 \*, repeat identical. Falsified for ep11 if
  blue \* < 0.90; for ep31 if the f0 error stays ≥ 7° (then S8 or re-segmenting the anchor remains).
- **T3 S8 gated polish** (gate frozen: coverage < 0.70, trim 80 %, ≤ 15°, ≤ 3 cm), on the fresh T2 tracks with masking off. Pass:
  the gate opens on ep31 with lib ≥ +0.05 and no opened episode < −0.005. Rollout: falsified if the ep31 seed-mean T rises < +0.03.
- **T4 area gate + S9.** (a) `det_replay`/`det_score` on the 23 Oct dumps: reject if any instance R0 gets right turns wrong.
  (b) On the T2 box: P_s ep0 \* ≥ 0.95, no P_o episode down > 0.005 lib. (c) S9 must not fire on any P_o track, or if it fires,
  must not lower it by > 0.005. **T4b:** report why ep18's sweeper jumps at f155 (guard log line) before S9 is adopted.
- **T5 robust VO + plane constraint** (CPU). First ep24 alone with vo17 on this VM (2 public b/c video pulls, $0), then 20 episodes
  on a CPU box. Pass: ep24 P_o \* ≥ 0.95; common-mode error ≤ 0.8 cm; no episode's common-mode error up by > 0.3 cm; no episode
  < −0.02. Plane-only: ep24 \* ≥ 0.93. Falsified if ep24 \* < 0.90 (VO) or < 0.88 (plane). S7 stays only if T5 finds the same ≥ 1 cm
  jumps that S7 finds (ep24 only). Rollout: ep24 seed-mean T ≥ +0.05.

## 4. Ranked order of work
1. **Eval 10 static hold (M1, S6).** It has the strongest evidence (frozen set = static set on 20/20, no episode worse) and the
   largest central value (+0.007). Commit S6 and run T1's reference part (CPU, $0). Run S6 GT-free on eval 10's stored track,
   listing the frozen objects and checking the overlay. Then, with the owner's go-ahead, the T1 rollout ($2.6–5.2) and an eval-10
   retrain with 2 seeds ($2.6); swap only under the multi-draw rule. This also delivers task 18 (physically consistent cup nest).
2. **$0 GT-free eval screen**, thresholds frozen in §3. It is eval QA outside the leak study (`../PLAN.md` §6), gets its own note,
   and changes no reference:
   - area ratio of the chosen proposals on 1, 3, 5, 6, 8, 20, 28;
   - S9 conditions on 8, 14, 32, 33;
   - `vo.json` bursts (≥ 4 switches in 25 frames) plus the S7 magnitude, on all 20 evals;
   - post-guard anchor mask coverage on 30, 19, 32, 33, 35–37;
   - S6 frozen sets on all 20 evals.

   The result decides whether steps 3–5 have any eval target.
3. **T5 VO** (CPU): ep24 on this VM first ($0), then a 20-episode CPU box ($0.3–1, go-ahead). It is CPU only and protects every eval.
4. **One GPU perception box** (about $1–2, about 1 h, go-ahead). It runs T2, T3 and T4(b) on one depth cache per episode. Build the
   perc2 flags (area gate, masking, registration order) and mock them on CPU first.
5. **Rollout gates** only for fixes that passed and have an eval target: ep31 (M2), then ep24 (M3). Then retrain those evals under
   the multi-draw rule. Budget about $5–25 [E].
6. **In parallel, no GPU from us:** the mesh session (registration-safe sweeper first: it is the only mesh item with > +0.003 upside;
   then the beige base and the lid frame) and the physics session (ep31 start-consistent hulls, audit H31-1).

**Dropped [M]:** frame-0 smoothing (ep0 F3: +0.0003, 10 episodes down); ungated frame-0 ICP (ep31 F1: ep12 −0.015/−0.085);
always-on S7 (ep21 −0.043); lid seat constraint (ceiling +0.003); upright snap; rack depenetration; the cup-upright correction U1/U2.
**For the leak readings:** read L2 on ep0 from the backfilled P_s (0.995, a CPU proxy), and book L3 on ep24 as camera (0.149 of 0.151).
