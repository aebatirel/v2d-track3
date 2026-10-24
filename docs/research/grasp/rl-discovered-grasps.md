# What grasp did the successful standard RL policy discover on the ep18 plates, and how does it differ from the grasp-lock grasp?

2026-10-24, CPU only (no rentals, no spending). Workflow step "rl-grasp" of the owner's option 2 (one recipe with designed
grasps). Labels: **[M]** measured here from stored traces, references and meshes; **[GT]** number computed against
mocap after inference (reporting only, never fed back); **[L]** literature I opened; **[I]** inference; **[H]**
hypothesis with the experiment that would falsify it.

## 0. Answer

**Dust pan (left hand).** The 0.889 policy grips the pan's ring handle with a **lateral (key) pinch** across the
handle's end band:
- the thumb pad and the thumb's proximal phalanx press on the band's **top** face;
- the index finger's middle phalanx (its radial side) and its fingertip pad push up on the **bottom** face, with the
  index tip inside the ring hole;
- the hand is **palm-up**: it slides in low and sideways under the raised ring;
- thumb and index touch **in the same frame (f16)**, and the pan moves at most 2.9 mm / 3.5° before it is lifted.

During the hold, the pan's far lip stays on the table in 70% of the held frames. For the 19 cm lift the grasp becomes a
**hook through the ring**: the middle and ring fingers go through the hole while the thumb stays on top or lets go.

**Sweeper (right hand).** The policy does **not** take the ring handle, as the human reference does. It moves its grasp
about 10 cm down to the **neck and top of the brush head** and clamps the whole plate width between two groups:
- on one face, the thumb column (metacarpal, proximal and distal phalanges);
- on the other face, all four fingers, flat across the plate, with their tips reaching the far edge;
- the palm and the index knuckle butt against the near lateral edge.

There are 10–13 links in contact, and the brush moves only 4.8 mm / 2.3° at closure.

**What the grasp lock does instead.** The like-for-like designed grasp (run E1: same settled reference, same meshes)
has no thumb on either plate when it closes:
- **dust pan:** the fingers come up from below first (f7–9). By f18 the pan has slid 62 mm, turned 22° and risen
  5.1 cm, all before any thumb contact; the thumb first touches at f54. The squeezed hold target touches the pan only with the backs of the
  index middle and distal phalanges at the end edge.
- **sweeper:** three fingertips (middle, ring, little) brush the ring edge at f50–56, and the brush tips over at
  f64–80.

The grasp-lock *policy* trace (rp18) never touches the pan, and its brush falls at f1–10, before any hand comes near
(a start-stability failure on the older `mc` reference with the rounded library_v2 sweeper; not like-for-like).

**What changed relative to the human reference.** The policy keeps the human's finger shapes; most of its joint means
are within about 15° of the reference. What it changes is **where and when the hand closes**:
- the wrist is offset 14 cm / 38° from the reference during the pan pick-up;
- the wrist is offset 8.5–10.7 cm / 19–37° throughout the sweeper hold;
- the thumb lands on the free top face at the same moment as the opposing finger.

A designed grasp must copy contact *roles and timing*, defined relative to the object, not the human wrist path.
Section 7 lists the exact specification.

## 1. Data, method, caveats

| source | what | run / file (HF store `aebatirel/v2d-store`) |
|---|---|---|
| RL (the 0.889 policy) | body trace of FDR seed 43, 250M (`policy_250003456`), played like the evaluator (VOC 0, start at f0, terminations off, GPU, 354 frames) | `runs/20261023-kf18-a674fd7/results/old889/{policy_trace.npz, view.mp4}`; policy `runs/20261023-fdr43-715c9f7/runs/perc2mckfid/ep18-s43/policy_250003456.safetensors` |
| RL official rollouts | 6 evaluations of the same policy (object poses only) | `runs/20261023-fdr43-715c9f7/results/hard_ab/ep18/mckfid-s43/r1..r6` |
| reference (human) | settled `perc2mckfid` reference the policy tracked | `runs/20261023-fdr43-715c9f7/refs/perc2mckfid/ep18/processed/.../3af5ffc5…-0.parquet` |
| grasp-lock design | E1 grasp-lock reference (approach 15 cm, SF=1, REPLAN=1, library_v3, same settled reference) | `runs/20261024-e1-e49e83d/refs/glock/ep18/.../ref_gl_ilc.parquet`, `ref_gl_grasp_lock.json` |
| grasp-lock executed | E1 zero-action replay of that reference (GPU) | `runs/20261024-e1-e49e83d/results/glock_public/ep18/zero.npz` |
| grasp-lock policy | rp18 grasp-lock fine-tune at 50M (`mc` reference, library_v2 sweeper, REPLAN 2) body trace | `runs/20261023-rp18-a674fd7/results/glock_public/ep18/vid/policy_trace.npz` (reference `ref_gl_r1_ilc.parquet`) |

**Policy configuration** [M] (safetensors metadata of the 0.889 checkpoint):
- default `SharpaHands` embodiment: soft wrist, kp 25 N/m;
- residual action: wrist position clip 0.2 m, wrist rotation clip 1 rad, finger clip 1 rad, EMA 0.3;
- final-stage objective weights: object keypoints 20, **force closure 6**, **contact wrench support 3**, unintended
  contact −2, missed contact −1, hand keypoints 0.25, hand joint position 0.25;
- collision: `robot_support_collision: false`. The hands pass through the table in training and in the evaluator,
  which rebuilds the checkpoint's resolved config. FlashCHORD's `physical.yaml` would turn this on.

**Is the trace representative?** [M] Yes. Compared with the 6 official rollouts:
- the rollouts follow the trace within 0.8–1.8 cm (mean) / 2.0–2.8 cm (p90) for both objects;
- the pan leaves rest at f15–19 (trace f18) and the sweeper at f55–56 (trace f57);
- maximum lifts are 17.6–19.1 cm (trace 18.9) for the pan and 7.5–10.1 cm (trace 8.8) for the sweeper;
- registered AUC [GT] of the rollouts: 0.868–0.902, mean 0.889.

**Geometry** [M] (scripts in `docs/research/grasp/rl-grasp-scripts/`):
- **hand:** collision-hull samples of each Sharpa Wave link (URDF convex meshes, with the fixed pads composed into the
  distal link, as FlashCHORD collapses them).
- **objects:** CoACD pieces of our library_v3 meshes (Newton settings), which the RL and E1 runs used. For rp18 I
  decomposed library_v2's sweeper the same way.
- **distance:** signed distance exact inside a piece, and the exact Euclidean distance (closest point on the piece's
  triangles) for near samples outside.
- **contact:** a link within **5 mm**.
- **plate frame:** PCA axes. axis1 = long axis with the ring handle at negative axis1; axis3 = plate normal.
  - Dust pan: axis1 < −4 cm is the ring, −4..−2 the neck, beyond that the pan.
  - Sweeper: axis1 < −3 is the ring, −3..+1 the neck, beyond that the head.
- **face label:** the mesh normal at the closest point (+axis3 / −axis3 / edge).
- **world side:** where the link sits relative to the surface (above / below / beside).
- **where on the link:** palmar pad / dorsal / radial (thumb side) / ulnar, from the contact sample's position around
  the link axis. The palmar direction is the direction the next joint flexes towards.
- **joint angles:** recovered from parent and child link poses with the URDF joint origins and axes. The off-axis
  residual is 0.000 rad on the simulator traces, so the recovery is exact.
- **ring holes in the collision pieces** (`hole_map.py`):
  - dust pan: 9.4 cm², 3.2 × 3.6 cm, inscribed radius 1.5 cm, centre (−6.4, 0.1) cm; the band around it is about
    1.1 cm thick;
  - sweeper: 6.4 cm², inscribed radius 1.0 cm, centre (−4.2, 0.4).
  - "in hole" means at least 3 link samples inside the hole's volume.

**Caveat found on the way: the reference parquets' link frames are not a consistent kinematic chain** [M]:
- In `perc2mckfid`, the `robot_*_frames` positions agree with forward kinematics of the wrist pose plus the
  `robot_*_finger_joints` column, except the middle phalanx in some frames (p90 10.5 mm, max 34 mm).
- Their **orientations** do not agree: the index proximal phalanx is off by 42° (median, max 69°) and the thumb
  proximal phalanx by 38°. Joint angles recovered from those frames are constant (index MCP 32° throughout), unlike the
  joint column (index MCP median 47°, up to 90°).
- In the grasp-lock `ref_gl_ilc`, the frames hold the *intended* palm. The wrist columns hold the ILC-corrected
  command, up to 80 mm away.

I therefore rebuilt both references by forward kinematics (`fk_ref.py`):
- the human reference: its wrist columns plus finger joint targets;
- the design: the intended palm from the frames (`--palm_from_frames`) plus finger joint targets.

The earlier plate audit (`audit-plates-ep18-ep39.md`) placed link geometry using the stale frames, so its
reference-contact details may shift. Its qualitative finding, that the designed pan grasp has no thumb opposition,
holds with the consistent kinematics (section 4).

**Other caveats:**
- The contact proxy is geometric. No forces were recorded (traces taken with CONTACTS=0).
- There is one deterministic trace (mean policy) per policy.
- The E1 grasp-lock policy has no body trace, so the grasp lock is compared through its design (FK) and zero-action
  replay.
- rp18 is not like-for-like (different reference, mesh library and start).

## 2. The discovered dust-pan grasp (left hand)

### 2.1 Timeline [M] (trace; lift = z − z₀ of the object origin; "low" = lowest collision point over the table top)

| frames | object | left hand |
|---|---|---|
| 0–15 | at rest: ≤ 0.4 mm, ≤ 1.1° | **Approach, low, palm-up and sideways** (palm normal z +0.55…+0.88), detailed below this table. |
| **16** | still at rest | **First contact, thumb and index in the same frame:** thumb PP and DP on the **top** face (−axis3; this plate's +axis3 points down); index MP (radial side) and DP (pad) under the band. The index DP is already inside the ring hole from below. The proximal and middle phalanges of the middle, ring and little fingers (and the index PP) reach 3–25 mm below the table top during f16–24. |
| 17–19 | slides 1.5–2.9 mm, turns 2.0–3.5° | 5–7 links; little DP at f18, middle MP/DP at f19, ring at f21 |
| 20–24 | lifted 0.6–1.7 cm (lowest point up to 10 mm) | 8.5 links on average; thumb and all four fingers |
| 24–60 | **tilt-hold**: pan origin raised 1.8 cm (max 3.0), tilt 28° (max 39°), **far lip on the table 81% of frames** | 5.7 links: thumb PP 100%, thumb DP 97%, index MP and DP 100%, middle DP 100%. **Thumb DP in the hole from above 92%, index DP in the hole from below 100%.** |
| 60–116 | put down flat while the brush sweeps (on the table 98%); the brush touches the pan at f115–117 | still holding: 6.0 links, thumb 89%, index 93%, middle 100% |
| 116–150 | **lifted to 18.9 cm** (reference 16.3 cm), tilt 6° then 36° | 7–9 links; **middle MP+DP and ring DP inside the hole** (100% in f116–130, 75–100% in f130–150: fingers through the ring); thumb on top 100% in f116–130, **30%** in f130–150 (hook carry) |
| 150–200 | put down | thumb off (0% in f150–170); index and middle DPs in the hole (hooked) |
| 200–353 | at rest | released (0 links) |

**Approach detail (f0–15).** The palm centre:
- moves from 11 cm to 6 cm beyond the ring end (axis1 −22 → −17 cm; the ring end is at −11);
- stays at table height (−4…+1 cm);
- travels sideways along +axis2 at about 2 cm per frame.

The fingertips are 7–9 cm *below* the table top (the hands do not collide with the table), and the thumb is 0.2–6.5 cm
above it.

Why fingers fit under the ring [M]: the pan rests on its plate tilted 12°, so the ring's underside is **20–24 mm
above the table** (f0–18). A fingertip fits under the band. The policy's hand is lower than it needs to be (palm centre
−4…+1 cm over the table, against 0…+7 cm for the human reference at f4–16), so its proximal phalanges dip into the
table.

### 2.2 Contacts while held [M] (f24–60, the tilt-hold)

- Faces: bottom (+axis3) 52%, top (−axis3) 33%, edge 15%. Region: ring 94%, neck 5%. Palm contact 0%.
- Where on the link:
  - thumb pad 25%, thumb side 8%;
  - index radial side 19%, index pad 16%;
  - middle radial side 13%, middle dorsal 10%.
- Opposition from the thumb-contact centroid to the finger-contact centroid:
  - 2.6 cm long, inclined about 30° out of the plate plane (|· plate normal| = 0.49). The human reference gives
    0.04–0.16, almost in the plate plane, and the design has no opposition;
  - in the palm frame (normal, finger direction, radial) it is (0.10, 0.37, −0.87): **transverse to the palm**, the
    side-opposition direction.
- **A lever, not a point pinch.** The thumb presses the top face at the ring's end (contacts at axis1 −8.5 … −9.0 cm),
  and the fingers push up on the bottom face **2.0–2.5 cm closer to the pan** (−6.4 … −7.0 cm), in f16–24, f24–60 and
  f116–150.
  - [I] This first-class lever is what resists the cantilevered pan's weight moment (about 0.24–0.30 N m about the
    ring end at the 0.3 kg placeholder mass), as when holding a pan by its handle with the thumb on top.
- During acquisition (f16–20) the index finger touches mostly with its **radial side** (35%, pad 5%) and the thumb
  with its **pad** (25%).
- Pictures: `docs/research/grasp/rl-grasp-figs/rl_pan.jpg` (plate frame, top and side views; red thumb, orange index,
  green middle, blue ring, purple little) and `rl_pan_video_crops.jpg` (from `view.mp4`).

### 2.3 Posture [M] (joint means, deg; RL vs the human reference by FK at the same frames)

| window | palm offset from the reference | thumb CMC_FE / CMC_AA / MCP_FE / IP | index MCP/PIP/DIP | middle | ring | little |
|---|---|---|---|---|---|---|
| f16–24 | **14.0 cm / 38°** | 72/3/19/3 vs 56/20/30/2 | 53/34/4 vs 38/45/15 | 69/32/0 vs 77/23/1 | 88/3/5 vs 77/35/1 | 59/3/22 vs 71/26/7 |
| f24–60 | 2.5 cm / 18° | 72/−9/36/1 vs 69/6/34/2 | 68/32/15 vs 81/32/17 | 76/23/15 vs 82/19/14 | 87/19/6 vs 84/16/9 | 82/21/8 vs 89/27/9 |
| f116–150 | 7.8 cm / 45° | 71/1/28/14 vs 65/19/38/5 | 32/37/0 vs 43/28/1 | 59/11/15 vs 63/12/3 | 52/8/0 vs 65/9/1 | 76/7/9 vs 64/9/1 |

[I] The finger shapes stay close to the human reference: most joint means are within about 15°, with a few
exceptions in the pick-up window (ring PIP 32° and little PIP 23° less flexed, thumb CMC_FE 16° and CMC_AA 17° apart).
What the policy changes is the wrist placement during acquisition, by 14 cm and 38°. During the hold, the thumb CMC is
strongly flexed (about 72°) with the IP straight, so the thumb pad presses down flat rather than with a curled tip.

### 2.4 Extrinsic contacts [M]

- **Table:** of the 182 frames in which at least 2 left links hold the pan, it touches the table in 127 (70%). It is
  lifted clear only in 52 frames, essentially the 16–19 cm lift. The far lip on the table carries part of the weight
  during the tilt-hold.
- **The other object:** the brush touches the pan only at f115–117, at the end of the last stroke.
- **The other hand:** never touches the pan.

### 2.5 Human-taxonomy reading

[L] Feix et al. 2016, "The GRASP taxonomy of human grasp types", IEEE THMS 46(1):66–77
(https://www.eng.yale.edu/grablab/pubs/Feix_THMS2016.pdf, PDF opened):
- "Side Opposition occurs between hand surfaces along a direction generally transverse to the palm … One holds a key
  between the volar surface of the thumb and the radial sides of the fingers";
- "The thumb is adducted only in cases where the opposition is between the thumb and the side of the finger (e.g.,
  lateral grasp) or the thumb is not involved in opposition";
- the lateral grasp (#16) "takes an intermediate stage between power and precision".

On the same source, the hook grasp is excluded from the taxonomy as non-prehensile, because its stability depends on
the hand's orientation.

[I] The pick-up and tilt-hold match a **lateral (key) pinch, #16**:
- the thumb pad on one face;
- the radial side of the index middle phalanx, plus the index pad, on the other face;
- the opposition axis transverse to the palm (radial component −0.87).

It is done **palm-up (supinated)**, with the index tip in the ring hole as a locating peg. For the high lift it changes
into a **hook through the ring**: middle and ring fingers through the hole, thumb on top, then the thumb releases. This
hook is stable only because gravity pulls the pan down onto the fingers.

The human reference (FK of its joint targets) instead **cradles** the ring end on the fingers from below [M]:
- the fingertips fit into the gap under the raised ring and stay 10–17 mm *above* the table at f8–16, so they do not
  pass through it;
- the middle and ring DPs curl up into the hole in 94–97% of f24–60 frames;
- the thumb sits under or at the end edge, touching with its **side** (thumb below 86–100% in f24–60, thumb side
  11–18%), never pressing on the top face;
- opposition |·n| 0.04–0.16.

[I] So the ring-hole hook comes from the human. The policy's additions are:
- the thumb pad on the top face (turning the cradle into a lateral pinch / lever);
- the simultaneous closure;
- a lower hand that dips its proximal phalanges into the table.

## 3. The discovered sweeper grasp (right hand)

### 3.1 Timeline [M]

| frames | brush | right hand |
|---|---|---|
| 0–54 | standing on its bristles, long axis vertical, ring up (tilt 87–88°); ≤ 0.3 mm, 0.2°. The reference brush starts moving at f38 (lifted 2.5 cm on average in f38–54); the policy waits. | Descends from 15.8 cm (palm centre over the table, f36) to 6.2 cm (f56), along the brush's lateral edge. The palm faces the edge: normal about horizontal (z −0.41 → −0.01 … −0.26), its plate-normal component going +0.38 → −0.53. Fingertips 16 cm → 1.6 cm above the table. |
| **55–56** | brush moves 4.8 mm / 2.3° | index PP and little MC (f55), then palm, thumb MC/PP/DP, index knuckle/MP/DP (f56): **10 links** |
| 57–60 | leaves rest at f57; lifted 2.2 cm at f58 and 3.7 cm at f60 | 11 links |
| 58–66 | catch-up travel of 7.5 cm | 11.6 links; thumb 100%, palm 100%, index 100%, ring 88%, little 100% |
| 66–118 (sweep strokes) | **hovering**: lowest point min 4.2 mm, median 39 mm above the table. The reference presses the rigid brush to 0 to −1.4 mm. | 10.6–11.2 links; palm 90–100% |
| 118–175 | lifted 7.3 / 6.7 cm, tilted 55–59° | 8.4–10.2 links |
| 175–260 | put down while still held | 9.7–9.8 links |
| 260–353 | resting | partly released (6.8 links) |

### 3.2 Contacts and layout [M] (f58–118)

- **Sides of the plate** (median offset of each link's samples from the plate mid-plane):
  - thumb MC −3.9, PP −2.6, DP −1.6 cm: the **−axis3 face**;
  - all four fingers +0.1…+3.5 cm: the **+axis3 face**;
  - palm: contact at the **−axis2 lateral edge** (axis2 −3.3 … −4.0 cm), with the index PP next to it (−2.8) and the
    index knuckle in contact 50–100% of frames.
- **Spread:** the finger contacts span the plate's width, from the index PP at axis2 −2.8 to the index and middle DP at
  +2.4…+3.1, i.e. to the far edge. The thumb pad is at axis2 +2.5…+2.9 on the opposite face.
- **Regions:** neck 52%, head 31%, ring 17%. Faces: + 58%, − 25%, edge 17%.
- **Where on the link:** index pad 24% (f58–66), radial sides of index, middle and little 13–21%, palm front 9%.
- **Opposition:** |·n| 0.76 at closure and 0.48–0.60 during strokes; length 2.7–3.8 cm.
- Pictures: `rl_sweeper.jpg`, `rl_sweeper_video_crops.jpg`.

**Posture at the grasp (f58–66)** [M]:
- thumb CMC_FE 84°, CMC_AA 17°, MCP_FE −22° (the thumb is hyperextended at the MCP and pressed flat), IP 1°;
- index 50/20/67°, middle 52/32/17°, ring 50/36/7°, little 48/54/10° (MCP/PIP/DIP);
- the MCPs are moderately flexed, and the PIPs vary from 20° to 54°.

**Relative to the reference** [M]:
- the palm is 10.7 cm / 37° away at closure and 8.5–9.7 cm away for the rest of the hold;
- the human reference's contacts are 97–100% on the **ring**, with no palm. The thumb touches in only 6–44% of frames
  before f118, and the finger contacts are mostly dorsal or edge contacts;
- the reference hand first touches the brush at f27–33 (FK), 11 frames before the brush moves.

**Extrinsic contacts** [M]:
- the brush touches the table only at closure (f55–56) and after f191 (put-down);
- it touches the pan at f116–117;
- the other hand never touches it.

### 3.3 Human-taxonomy reading [I]

The sweeper grasp is a **palm-braced, flat-plate thumb–fingers clamp**:
- the plate is pinched across its thickness between the thumb column on one face and four pads/phalanges on the other
  face (pad opposition);
- the palm and the index MCP butt against the near edge, which adds a third support.

In Feix's terms it lies between:
- the **Parallel Extension grasp (#22)**, the thumb opposing the finger pads. Feix places it in the Pad / thumb-adducted
  cell because the thumb is "in some intermediate position between abduction and adduction" and "the opposition is
  done partly by the side of the thumb"; here the thumb opposes with its whole column;
- a **power grasp**: the palm takes load at the edge (Napier 1956's power/precision split, as summarised by Feix).

It is clearly not the human's fingertip contact on the ring.

[L] Napier JR, "The prehensile movements of the human hand", J Bone Joint Surg Br 1956;38-B:902–913
(https://pubmed.ncbi.nlm.nih.gov/13376678/, record opened; the abstract is not online, so I cite it only as the origin
of the power/precision distinction, as Feix summarises it).

## 4. Versus the grasp-lock grasp

### 4.1 Designed (E1 `ref_gl_ilc`, FK with the intended palm) and executed (E1 zero action) [M]

**Design, dust pan** (`SNAP human grasp`, grasp frame f16, hold from f8, closed at f18; squeeze 0.4 rad):
- designed first touches: ring and middle MP/DP from below at f7–8, index f11, thumb DP f14 (end edge);
- squeezed hold target, f18–150: **only the index MP and DP are within 5 mm (2.7 / 3.2 mm), with their dorsal
  side, on the end edge**. No thumb, no face-to-face opposition;
- posture: middle and ring MCP at their 90° limit; thumb tucked (CMC_FE 81°, MCP 53°, IP 40°);
- picture: `design_pan.jpg`.

**Executed, dust pan** (zero action):
- middle MP/DP touch from below at f7 and ring at f8–9. **The pan leaves rest at f7**;
- f13–19: lifted 3.3 cm on average (max 5.1) and slid 43 mm on average with **0 thumb contact**. At f18 it had slid
  62 mm horizontally, turned 22° and risen 5.1 cm (the audit measured 80 mm in 3-D). The thumb first touches at f54;
- side of the plate (`extra.py`): in f7–13 every near finger link is under the pan, with the little MP/DP 11–14 mm
  below the table top. In f13–19 even the thumb DP/PP are under the plate (75–80% of frames), so **the whole hand
  scoops the pan from below**;
- the pan then stands on its edge (tilt 53–76°) and contact is lost (0.9–1.5 links);
- picture: `e1zero_pan.jpg`.

**Design, sweeper** (hold from f53, closed at f63):
- 4 links on the ring band near its lateral edge: thumb PP/DP, and ring MP and little MP touching with their **dorsal**
  side;
- contact span 1.5 cm, opposition |·n| 0.26 (mostly in the plate plane), no palm;
- picture: `design_sweeper.jpg`.

**Executed, sweeper:** middle, ring and little DPs touch the ring edge with their ulnar sides at f50–56, with no thumb.
The brush is pushed 5 mm / 5° and then **tips over at f64–80** (tilt 86° → 5°, lying flat by f80).

### 4.2 Grasp-lock policy (rp18, 50M) [M]

- **sweeper:** falls at f0–10 (tilt 64° → 11°, lift −5 cm, slide 67 mm) with no hand link within 5 mm. Afterwards only
  the back of the thumb MC/PP touches it (f54–66);
- **dust pan:** **0 contacts in 354 frames**; it stays at rest;
- this matches the audit's "learned avoidance" reading, but the start failure (`mc` reference, rounded library_v2
  sweeper) makes it a weaker comparison than E1.

### 4.3 Side by side

| | RL 0.889 (pan) | grasp lock (pan) | RL 0.889 (sweeper) | grasp lock (sweeper) |
|---|---|---|---|---|
| grasp site | ring end band around the hole: thumb at axis1 −8.5…−9 cm, fingers 2–2.5 cm closer to the pan | end edge of the ring (axis1 −10…−13) | neck and upper head across the full width | ring band at its lateral edge |
| thumb | pad on the top face from the first contact frame | absent at closure (first touch f54) | thumb column on one face | thumb PP/DP, 1.5 cm from the fingers |
| opposing fingers | index MP radial side + DP pad underneath; middle under | middle/ring/little from below only; index back on the edge | four fingers flat on the other face to the far edge | ring/little MP backs |
| palm | none (palm-up, under the band) | none | **against the near edge** | none |
| opposition |·n| | 0.49 | none | 0.5–0.8 | 0.26 |
| first-contact order | thumb + index in the same frame (f16) | fingers f7, thumb f54 | index PP/little MC f55, palm + thumb f56 | 3 fingertips f50–51 only |
| object disturbance at closure | 2.9 mm / 3.5° | 62 mm / 22° and +5.1 cm by f18 (E1 zero action; audit: 63–80 mm / 17–22° across variants) | 4.8 mm / 2.3° | knocked over |
| extrinsic support | lip on the table 70% of held frames; index tip pegged in the hole | – | brush hovers 4–40 mm in strokes | – |
| wrist | soft (kp 25), residual up to 14 cm from the human path | stiff (kp 400), ILC-tracked to 0.7–1.4 cm of the design | 8.5–10.7 cm from the human path | as designed |

## 5. What the RL policy changed, in one line each [M → I]

1. **Grasp site:**
   - dust pan: from the ring's *end edge* (design) or the end-cradled ring (human) to the *end band around the hole*;
   - sweeper: from the ring handle (human and design) to the **neck and head**, about 10 cm lower.
2. **Contact roles:** the thumb takes one face (the pan's top, the brush's − face) and an opposing finger group takes
   the other. The opposition is inclined 30–50° out of the plate plane (|·n| 0.49–0.76), against 0.04–0.26 (nearly
   in-plane) in the human reference and the design.
3. **Timing:** the thumb and the first opposing finger touch in the same frame, and the object stays within 3–5 mm /
   2–3.5° until the lift. The grasp lock closes the fingers before the thumb: 6–7 frames earlier in the design and
   47 frames earlier in the zero-action replay.
4. **Wrist:** 8–15 cm and 20–45° away from the human wrist path at grasp time; the fingers stay within about 15–30° of
   the human shapes.
5. **Environment:**
   - the pan's lip stays on the table, and the index tip is pegged in the ring hole;
   - the policy passes its proximal phalanges through the non-colliding table during the pan pick-up (3–25 mm deep);
     the human reference's fingers stay 10–17 mm above the table in the gap under the ring;
   - it keeps the rigid brush off the table during strokes.
6. **Phase change:** pinch for the pick-up, then a hook through the ring for the high carry.

## 6. Literature on RL rediscovering human grasps [L]

- OpenAI et al. 2018, "Learning Dexterous In-Hand Manipulation" (arXiv 1808.00177, https://arxiv.org/abs/1808.00177,
  PDF opened). With no human demonstrations, the policy "naturally discovers grasp types found in humans, such as the
  tripod, prismatic, and tip pinch grasps". Its Fig. 7 classifies the learned grasps with Feix's taxonomy (tip pinch,
  palmar pinch, tripod, quadpod, 5-finger precision, power). It notes the policy adapts them to its own hand ("our
  system can rediscover grasps found in humans, but adapt them to better fit the limitations and abilities of its own
  body").
  - Our case is similar: a key pinch and a hook appear, adapted to a hand that can pass through the table.
- Zhou & Held 2022, "Learning to Grasp the Ungraspable with Emergent Extrinsic Dexterity", CoRL (arXiv 2211.01500,
  https://arxiv.org/abs/2211.01500, abstract opened). Model-free RL learns, without any extrinsic-dexterity reward,
  to push objects against the environment before grasping them (78% success on hardware).
  - The pan's lip-on-table tilt-hold and the ring-hole peg are milder instances of the same effect.

## 7. What a designed grasp must copy (specification, from the measurements above)

**Dust pan (ep18 left; also the ep39 pick-up hand):**
1. **Site:** the ring's end band around the hole, axis1 −10 … −5 cm (hole centre −6.4 cm), not the end edge alone.
2. **Roles:**
   - **thumb pad + thumb PP on the top face** (the world-up face);
   - **index MP (radial side) + index DP (pad) on the bottom face**, the DP tip inside the ring hole from below
     (≥ 3 samples in the hole volume);
   - middle MP/DP on the bottom face next to the index;
   - ring and little fingers optional, not loaded;
   - no palm contact; palm-up (palm normal z +0.3 … +0.7).
3. **Opposition and lever:** thumb-to-finger centroid 2.4–2.8 cm, at least 0.4 along the plate normal.
   - The thumb sits at the ring's end (axis1 ≈ −9 cm) and the fingers about 2–2.5 cm closer to the pan
     (axis1 ≈ −6.5 cm).
   - The thumb and index targets must sit on opposite faces with a planned interpenetration (squeeze) along that axis,
     not a uniform joint curl.
4. **Approach:** sideways and low, along the ring's short axis (+axis2), palm-up, the fingertips sliding into the
   **20–24 mm gap** under the raised ring.
5. **Closure:** thumb and index **in the same frame** (±1 frame at 20 fps); other fingers 2–5 frames later.
   - Gate: object displacement ≤ 3–5 mm / 3.5° until the lift (RL: 2.9 mm / 3.5°).
6. **Posture targets (deg):**
   - thumb CMC_FE ≈ 72, MCP_FE ≈ 20–36, IP ≈ 0 (pad flat);
   - index MCP ≈ 53–68, PIP ≈ 32, DIP ≈ 4–15;
   - middle MCP ≈ 70–76, PIP ≈ 23–32;
   - ring and little MCP ≈ 60–88, with their PIPs extended (≈ 3–20) at the pick-up.
7. **Hold:** keep the far lip on the table wherever the reference has the pan tilted with its lip down (f24–115).
8. **High lift (> 5 cm):** convert to a hook. Put the middle (and ring) finger through the hole, curled under the band,
   with the thumb on top. The thumb may lift off once the pan hangs.

**Sweeper (ep18 right; [I] probably also the standing-sweeper starts of ep31 and eval twins 19 and 30):**
1. **Site:** the neck and the top of the head, axis1 −3 … +5 cm, across the full width. Not the ring.
2. **Roles:**
   - palm and index MCP knuckle against the near lateral edge;
   - four fingers flat across the + face to the far edge (fingertips at the far edge);
   - thumb column (MC, PP, DP) on the − face with the DP near the far edge.
   - 10–13 links in contact; opposition |·n| ≥ 0.5.
3. **Approach:** from above along the near lateral edge, with the palm facing the edge (palm normal about horizontal);
   no contact before the closing frames.
4. **Closure:** palm, thumb and fingers within 2 frames (f55–56 in the policy). Lift 2 cm within 2 frames. Gate:
   ≤ 5 mm / 2.5° before the lift.
5. **Posture:** thumb CMC_FE ≈ 84, MCP_FE ≈ −20 (hyperextended), IP ≈ 0; finger MCPs ≈ 50; PIPs 20–55.
6. **Strokes:** keep the rigid brush 0.5–4 cm above the table where the reference presses it into the table.

**Both objects:**
- define the grasp in the object frame from these roles and solve the wrist from it; do not take the human wrist path
  (the policy's wrist is 8–15 cm away from it at grasp time);
- **start the hold at the object's motion onset**, not at the hand-contact labels. The policy grasps the brush 15–17
  frames after the reference brush starts moving and pays about 3.8 cm of error for it in f38–54.

## 8. Hypotheses and the experiments that would falsify them

| # | hypothesis | experiment (GPU replay ≈ 0.1 $ each, CPU for building the reference) | falsified if |
|---|---|---|---|
| H1 | A grasp-lock reference with the pan specification above (thumb top, index radial side + DP bottom with the tip in the hole, palm-up low approach, simultaneous closure) holds the pan at zero action on ep18 and ep39. | `grasp_lock.py` with a designed-grasp option filled from section 7; zero-action replay + rest_check | displacement > 5 mm / 5° before the lift, or in-hand slip > 2 cm over f20–150 (ep18) |
| H2 | Simultaneity (thumb and index within 1 frame) matters more than the exact contact site. | H1 with the thumb delayed by 3 and 6 frames | the delayed variants also pass the H1 gate |
| H3 | Moving the sweeper grasp to the neck/head with the palm against the edge holds the standing brush at zero action, where the ring grasp knocks it over. | grasp-lock reference with the section 7 sweeper roles, hold started at motion onset; zero action | the brush tips > 5° before closure, or slips > 2 cm during the strokes |
| H4 | The RL pan pick-up does not need fingers through the table: the 20–24 mm gap under the ring is enough for a shallower approach. | replay the 0.889 policy with `collision=physical` (`robot_support_collision: true`), 5 rollouts; and H1 with the hand kept above the table plane | the pan is not lifted > 5 cm by f30 in ≥ 4/5 rollouts *and* the above-table H1 variant fails its gate |
| H5 | Distilling the policy's own grasp into the grasp lock gives the grasp-lock recipe the RL's ep18 result. Take the trace's object-relative hand poses (wrist + 22 joints) over each hold as the locked grasp. | build `ref_gl` from `policy_trace.npz` (object-relative), zero action, then the 70M fine-tune | zero-action sim_vs_ref < 0.6, or fine-tuned registered AUC < 0.8 on ep18 (RL: 0.889) |
| H6 | Hovering the brush 0.5–4 cm during the strokes costs less than following the pressed reference with a locked rigid brush. | two grasp-lock references for the ep18 sweeper (as perceived vs +2 cm during strokes); zero action | the hovering variant does not reduce brush pose error over f50–112 |

**Implication for the evolutionary-search question [I/H]:** the policy's solution differs from the human reference
mainly in the object-relative **wrist pose** (8–15 cm, 20–45°) and in **which face the thumb takes**, and less in finger
shape. A population search (CMA-ES or GA) over grasp designs should therefore search over:
- the object-frame palm pose: 6 continuous dimensions, seeded at the RL pose;
- the thumb face, a binary choice;
- the closure delay between thumb and fingers;
- one squeeze depth along the opposition axis;

about 9–10 dimensions in all, scored by the zero-action gates above. A search over finger closure parameters alone, at
the human wrist, would miss what the policy found.
- **Falsifier:** a CMA-ES run seeded at the human wrist pose that reaches the H1 gate without moving the palm more than
  3 cm from the human path.

## 9. Optional ep39 CONTACTS=1 CPU trace: skipped

Reasons [M]:
- The FlashCHORD CPU environment (`scratchpad/fcvenv`) has no JAX, which FlashSAC inference needs.
- This repository has never run a policy rollout on CPU (only zero-action replays).
- The ep39 scene would need to be rebuilt locally from the HF store.
- CPU and GPU physics diverge on these starts. The work log records the settled brush tipping at f12–20 on CPU while it
  stands on GPU, so a CPU policy trace would not be a faithful copy of the official rollouts.
- The machine's load average was 7–11 on 4 CPUs during this work.

Proposed instead (next box, about 2 minutes of GPU, no new training): the `old889.sh` recipe with `CONTACTS=1`. It
records the contact forces the 0.889 analysis lacked. Run it on:
- the ep39 standard policy (`runs/20261024-std39-1f306be/runs/perc2mcks/ep39-s42/policy_250003456.safetensors`);
- the ep18 0.889 policy (`runs/20261023-fdr43-715c9f7/runs/perc2mckfid/ep18-s43/policy_250003456.safetensors`).

## 10. Reproduction

- **Machine:** Claude cloud VM, 4 CPUs. **Code:** repository at d166d75 plus the new, uncommitted scripts in
  `docs/research/grasp/rl-grasp-scripts/`. They read the Sharpa URDFs from the scratchpad FlashCHORD source, the path
  set in `rlgrasp_lib.py`. **Environment:** Python with numpy, scipy, trimesh, pyarrow, matplotlib
  (`scratchpad/venv`); CoACD from `scratchpad/fcvenv`.
- **Work dir:** `scratchpad/grasp_work/rl-grasp/`, with downloads in `data/hf/runs/...`. All runs used
  `OMP_NUM_THREADS=1` and single processes.

Commands (`$M3=meshes/library_v3`; `V3` = `mini_sweeper=hulls/mini_sweeper_v3.npz=$M3/mini_sweeper.glb
mini_dust_pan=hulls/mini_dust_pan_v3.npz=$M3/mini_dust_pan.glb`):

1. Download: `dl.py data/hf <patterns>` (`huggingface_hub`, repo `aebatirel/v2d-store`, type dataset).
2. CoACD hulls:
   - `hulls.py library_v2/mini_sweeper.glb hulls/mini_sweeper_v2.npz` (14 s, 19 pieces);
   - the library_v3 pieces were reused from `scratchpad/audit/hulls/`, made with the same script and settings.
3. Ring holes: `hole_map.py hulls/mini_dust_pan_v3.npz $M3/mini_dust_pan.glb -3 out/hole_pan.npz` (same for the
   sweeper with `-1`).
4. Consistent references:
   - `fk_ref.py <perc2mckfid parquet> out/fk_ref889.npz`;
   - `fk_ref.py <E1 ref_gl_ilc.parquet> out/fk_e1.npz --palm_from_frames`.
5. Per-frame contacts:
   - `frames.py <trace or fk npz> out/<tag>_sim.jsonl --objs $V3`, for `old889` (`old889_sim2`), E1 `zero.npz`,
     `fk_ref889`, `fk_e1`;
   - rp18 with the library_v2 sweeper pieces;
   - 3–15 minutes per 354-frame trace under load.
6. Hole / side / under-table: `extra.py <npz> out/<tag>_extra.jsonl --objs name=hulls=glb=holemap ...`.
7. Summaries:
   - `summ.py <frames.jsonl> <npz> <obj> <hulls> <glb> <side> "<windows>" | brief.py`;
   - `extra_summ.py`, `timeline.py`, `approach.py <trace> <fk_ref> ...`, `jdev.py <trace> <fk_ref> <side> "<windows>"`.
8. Rollouts vs trace: `rollouts_vs_trace.py policy_trace.npz r*/episode_000018.parquet` (kit reader).
9. Figures: `viz.py <npz> <obj> <hulls> <glb> <side> out.png <frames>`, plus ffmpeg crops of `view.mp4`. Copies are in
   `docs/research/grasp/rl-grasp-figs/`.

Per-frame outputs (JSONL, 0.3–1 MB each) stay in the scratchpad (`grasp_work/rl-grasp/out/`) and are not committed.
