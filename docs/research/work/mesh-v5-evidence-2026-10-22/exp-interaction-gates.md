# S3 interaction exclusion: adversarial test of XCarve R1/R2/R3 and gates (critique items 14–19)

S3 should not change the submitted mesh. Gross track failures are always rejected, but moderate track bias gets past every claim gate. R2 then cuts real material, and the rest of S3 removes almost nothing on S1/S2 grids. All work was CPU only ($0) and the repo is unchanged. Labels: [M] uses method inputs only, [D] reads public scans or mocap, [E]/[H] are estimates and hypotheses.

## What I ran
- **Harness:** `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/v5/xcarve_adv/code/s3x.py`, with driver `run_cases.py`, and summary scripts `bias_agg.py`, `policy_table.py`, `p4.py`, `kmargin.py`, `diag_where.py`. Every command with its time is in `.../v5/xcarve_adv/COMMANDS.txt`; the raw tables are in `tables_raw.txt`.
- **Solid:** the S1 default variant `4c12_adj_g2[m]_f0_cont@lc25`, built on existing S1/S2 grids.
- **Voxel classes:**
  - S (strong): 4 mm field, at least 3 votes, inside, and not silhouette-free.
  - C: inside by the coarse field only.
  - U: inside only through closing.
- **Claims:** count frames only where the partner voxel is observed (C or S), sampled at stride 2. A voxel is contested at K = 5. Frames go through the G1 jitter filter first.
- **Rules tested:**
  - R1: U loses.
  - WS: C loses to S.
  - R3: C against C, ratio 2.
  - R2a: the original XCarve split.
  - R2s: the same split restricted to S-vs-S voxels (item 16).
- **Claim gates, applied per episode:** Gss (S-vs-S at most 5 % of the smaller solid and at most 10 cm³), Gsse (the same with XCarve's evidence-median "strong"), Gcon (contested share at most 0.25), Gobs (observed-carve share at most 2 %, as the min or the max of the two objects).
- **Outcome gates:**
  - Budget at most 10 % of the solid.
  - No split.
  - Literal item 17: Euler number unchanged and no new 1-voxel-thin material.
  - One-sided Betti form: no new tunnel, cavity or split.
  - G6 registration check.
- **Diagnostics [D]:** real material carved = carved voxels inside the defects-study scan solid, and "deep" = at least 1 voxel inside it. The kit's CD-O and ADD come from `v5/metric/mesh_metric.py`.
- **Runs:**
  - 13 real cases (`real_all.jsonl`).
  - 80 bias runs on ep2 and ep24 (`bias.jsonl`): 2/5/10 mm and 2/5/10° about each axis in both signs, and 180° flips, applied to the lid and to board 2 in the claim step.
  - 18 bias runs on ep31 (`bias31.jsonl`).
  - K-margin runs (`kmargin*.json[l]`).
  - The kit metric on 14 meshes (`metric_s3.jsonl`).
- **Fetched and fused:** ep0 depth (0.6 GB, deleted afterwards). ep0 grids along our own ep0 tracks. Eval-style grids fused along own-mesh (perc2m) tracks for ep24 and ep18.
- **Caveat on inputs:** the S1 grids were fused with library_v2 as region of interest, `--others` and band mask, so they are indirectly scan-contaminated. Most tracks are scan-templated. Every threshold below needs re-checking on compliant v5 grids.

## Real cases [M], with real material carved [D]

| case | max overlap cm³ | contested A/B cm³ (real) | S-vs-S | Sse | contested share | insertion? | Gss / Gsse / Gcon |
|---|---|---|---|---|---|---|---|
| ep24 boards | 0.58 | 0.72 (0.24) / 0.92 (0.56) | 0.6 | 0.1 | 0.010 | Y (6.0 cm, 0.88) | pass / pass / pass |
| ep24, own tracks, eval-style | 0.86 | 1.58 (**1.34**) / 1.12 (0.20) | 0.8 | 0.0 | 0.016 | Y (8.9, 0.89) | pass / pass / pass |
| ep2 lid/pot | 14.05 | 17.5 (3.7) / 19.0 (3.2) | **10.9** | 2.2 | 0.157 | n | **FAIL** / pass / pass |
| ep0 tracks on ep2 grids | 25.8 | 61.7 (24.1) / 41.2 (15.2) | 36.0 | 10.8 | 0.34 | n | FAIL / FAIL / FAIL |
| ep0 per-episode (`nbk` grids) | 94.8 | 121 / 134 | 31.6 | 42.2 | 0.58 | n | FAIL / FAIL / FAIL |
| ep11 nested cups | 74.2 | 89.7 (14.7) / 116 (19.5) | 32.0 | 43.8 | 0.86 | Y (10.2, 0.92) | FAIL / FAIL / FAIL |
| ep12 / ep13 cup in rack | 0.18 / 0.82 | at most 0.8 | 0.4 | 0 | 0.004 | n | pass / pass / pass |
| ep31 sweeper in rack | 1.84 | 3.1 (0.1) / 3.2 (1.2) | 0.4 | 0.3 | 0.039 | n (3.1, 0.57) | pass / pass / pass |
| ep18, both track sets | 0.0 | 0 | 0 | 0 | 0 | – | pass / pass / pass |

- **ep0 per-episode, default grids:** our ep0 pot track sinks the pot 8–13 cm below the table for about 80 frames. The per-frame below-table carve erases the pot (10 cm³ solid). With the plan-S1 counter (`nbk`) it is 209 cm³. This is an S1 bug and confirms the plan's below-table counter.
- **Without gates (R1+WS+R3, "R1R3" below):**
  - ep0 cases carve 25 cm³ of pot (7.7 real), and 59 / 65 cm³ in the per-episode case.
  - ep11 carves 34 / 30 cm³. With R2s it is 47 / 45 cm³ (5.8 / 10.1 real), and [D] the blue cup's CD-O goes 1.17 → 1.43 cm with ADD 9.9 → 77 mm.
  - The claim gates reject all of these, and the outcome gates would too (budget, split, tunnels).
- **ep2:** this is a correct track (8 mm / 3° error [D]), but Gss rejects it.
  - Without gates, R1R3 would cut the closed overlap from 10.3 to 4.6 cm³ (pot 3.3 cm³ carved, 0.48 real; lid 5.6 cm³, 0.07 real).
  - It perforates the S1 lid ring: 13 new tunnels.
  - [D] CD-O: pot 0.732 → 0.743, lid 0.377 → 0.379. ADD: pot 9.8 → 10.0 mm, lid 12.6 → 12.3 mm. No score gain.

## Bias injection (items 14 and 16) [M] / [D]
Realistic sizes [D]: the 90th-percentile relative-pose error of our tracks is 10–17 mm and 3–11°. Own-mesh tracks on ep24 are 7.6 / 16.9 mm at the median / 90th percentile, against 4.0 / 10.8 mm for scan-templated tracks.

**How often each gate fired:**

| case | runs | Gss | Gsse, Gcon | Gobs-min |
|---|---|---|---|---|
| ep24 | 39 | 0 | 0 | 0 |
| ep31 | 18 | 0 | 0 | 0 |
| ep2 | 39 | 31 | 0 | 0 |

- On ep2, Gss also fails the unbiased track. The ep2 biases that pass Gss are the ones that move the lid away from the pot (+10 mm in x, flips).
- G1 and K cannot see a constant bias.
- Gobs-min passes ep0 at 1.65 %. Gobs-max rejects correct carves: the ep2 lid (4.6 %) and the ep31 sweeper phantom (3.0 %).

**Worst real material carved [D], cm³ per object.** "Plan + Betti" is the plan's claim gates with the one-sided topology gate. "Recommended" is Gsse + Gcon claim gates with the Betti gate (labelled P4 in `p4.py`).

| case | rule set | no gates | plan + Betti | recommended |
|---|---|---|---|---|
| all runs (115) | R1 alone | ≤ 0.12 (≤ 0.28 carved) | – | – |
| ep2 | R1R3 | 2.35 | 0.26 | 0.75 pot / 0.26 lid |
| ep24 | R1R3 | 0.21 | 0.21 | 0.21 |
| ep24 | R2s / R2a | 1.72 / 1.64 per board | 1.31 / 1.51 | 1.31 |
| ep31 | R1R3 | 0.70 (sweeper) | – | 0.42 (rack) |

- **R2 triggers on biased drags:** with G1 on, 5 of 18 biased ep31 runs are classed as insertions (for example +5 mm in z gives 17 cm of travel at straightness 0.82). The rack then loses up to 4.5 cm³ (1.8 real) under R2a and 2.7 cm³ (0.8 real) under R2s.
- **Restricting R2 to S-vs-S voxels (item 16):**
  - It cuts the ep31 rack damage 3–9×.
  - It does nothing against bias at a true insertion: ep24 damage is the same as R2a.
  - With own-mesh tracks and no bias, on eval-style grids it still removes 0.34 cm³ of real board 1 (0.26 deep). 85 % of board 1's contested voxels there are real wood.
  - [D] A 0.49 cm³ R2s carve flips the kit registration on 1 of 6 seeds (board 1 ADD 2.8 → 4.6 mm).

## Items 15, 17, 18 and 19
- **15, ep31:**
  - Sweeper side: R1R3 removes 2.38 cm³ of coarse-only voxels. Only 0.01 cm³ is real [D]: they sit a median 19.6 mm from the scan surface, so this is a phantom blob, not bristles. [D] CD-O 0.269 → 0.266, ADD 1.8 → 1.7 mm.
  - Rack side: R1R3 removes 0.14 cm³. Across the 18 biases the rack loses at most 1.85 cm³ (0.42 real).
  - R2 does not classify the drag as an insertion with G1 on (3.1 cm, 0.57). It does with G1 off (21.1 cm, 0.76): R2a then cuts a 13.8 cm strip along the slats (3.37 cm³, 1.23 real, 89 % within 4 mm of the scan surface).
  - G1 drops 13–43 % of frames: all fast relative motion, not only jitter. It is not a dependable guard.
- **17, thin walls:**
  - The literal gate fires on every carve of 0.06 cm³ or more. New 1-voxel-thin voxels: ep24 2/7, ep2 211/189, ep13 27/18, ep31 46/2.
  - So the literal gate also blocks correct carves. Board 1's Euler change of +1 is a bridge across the slot being removed (one tunnel fewer), which is the desired effect.
  - The one-sided Betti form separates the cases:
    - new tunnels: ep2 lid +13, pot +1; rack +3 under R2a;
    - cavity: ep13 cup +1;
    - splits: ep0 pot 5, ep11 cups 5–22.
  - Mesh-level Euler numbers agree: lid −8 → −30, pot −154 → −164.
  - G6 never exceeded 0.2 mm, so it says nothing.
- **18, per-episode gating:**
  - Gating each episode rejects ep0 and keeps ep2 under the Gsse + Gcon claim gates (the alt policy in the scripts); summing ep2 and ep0 first fails all three gates, so no episode's claims survive. With these volume gates, summing first is not less safe; it only throws away good episodes.
  - Volume that reaches K only through the sum: lid 0.21 cm³; boards 0.09 / 0.09 cm³, of which 100 % / 67 % is real [D]. Require K within one passing episode [H].
- **19, K margin on ep18:**
  - Zero claims with either track set, with or without G1, at stride 1 or 2.
  - The S1 solids come no closer than 4.5 mm (scan-templated tracks) or 2.0 mm (own-mesh tracks).
  - Voxels within 6 mm of the partner reach at most 3 sampled frames (5 at stride 1, longest run 3). True contacts reach 23–162.
  - The margin is real but depends on S1's thin bristles.

## Safe on eval with frozen parameters
- **Safe automatically:** R1 (closing loses). Under 0.12 cm³ real across all 115 runs even without gates, but nearly inert (at most 0.28 cm³).
- **Allowed only on the simulator collision copy, not the submitted mesh:** WS + R3 (R3 ratio 2). Settings: K = 5 at stride 2, observed-only claims, per-episode claim gate Gsse AND Gcon, outcome gate = budget at most 10 %, no split, no new tunnel or cavity, each object reverted separately. Measured CD-O and ADD change is within ±0.01 cm [D], with bounded risk (worst 0.75 cm³ real on the pot under bias). Putting carves only on the collision copy is owner decision #2 in the plan.
- **Must stay off:**
  - R2 in both forms. S1+S2 already open the board slot (overlap 0.58 cm³); R2 only takes the last-frame overlap from 0.24 to 0.03 cm³ and turns track bias into real cuts the gates cannot see.
  - The Gobs gate.
  - Gss at 10 cm³ (it rejects correct ep2). If kept as a third vote, a cap of about 20 cm³ fits the measured gap of 16.5 against 25 or more [H].
  - The literal item-17 gate.
  - Summing claims across episodes before gating.
  - Any decision that depends on G1.
- **The claim gates are thin on margin:** contested share is at most 0.178 for good and biased runs against at least 0.34 for gross failures; Sse is at most 3.3 against at least 10.8. They were calibrated on scan-templated tracks and must be re-checked on v5 grids with own-mesh tracks.
- **Constant biases [E]:** a bias that is constant over a whole episode should cancel when an eval episode is re-fused along its own track, so only errors that vary in time matter. ep0 is that kind and is rejected. This follows from the geometry and was not measured.

## What to port
- From `s3x.py`, into the planned `pipeline/xcarve.py` (or `interact_resid.py`):
  - the S/C/U labelling from S1 grids;
  - observed-only claims;
  - per-episode claim gating with K required within one episode;
  - WS + R1 + R3;
  - the Betti outcome gate (`betti()`), reporting thin voxels without gating on them;
  - the overlap-after report;
  - output written to the collision copy.
- Do not port R2, the hand claims, or the Gobs gate.
- Into diagnostics only: `run_cases` bias injection, `kmargin.py`, `diag_where.py`.
- S1 fix: below-table hits as a counter (`nbk`), because the per-frame below-table carve destroyed the ep0 pot.