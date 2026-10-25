# Root-cause audit: ep18 (mini_sweeper + mini_dust_pan) and ep39 (mini_dust_pan) under the grasp-lock recipe

2026-10-24, CPU only (no rentals). Workflow step "audit-plates" of the owner's option 2 ("one recipe with designed
grasps; make sure the failures really are grasp failures"). Labels: **[M]** measured by this audit from stored traces,
references and meshes; **[GT]** diagnostic that reads ground truth (public mocap or the organisers' scan), after
inference, reporting only; **[L]** literature I opened; **[I]** inference; **[H]** hypothesis, with the experiment that
would falsify it.

## 0. Answer

| object (episode) | registered AUC, grasp-lock | is it a grasp failure? | root cause (first thing that goes wrong) |
|---|---|---|---|
| mini_dust_pan (ep18, left hand) | pan part of 0.302 ± 0.094 (per-object AUC 0.13–0.67 per rollout) | **yes, mostly** | The designed (snapped) grasp has **no opposition**: in the squeezed hold target only index/middle/ring middle phalanges touch the far end edge of the ring handle, the thumb is 20 mm off. Closing from below (the hands pass through the table) **flicks the pan**: 63–80 mm / 17–22° and +5 cm before the reference has moved 1 cm (4 of 4 zero-action variants). It is then carried on fingertips from below and slips out (median 3.8–9.4 cm, 54–92° in the hand). |
| mini_sweeper (ep18, right hand) | sweeper part of 0.302 (per-object AUC 0.10–0.20) | **no** | **Hold timing.** The brush really moves from f38 (mocap: lifted 5 cm at f44), but our human hand has 0 MANO contacts on it until f60, so the hold starts at f61 (lock from f53). From f38 the backed-off pre-grasp follows the moving reference brush and never meets the simulated one. The fingertips clip it at f52–56 (12°), it rocks over a 3.2° stance margin and falls flat at f64–76. At closure the palm is 11.6 cm away. The designed clamp itself (thumb on one face, three fingers on the other, like the human) is the right type, but it was never tested. Older variants: the approach knocked it at f24–27 (approach 6 cm / none), or it fell by itself at f1–9 (rp18: `mc` reference, library_v2). |
| mini_dust_pan (ep39) | 0.174 ± 0.003 | **no** (primary); also yes (secondary) | **Carrier merge.** `--single_hand 1` kept the hand with the most hold frames (right, f70–292) and started it at *its* first hold. That deleted the left-hand pick-up (f36–103), so no robot hand is on the pan while the reference pan rises 20 cm (f46–64). The right hand closes on the airborne reference pose, 7.5–10 cm from the real pan. The simulated pan never moves more than 2.8 mm (zero action 0.1755 = floor 0.1763). Secondary: even the designed right-hand grasp touches nothing (all links ≥ 3.9 mm off, thumb ≥ 21 mm). |

In short: of the three object failures, one is a grasp failure (the ep18 dust pan). Two are failures in building the
reference: the hold starts too late (ep18 sweeper) and the carrier merge drops the pick-up (ep39). A better grasp
would not fix either of those two, because the hand is never at the object when it closes. Standard RL on the same
references lifts every object, which shows the physics allows it:
- ep18 seed 43: dust pan 17.6–19.1 cm (reference 16.3) and sweeper 7.5–10.1 cm (reference 8.4), in all 6 rollouts;
- ep39: the pan follows its 26.9 cm lift in 4 of 5 rollouts.

The fine-tune's degradation (ep18: 0.446 at 10M down to 0.060 at 70M) is a consequence of these failures, not a
separate cause. Once neither object can be acquired, RL learns to avoid contact (rp18: the left hand stays 4–13 cm
from the pan for the whole hold) or to fling the objects (E1 at 70M: the pan is more than 10 cm off its path from f17 and is thrown up to 30 cm).

## 1. Data, method, caveats

Runs (HF store `aebatirel/v2d-store`, downloaded to `scratchpad/grasp_work/audit-plates/data/hf`):

| run | what | files used |
|---|---|---|
| `20261024-e1-e49e83d` | ep18 grasp-lock, settled `mckfid` reference, library_v3, SF=1, REPLAN=1, `--approach_cm 15` (and `ep18_app6` = 6 cm) | `results/glock_public/ep18{,_app6}/zero.npz`, `best/r1..r5`, `curve/policy_*`, `refs/glock/ep18*/…/ref_gl{,_ilc}.parquet`, `ref_gl_grasp_lock.json`, `refs/perc2mckfid/ep18/*`, `glock_ep18.log` |
| `20261023-rp18-a674fd7` | ep18 `mc` reference, library_v2, REPLAN=2 (r1 kept), policy 50M | `vid/policy_trace.npz` (full-body policy rollout played like the evaluator), `zero_r1.npz`, `best/r1..r5`, `ref_gl_r1_ilc.parquet` |
| `20261023-kf18-a674fd7` | ep18 settled reference, SF=0, no early approach | `zero.npz`, `ref_gl_ilc.parquet`, grasp-lock json |
| `20261024-e3-e49e83d` | ep39 grasp-lock (approach 6 cm) | `zero.npz`, `best/r1..r5`, `ref_gl{,_ilc}.parquet`, json, `refs/perc2mck/ep39/*`, `glock_ep39.log` |
| `20261024-std39-1f306be` | ep39 standard FDR RL 250M (`mcks`) | `results/hard_ab/ep39/mcks-s42/r1..r5` |
| `20261023-fdr43-715c9f7` | ep18 standard FDR RL s43 250M (0.889) | `results/hard_ab/ep18/mckfid-s43/r1..r6` |

Method [M] (scripts in `docs/research/grasp/audit-plates-scripts/`, summary JSONs in its `out/`):
- **Trace audit** (`analyze_trace.py`): each object's simulated pose is compared with its pose in our reference parquet,
  frame by frame: lift (z − z₀), error, displacement from its own simulated frame-0 pose, and slip. Slip is the
  object's pose in the holding hand's palm (C_MC) frame, relative to the frame where the fingers finished closing.
  The per-phase frames come from `ref_gl_grasp_lock.json` (`hold_from`, `closed_at = hold_from + close`,
  `move_frame`, `end`).
- **Contact proxy:**
  - hand side: per link, the minimum signed distance from that link's collision-hull surface samples (Sharpa Wave
    URDF meshes; the fixed elastomer pads composed into the distal link, as FlashCHORD collapses them) to the object;
  - object side: our library_v3 mesh's CoACD pieces (Newton settings; 19 pieces for the sweeper, 26 for the dust
    pan), posed by the trace or by the reference;
  - "contact" means within 3 mm.
  - The CoACD pieces stand 0.3–1.0 mm outside our mesh (median; p5 2.4–2.9 mm).
  - Face labels (+axis3 / −axis3 / edge) come from the mesh normal at the closest point, in the plate's PCA frame:
    axis1 = long axis with the handle ring at negative axis1, axis3 = plate normal.
- **Reference contacts:** the same proxy on the reference's own robot link frames (`robot_*_frames`) against the
  reference object pose. This is the *designed* grasp: the PD targets, including the squeeze.
- **Human contacts** (`mano_where.py`, `mano_contacts.py`): the MANO contact columns of our reference (our perception of
  the human, not ground truth).
- **Policy rollouts** (`rollouts.py`): the kit's `read_trajectory` (`pose_xyzw` simulated, `reference_xyzw`
  reference). These rollouts contain only object poses, so contacts are measured for the policy only on
  `policy_trace.npz` (rp18).

Caveats:
- The policy body trace exists only for rp18 (50M, `mc`/library_v2 reference). The E1 policy rollouts give object
  poses only.
- The contact proxy is geometric. Contact forces from FlashCHORD's readout are not calibrated (notes 24) and were not
  used.
- The batch traces were analysed every 2nd frame (`app6`, `kf18`, `rp18 zero_r1`), the others every frame.

## 2. Object geometry (our library_v3 meshes; the scan only as a [GT] diagnostic)

| | mini_dust_pan (ours) | mini_dust_pan (scan) [GT] | mini_sweeper (ours) | mini_sweeper (scan) [GT] |
|---|---|---|---|---|
| bounding extents (PCA) | 17.3 × 15.8 × 3.7 cm | 19.0 × 16.7 × 4.5 cm | 14.4 × 11.0 × 3.3 cm | 14.3 × 11.4 × 4.8 cm |
| plate part thickness (1 cm cells, axis-3 extent) | 11–12 mm over the pan | 4–8 mm (thin sheet; ~2.5 cm raised hood) | 12–17 mm over the bristle head | 6–8 mm |
| solid wall thickness (ray, p10/p50/p90) | 7.7 / 11.0 / 15.8 mm | – | 10.9 / 15.9 / 24.7 mm | – |
| handle | flat **ring**: hole inscribed Ø 2.9 cm (3.0 × 3.8), end band 2.0 cm wide × 1.3 cm thick, ring 7.1 cm wide | hole Ø 3.3 cm, band 2.0 cm, ring 7.6 cm | flat **ring**: hole Ø 2.0 cm (3.2 × 2.8), end band 1.8 × 2.5 cm, ring 7.2 cm | hole Ø 3.9 cm, band 1.4 × 2.0 cm, ring 7.0 cm |
| hole in the collision pieces | free ≈ 3.0 (axis1) × 3.5 (axis2) cm | – | free ≈ 1.5–2.5 cm | – |
| volume | 157.7 cm³ | not watertight | 115.8 cm³ | not watertight |
| mass, COM, inertia (URDF used by the simulator) | 0.3 kg (kit placeholder); COM (−0.52, −0.18, −0.42) cm; I = (10.3, 6.7, 4.0)·10⁻⁴ kg m² | – | 0.3 kg; COM (−0.16, −0.03, 0.00) cm; I = (7.4, 5.8, 1.9)·10⁻⁴ kg m² | – |
| COM lever from the handle | 10.3 cm to the ring end, 6.8 cm to the hole centre → gravity moment about a grip at the ring end, plate horizontal: **0.30 N m** | – | 8.0 / 4.4 cm → **0.23 N m** | – |
| PCA singular-value ratio σ1/σ2 (mesh vertices; the wrap rule uses hull vertices, threshold 3) | 1.28 | – | 1.74 | – |

Readings:
- [M] Both objects are plates with a **ring handle**. Neither qualifies for `wrap_grasp` (PCA ratio ≥ 3), so the
  recipe gave both the snapped human grasp.
- [GT] Our meshes are 1.5–2× thicker than the real plates (TSDF voxel 4 mm). Our sweeper's ring hole is half the
  real area (6.6 vs 13.2 cm²).
- Robot finger links (collision hull bounding boxes) [M]:
  - index distal (DP) 2.7 × 1.4 × 1.5 cm; middle phalanx (MP) 3.6 × 1.9 × 1.7 cm; proximal (PP) 4.5 × 1.9 × 2.2 cm;
  - thumb DP 3.0 × 1.7 × 1.7 cm; palm 8.4 × 8.6 cm.
  - One finger fits through the dust-pan hole in the collision pieces. The sweeper hole fits only a distal phalanx,
    tightly.

## 3. What the human does

**Motion [GT] (mocap displacement from frame 0), confirmed by our reference (same timing, ±1 cm):**

- ep18 dust pan:
  - lifted and tilted at **f16–24**: +2.6 cm, 43°;
  - held tilted (lip on the table, dz 1.5–2.6 cm, 43–50°) f24–115;
  - lifted to 16 cm f116–150;
  - put down f150–160.
- ep18 sweeper:
  - still until **f36**;
  - **lifted 5.0 cm and turned 24° at f38–44**;
  - set down f50, then sweeping strokes with the bristles pressed **0.4–0.9 cm below the rest height**: f50–62 (13 cm),
    f78–88, f100–112;
  - lifts of 6–8 cm in between and over f118–175;
  - put down by f190.
- ep39 dust pan:
  - still until **f45**;
  - lifted 6.5 cm at f54, 14.3 cm at f57, **20.7 cm at f63**;
  - then a carry with 90–109° tilts and up to 27 cm lift;
  - put down f240–270.

**Hands (our MANO contacts) [M]:**

> **Correction, 2026-10-25 [M].** This table and the first reading below label the contact slots in MANO link order,
> which does not describe our references' slots. They are kept as written; the corrected table follows the readings.

| hold | frames | palm share | thumb / finger contact share | thumb-vs-finger opposition across the two faces | where |
|---|---|---|---|---|---|
| ep18 left on dust pan | 10–187 | 0.13 | 0.83 / 1.00 | 0.38 of frames | 47% of contacts on the ring region (axis1 < −5 cm). Thumb segments on the **top face** (83–86%); ring-3 and little-3 on the **bottom face** (59%, 100%), little-1/2 split. |
| ep18 right on sweeper | 38–323 | 0.04 (0.15 over f60–120) | 0.82 / 0.73 | 0.53 | 64% on the ring and neck. Thumb-1/2 on +face (54–56%); middle-2, ring-3, little-1/2 on the −face (79–94%). |
| ep39 left (pick-up) | 36–103 | 0.45 | 1.00 / 0.99 | 0.69 | 73% on the ring. Fingers on +face (index-3 86%, middle-1 77%); thumb distal on −face (82%). An inverted clamp. |
| ep39 right (carry) | 104–292 | 0.26 | 0.93 / 0.99 | 0.64 | 81% on the ring. Thumb on +face (thumb-1 94%); fingers mixed; little-3 at the ring end. |

- [M] This confirms the work-log reading (a thumb-fingers clamp, palm 4–45%). It adds one point: the human clamps the
  **ring handle across its thickness**, with the thumb and the fingers on opposite faces.
- [M] **The human's sweeper contact labels start too late.** The right hand has 0 MANO contacts on the brush from f30
  to f58, while the brush moves from f38. The MANO joints are 15–19 mm from the reference brush at f28–40 and about
  4 mm from f42. So the contact labeller, not the hand tracking, misses the first 22 frames of the manipulation.
  `hold_phases.py` therefore reports `right holds mini_sweeper 61–219` instead of starting about f36.

**Correction, 2026-10-25: hands table with the right slot labels [M].** `mano_where.py` and `mano_contacts.py` read
the reference's `mano_link_names` (palm, thumb1 … pinky3) as slot labels. `pipeline/mkref.py` fills the 16 slots in its
probe order: thumb, index, middle, ring and pinky tips, then their DP sites, then the thumb MCP and the finger MP sites,
and the palm last (`approach3-grasp-taxonomy.md` §9). So "palm" above was the thumb tip, "thumb1–3" the index, middle
and ring tips, and "little-3" the palm. Same references, windows and code, scripts fixed; old and corrected output:
`audit-plates-scripts/out/mano_where_slotfix-20261025.txt`.

| hold | frames | palm share | thumb / finger contact share | thumb-vs-finger opposition across the two faces | where |
|---|---|---|---|---|---|
| ep18 left on dust pan | 10–187 | 0.02 | **0.19** / 1.00 | 0.12 of frames | 47 % on the ring region. Index–little tips on the **top face** (83–86 %); middle MP on the bottom face (59 %). |
| ep18 right on sweeper | 38–323 | 0.00 (0.00 over f60–120) | **0.09** / 0.83 (0.35 / 1.00 over f60–120) | 0.05 (0.15 over f60–120) | 64 % on the ring and neck. Index and middle tips on +face (54–56 %); ring DP and the middle / ring / little MPs on the −face (79–94 %). |
| ep39 left (pick-up) | 36–103 | 0.00 | 0.52 / 1.00 | 0.22 | 73 % on the ring. Index and middle DPs on +face (86 %, 77 %); ring tip on −face (82 %); thumb tip 0.45, faces mixed. |
| ep39 right (carry) | 104–292 | **0.73** | 0.31 / 0.98 | 0.09 | 81 % on the ring. Palm at the ring end (axis1 −9.3 cm); index tip on +face (94 %); thumb tip 0.26, on the +face or edge. |

- [M] In our perception the fingers hold the ring band across its thickness: tips on one face, DPs or MPs on the
  other. The **perceived thumb is mostly absent** (0.09–0.52; thumb-vs-finger opposition 0.05–0.22 of frames). The
  reading "the human clamps the ring handle with the thumb and the fingers on opposite faces" therefore has no basis
  in our contact labels. The ring-region shares, the late sweeper labels and the motion readings above are unchanged.
- [I] Thin bands (1.2–2.3 cm) are at or below our hand error (±1–2 cm), so the thumb may be there in the video and missed
  by perception. The statements in §0, §5 and §8 that cite "the human's clamp" (thumb on one face, fingers on the other) remain
  hypotheses on mechanical grounds; they are no longer supported by the human contact data. The robot-link contact
  proxy (§4–§6, including the human-retargeted `mckfid` rows) uses robot geometry and is unaffected.

## 4. ep18 mini_dust_pan (left hand): a grasp failure

**The designed grasp [M]** (`SNAP human grasp`, closing index 0.2, middle 0.025, ring 0.025, little 0.175,
thumb 0.175; grasp pose from f16; hold from f8; closed f18; end f187).

Link distances to the pan in the reference:

| reference | f16 (grasp frame) | f18–186 (squeezed hold target) | f192 (touching pose, at release) |
|---|---|---|---|
| grasp-lock `ref_gl` | index MP −2, index DP −1, middle MP 0, ring MP +3, **thumb DP +9**, middle DP +9 mm | index MP −1, middle MP 0, ring MP +3, index DP +3, little MP +10, **thumb DP +20** mm | middle/ring MP and DP −6 to −8, thumb DP +3 mm |
| human-retargeted `mckfid` (input) | 6 links within 1 mm, **thumb DP 0 mm** | (f16–60) 5 distal links in contact (index/ring/little 98%, middle 95%, **thumb 75%**) on the ring end and side | – |

- The squeezed hold target (`robot_*_frames`, f18–186) touches only the **far end edge of the ring** (axis1 −9.6 to
  −10.0 cm, edge faces): index/middle/ring middle phalanges, a hook. There is no contact on either face and no
  thumb.
- The +0.4 rad squeeze curls the distal links and the thumb *away* from the plate: the thumb goes from 3 mm to 20 mm,
  the middle/ring distal links from about −7 mm to +12–14 mm. On a thin plate, curling past the edge loses the
  contacts that the snap had found.

**Zero action, E1 (approach 15 cm) [M], per frame:**

| frame | reference lift | sim lift | sim displacement / turn | left links within 3 mm (sim) | hand |
|---|---|---|---|---|---|
| 0–6 | 0 | 0 | ≤ 0.7 mm / 2.3° | none (38 mm) | the left fingers are **below the table plane** (lowest little/ring links z 0.547–0.59 m vs table 0.600); hands do not collide with the table |
| 7–12 | 0.1 cm | −0.1 cm | 1–2 mm / 2–3° | middle DP+MP, ring MP+DP, on the **bottom face** of the ring | closing (MCP first) |
| **13–18** | 0.0 → 0.9 cm | **0.4 → 5.1 cm** | **9 → 80 mm / 2 → 22°** | 4 links, bottom face only | fingers rise from below; the pan is scooped up |
| 19–31 | 1.3–2.6 cm | 4–5.7 cm (pan standing on its edge, turned 27–62°) | 85–89 mm | 2–4 distal links | held from below only |
| 32–41 | 2.5 cm | 4.4 cm | turned 75–83° | **0** | contact lost |
| 42–187 | 0.2–16.3 cm | ≤ 7.0 cm | slip median 3.8 cm / 54°, max 20.7 cm / 158° | about 1 link (index DP 47% of frames) | the reference peak (16.3 cm at f148) is followed at 4.5 cm |

The same flick at closure appears in every zero-action variant [M]:

| variant | at f18 (closure) | pan in-hand slip (median / max) |
|---|---|---|
| E1, approach 15 | 80.1 mm / 21.6° | 3.8 / 20.7 cm |
| E1, approach 6 | 62.8 mm / 21.9° | 4.2 / 18.0 cm |
| kf18, no approach | 64.1 mm / 16.9° | 9.4 / 23.0 cm |
| rp18 r1 (`mc` reference) | 35.6 mm / 36.4° | 8.5 / 15.2 cm |

In rp18 r1 the pan was pushed from f14, its contact was lost at f20, and it fell back flat.

**Policy rollouts [M]:**

| policy | pan leaves rest | lifted > 2 cm on the reference's lifted frames | other |
|---|---|---|---|
| E1 10M, 5 rollouts | f10–12 (reference moves at f18) | in 0 of 5; r3 3.1 cm early, r5 11.5 cm but 7–18 cm off its path | – |
| E1 curve: 30M / 50M / 70M | – | max lift 2.0 / 4.7 / **30.2 cm** | at 70M the pan is >10 cm off from f17 (flung) |
| rp18 50M, 5 rollouts | – | max lift 0.0 cm in 5 of 5 | the full-body trace shows the left hand **4–13 cm from the pan for the whole hold** and 0 contacts (learned avoidance) |

**Verdict [I]:**
- This is a grasp failure:
  - the type: a hook with no opposition;
  - the contacts: one edge, then the bottom face only;
  - the closure direction: from under the table plane, so the closing fingers lift a free plate.
- The standard policy on the same human-retargeted hand grasps it: it leaves rest at f15–19 and lifts 17.6–19.1 cm,
  within 3 cm in 93–97% of frames, so the physics allows it.

## 5. ep18 mini_sweeper (right hand): hold timing and approach knocks, not grasp type

**The designed grasp [M]:**
- grasp pose from f62, hold from f53, closed f63;
- squeezed target: thumb PP + DP on the **+face**, middle / ring / little MP on the **−face** of the ring's side band
  (axis1 −3.8 to −5.1 cm, axis2 −3 cm), pressed −2 to −6 mm;
- palm 52 mm from the brush.

This is a clamp across the band, the same type as the human's. The human-retargeted reference has the same
arrangement (thumb DP and index on +face, ring/middle/little on −face).

**Zero action, E1 (approach 15 cm) [M]:**

| frame | reference displacement | sim displacement / turn | right hand (sim), min distance; palm | event |
|---|---|---|---|---|
| 0–36 | ≤ 2.3 mm | ≤ 4 mm / 0.3° | approach from f16: 6.7 mm at f20, then 30–40 mm (backed-off pre-grasp); palm 61–84 mm | brush stands |
| **38–50** | **7 → 51 mm** (lift 4.9 cm at f44) | ≤ 2 mm | 36–50 mm; the pre-grasp **follows the moving reference brush** | the human's real pick-up [GT]; our hold has not started |
| 52–56 | 49–84 mm | 4–13 mm / 4–12° | **ring DP + little DP touch** (−0.3 to +2.9 mm, side edge of the ring) | fingers slide into the reference pose, 5–8 cm from the sim brush, and clip it |
| 58–63 | 98–129 mm | 3–7 mm | 42–71 mm; **palm 112 mm at closure (f63), 0 contacts** | closes on air |
| 64–76 | – | tips 3 → 86° (lift −5 cm = lying flat) | 45–78 mm; nearest left link > 25 cm; dust pan 18–21 cm away | falls by itself after the f52–56 clip (stance margin 3.2°) |
| 77–323 | reference lifts to 8.4 cm | never lifted (max 0.0 cm), 0 contacts | 0.0 mean contacts | – |

The other variants agree [M]:
- E1 approach 6: knocked at f26 (right hand 11.9 mm), lying flat;
- kf18 (no approach): knocked at f26 (21 mm, 25 mm / 24°);
- rp18: falls at f1–9 with no hand within 12.6 cm (the `mc` reference with the library_v2 sweeper; the start
  failure documented on 23 Oct).
- Policies [M]: in E1 10M the sweeper leaves rest at f28–32 in 4 of 5 rollouts (before the reference moves at f39)
  and lies flat by f40–60. It is lifted > 2 cm in 0 of 5 rollouts (max 1.3 cm). At 70M it is flung (5.9 cm, >10 cm
  off from f22).
- The standard policy grabs the brush at f55–56. It misses the f38–55 pre-move, as our hold detection does, but
  catches up: within 3 cm in 87–90% of frames, lift 7.5–10.1 cm.

The [GT] mocap also shows the reference asking the rigid brush to go **0.2–0.9 cm into the table** during the sweeping
strokes (dz −0.7 cm at f54–56). The real bristles bend; our rigid mesh cannot. A locked grasp following that path
pushes the brush into the table. This has not been tested yet; it matters once the brush is held.

**Verdict [I]:** the sweeper failure is not a grasp failure. The grasp type matches the human and was never
exercised. The hold starts 15–23 frames after the object starts moving, so the approach follows a phantom and knocks
the brush on a 3.2° knife-edge stance.

## 6. ep39 mini_dust_pan: carrier merge, then an empty grasp

**Phases [M]** (`hold_phases.py` on the grasp-lock reference): `left holds mini_dust_pan 44–103`, `right holds
mini_dust_pan 70–292`, two-handed f70–103.

`--single_hand 1` chose the right hand (222 frames vs 59) and merged to `right 70–292`, parking the left hand at its
frame-0 pose. The left-hand pick-up was deleted. The rule started the carrier at the carrier's first hold (f70)
instead of the object's first hold (f44). The human-retargeted input reference has the left hand on the pan from f40
to f100: index/middle/ring/little distal links within 0–5 mm, thumb distal 0–8 mm.

**Zero action, E3 [M]:**

| frame | reference lift | sim displacement | right hand (sim) min distance / palm | reference right hand to the reference pan |
|---|---|---|---|---|
| 30–46 | 0 | 1.2 mm | 247–251 mm | 230–240 mm |
| 48–56 | 0 → 10.8 cm | 1.2 mm | 196–247 mm | 128–214 mm |
| 58–64 | 14.8 → 20.4 cm | 1.6–2.8 mm | 75–94 mm / 111–123 mm | 79 → 7 mm |
| 66–70 (closing) | 20.4–18.6 cm | 2 mm | 93–103 mm | −9 to −3.5 mm (index/middle/ring/little DPs) |
| 72–292 | up to 26.9 cm | ≤ 2.8 mm all episode | 81–104 mm over f72–110, never closer than 26 mm later; **0 contacts in the whole episode** | squeezed target: **no link within 3 mm** (middle MP 3.9 mm, others 9–17 mm, thumb > 21 mm) |

- zero action sim_vs_ref 0.1755 vs floor 0.1763;
- slip median 19.1 cm; error > 10 cm from f56;
- the parked left hand stays 107–115 mm away.

**Policies [M]:**
- grasp-lock fine-tune, 5 rollouts: max lift 0.0–0.8 cm, within 3 cm 17% (rest frames only), registered
  0.168–0.175;
- standard RL, same perceived path, keeps the human's left-hand pick-up and the handover: 4 of 5 rollouts follow the
  lift to 26.2–26.7 cm (within 3 cm 97–100%, AUC 0.937–0.948). The one failure (r2, 0.241) drops the pan at f90–97,
  inside the human's two-hand handover (f70–103).

**Verdict [I]:**
- primary: the carrier merge, a reference-construction bug, not a grasp failure;
- secondary: the snapped right-hand grasp would not hold either (it has no contact and no thumb), the same defect as
  the ep18 dust pan (snap: `"thumb": null`, gap 5.3 mm, 4 fingers).

## 7. The fine-tune degradation is a consequence [M]

E1 curve (sim_vs_ref, one evaluation each): 0.446 at 10M, 0.357 at 30M, 0.307 at 50M, 0.060 at 70M.
- The dust pan is never lifted by 10–50M policies (max 1.2–4.7 cm). At 70M it is flung to 30.2 cm and is more than
  10 cm off its path from f17.
- rp18's chosen 50M policy keeps the left hand 4–13 cm from the pan for the entire hold, with 0 link contacts.

Inference [I]: the reference cannot be achieved from the first contact on (the closure flick, a phantom brush, a pan
in the air). Contact therefore costs reward, and the residual policy either retreats, which scores the resting floor,
or exploits impulses. This matches the 23 Oct observation "the fine-tuned policy moves its hands away from the
table". No training change can repair a reference whose grasp is never acquired.

## 8. What grasp would hold each object (design, labelled as hypotheses)

Physics budget [M + I]:
- gravity moment about a grip at the ring end: 0.30 N m (pan), 0.23 N m (brush);
- weight 2.94 N (0.3 kg placeholder);
- contact μ 1.0, pyramidal cone (worst case μ ≈ 0.71), no torsional friction at condim 3 (notes 24);
- finger PD kp 1.7 N m/rad, so a 0.4 rad squeeze gives about 0.68 N m, or 9–14 N at a 5–8 cm lever.

Without torsional friction, a two-point pinch cannot resist rotation about the line joining its two contact points.
Moments must come from **spread normal-force couples**: for 0.30 N m, the couple lever must be at least 2–3 cm at
10–15 N.

Literature [L] (opened):
- Feix et al. 2016, "The GRASP taxonomy of human grasp types", IEEE THMS 46(1):66–77
  (https://www.eng.yale.edu/grablab/pubs/Feix_THMS2016.pdf).
  - Pad opposition needs an **abducted thumb** opposing the finger pads. The thumb is adducted only for side
    opposition (the lateral/key grasp #16) or when it is not used.
  - The lateral grasp is the type most consistently named across taxonomies, and it sits between power and precision.
  - Grasps with the same hand shape differ by contact type: the medium wrap has palm contact, the prismatic
    four-finger grasp only pads.
- Bimbo et al. 2019, "Exploiting robot hand compliance and environmental constraints for edge grasps", Front. Robot.
  AI 6:135 (https://www.frontiersin.org/articles/10.3389/frobt.2019.00135/pdf).
  - "there are several objects that cannot be grasped from the top when lying on a hard surface, e.g., flat or small
    objects … we typically grasp them with a flip or a slide-to-edge grasp".
  - 320 trials with 16 objects. Continuous slide-and-grasp suits small flat objects; pivot-and-regrasp suits larger
    ones.
- Eppner et al. 2015, "Exploitation of environmental constraints in human and robotic grasping", IJRR (abstract,
  https://depositonce.tu-berlin.de/items/ec161341-6477-4b57-927f-43fb98fa3942/full): robust grasping is "a process of
  successive exploitation of environmental constraints".
- Zhou & Held 2022, "Learning to grasp the ungraspable with emergent extrinsic dexterity", CoRL
  (https://arxiv.org/pdf/2211.01500): an RL policy learns to push a flat object against a wall before grasping it,
  with 78% success on hardware.

Relevance to us [I]:
- Our plates have **ring handles**, so a slide-to-edge or flip is not needed. The ring band can be grasped from above,
  as the human does.
- Our simulator lets fingers pass through the table (`robot_support_collision: false`). That makes a clamp across a
  lying plate possible, and it is also what scoops the pan when fingers close upward from below with nothing on top.

**Dust pan (ep18 left, ep39 pick-up and carry): a ring-handle grasp with opposition [H].**
- Type: pad opposition, thumb abducted.
  - Option A: the thumb pad on the **top** face of the ring's end band, index and middle pads on the **bottom** face,
    spread at least 2 cm apart along the band.
  - Option B, preferred where the hole is free in the collision pieces (dust pan: about 3 × 3.5 cm): the **index
    finger inserted down through the hole**, its middle and distal phalanges curled under the far band, the thumb pad
    pressing the band's top face over it, and the middle finger under the end band. The ring then cages the hand, so
    gravity and the 90–109° tilts of ep39 load normal forces rather than friction.
- Approach: from **above, along the plate normal**, with the fingers pre-shaped. No finger may sweep under the plate
  before the thumb is on top. Today the closing fingers start below the table plane, f0–12.
- Closure order:
  1. the thumb and the hooking/opposing index touch within the same 1–2 frames, a balanced squeeze with net force on
     the free plate about 0;
  2. then the middle finger;
  3. MCP-first applies to the fingers that are not hooking.
- Squeeze: hold the contact set. The current +0.4 rad uniform squeeze curls the thumb 20 mm *off* the plate. Instead,
  squeeze along each contact normal (the BODex/DexGraspNet-style target already noted in notes 23), or Δq = Jᵀf/kp
  with f ≥ 10 N per opposing pair.
- Gate: on the zero-action replay:
  - pan displacement ≤ 5 mm / 3° from hold start through closure (now 63–80 mm / 17–22°);
  - in-hand slip ≤ 1 cm / 5° through the tilt (f20–115) and the 16 cm lift.

**Sweeper (ep18 right) [H].**
- Type: the human's clamp across the ring side band or neck, which is already the designed type: thumb on one face,
  index/middle/ring on the other, spread at least 2 cm. Our sweeper hole (about 2 cm in the collision pieces) is too
  tight for a hook, so use the band clamp.
- Timing: the hold must begin at the **object's motion onset**: the first reference frame where it leaves its rest by
  more than 1 cm or 3°, minus the closing frames. That is about f28 for ep18, not the MANO contact onset (f61).
- Approach: **horizontal, along the plate normal**; the brush stands upright on a 3.2° stance margin. The hand opens
  wide enough to clear both faces (the plate is 2.5 cm thick plus about 2 cm finger pads).
- Closure: thumb and fingers simultaneously, so the free brush feels no net push.
- During the sweep strokes, keep the reference brush above the table (the reference presses it 2–7 mm in), or let
  the grip comply. Otherwise a locked grip drives a rigid brush into the table.

**ep39 carrier rule [H].** With one carrier per object, the carrier must take over at the **object's first hold**
(f44): it picks the pan up where it lies, at the time the human's left hand did. The alternative is to keep the
human's own pick-up hand until the handover. A second hand that closes on an object the reference already shows in
the air can never succeed.

## 9. Hypotheses and the experiments that would falsify them

| # | hypothesis | experiment (CPU-buildable; one GPU replay each, about $0.1) | falsified if |
|---|---|---|---|
| H1 | ep39: if the single-hand carrier starts at the object's first hold (f44) with the human's pick-up hand or the carrier, the pan is lifted at zero action. | rebuild `ref_gl` with the fixed merge rule; zero-action replay | zero-action pan lift at f60 < 5 cm, or sim_vs_ref ≤ 0.2 |
| H2 | ep18 sweeper: if the hold starts at motion onset (reference leaves rest > 1 cm / 3°, f38 → h0 ≈ f28), with a horizontal approach and simultaneous closure, the brush is held before it moves. | same as H1 for ep18 (no change to the dust pan) | the brush tips more than 5° before closure, or lifts < 3 cm at f44 |
| H3 | Dust pan: an opposition ring grasp (A or B above), approached from above with the thumb and index closing together, does not flick the pan. | grasp-lock with the designed ring grasp; zero action ep18 and ep39 | closure displacement > 10 mm or turn > 5° (now 63–80 mm / 17–22°), or in-hand slip > 2 cm during f20–150 (ep18) |
| H4 | Contact-label lateness is general: wherever MANO contacts start after the object's motion onset, a hold detected from contacts alone is late. | over all public references, compare the hold start with the reference-motion onset (CPU) | in fewer than 2 of the remaining failed public episodes is the hold more than 5 frames late |
| H5 | With an achievable zero-action reference (H1–H3 hold), the fine-tune curve rises with training instead of falling (0.446 → 0.060 now). | 70M fine-tune, 3 evaluations per checkpoint | the curve still falls after 30M |
| H6 | Our over-thick meshes (pan 11–12 mm vs real 4–8 mm [GT]) do not block the ring grasp: the collision pieces keep a 3 × 3.5 cm hole. | H3's replay already tests this | the index finger cannot pass the hole without moving the pan (> 5 mm) |

## 10. Implications for the owner's evolutionary-algorithm question (brief, [I]/[H])

The audit splits the failures into two classes:
- **Reference construction:** hold timing, carrier merge. A wrong reference is wrong for any optimiser. RL from it
  degrades, and an evolutionary search over grasp parameters scored on the same reference would return no feasible
  grasp, because the hand is never at the object when it closes.
- **Grasp design:** the dust pan's contacts, approach and closure. Here the search space is small and structured:
  - contact location along the band (1-D);
  - hook vs pinch (categorical);
  - approach direction (2 angles);
  - closure order and timing (3–4 scalars);
  - squeeze per joint.
  The fitness is a cheap zero-action replay: closure displacement, slip, lift.

That shape suits population methods (CMA-ES or a genetic algorithm over about 10 parameters, run as parallel worlds
in one GPU replay). OmniHOI, as recorded in notes 23 and not re-opened here, reports CMA-ES keyframe offsets reaching 89% Sharpa success against 19% for SPIDER in its benchmark.
[H] An evolutionary grasp-design step in front of the RL fine-tune (fitness = gate H3) would beat further RL-only
training on ep18/ep39. It is falsified if a 64-member, 20-generation CMA-ES over these parameters finds no candidate
that passes the H3 gate while the hand-designed opposition grasp does, or if neither passes.

## 11. Reproduction

Scripts: `docs/research/grasp/audit-plates-scripts/` (Python 3 with numpy, scipy, trimesh, pyarrow, pandas;
`audit_lib.py` reads the Sharpa URDFs from the scratchpad FlashCHORD source and the CoACD pieces from
`scratchpad/audit/hulls/*.npz`).

Commands, run from `scratchpad/grasp_work/audit-plates` with `OMP_NUM_THREADS=1`; machine: the Claude cloud VM (4
CPU); code at d09b128 plus these scripts. `$G` below is the reference directory
`data/hf/runs/<run>/refs/glock/ep<N>/processed/sequence_id=*/robot_name=sharpa_wave`.

- Trace audits, about 7 min each (every frame):
  - `analyze_trace.py $G/ref_gl_ilc.parquet $G/ref_gl_grasp_lock.json data/hf/runs/<run>/results/glock_public/ep<N>/zero.npz out/<tag>`
  - for rp18, the policy: `… ref_gl_r1_ilc.parquet ref_gl_r1_grasp_lock.json …/vid/policy_trace.npz out/rp18_policy`
- Contact locations: `robot_where.py REF SIDE OBJ F0 F1 [TRACE] [MM]`
- Human contacts: `mano_where.py REF SIDE OBJ F0 F1` and `mano_contacts.py REF counts F0 F1 STEP`
- [GT] motion: `gt_vs_ref.py episode_0000NN.parquet REF scripts STEP`, with the public parquet from the HF cache or
  `nvidia/video_to_data_challenge`.
- Rollouts: `rollouts.py …/episode_0000NN.parquet …`
- Geometry: `geom.py`, `geom_map.py`, `ring.py`; object-to-object distances: `obj_obj.py`.

Outputs: `out/*.json` (phase summaries and events per trace, geometry). The per-frame CSVs are in the scratchpad only
(`scratchpad/grasp_work/audit-plates/out/*_frames.csv`, about 100 kB each).
