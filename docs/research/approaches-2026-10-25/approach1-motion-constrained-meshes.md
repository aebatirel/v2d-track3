# Approach 1: meshes from the motion they must allow (2026-10-25)

Owner's idea: the tracked motions come from real physical interactions (two boards slide into a cross-lap joint),
so a region that the partner passes through cannot be solid; carve it, and adjust the mesh during optimisation or
policy generation to fit the world and the video.

Labels: **[M]** measured here without ground truth; **[V]** seen in the episode video; **[D]** diagnostic with public
scans or mocap, after inference; **[L]** primary source read in full; **[L-abs]** abstract only; **[I]** inference;
**[H]** hypothesis plus the experiment that would falsify it; **[E]** estimate. Scripts: `approach1-scripts/`
(commands in §8). CPU and web only, $0, no repo file changed apart from this new folder.

## Answer

**Largest new finding: the interaction exposed a perception error on eval 25, not a mesh error.**
- **What the joint showed.** Eval 25's assembled relative pose is not a configuration a cross-lap joint allows: it
  differs from the mocap-validated ep24 configuration by 178° [M].
- **What the video showed.** The video check (§2.6) found the cause: **our two board identities are swapped** on
  eval 25, and one board is also turned 180° in its plane [V].
  - A GT-free rule built only from our meshes' marker knobs and the video picks the right assignment on the good
    public track and flags both the eval-25 track and the 24 Oct ep24 track as swapped.
  - On that 24 Oct ep24 track, applying the rule's repair raises the score against mocap from **0.029 to 0.706** [D].
- **What it costs today.** With swapped names the scorer compares each of our boards with the other board's mocap and
  anchors the scene on the wrong board. On public ep24 a swap alone drops a 0.795 track to 0.057 [D]. Eval 25 is
  therefore near zero against the truth whatever the robot does, although its sim_vs_ref is 0.232 [I].

**Mesh side of the idea.**
- **What works:** motion-consistent free space for the **simulator collision copy only**.
  - With FlashCHORD's default CoACD hulls of the eval-25 assets, a board driven along our own reference cannot enter
    the cross: it ends **101° off** (105° on public ep24).
  - A planar slot cut in the collision copy, taken from our reference alone, brings it to **0.05 cm / 0.5°**, the same
    as with board–board contact off [M, CPU MuJoCo proxy].
  - This is the arc foot's sibling. The arc foot adds "physible" support under observed rests; the carve removes
    "physible" free space where our reference puts a partner.
- **What does not work:**
  - **Editing the submitted mesh from motion.** Every carve on 22 Oct was CD-O-neutral (±0.01 cm) or harmful: the
    lid min-cut added 0.14–0.18 cm, nested cups went 1.17 → 1.43 cm, and new registration flips appeared [D].
  - **Our tracks are not precise enough to place a slot.** Their bias is about one slot width (0.8 cm / 2.4°), and
    tracks can be swapped or flipped.
  - **The overlap is not all filled notch.** 36–47 % of what our cut removes is real wood [D].
  - **Interactions cannot reach the big defects** (pitcher, pot, rack, dust pan, beige cup; 22 Oct).
  - **Co-optimising the mesh with the policy** cannot be afforded in 10 days and rewards ghost geometry.

**Recommended version, A1-min** (three GT-free rules, frozen on public twins):
1. **Identity and in-plane symmetry check** for near-identical objects (boards; later any look-alike pair), run at
   perception time. Measured on public data; eval 25 is flagged.
2. **Collision-copy carve** where the partner sits in persistent contact (slots, nested cavities). It must be
   delivered as convex pieces or primitives, because CoACD refills an 8 mm slot.
3. **Start depenetration** of stacked objects (lid on pot, pot in rack) by the same carve at frame 0.

**Expected gain [E]:**

| Item | Effect on eval 25 | Effect on the 20-episode AUC |
|---|---|---|
| Rule 1 on eval 25 alone | about +0.15–0.20 (from about 0.03 to about the static floor) | **+0.008–0.010** |
| Rules 2 and 3 (evals 25, 1, 10, 28), now | – | +0.00–0.01: grasps and perception bind first |
| Rules 2 and 3, after the board clamp and lid grasp | – | up to +0.02–0.03 |
| CD-O | 0 by design | 0 by design |

**Cost:**
- Rule 1: done as a prototype. Re-running eval 25 with corrected names ≈ $4–6 GPU.
- Rules 2 and 3: about 1–1.5 days CPU.
- Twin A/B tests: $25–75 (§6).

## 1. What the 22 Oct experiments found (Q1)

| Experiment (source) | Metric effect [D] | Wrong or harmful? | Physics tested? |
|---|---|---|---|
| XCarve on ep24 Design-O grids (`judged-plan` §1, `exp-interaction-gates`) | Slot fill 80/52 % → 11/0 %; overlap 2.86 → 0 cm³; CD-O +0.006/+0.007; board 2 **new flip, ADD +103 mm** | R2 (insertion split) turns track bias into real cuts: 1.3–1.5 cm³ per board under 5–10 mm or 5–10° bias, 0.34 cm³ even unbiased on own tracks; flips board-1 registration on 1 of 6 seeds | No |
| XCarve ep2 / ep18 | CD-O +0.001 to +0.012 | Nearly inert | No |
| Joint min-cut, carve_both on lid/pot ep2 | **Lid CD-O +0.14 to +0.18 cm** | Harmful. Without its halving prior it cut board 2 in two | No |
| WS + R1 + R3 safe set | ±0.01 cm | Bounded: ≤ 0.75 cm³ real wood under bias | No |
| Nested cups ep11 (R2s) | Blue cup 1.17 → 1.43 cm, ADD 9.9 → 77 mm | Harmful: the inner cup's track sinks 2.7 cm | No |
| Hand capsules (defects study) | – | Carve ≈ conflict (pot 69 vs 71 cm³): hands are off by about 1 cm | No |
| S5 rest replay at the ep24 assembled pose | – | – | **Partly**: boards *held* at the pose drift 5–46 mm under every decomposition; a box control sinks 9.6 mm. No insertion was tested |
| S8 GPU A/B (plan) | never run | – | The ep24 test with v4 boards stopped at perception (AUC 0.029), before training. §2.6 shows that was the identity swap, not the v4 meshes |

The rejections split into two groups:

- **Metric barely moves:** XCarve and the safe set (±0.01 cm). The judged plan's own words were "interaction
  carving improves physics, not mesh quality".
- **Wrong or harmful:** the min-cut lid, R2 under bias, nested cups and the hand capsules, plus a new flip from
  XCarve's board 2.

**Nobody had tested whether the cross can be assembled in a simulator** (§2.5).

## 2. Boards, measured (Q2)

### 2.1 Interpenetration at assembly [M]
`pair_overlap.py`: our meshes, our poses, 1.5 mm solid samples, both directions.

| Episode, poses, meshes | Assembled frames | Overlap cm³ (median, min–max) | Penetration | Location (board-1 frame) |
|---|---|---|---|---|
| ep24, own-mesh track (perc2m), v3 | 215–274 | 10.65 (10.4–10.9) | 6.4 mm | column 1.0 × 11.2 × 1.2 cm across the width at mid-length |
| ep24, 23 Oct reference, v3 | 215–274 | 10.54 | 6.4 mm | same |
| eval 25, track (perc2), v3 | 290–355 | 10.53 (9.0–10.8) | 6.5 mm | same column, y −5.9 … +5.3 cm |
| eval 25, packed reference + simulator assets (support-filled board 2) | 295–355 | 10.55 | 6.4 mm | same |

- The column is the two missing notches plus board 2's extra thickness: 12.0 mm against 9.1 mm in the scan.
- On 22 Oct mocap poses gave the same 10.5 cm³ [D], so this is a mesh error, not a track error.

### 2.2 Pose noise against slot width
- **Jitter** at assembly, from a 9-frame median [M]:
  - ep24: 0.6 mm median, 1.4 mm at the 90th percentile; 0.7° / 1.3°;
  - eval 25: 1.0 / 1.6 mm; 1.8° / 2.9°.
  - That is small against an 8.5–8.9 mm slot.
- **Bias** [D, ep24 against mocap]:
  - 0.8 cm / 2.4° (own-mesh track) and 0.4 cm / 1.5° (scan-templated track) at assembly;
  - 7.6 / 16.9 mm median / 90th percentile over the episode (22 Oct).
- **Gross errors:** a name swap plus a 180° turn on eval 25 (§2.6).
- **Consequence:** a slot carved into the *submitted* mesh from our tracks can be misplaced by about its own width, or
  put into the wrong board.

### 2.3 Would carving the swept intersection hit the right region?
- **Naive carve:** carving each board by the partner's full swept solid removes the whole column from both boards.
  Per board [D, 22 Oct census], the entry half is filled notch (7–29 % inside the scan) and the other half is real
  wood (66–70 % inside).
- **Planar half-cut** (`insert_test.py`): splits the column at one shared plane, using the insertion direction from
  our reference. Of what it removes on ep24 [D, `diag_cut_realwood.py`]:
  - board 1: 7.4 cm³, of which 3.5 cm³ (47 %) is real wood;
  - board 2: 10.4 cm³, of which 3.8 cm³ (36 %) is real wood.
  - The slab is 14–18 mm wide against an 8.5 mm notch, because rotation jitter during insertion widens the claim.
- **Verdict:** right for physics, wrong for scoring. On the collision copy the extra clearance is harmless. On the
  submitted mesh it repeats 22 Oct.

### 2.4 Does a slot survive CoACD?
- **No.** FlashCHORD decomposes every collision mesh (CoACD threshold 0.05). Our eval-25 URDFs have one `<collision>`
  mesh per board.
- **Measured on the actual eval-25 assets** (`hullovl.py` from 22 Oct) [M]:
  - 19 + 14 hulls;
  - **hull overlap 13.7 cm³** (max 14.8) against 10.3 cm³ of mesh overlap.
- **Earlier numbers** (22 Oct): a slotted Design-O board still showed 13.5 cm³ at 4096 faces and 6.7 cm³ at full
  resolution. Only our own convex pieces, one `<collision>` each, reached 3.0–4.1 cm³ (FlashCHORD keeps convex pieces
  unchanged, 256/256), and primitives are never decomposed (note 19 §1).
- **Production gap:** `make_assets.py --pieces` and `pipeline/collision_decomp.py` exist (d7576a4), but no job in
  `ops/jobs` passes pieces. **Today no slot can reach the simulator.**

### 2.5 Can the cross be assembled in simulation? [M, proxy]
`insert_test.py`, CPU MuJoCo 3.8.1:
- board 1 fixed; board 2 free (0.3 kg, gravity off), welded to a mocap target that follows our reference's relative
  path at 20 fps, dt 2 ms;
- hulls exactly as FlashCHORD builds them;
- "cut" = every hull clipped by three half-spaces (slab ∩ entry side), convex output only.

| Variant | ep24 (23 Oct ref., f160–275): lag at assembly / max / penetration | eval 25 (packed ref., f200–356): lag at assembly / max / penetration |
|---|---|---|
| default CoACD hulls (what eval 25 simulated) | 1.11 cm, **105°** / 5.4 cm / 6.7 mm | 0.94 cm, **101°** / 4.6 cm / 5.4 mm |
| collision-copy planar cut (32 + 19–21 pieces) | **0.05 cm, 0.5°** / 0.33 cm / 0.3 mm | **0.05 cm, 0.5°** / 0.48 cm / 0.6 mm |
| board–board contact off (drive floor) | 0.02 cm, 0.1° / 0.33 cm / 0 | 0.03 cm, 0.2° / 0.34 cm / 0 |

- **Result:** default hulls twist board 2 out of the joint. The cut tracks like the no-contact floor.
- **Caveat:** this is a geometry proxy, not FlashCHORD's Newton / MuJoCo-Warp configuration (dt 0.01, one contact per
  convex pair). T-a in §6 closes that gap.
- **First-version bug, kept for honesty:** the first version split each board at its own claim median and left a
  1.3 cm uncut band (1.4 cm / 8.4° lag). Both boards must split at one shared plane.

### 2.6 The joint exposed swapped identities on eval 25
1. **Relative configuration at assembly** (board-2 axes in board 1's frame) [M]:
   - ep24 own-mesh track: (x → +z, y → −y, z → +x), confirmed by mocap to 2.4° [D];
   - eval 25, both stored references (evD and the evR rerun): (x → +z, **y → +y**, z → −x).
   - A cross-lap joint between these boards admits only the ep24 configuration and its face-flip. Eval 25 differs by
     178° about board 2's thickness axis, constant from frame 0 (no step over 7°/frame).
   - Overlap cannot arbitrate: our meshes keep too little notch, and every 180° re-pose changes the overlap by under
     0.2 cm³ (`flip_test.py`) [M].
2. **Notch side in the video** (`notch_view.py`, rectified ego_cam_c, the two candidate notch lines of a board
   projected from our track) [M/V]:
   - **ep24 (correct track):** the dark slot lies under board 2's +y line. The intensity gap from wood is 24–62 grey
     levels in 6 of 8 frames, while the −y line matches wood (≤ 3.6 levels in 7 of 8).
   - **eval 25:** the slot lies under the **−y** line (25–137 levels in 7 of 8 frames), while +y matches wood
     (≤ 6.6).
3. **Marker knobs identify the boards** [V; patterns confirmed on the scans, D]:
   - wooden_piece_1 has four corner knobs on +x; wooden_piece_2 has three knobs on −x. Our own meshes reproduce 3 and
     2 of them.
   - Both episodes show the same layout: the four-knob board on the left, the three-knob board on the right.
   - Our mocap-validated ep24 track calls the left board wooden_piece_1. Our eval-25 track calls it
     wooden_piece_2: **the names are swapped**.
   - Perception names the two boards by detector score alone (eval 25: 0.41 / 0.54), which for twin boards is a coin
     flip.
4. **GT-free repair rule** (`identity_rule.py`):
   - For each name assignment and each of the four in-plane symmetries per board, project our own mesh's knobs on the
     camera-facing side at frames 0, 2, 4 and 6, and score knob darkness against the plate.
   - Results:

   | Track | Rule's choice | As-tracked rank | Against mocap [D] |
   |---|---|---|---|
   | ep24, 21 Oct own track | as tracked (−79.9 vs −52.6 for the next) | 1 of 32 | 0.795 |
   | ep24, 24 Oct w1 track | **swapped**, board-1 track turned 180° about x | 22 of 32 | 0.029 → **0.706** after the rule's repair |
   | eval 25 | **swapped**, same prescription | 21 of 32 | (no GT) |

   - The work log blamed the w1 failure on the flattened v4 boards. The repair shows it was this swap.
5. **Cost on the score** (kit-style slot-0 anchor, ADD-AUC 1–9 cm; ep24 own track against mocap,
   `diag_swap_cost.py`) [D]:
   - as tracked 0.795;
   - names swapped **0.057**;
   - board 2 turned 180° about x: 0.38; about z: 0.47.
   - Boards have no declared symmetry, so eval 25 scores about 0.03–0.06 against the truth now [I], whatever the
     simulation does.

## 3. Other "interaction-infeasible" eval failures (Q3)
`eval_census.py`: packed references and their simulator assets, mesh-mesh overlap. CoACD hulls add more (§2.4).

CENSUS_TABLE

| Eval (twin) | Failure (24 Oct analysis) | Interaction-infeasible? | Would carving or a physics edit fix it? | Binding failure that remains |
|---|---|---|---|---|
| 25 (ep24) boards | no slots; grasps never acquired | **Yes** (§2) | the insertion (collision copy, §2.5) | **identity swap** (§2.6), then the board grasp (0.202 floor; counterfactual 0.803) |
| 1 (ep2) pot + lid | lid 7.6 mm inside the pot at f0, wedged | **Yes**, at start; mostly mesh (lid underside about 7.7 mm too low) [D, 22 Oct] | start jolt: carve the lid's collision underside by the pot at seated frames. Better than lifting the lid in the reference (Picasso / PhysPose style), which adds about 8 mm of pose error [I] | lid pick (flat disc) and pot handle grasp |
| 10 (ep11, roles reversed) cups | beige cup an open shell that falls at f3; blue cup interior 37 % (O fusion 22 %) solid | Partly: stacking into a filled cavity | collision-copy cavity carve; keep a 2 mm skin so a sunk inner-cup track (2.7 cm on ep11) cannot cut the floor [H] | beige-cup support; also run the identity check (look-alike cups on a grayscale camera) [H] |
| 20 (ep21) pitcher | twisted shell, falls at f8 | **No**: pouring never touches (47–75 mm) | nothing. The fix is support (arc foot) | – |
| 30 (ep31) sweeper + rack | detected on the wrist from f0 | Secondary: the sweeper rests in the rack's dividers (rack hull concavity 7.5–9.3 mm, note 19) | rack collision carve at the sweeper's rest frames, gated for compliant bristles | perception |
| 14 (ep12) cup on rack peg | track jumps to the wrist | Possibly: cup cavity filled 37 % from the base | collision-copy cavity | perception |
| 28 (ep26/27) pot + rack | pot placed 8.5 cm off; rack knocked | ep26 twin: start jolt, pot 117 mm / 52° (hull overlap 9.8 mm) | start depenetration | placement |
| 32, 33 cup + spoon | 33: cup on the wrist | In our reference **neither spoon end ever enters the cup's hull** (0 frames) [M]: if the person stirs in the cup, our relative pose is wrong | no mesh fix; a perception flag | perception |
| 3, 5, 6 pot + spoon | – | consistent: the bowl end is in the pot in 14 / 88 / 76 frames, the handle end in 0 (`spoon_end_check.py`) [M] | no flip suspected | – |

## 4. Literature and open source (Q4)

| Work | What it does | Needs | Fit for us in 10 days |
|---|---|---|---|
| PhyRecon, NeurIPS 2024 (arXiv 2404.16666) [L] | SDF scene reconstruction with a differentiable particle simulator; stability loss on support; physics-guided sampling of thin parts | posed multi-view images and masks; one A100; about 12–13 h per scene; code (phyrecon.github.io) | No. Static support only. Its limitation is our risk: the physics loss "may lead to degenerated object shapes, e.g., bulges, to maintain physical stability" |
| Atlas3D, NeurIPS 2024 (2405.18515) [L] | standability loss through Warp rigid-body simulation over all vertices | RTX 3090; about 36 min per refinement | No. Stability only, and "distorted meshes" (its limitation). Note 25's certificate already covers support analytically |
| Physically Compatible 3D modelling (2405.20510) [L-abs] | static equilibrium as a hard constraint on rest shape | single image, FEM | No (deformable, single object) |
| **Vysics**, RSS 2025 (2504.18719) [L] | closest to the owner's idea: "physible" geometry inferred from contact events in the object's motion, fused with BundleSDF's SDF | RGB-D, robot proprioception (exact partner), known table; one rigid body; convexity bias; code on the project page | Concept yes, code no. Its partner is exact; ours is another reconstructed object or a hand off by about 1 cm (carve ≈ conflict, 22 Oct) |
| Picasso, RSS 2026 (2602.08058) [L] | multi-object pose correction under non-penetration, support and free-space constraints; rejection sampling over a contact graph | RGB-D; shapes from SAM3D / CRISP; < 1 s per object on an RTX 4090 | Partly. It corrects poses, not shapes; static. Where the error is in the mesh (lid underside), pose correction moves the lid away from the truth |
| PhysPose (2503.23587) [L-abs] | post-hoc pose refinement with non-penetration and gravity | scene geometry and poses | Same caveat |
| BundleSDF, CVPR 2023 (2303.14158) [L] | joint pose-graph tracking and neural SDF from RGB-D | GPU, first-frame mask, code (NVlabs) | Tried in spirit (Design O, v5). It has no object-object constraint and no identity or symmetry handling |
| HOLD (2311.18448), HOISDF (2402.17062), IHOI (2204.07153), ContactOpt (2104.07267), HOMAN (2108.07044) [L-abs] | hand-object reconstruction with contact and penetration terms | hand pose within a few mm; training data | No. Our MANO hands are ±1–2 cm, and hand carving was measured to cut real material |
| gradSim, ICLR 2021 (2104.02646); PhysTwin 2025 (2503.17973) [L-abs] | differentiable simulation plus rendering for system identification | GPU; simple or deformable scenes | No |
| Scalable Real2Sim 2025 (2503.00370) [L] | robot-scanned assets: visual mesh; collision geometry by convex decomposition; inertia by identification | robot plus cameras; code (nepfaff/scalable-real2sim) | Supports our design: collision geometry is a separate, simulator-specific artefact. It warns that overlapping pieces create interior contacts and proposes primitives as an alternative |

Literature summary:
- Physics-aware reconstruction exists for static support, single objects or known partners.
- No open method carves object-object free space between two reconstructed objects from their tracks.
- The robust pattern in the sources is a separate collision asset.
- Search note: WebFetch could not resolve arxiv.org from this container, so the papers were read through curl and the
  proxy.

## 5. "Update the mesh during optimisation or policy generation" (Q5)

Two facts frame this:
- The submitted mesh sets CD-O *and* the Sim(3) registration behind every pose metric.
- The collision copy can differ: the URDF names its own `<collision>` elements, the evaluator runs our URDFs, and
  Kaggle scores our submitted trajectories without re-simulating (S5 §1, note 19).

| Variant | What it changes | Risk | Verdict |
|---|---|---|---|
| (a) render-and-compare refinement of the submitted mesh along our tracks | CD-O, registration, physics | v5 was worse than v2 except the beige cup; the silhouette is inert on the grayscale camera; tracks are biased, and here even swapped, so fusion along them blurs or mixes shapes | Only through the v5 gates, never driven by simulator success |
| (b) physics-in-the-loop edits of the **collision copy only** (support fill, arc foot, carve, start depenetration) | physics only | Ghost geometry could let the simulator follow a wrong reference, but the score already pays for a wrong reference, and the policy is trained to follow it | **Safe, recommended.** Support only under observed rests; carve only partner occupancy in persistent contact; volume ≤ 10 % of the solid; no tunnel through the outer skin; never from GT |
| (c) co-optimise the mesh with the policy (choose the collision variant with the best sim_vs_ref) | physics, selected by RL | 2.5 h per variant; sim_vs_ref rewards deleting contacts that resist the robot; choosing on eval is tuning on eval | No in 10 days. At most a pre-registered 2-arm choice on public twins |

Inference in (b) and in the identity rule uses only our reference, our meshes, video, calibration and object names.
Scans and mocap appear only as [D] in this report.

## 6. Sub-ideas: effect, cost, and pre-registered public-twin tests (Q6)
Effects are on the 20-episode AUC; one eval episode weighs 0.05.

| Sub-idea | Evals | Expected effect [E] | Cost |
|---|---|---|---|
| R1: identity and in-plane symmetry rule | 25 (check 10) | **+0.008–0.010** (eval 25 from about 0.03 to about 0.2) | CPU done; eval-25 rerun ≈ $4–6 |
| R2: collision-copy slot carve | 25 | +0.000 now; +0.01–0.02 after the board clamp (H24-1) | 0.5 day CPU |
| R3: start depenetration (lid, pot in rack) | 1, 28 | +0.000–0.008 | 0.5 day CPU |
| R4: cup cavity carve (collision copy) | 10, 14 | +0.000–0.005 until the beige cup stands and perception holds | 0.5 day CPU |
| Carving the submitted mesh | – | ≤ 0 (22 Oct) | drop |

**Cheapest falsifying tests (CPU; rules written before running).** Each row is one test.

| ID | Twin | Test | Pass / fail rule | Status |
|---|---|---|---|---|
| T-1 | ep24 (21 Oct and 24 Oct tracks) and ep23 | identity rule on each public two-board track at frames 0, 2, 4, 6 | Must keep every track whose mocap AUC is ≥ 0.5 and must repair every swapped one to ≥ 0.6 [D]. **Falsified if** any good track is changed | **ep24 both cases pass** (rank 1; 0.029 → 0.706). ep23's G1 track is broken (AUC 0.04) and was not tested |
| T-a | ep24 | FlashCHORD's own stepping (s5coll `replay_rest.py` harness, Newton / MuJoCo-Warp CPU, dt 0.01, object assist driving board 2 along the 23 Oct reference f160–275). Default vs planar-cut pieces through `make_assets --pieces` | **Pass:** cut ≤ 5 mm / 5° over f240–274 with board 1 tilt ≤ 5°, while default ≥ 2 cm or 20°. **Fail:** cut > 1 cm or 10°: the proxy does not transfer; switch to primitives | to run (≈ 2 h) |
| T-b | ep2 | collision-copy lid carve by the pot at the seated frames f0–59, zero-action replay | **Pass:** lid ≤ 3 mm / 3° by f30 (now 31 mm / 27° by f23, work log 24 Oct). **Fail:** > 5 mm | to run |
| T-c | ep11 | outer cup's collision cavity carved by the inner cup along our reference, keeping a 2 mm skin; kinematic drive into the nest | **Pass:** lag ≤ 1 cm at the nested frames and the outer cup moves < 5 mm | to run |

**Strongest tests (GPU; owner update; not rented).** One 250M training is about 2.5 h; two trainings can share a box
(`TRAIN_SLOTS = 2`); $1.4–1.9 per box-hour; evaluations about 12 s each.

| ID | Design | Hours / cost [E] | Pass / fail rule | Decides |
|---|---|---|---|---|
| G-1 | Public: re-run ep24 perception plus reference with R1 inside perc2. Then train both learners on the corrected 24 Oct-style track, 2 seeds × 5 evaluations, registered AUC vs mocap | ≈ 0.5 h perception + 4 trainings ≈ 11 GPU-h; **≈ $15–21** | **Pass:** reference AUC ≥ 0.7 and policy mean ≥ the 23 Oct reference's result (0.241) − 0.03 | ship R1 in the eval pipeline and rerun eval 25 (≈ $4–6) |
| G-a | ep24: {default assets, cut collision copy} × 3 seeds × 5 evaluations, current recipe | 6 trainings ≈ 15 GPU-h; **≈ $21–29** | **Pass:** mean(cut) − mean(default) ≥ +0.05 with ≥ 2 of 3 seed pairs positive. **Fail:** < +0.02 (grasps bind) | whether eval 25 is rerun with the cut. Run only after H24-1 passes its zero-action test; otherwise both arms sit at the 0.20 floor |
| G-b | ep2 lid: {default, lid carve} × 2 seeds × 5 evaluations | 4 trainings ≈ 10 GPU-h; **≈ $14–19** | **Pass:** ≥ +0.05 and no seed worse than −0.02 | eval 1 rerun |
| G-c | broad: twins ep24, ep2, ep26, ep11 × {A1-min off, on} × 2 seeds × 5 evaluations | 16 trainings ≈ 40 GPU-h; on 8 boxes ≈ 6 h wall; **≈ $56–76** | **Pass:** mean gain ≥ +0.03 and no twin below −0.03, thresholds frozen before launch, seeds 42 and 43 | adopt A1-min for all eval reruns |

**Order:**
1. R1: T-1 is done, so G-1 next, then the eval-25 rerun.
2. T-a and T-b.
3. G-a and G-b, only behind the grasp fixes.
4. G-c, if the owner wants breadth.

## 7. Risks and open questions
- **The identity proof rests on marker knobs.** They are mocap markers attached to the boards, confirmed in the public
  scans. If the organisers re-attached markers between recordings, the knob test would mislead, but the notch-side
  test (§2.6, item 2) is independent of markers and agrees.
- **Rules question.** Relabelling an already-simulated rollout at pack time would recover most of the eval-25 gain at
  no GPU cost. But the board simulated under one name used the other board's mesh, so re-running perception and
  training with corrected names is the clean route. Ask the owner.
- **The CPU proxy is not the evaluator's solver.** T-a closes that gap.
- **Collision pieces raise memory per world about 2×** (22 Oct S5). Primitives (boxes for boards, a ring for the lid)
  may be simpler for these joints. Box-slot boards are being prototyped separately (approach-2 scratch files); I did
  not evaluate them.
- **Owner decision O4** (collision geometry differs from the submitted mesh) remains open.

## 8. Files and commands (CPU, 2026-10-25, repo at c4cc38e)
- `approach1-scripts/`:
  - `pair_overlap.py` (§2.1); `flip_test.py` and `diag_relpose_mocap.py` [D] (§2.2, §2.6); `diag_cut_realwood.py` [D]
    (§2.3);
  - `insert_test.py` (fcvenv with the FlashCHORD CoACD cache; §2.5);
  - `notch_view.py`, `identity_view.py`, `identity_rule.py`, `diag_swap_cost.py` [D] (§2.6);
  - `eval_census.py`, `spoon_end_check.py` (§3).
  - §2.4 reused the 22 Oct `interact/v5/s5coll/scripts/hullovl.py`.
- Inputs from the HF store (≈ 55 MB, scratch only):
  - `runs/20261024-ev{A,B,C,D,E,F,R,R2}-*/refs/sf/ep*/`, `runs/20261024-ev30rp-07eef1a/refs/sf/ep30/`;
  - `runs/20261024-evD-664e5fd/perc2/ep25/`, `runs/20261024-w1-37cc551/perc2/ep24/`;
  - `runs/20261025-g1-022fece/perc2m/ep23/`.
- From the organisers' dataset: eval-25 and ep24 ego_cam_c videos and the calibration (7 MB).
- Outputs: `$S/approach1/out/`, with
  `S=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad`.
