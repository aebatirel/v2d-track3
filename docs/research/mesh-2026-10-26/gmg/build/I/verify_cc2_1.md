# verify_cc2_1: physics, geometry and contact-budget check of collision carve round 2 (T-I16 public 719e1a8, eval precheck cea1342)

Verifier of the collision-carve round-2 workflow, physics / geometry / contact-budget lens. 1 Nov 2026, 02:06-03:05 UTC.
Checked: the T-I16 public rerun (`build/I/results/collcarve2-public/`, run code 88f49df, run folder
`<scratch>/gmg/runs-dev/20261101-fi5r2pub-88f49df`) and the eval precheck (`build/I/results/collcarve2-evalcheck/`,
data `<scratch>/evck`), against PREREG F-I5.15 / F-I5.16 / F-I5.17 and the run's own pieces, SHELL bodies, tracks,
hands and records.

**Integrity.** Public inputs are GT-free: our v6 bundle tracks and table plane, our M1 hands, the run's `shell_t5p36`
candidates, its structure JSON and its round folders. No scan, mocap, parquet `pose`, `*_align` file or scan-derived
constant was read. The eval spot-checks read only the evalcheck's own pose arrays (our perception references, tier P1)
and the pack's colliders as the simulator loads them; library meshes enter only as the pack's colliders, never as shape
evidence. Nothing was tuned and nothing decides anything: every number below is a post-hoc diagnostic. No gmg code was
edited and gmg was not imported by the measuring scripts (own voxelizer, own MJCF writer, own transforms; manifold
booleans and trimesh rays). Machine: this container, nice 10, every process capped at 5-6 GB after two of my first jobs
(pids 8991 and 9277, both mine, 8.9 and 13.1 GB) were OOM-killed by the memory cgroup at 02:16-02:17 UTC. No other
process was killed in that window, and I touched no other agent's process. Load 1-6. About 70 CPU-minutes.
No rental, $0. Labels: [M] measured here, [E] estimate, [H] hypothesis.

Scripts and outputs (scratch, not committed): `<scratch>/vcc2_1/` (`precheck_indep.py`, `precheck_w.py`, `vox.py`,
`pieces_geom.py`, `simcheck.py`, `evalspot.py`, `ringcheck.py`, `ringrough.py`, `scan_frames.py`,
`clean_frames_hands.py`; JSON / log beside each). `<scratch>` = `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`.
Commands: `nice -n 10 <venv>/bin/python <script> [args]` from that folder (args as listed in each section).

## Verdict

The round's measurements reproduce: delivered shares, the precheck numbers at four frames, the S outcome on delivered and
faithful pieces, the packed-default hull counts, the stray-ray counts behind B4 and the two eval rows I spot-checked. The
round's verdict stands: nothing may be used, and every public floor frame is `pose_impossible`. Two things change what
has to be decided next:

- **(B1) B4's proposed fix does not work.** The public README offers "B4's robust ring profile" as one of two cheap
  next changes. Its stated falsifier has fired in my independent measurement: with the robust profile, the 12-sector
  wall of the ep12 / ep13 blue cups still drops below 1.5 mm (in fact below 0), and it does so at 16, 24 and 32 sectors
  too. The stray sheets are not the main cause. The SHELL surface is rough by about 1 mm, and the cavity-safe ring rule
  turns that roughness straight into lost wall.
- **(B2) The eval precheck's "hands-off" is not the rule's hands-off.** The summary table counts H0 frames (no
  contact label). Many of those frames have a robot hand point within 0.4-3 mm of the object. F-I5.3 (b) and F-I5.16
  (3)(a) define hands-off as no hand point within 30 mm (H30). Under H30, the two headline table penetrations vanish:
  eval 14 goes from 16.6 to 3.2 mm, and eval 32 from 19.5 to 1.0 mm. The failing counts change too, for example eval 14
  from 47/63 to 18/29. These numbers are meant for the pose lanes, so they should be corrected before they are relayed.

## Blocking findings

### B1. B4's [H] is falsified on both blue cups; the mechanism is SHELL roughness, not only stray sheets [M]

Method (`ringcheck.py 12|13 blue_cup <phase>`, `ringrough.py`). I cast my own radial rays from the run's structure
axis (`ep*/structure_blue_cup.json`) through the `shell_t5p36` SHELL: every 1 deg, at the 1 mm level midpoints of the
main wall run, with all hits and parity intervals. The wall run's bounds come from the run's `diag/profile_*.json`. Per
sector and 1 mm row I computed the F-I5.15 (1b) wall: a tangent inner face at the sector's max of r_in cos(dphi), a
chordal outer face at its min of r_out cos(dphi) / cos(theta), wall = min(R_out cos theta - rho_in, R_out - rho_in / cos theta).
A 1 mm band is the most generous banding there is, so this "local" wall is an upper bound on check (i) for any layout.
On analytic profiles the formula reproduces the closed form (round: 3.853 mm at 12 sectors; a 1.5 mm eccentric
circle keeps 3.44 mm).

Reproduction of the run's diagnostics: stray rays with r_out more than 10 mm below the row median: **618** (run 617)
in 40 rows for ep12, **3,851** (run 3,852) in 64 rows for ep13. The median wall is 5.41 / 5.44 mm, and the r_out
median spans 33.7-46.0 mm, as in the run.

| cup, profile | rows of the main wall run with some sector < 1.5 mm (12 / 16 / 24 / 32 sectors) | min local wall, mm (12 / 16 / 24 / 32) | median local wall, mm (12 / 32) |
|---|---|---|---|
| ep12, innermost interval (the rule) | 167 / 167 / 168 / 168 of 168 | -20.3 / -19.4 / -19.0 / -18.8 | 1.3 / 4.1 |
| ep12, interval holding the row's median wall (B4's [H], as worded) | 139 / 99 / 86 / 75 | -1.14 / -0.48 / -0.27 / -0.02 | 2.9 / 4.5 |
| ep12, same, sectors offset half a sector | 151 / 100 / 83 / - | -1.16 / -0.40 / -0.07 / - | 2.7 / - |
| ep12, interval holding a fitted eccentric + oval circle (most favourable variant) | 154 / 148 / 138 / 111 | -2.08 / -1.11 / -0.33 / -0.43 | 2.7 / 4.6 |
| ep13, innermost interval | 169 / 168 / 171 / 169 of 172 | -26.9 / -32.0 / -27.0 / -28.2 | 1.7 / 4.5 |
| ep13, holding the row median | 121 / 103 / 103 / 88 | -1.09 / -0.43 / -0.22 / -0.06 | 3.0 / 4.6 |
| ep13, holding the fitted eccentric + oval circle | 126 / 102 / 86 / 81 | -4.86 / -4.10 / -2.42 / -1.46 | 3.1 / 4.8 |

- **B4's [H] reads** "take the interval holding the row's median wall ... Falsifier: with that profile, the 12-sector
  min wall of the ep12 / ep13 blue cups stays < 1.5 mm." It stays at -1.1 mm on both cups, under all three robust
  variants and both sector phases. More sectors do not rescue it: even at 32 sectors, 75-111 of 168 rows (ep12) and 81-88 of 172 (ep13) still fail.
- **Mechanism [M].** Fit r(phi) = a0 + a1 cos + b1 sin + a2 cos 2phi + b2 sin 2phi per row (eccentricity plus
  ovality). What is left over is roughness:
  - Residual std is 0.73 / 0.92 mm on r_in / r_out for ep12, and 0.81 / 0.68 mm for ep13.
  - The range of the residual inside one 30 deg sector has a median of 1.0-1.35 mm and a p90 of 2.7-3.9 mm, on each
    face.
  - The cavity-safe rule pays both ranges: the inner face must clear the sector's largest r_in, and the outer chord
    must stay inside its smallest r_out. On a 5.4 mm wall at r about 40 mm, that is 5.4 - 1.5 (chord loss, 12
    sectors) - 2.5 (median roughness) = 1.4 mm, under w_min = 1.5 mm in most rows. That is what the table shows.
  - The structure axis is also off the SHELL's centre: the median eccentricity of r_out is 1.84 mm for ep12 (p90 2.84)
    and 2.79 mm for ep13 (p90 5.31). Tangent faces absorb a constant eccentricity, so this is not the main cost. It is,
    however, why "the interval holding the row's median" rejects 20-31 % of the hit rays (44,564 of 55,991 and 36,381
    of 53,043 keep an interval).
- **Not caused by overlapping SHELL bodies** (see N4). I unioned the bodies first (manifold, `UNION=1`). The stray
  counts barely changed (618 -> 625, 3,851 -> 4,181), and the failure stayed (12 sectors: 136 / 104 rows below 1.5 mm, holding the
  median).
- **Consequence.** A never-intrude ring cannot keep 1.5 mm of these SHELL walls at any N_s up to 32, whatever profile
  interval it takes. [H] A ring that may intrude by a stated roughness allowance (for example, faces at the sector's
  95th / 5th percentile instead of max / min, with the intrusion reported) would keep about 3-4.5 mm. Falsifier: with
  quantile faces at q = 0.05, the 16-sector min local wall of the ep12 / ep13 cups stays below 1.5 mm. This trades
  F-I5.15 (1f)'s "intrusion <= 1e-6 m" for a measured allowance. That is a rule change for the orchestrator, not a code
  fix.

### B2. The eval precheck labels H0 frames "hands-off"; under the rule's 30 mm hands-off the headline numbers change [M]

From the evalcheck's own per-frame records (`<scratch>/evck/out/geo2/ep*_frames.json`, fields `H0`, `H30`,
`hand_min_mm`, `fails`, per-object `pen_*`):

| eval | H0 frames failing / H0 (the table) | of these, a hand point within 30 mm (closest, mm) | H30 frames failing / H30 | max table penetration, mm: the table's H0 value -> H30 mesh (faithful) | max overlap faithful / packed, H0 -> H30 (cm3) |
|---|---|---|---|---|---|
| 10 | 37 / 52 | 12 (0.8) | 25 / 33 | 1.5 -> 1.3 (1.3) | 88.5 / 32.7 -> 88.5 / 22.4 |
| 1 | 56 / 56 | 6 (1.6) | 50 / 50 | 2.4 -> 1.3 (2.3) | 34.9 / 0 -> 34.9 / 0 |
| 14 | 47 / 63 | 29 (0.4) | **18 / 29** | **16.6 (f42) -> 3.2 (3.9)** | 24.9 / 38.2 -> 10.7 / 17.6 |
| 15 | 24 / 92 | 12 (0.8) | 12 / 54 | 5.1 -> 2.1 (2.5) | 0.34 / 0.73 -> 0.3 / 0.7 |
| 16 | 19 / 86 | 5 (0.8) | 14 / 60 | 2.5 -> 2.0 (2.5) | 0.11 / 0.71 -> 0.0 / 0.7 |
| 30 | 59 / 63 | 37 (1.5) | 22 / 22 | 4.7 -> 2.7 (3.0) | 11.1 / 22.1 -> 8.4 / 18.7 |
| 32 | 6 / 21 | 6 (0.7) | **0 / 3** | **19.5 (f33) -> 1.0 (1.7)** | 0 / 0 |
| 33 | 4 / 30 | 4 (2.2) | **0 / 14** | 1.7 -> 1.4 (1.5) | 0 / 0 |

- Under H30 no eval frame fails the table check (a): the largest penetration is 3.9 mm on the faithful corners (eval 14),
  under s_max = 4 mm. The (a) failures in the table all come from frames with a hand nearby.
- At eval 14 f42, the frame behind the bold "16.6 mm (cup, f42)", the record has `H0: true`, `H30: false` and
  `hand_min_mm [3.0, 8.8]`: a hand point is 3.0 mm from the cup. The 16.6 mm is also the faithful 2 mm box corner. The
  mesh itself is 15.65 mm below the table (record `pen_visual_mm`, and my own vertex check gives 15.65 mm).
- The README defines H0 openly ("no contact label") and computes H30 too, so nothing is hidden. But F-I5.15 (3) /
  F-I5.3 (b) call only the 30 mm rule "hands-off", and these tables go to the pose lanes. Proposed correction: give the
  H30 columns as primary, or label the H0 columns "no contact label (hand may be within 30 mm)".

## Non-blocking findings

- **N1. "0.05 mm of wall left" is the ray offset, not a wall [M].** `carvable_mesh` starts its rays 0.05 mm off the
  sample and adds the 0.05 mm back (F-I5.17 (6)), so no ray can report less than 0.05 mm. I repeated the rays with a
  1e-6 m offset and all hits (`precheck_indep.py`):
  - ep13 f181: min 0.001 mm; 73 of 4,734 samples have less than 0.05 mm left; 1,273 have less than 1.5 mm (the run
    counted 1,386 of 4,976 as bad).
  - ep11 f127: min 0.0012 mm; 415 samples under 0.05 mm; 8,556 of 19,890 under 1.5 mm (run: 8,221 of 19,880).
  - The guest's surface reaches the receiver's surface, so the true minimum is about 0. The verdict is unchanged. The
    offset has a side effect: a sample within 0.05 mm of the exterior skips to the next surface and can read as
    passing (a small pass bias). The README and the summary report "0.05 mm wall left" as if it were a measurement.
- **N2. The delivered boxes are not "wholly inside" the SHELL [M]** (`pieces_geom.py`, exact manifold volumes, 1 mm
  surface points). Route 4 keeps a 6 mm cell when all of its 2 mm sub-cell centres are inside, so a box can reach past
  the surface:

  | ep / object | boxes | share of SHELL (run) | volume outside the SHELL, cm3 | max per box, cm3 | farthest reach outside, mm |
  |---|---|---|---|---|---|
  | 12 blue cup | 29 | 0.0498 (0.050) | 0.43 | 0.083 | 1.50 |
  | 12 rack | 45 | 0.0607 (0.061) | 1.66 | 0.179 | 1.44 |
  | 13 blue cup | 25 | 0.0485 (0.048) | 0.07 | 0.071 | 2.31 |
  | 13 rack | 24 | 0.0361 (0.036) | 0.72 | 0.132 | 1.48 |
  | 31 sweeper | 3 | 0.0185 (0.019) | ~0 | 0.023 | 1.35 |
  | 31 rack | 47 | 0.0468 (0.047) | 1.38 | 0.101 | 1.56 |
  | 11 blue cup | 17 | 0.0380 (0.038) | -0.28 (see N4) | 0.061 | 1.67 |
  | 11 beige cup | 20 | 0.0378 (0.038) | 0.47 | 0.099 | 2.23 |
  | 2 pot | 42 | 0.0609 (0.061) | 1.00 | 0.192 | 1.49 |
  | 2 lid | 25 | 0.0865 (0.086) | 1.22 | 0.186 | 1.42 |

  All ten shares reproduce, and every one is far below f_keep 0.5. The keep-out of 0 that the gate measured is safe:
  no box has more than 0.19 cm3 outside the SHELL, so its keep-out is below the 0.3 cm3 tolerance whatever the
  FREE labels and the grid anchor. The README's "0 by construction ... wholly inside the body" is not accurate,
  though. Better: "measured 0; bounded by <= 0.19 cm3 per box".
- **N3. The packed default explodes at these impossible frames, and the delivered boxes would have passed G1 [M]**
  (`simcheck.py`: own MJCF, plain MuJoCo 3.17.0 with the sim=rl options; config sha256 695536b7...4b66 checked;
  dt 0.01, Newton, implicitfast, pyramidal, impratio 20, 100 / 50 iterations, condim 3, friction 1.0; 200 steps, one
  unjittered copy; the packed default is my own coacd 1.0.11 call (0.05, -1, auto) on the round folder's `<obj>.glb`,
  which reproduces the run's hull counts exactly: ep13 66 / 24, ep11 58 / 47).
  - These are report-only rows: both frames are `pose_impossible`, so the rule gates nothing there.

  | frame | scene | delivered: max ncon / nefc | packed default: max ncon / nefc |
  |---|---|---|---|
  | ep13 f181 (rack <- cup) | S (receiver fixed) | 12 / 48 | 33 / 132 (the packed cup is thrown 1.58 m in 2 s) |
  | ep13 f181 | settle (both free) | 20 / 80 | 41 / 164 |
  | ep11 f127 (beige <- blue) | S | 14 / 56 | **508 / 2,032 at step 0** |
  | ep11 f127 | settle | 13 / 52 | **513 / 2,052** |

  - If these frames had been gated, the boxes would pass easily (ratio about 0.5 at ep13). At ep11 the packed default
    itself overflows four times over (`packed_overflow`).
  - So the G1 ratio is meaningless at impossible poses, which supports F-I5.16 (1c)'s exclusion of those frames.
  - G1 being vacuous does not hide a contact problem of the delivered boxes. The folders are do-not-use on the share
    anyway.
- **N4. The SHELL bodies are several overlapping solids; parity-based code reads the overlaps as empty [M].**
  - Each `shell_t5p36` I measured (ep11 both cups, ep12 cup and rack, ep13 cup) has 9-33 bodies over 0.1 cm3 (16-52
    in all).
  - Their summed volume exceeds their manifold union by 1.3-6.6 cm3, or 0.5-3.0 %: ep11 blue cup 3.51 cm3, ep12 blue
    cup 3.78, ep13 blue cup 6.63, ep12 rack 1.87, ep11 beige 1.29. The ep2 pot has a body that is not a volume, so
    manifold refuses its union.
  - `fast_inside` (faithful boxes, route 4) uses the winding number, so it counts overlaps as solid. `_intervals`,
    `Profile2.radial` and `continuity2` use parity, so they count overlaps as empty.
  - My own first voxelizer used parity too, and it under-read V_ov at ep13 f181 by 9 % (2.416 against 2.656 cm3). With
    a winding count I get 2.664.
  - `exact_share` and the precheck's `removed_share` divide by `body.volume`, which counts overlaps twice. Hence the ep11
    blue cup's negative "outside" volume (-0.28 cm3, in the run and here).
  - None of this changes a verdict (union test in B1). But the code uses two inside tests that disagree, and they
    should be reconciled (one union at load) before rings are tried again.
- **N5. "Every touching frame fails the pose check" is true only for hands-off frames [M]** (`scan_frames.py` over every
  frame, own 2 mm parity cells; `clean_frames_hands.py` with our M1 hands and the 30 mm rule).
  - Some frames are clean: the faithful colliders are within 4 mm, with no overlap, and the guest is above the table.
    They are ep12 f113-120, ep13 f97-102 and ep2 f63-66 and f260-263.
  - Every one of them is in hand (hand point 0.3-20.5 mm from the guest) and moving (1.8-26 mm per frame). So none can
    be an S frame, and the rule's outcome is right.
  - ep11 has no clean touching frame: 96 of its 97 near frames overlap. ep31 never comes within 4 mm at all.
  - Reading: the tracks are clean while the cup is being lowered, and go wrong once it comes to rest. That points the
    pose lanes at the rest phase. The README's general statement "at every frame where the two objects touch" should
    say "at every hands-off static frame".
- **N6. G1 records say `g1_pass: true` where G1 was vacuous [M].** All five `r0/contact_gate.json` carry `g1_pass:
  true` next to `contact_gate_pair_vacuous` (`contactgate5.g1` returns `pass_=True` with no gated row). DO_NOT_USE
  overrides this here. Still, a later script or reader could take it as a pass. Suggest `g1_pass: null` with
  `g1_status: vacuous`.
- **N7. G1's S scene leaves out the receiver-table contacts [M, rule-level].** The S scene welds the receiver to the
  world, so receiver-table pairs are filtered. Out-of-scope pairs get S scenes only, with no settle scene, so their G1
  under-counts against the evaluator, where every object is free.
  - ep13 f181: settle has 20 contacts on the delivered pieces against 12 in S.
  - In the eval-14 pair scene, the rack-table pairs alone make 37-63 contacts.
  - G2 still binds, so this changes no verdict. It is worth one line in the gate's caveats.
- **N8. Eval 10: the overflow at the one hands-off frame is marginal; the large maxima come from in-hand frames [M].**
  The three contact frames are f111 (static, in hand), f142 (not static, H0 and H30) and f116 (not static, in hand),
  all through the post-hoc fallback.
  - At f142, max nefc per copy is 516-656 (median 536). At step 0 it is 516-568.
  - With no jitter (my run), f142 gives exactly 128 contacts / **512 rows = njmax**, which is at the limit, not over it.
  - The 1,252-1,296 maxima are at f111 / f116, where the hand that holds the cup is missing from the scene.
  - P103 is still falsified: 16 of 16 copies exceed 512 at f142. But "656-1,296 rows at the nested rest" mixes in-hand
    frames into the rest numbers. At the rest, the pair alone uses 101-128 % of njmax, before any hand contact.
- **N9. Eval 14 and 30: no overflow, but the packed guest is thrown out [M]** (evalcheck `contacts2/ep*_contacts.json`,
  per-copy `disp_mm_receiver_guest`; my run agrees, for example ev14 f149 copy 0 moves the guest 141 mm against
  their 136).
  - Eval 14, at the rack rest (f149 H30, f135, f137): the packed cup moves 132-140 mm (median of 16 copies, max 246)
    in 2 s.
  - Eval 30: the packed sweeper moves 23-62 mm (median, max 351).
  - "0 / 48 copies over the limit" is true, but these resets are violent. This fits the "packed collider fills the
    slot" column, and it belongs in the relay to the pack lane.
- **N10. G1 has no engine-validity check in this round.** T-I17 c1 did not run (the ep24 v6 bundle is not on this
  machine). Every G1 and eval contact number is plain MuJoCo with limits applied to the counts, never MuJoCo-Warp.
  F-I5.16 (1h) allows citing F-I4.17's check where it ran the same scene, options and draws. The record should say
  whether it does, or keep the "plain MuJoCo, not validated against MuJoCo-Warp here" caveat on every row.
- **N11. H-d cannot be re-tested from the records [code reading].** The repair computes its keep-out points once,
  anchored at the original CoACD set's bounds (`repair`: `keepout(body, ev, allh, ...)`). The gate re-anchors at the
  final set's bounds. So the mechanism H-d names exists. The anchor moves only when a hull holding a global bound is
  split. With 2 mm points and a 0.3 cm3 tolerance (37.5 points), the verdict on thin hulls is grid noise either way.
  The route-3 hulls are not saved in the round folders (only the delivered boxes), so H-d needs CoACD to be re-run.
  Suggest saving every route's hulls in `_tried/`.

## Confirmed [M]

- **Precheck at four frames**, with my own winding-number 2 mm cells (`precheck_w.py`), against the run (`floor.json`):

  | frame | (a) lowest faithful / mesh, mm | V_ov faithful, cm3 | (b) gap, mm | exact mesh overlap, cm3 | (c) removed share | 1 mm components, default -> cut |
  |---|---|---|---|---|---|---|
  | ep13 f181 rack <- cup | -5.73 / -5.62 (run -5.73 / -5.62) | 2.664 (run 2.656) | 0 | 2.99 | 0.0103 (run 0.0103) | 11 -> 15 (run 13 -> 17) |
  | ep11 f127 beige <- blue | 3.14 / 3.10 (run 3.14 / 3.10) | 84.496 (run 84.504) | 0 | 89.62 | 0.5256 (run 0.5256) | 2 -> 67 (run 2 -> 69) |
  | ep2 f13 pot <- lid | 61.29 / 60.96 (run 61.29) | 23.848 (run 23.848) | 0 | - | - | - |
  | ep31 f285 rack <- sweeper | 46.61 / 44.74 | 0 | 12.00 (run 12.0) | 0 | - | - |

  - Moving the 2 mm grid by 1 mm changes V_ov by 0.3-3 % and the lowest faithful corner by 0.4-0.9 mm. For example,
    ep13 goes from -5.73 to -5.08 mm, still past -4 mm, and ep31's gap goes to 13.09 mm.
  - No verdict flips. Every frame fails exactly as the run says: ep13 (a) and (c); ep11 and ep2 (c); ep31 vacuous.
  - My components count differs from the run's by 2 because the grid method differs (parity, 26-connected). The
    increase is the same: +4 at ep13, and +65 against +67 at ep11.
- **S, one unjittered copy, own scene** (`simcheck.py 13 plastic_dish_rack blue_cup 181`): receiver fixed, guest free at
  0.3 kg, table friction 0.5, 2 ms, 2 s.
  - Delivered boxes: displacement 115.6 mm, dz 56.9 mm down, tilt 101 deg. The run's 16-copy mean is 121.8 / 53.8 /
    121.3.
  - My faithful 2 mm boxes (3,494 / 2,865 boxes from parity cells): 13.4 mm, 7.9 mm up, 9.3 deg. The run's 4-copy mean
    is 12.2 / 7.0 up / 8.6, and both fail.
  - The faithful scene starts with 1,144 contacts / 4,576 rows at step 0, which shows how deeply the tracked pose
    interpenetrates.
- **Eval spot-checks** (`evalspot.py`; own MJCF, exact-union inertia, sim=rl options, both objects free, z-up table
  plane at 0.600 m, the evalcheck's copy-0 jitter):
  - ev10 f142: V_faithful 83.464 cm3, identical (run 83.464); exact mesh overlap 83.95. Copy 0: step-0 and max 131 /
    524, identical. Displacements 17.8 / 16.8 mm, identical.
  - ev10 f116: copy 0 gives 221 / 884 against 216 / 864. I attribute the difference to vertex rounding (7 against 6
    decimals) on hulls that touch [H].
  - ev14 f149: copy 0 gives step 0 45 / 180 and max 48 / 192, identical. Guest displacement 141 against 136 mm (my
    exact inertia against their 1.5 mm voxel inertia).
  - ev14 f42: V_faithful 24.936 cm3, identical. The cup mesh is 15.65 mm below the table (see B2).
- **Rule plumbing.**
  - The G1 vacuity is correct as written, since no floor or acceptance frame passes the precheck.
  - The sim=rl options in every `contact_gate.json` equal `cfg_sim_rl.yaml`: sha256 695536b7...4b66; njmax 512,
    nconmax 256, newton, implicitfast, pyramidal, impratio 20, 100 / 50 iterations.
  - `DO_NOT_USE.json` is present in all five round-2 folders (committed copies), in the five round-1 scratch round
    folders, and beside the five committed round-1 manifests.
- **The innermost-profile ring walls are negative at every sector count** (B1 table, rows 1 and 5). This agrees with
  the run's -21 to -173 mm on check (i). My figures cover the main wall run only, in 1 mm bands: -19 to -32 mm local,
  and -22 to -85 mm with 1-6 linear-face bands.

## What this means for the next decision (orchestrator)

- **Do not adopt B4's robust profile as the ring fix (B1).** Any ring rule that never intrudes on any measured ray
  pays the SHELL's roughness of about 1 mm on each face, which is more than these 5.4 mm walls can afford. The open
  choices are these:
  - a measured intrusion allowance with quantile faces ([H], falsifier stated in B1);
  - smoothing the SHELL before the profile is taken (a new input rule);
  - giving up rings for these SHELLs.
  Each choice needs a dated entry before a run.
- **Correct the eval precheck's hands-off labelling before relaying it (B2).** Add N8 (eval 10 at its rest frame is
  101-128 % of njmax for the pair alone) and N9 (eval 14 / 30 resets throw the guest out) to the relay to the pack lane
  and to determined-wright.
- **Everything else stands.** Nothing public is usable, the poses at rest must be corrected first (N5 shows they are
  clean in hand), and G2 is still pending everywhere.
