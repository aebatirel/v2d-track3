# Generalized mesh generator (gmg): specification v1, revision 1

Date: 2026-10-30. v1 was written at repo commit `a9ef3c0`; revision 1 at commit `161a094` (both read only). Writing
v1 and revision 1 used **zero new scan scorings**. Companion file: `PREREG.md` in this folder. It freezes the
selection rule, the scoring rounds and the adoption criteria. If this SPEC and PREREG.md disagree on any frozen item,
PREREG.md wins. Revision 1 answers a design review (15 must-fix items, integrity risks, missing items); the changelog
is at the end.

Labels: [D] measured against the scan, [M] measured without the scan, [E] estimate, [H] hypothesis,
[R] read from code or documents (not run), [U] unverified source. "dev" marks a number computed from `obs_all`
(library_v3 ROI and `--others`; see section 2). CD-O is in cm (lower is better). ADD is in mm.

Evidence behind this spec: `evidence.md` (this folder), `../lit/gmg-2026-10-30.md`, four candidate designs and three
judges (workflow `wf_cb2e792a-f27`; design probes in the session scratchpad under `gmg/design/<design>/`).

---

## 0. One page for the owner

**What it is.** One automated pipeline. It takes one episode, public or eval. For every tracked object in that
episode it makes one mesh in our tracked object frame. That mesh is watertight, has at most 4096 faces, and rests
correctly in the simulator. There is no per-object code and no per-object constant. The same code runs on the 20
eval episodes, and each eval mesh comes from that eval episode's own video and depth (your 22 Oct decision).

**How it works.**
1. A CPU core builds candidates from our own stereo depth along our own tracks: thin shells, symmetric
   completions (lathe, mirror), a generic part grammar, and a carved hull. Detected marker balls are added.
2. Optional GPU producers add generated candidates: SAM 3D with our metric depth, and Pixal3D multi-view. Each
   generated mesh is fused with our observations: our surface where we saw it, generated surface only where we
   never saw anything.
3. One frozen, GT-free rule picks one candidate per object and episode. It tests each candidate against frames
   that were held out from building it, and it penalises both missing and extra surface.

**Your pot and lid point is a core rule, written generically.** The episode tells the gmg which objects are
tracked. Every object gets its own mesh. Touching objects are kept apart in five places:
- depth samples are assigned to exactly one object, so lid points never feed the pot (section 7, extraction passes);
- generator inputs come only from frames where the target is apart from every other tracked object, with the
  other objects' pixels removed from the mask and the depth; if those frames all show one view, the generator gets
  that one view with several seeds, never a contact frame;
- text-prompt masks are assigned exclusively: one proposal per object, the partner's pixels as negative prompts;
- no completion of any kind (lathe, mirror, part, generated fill, hull) may put volume where a partner sat during
  contact;
- after generation, a mesh is vetoed if it contains or copies the partner's observed surface (the nested cups case
  included).

SAM 3D's earlier "lid" was a whole pot with a lid on top, because its input frame showed the lid sitting on the pot
[M]. In ep2 the lid is apart from the pot and free of hands in 77 of 172 frames [M, dev]. Those frames all look from
nearly one direction (spread 2 degrees), so the lid gets one view with several seeds.

**Why this design.** It combines the four designs the judges scored. Its base is the CPU observation-first design
(most feasible, safest ADD). It adds the hybrid design's generator producers (the only way to reach the measured
generator wins on the pitcher, dust pan and cups), the generator-first design's contact-aware inputs and clean
re-tracking, and the neural design's three-state evidence field. Everything a judge showed fatal is removed
(section 21).

**What comes first.** Your hypothesis is tested early. (1) Fix the input guard. (2) A walking skeleton runs end to end
on 3 pairs (about 1-2 days of build). (3) A $0 CPU check of the generator view choice and masks on our local videos.
(4) A small GPU batch G0 (about $1-2 [E]): SAM 3D on the ep2 lid from a separated view and on the ep2 pot from a
lid-off view, 2 seeds each. G0 and every clean extraction need `HF_TOKEN` and `VAST_API_KEY` in this environment.
Neither is set today, and no public depth is stored locally [M]. Until then, dev work continues.

**Expected result [E].** CPU core only: eval-pair-weighted CD-O about 0.39 (range 0.37-0.44) against library_v3's
0.491 on the same weighting [D]. With generators: about 0.37 (0.34-0.41). Leaderboard estimate about 0.32-0.33,
against 0.402 today; the leaders are at 0.11-0.15. These are estimates, not measurements.

**Cost.** CPU core $0 on the 4 local cores, but a public batch is 45-110 CPU-h [E] (about 12-35 h wall); a rented
32-vCPU CPU box does it in 2-4 h for about $1-3 [E, price U]. GPU batches: G0 hypothesis probe $1-2, G1 kill test
$1.5-3.5, G2 public generation $4-8, G3 clean re-track $3-5, G4 eval generation $4-8. Total $14-27 [E]. Your
standing go-ahead (30 Oct, 12:20 UTC) covers them; each batch is still stated with its cost in the work log first.

**Your decisions (section 22):** add `HF_TOKEN` and `VAST_API_KEY` (D1); O1 (accept tier P1 tracks for a CPU-only
submission or require the clean re-track); what to submit for an object where the gmg fails (O2); the spoon (O5).

---

## 1. Goal and scope

- **Goal.** For any tracked object in one episode, produce a simulator-ready mesh in our tracked object frame. It
  must minimise CD-O against the public scans (development yardstick only) and stay ground-truth-free at
  inference.
- **Scope.** The 10 scanned objects, the wooden spoon (10 of 36 eval pairs; no public scan) and any new object.
  The spoon is the built-in "unseen object" test. It gets no template privilege.
- **Not in scope.** Pose refinement (refine.py was refuted as a default), grasp and simulation tuning, eval
  scoring of any kind.
- **Done means.** PREREG.md's adoption criteria are met on the public round, and the eval path has produced 36
  meshes with clean manifests.

## 2. Rules the gmg enforces

| Rule | How the gmg enforces it |
|---|---|
| Inference reads no ground truth | `gmg/guard.py` wraps every file open. In clean mode it uses an **allow-list** of input roots per role (below); everything else is refused. On top of that: the deny-list paths and hashes (`ops/provenance/denylist.json`, via `pipeline/provenance.py`), the substrings `/scan`, `/loc/`, `_align`, `.parquet`, `mocap`, the extra refusals below, and any file with more than one hard link. An strace audit runs on every production run (stage 1b reached 0 forbidden opens). |
| No library_v1-v4, also not as ROI, fallback, reference or frame anchor | They are refused as inputs. The ROI is a generic cube. `--others` is replaced by ownership voting. There is no library fallback. Gate references are our own points. Cross-episode comparisons register meshes onto our own points (section 12), not through the shared track frame. Residual: the current tracks were templated on library_v2 (public) and library_v3 (eval). That is flagged and removed only by the Phase-2 re-track (section 16). |
| No constant from the scans | Every constant is logged with its origin: `sensor`, `generic`, `fitted:<what>` or `informed` (chosen after seeing results; PREREG §A.6 lists them). The 7 mm ball radius, the brief thicknesses (2.5 mm included), the hand-kit windows and the V3 threshold 0.20 are not used. The default unseen thickness and the V3 threshold are fitted from our own public observations (sections 8 and 11). |
| Public and eval stay separate | Eval runs use frozen code, a frozen selector variant, constants fitted on public observations only, and no eval numbers. Nothing is scored on eval. Eval tracks were looked at during design (section 4); no constant depends on that. |
| Scan scorings are counted and pre-registered | Only `scripts/mesh_metric.py`, only inside the rounds in PREREG.md, only after the candidate hashes are frozen. Inference never imports `mesh_metric.py`: it holds scan paths at module level (`SCANS = .../loc/t3/mesh`). `gmg/score.py` carries its own copies of `ambiguity` and of the kit decode used by V1. |

**Clean-mode allow-list (role: roots).** calib: `data/calib.json`. tracks: `data/sweep/ep*/poses.npz` (public, P1),
`data/eval/ep*/poses.npz` (eval, P1; sha256 must match the frozen run, section 17), Phase 2: `RUN/tracks/`. depth: the
local download folder of the HF store `cache/depth/` (public and eval). video: the public dataset videos and
`ep<N>_a.mp4` streams. det: `data/store/ep*/det_f0.npz`, keys `masks`, `mask_shape`, `frame`, `K`, `image`, `depth`,
`names` only. roster: kit `data/track_3_evaluation_objects.json` and `gmg/roster_public.json` (section 3). kit:
kit code and config, scorer excluded. weights: generator weights on the box. own: the run's `RUN/` folder.

**Clean-mode refusals added in revision 1** (also refused if a future allow-list change would admit them):
- `meshes/library_v1..v4/**`, `meshes/library_v3x/**`, `results/prim/**`, `scratchpad/prim/**`, `scratchpad/lathe/**`;
- `scratchpad/auto/**` (stage-1b outputs; 12 of 12 integrated episodes picked library_v3 [M]);
- `scratchpad/gen/mesh-20261029-gen-*/**` (generator outputs from crops seeded with library_v3);
- `scratchpad/crops/**`, `scratchpad/evalcrops/**` (crops seeded with library_v3);
- `scratchpad/diag/**` (`diag/sam-placement/common.py` defines `load_scan()` and holds placements fitted to the scan;
  the `/scan` substring does not catch these paths);
- `scratchpad/gmg/design/**` (design-probe outputs, derived from `obs_all`);
- `scratchpad/obs_all/**` and `scratchpad/obs/**` (library_v3 ROI and `--others`);
- in `det_f0.npz`, every key not listed above. The same file holds library-derived fields: `sim` (DINOv2 against
  library renders), `template_extent`, `template_intensity`, `chosen`, `score*`, `verify*`, `rules`, `params`. The
  Grounding DINO boxes (`gdino`) are refused too; Phase 2 runs its own detector.

**Dev mode** (`GMG_MODE=dev`) may also read `obs_all/*.npz`, the X0 pool meshes and their existing labels (role
`x0_pool`, validation code only) and named test fixtures (role `fixture`, tests only). Dev outputs are tier DEV. They
are never scored in a pre-registered round, never submitted, and their contact or V2 numbers are never evidence for
the pot-and-lid rule: `obs_all` removed partner points within 12 mm of the library_v3 meshes, so dev data overstates
separation.

**Must-fix before any gmg run (build step B0).** `autokit/io_gt.py` lists `meshes/library_v3`, `scratchpad/auto`,
`results/prim/meshes`, `scratchpad/prim` and `scratchpad/lathe` in `ROOTS['mesh']`, and it never loads the deny-list
[M, read today]. B0 removes all five roots, makes `io_gt` call the deny-list, and makes the gmg guard refuse any
`io_gt` root that is not on the gmg allow-list.

## 3. Inputs

**Allowed inputs.**

| Input | Tier | Source |
|---|---|---|
| Rectified stereo and colour video | P0 | public dataset; eval `ep<N>_a.mp4` (local) and b/c streams |
| FoundationStereo depth cache `depths_fs0.5.npy` | P0 | HF store `cache/depth/` (public must be downloaded again: the local folders are empty [M]) and `cache/depth/eval/` (all 20 eval episodes) |
| Calibration, VO `world_T_cam` | P0 | `data/calib.json`, `poses.npz` |
| Table plane | P0 | RANSAC on our depth (`pipeline/recon_mesh.table_plane`) |
| Object names and slot order | P0 | eval: kit `data/track_3_evaluation_objects.json` [R; that it holds slot order is U]. Public: `gmg/roster_public.json`, written once by `gmg/tools/roster_public.py`, which reads only the object-name field of the public parquets by column projection (never `pose`), in its own audited process. The gmg reads only the JSON. The `poses.npz` keys give names, not slot order. |
| Hands | P0 | MediaPipe (`pipeline/hands_mp.py`), run by M1 on every episode |
| Frame-0 SAM2 proposals | P0 | `data/store/ep*/det_f0.npz`, mask keys only (section 2) |
| Kit code, generator weights | P0 | kit; HF store (SAM 3D checkpoints, 12.4 GB) |
| Object tracks `cam_T_<obj>` | **P1** | Phase 1: public sweep `20261025-sweep-a894083` (templated on library_v2); eval `20261025-evperc-4f596df` (templated on library_v3; frozen, section 17). Phase 2: our own tracks (section 16). |

**Never read at inference:** public scans (any `*scan*` path), mocap, the parquet `pose` field, `*_align.npz`,
`meshes/library_v1..v4`, `library_v3x`, hand-kit outputs, `obs_all/*.npz` (except dev mode), the refusals of
section 2, and anything derived from them.

**Provenance tier of an output** is the worst tier among its inputs. Phase-1 outputs are tier P1. They may be
submitted only if the owner accepts tier P1 (decision O1).

## 4. Objects in contact are separate meshes (owner requirement, 30 Oct)

The rule is generic. It uses only the episode's list of tracked objects, their tracks and our depth. There is no
pot-specific code.

**Contact pairs.**
- Public [M, dev census `gmg/design/gen-first/contact_census.jsonl`]: pot + lid (ep0, ep2), cups nested (ep11),
  cup, pot or sweeper with the dish rack (ep12, ep13, ep26, ep27, ep31), the two boards (ep23, ep24), sweeper + dust
  pan (ep18; 3-D contact in 7 of 177 frames). Every measured public pair is apart in 3-D for part of its episode.
  Some pairs overlap in the image on every frame: cup and rack (ep12, ep13), sweeper and rack (ep31), pot and rack
  (ep26) [M, dev]. Their generator inputs run in contact mode (mechanism 2).
- Eval two-object episodes, from the roster (names only, allowed metadata; whether a pair touches is decided by the
  census at run time): pot + lid (eval 1), pot + spoon (eval 3, 5, 6), pot +
  beige cup (eval 8), cups (eval 10), blue cup + rack (eval 14), rack + spoon (eval 15, 16), sweeper + dust pan
  (eval 19), blue cup + pitcher (eval 20), boards (eval 25), rack + pot (eval 28), sweeper + rack (eval 30), blue cup
  + spoon (eval 32, 33). 16 of the 20 eval episodes have two tracked objects. Every eval pot pair has a partner (lid,
  spoon, beige cup or rack). 5 of the 9 public pot episodes (41-45) have none.
- The spoon pairs (7 eval episodes, 14 of the 36 eval pairs) were never measured: there is no public spoon. The gmg
  measures them itself at eval time with the same census.

**Disclosure: eval tracks were analysed during design.** The design probes measured contact on eval tracks:
`neural-recon/contact_states.txt` (eval 1, 10, 14, 30), `neural-recon/relmotion.jsonl` (eval 1, 8, 10, 14, 19, 25,
28, 30) and `gen-first/eval_contact_proxy.txt` (all 20 eval episodes). This was looking at eval inputs, not at eval
results. No constant below depends on it. v1 justified the V2 interface band with "the eval-1 lid starting 7.6 mm
inside the pot"; no saved file contains that number, and the band was replaced (mechanism 3).

**Definitions (frozen in PREREG §A.6).**
- A frame is a **contact frame** for objects (o, p) if the smallest 3-D distance between their owned points is at
  most 10 mm, or their projected masks, dilated by 10 px, overlap. Generic: 10 mm is more than 10 times the depth
  noise (sigma 0.78-0.97 mm [M, public]) and 2.5 voxels; 10 px is about 10 mm at the median working distance
  (0.5-0.6 m, focal 600 px [M, public]).
- A frame is **separated** for target o if the 3-D gap to every other tracked object is above 20 mm and the 2-D gap
  above 16 px. Generic: twice the contact thresholds (16 px = two 8-px footprint cells), so that the two states
  cannot flicker.
- A frame is **3-D-separated** if only the 3-D test holds (the 2-D test dropped). Used where the reference needs
  geometry, not clean pixels (PREREG B.2).

**Mechanism 1: ownership at extraction.** One pass over the depth serves all tracked objects (section 7, M2, which
spells out the order of passes). Each depth sample goes to the object in whose frame its voxel is most persistent
(hit ratio). Ties within 2 binomial standard errors are **shared**. Shared samples feed no fit but count as occupied
in the contact checks. Lid samples therefore never feed the pot. A pot sample on the rim under the lid is persistent
only in the pot's frame. When two objects hold one relative pose for a whole episode, persistence ties for every
sample of both; a tie-break then decides (section 7), else the samples stay shared and the pair is flagged. Every
measured pair moves relative to its partner (modal relative-state share at most 0.28 [M, `relmotion.jsonl`, public
and eval]). The spoon pairs were never measured.

**Mechanism 2: contact-aware generator inputs.** A generator sees a frame only if the target is separated in it,
hands cover at most 25 % of the target mask, the visible area is at least 0.6 of the episode's maximum, and at least
0.6 of the mask has valid depth. At least one such frame is needed. Up to 6 views are chosen, at least 8 degrees
apart in view direction (farthest-point sampling).
- **Views too similar.** If the qualifying frames span less than 8 degrees, the generator gets **one view times
  several seeds** (4 seeds in G1, 2 in G2). Among separated, hand-free frames the camera-direction spread p90 is
  2.0 degrees for the ep2 lid, 4.5 degrees for the ep2 pot (12 frames) and 3.5-4.6 degrees for the ep11 cups [M, dev
  census], so these get one view each.
- **Pixal3D-MV needs at least 3 views.** If fewer than 3 qualifying views exist, it is not run for that pair (flag
  `mv_skipped`). It is never fed contact frames to reach 3 views, because that brings the partner back.
- **Masks.** The target mask excludes every partner's pixels (dilated by 10 px) and hand pixels. The pointmap is set to
  NaN outside the target mask. Phase-1 masks are projected owned points (closed, filled), refined by SAM2 with point
  prompts on the target and the partner's pixels as negative prompts. Phase-2 masks follow section 16. A refined mask
  that gains any partner pixel is cut back to the projected mask.
- **Contact mode.** If no frame is separated, the input uses the frames with the least partner overlap, the partners'
  pixels replaced by local background, and the flag `contact_mode`.
- **No joint conditioning.** SAM 3D's public "multi-object" mode is one single-object inference per mask, composed by
  the layout [R, from reading `make_scene()` in `lit_gmg/sam3d_up/notebook_inference.py`; the multi-object notebook is
  not stored locally, so partly U]. The gmg therefore runs one inference per exclusive mask. Each result is then
  tested by V2 against the partner's samples like any candidate. v1 also claimed a mutual check between the two
  results; that claim is dropped.

**Mechanism 3: post-generation contact check (veto V2).** It works on surface samples, with a band scaled to the
measured noise. For a partner p, take one surface sample per p-OBSERVED voxel (the centroid of p's owned points in
it, with its normal oriented towards the cameras). In each contact frame, move these samples into the target's frame
through the two tracks. A sample violates if:
- (a) it lies inside the candidate's closed volume deeper than the band b, or
- (b) it lies within b of the candidate's surface, its normal agrees with the candidate's surface normal there
  (cos > 0.5), and it is farther than b from every owned point of the target. This catches a mesh that copies the
  partner's surface, such as a nested double cup or a thin phantom pot under a lid, even when the copy has no
  interior. A correct wall touching the partner faces the other way, so it does not count.

The band is b = min(8 mm, 3·sqrt(sigma_o² + sigma_p² + j²)). j is the pair's relative track jitter, fitted per pair
and episode (PREREG A.2). The cap 8 mm is two voxels. The candidate is vetoed if the median over contact frames of the
number of violating samples exceeds max(3, 1 % of p's samples). There is no interface exclusion zone around the
target's voxels: v1's 2-voxel (8 mm) Chebyshev band dropped up to 97 % of the beige cup's voxels in ep11, because they
lie within 8 mm of the blue cup's voxels [M, dev, `obs-first/v2/RUNS.txt`; an under-count, since those grids had
library_v3 `--others` removed]. The check uses samples, never a convex hull: the good 0.219 lid lies 84 % inside the
pot's convex hull [M]. Veto V3 (section 11) catches a generated neighbour seen as empty space.

**Mechanism 4: no completed volume where a partner sat.** Every completion obeys this, not only the hull closer: the
lathe (hollow or solid), mirror and rotation completion, every P-PROG part, the FUSE fill and the HULL. No completed
volume may contain a partner sample from a contact frame deeper than b (the V2 (a) test, applied during
construction). The `pocc` grid (section 6) stores those samples' voxels for fast lookup. An UNKNOWN region that touches
a partner's owned or shared surface during contact frames is closed by the target's own structure if one is accepted
and it passes this test; else it is left as a thin-walled opening (rim plus thickness t; still watertight). The pot's
opening under its lid stays open. The outer cup's opening around the inner cup stays open.

## 5. Data flow (one episode; identical code for public and eval)

```
 inputs (section 3) --> guard (M0: allow-list, deny-list, key filter)
   |
   +--> hands (M1, CPU, MediaPipe)
   |
   +--> joint extraction for ALL tracked objects (M2) --> episode bundle (section 6)
            pass 0 persistence per object -> pass 1 provisional owners + census -> pass 2 seeds
            -> pass 3 final owners (+ co-moving tie-break) -> pass 4 final census, grids
            (hits from owned samples, free from all rays, shared, pocc), sigma, table plane, at-rest planes
   |
   +--> track sanity and identity checks (M3) --> good frames, TRACK_FAIL / IDENTITY_SWAP flags
   +--> contact census (M4) --> contact / separated / 3-D-separated frames per pair, jitter j
   |
   per object:
   +--> structure hypotheses (M5): axis, mirror planes, plane pairs, repeats
   +--> markers (M6): balls, one radius consensus per episode
   +--> CPU producers (M7): SHELL, SYM, PROG, HULL  (+ balls; completion into UNKNOWN only, never into a partner;
                                                     M8 closing rules)
   +--> GPU producers (optional, M9-M12): contact-aware views -> SAM 3D / Pixal3D-MV -> remesh -> place
                                          -> GEN candidates and FUSE candidates
   +--> features on held-out time blocks (M13): ray score, FSV_far, V2, below-table, ambiguity
   +--> frozen selector S1 (M14): vetoes -> score -> 1-SE tie band -> fixed priors -> pick | fallback ladder
   +--> output (M15): packed mesh <= 4096 faces, watertight after the kit decode; simulator copy (CoACD, rest check)
   +--> report.json + manifest.json (inputs, hashes, constants with origins, commit, tier, flags)
```

## 6. Data formats

All lengths are in metres in files, and in mm in reports. Frames are track frame indices.

**Run folder.** `RUN = <scratchpad>/gmg/runs/<yyyymmdd>-<tag>-<commit7>/`. GPU boxes write to the HF store
`runs/<same name>/` only. Git receives reports, scores and SHA256SUMS, never meshes over 10 MB or grids.

**Frozen constants file** `gmg/frozen_constants.json`: `{t0_mm, tau_v3, computed_on, commit, sha256 of the inputs}`. Written from the public clean CPU batch and committed before R1 (PREREG A.6). The eval run reads it; it is
never refitted on eval.

**Episode bundle** `RUN/bundle/<split>/ep<N>/`:
- `episode.json`:
  `{split, ep, objects: [names in slot order], roster: {path, sha256}, T, stride, vox, tier: "P1"|"DEV",
  tracks: {path, sha256}, table: {n, d} (world), rest: {obj: {frames, n_obj, d_obj}}, good: {obj: [bool per frame]},
  sanity: {obj: {flags, below_table_frac, block_resid_mm, identity_split, identity_cross}},
  contact: {"o|p": {contact: [frames], separated: [frames], sep3d: [frames], d3_mm: [per frame], j_mm,
  co_moving: bool, tie_break: "mask"|"seed"|"none"}}, census_change: {"o|p": frac},
  sigma_mm: {obj: float}, constants: [{name, value, origin}], inputs: [{role, path, sha256, tier}], commit}`.
- `<obj>.npz`, keys compatible with `obs_all` so autokit runs unchanged:
  `pts` (N,3) float32, object frame; `cam` (N,3) float32, camera centre in object frame; `frame` (N) int32;
  `own` (N) uint8 (0 owned, 1 shared); `lo` (3) float32; `vox` float32; `hits`, `free` (X,Y,Z) uint16;
  `state` (X,Y,Z) uint8 (0 UNKNOWN, 1 FREE, 2 OBSERVED); `shared` (X,Y,Z) uint16; `pocc` (X,Y,Z) uint16;
  `args` (JSON string).
- **Which samples feed which grid.** `hits`: owned samples of this object only (`own` = 0). `free`: carved along
  every valid depth ray in the cube, whoever owns its sample, up to 10 mm before the sample (the existing `free`
  margin). `shared`: samples labelled shared. `pocc` (partner occupancy): for each other tracked object p, p's surface
  samples (one per p-OBSERVED voxel) moved into this object's frame at each contact frame; the count is the number of
  contact frames in which the voxel receives such a sample. `state`: OBSERVED if hits ≥ 3 and hits/(hits+free) ≥ 0.5
  (the existing keep rule); FREE if free ≥ 3 and hits/(hits+free) < 0.2; else UNKNOWN. `pts` holds owned and shared
  samples (flagged by `own`); fits use owned samples only.

**Candidate** `RUN/cand/<split>/ep<N>/<obj>/<cid>.glb` plus `<cid>.json`:
`{cid, producer, cls: STRUCT|FUSE|GEN|SHELL|HULL, params, n_params, t_mm, balls: n, built_on_frames: "all"|"fold k",
gen_input_frames: [...], gen_views: n, sha256, faces, watertight_after_decode, flags}`.

**Features** `RUN/feat/<split>/ep<N>/<obj>.jsonl`, one line per candidate:
`{cid, E, E_blocks: [..], E_se, ray: {n, miss_frac, extra_frac, mean_cost_sigma}, fsv_far, fsv_far_shell,
v2: {partner: {n_median, a, b, band_mm}}, below_table_frac, amb_mm, amb_floor_mm, amb_noball_mm, obs_flip_margin_mm,
rest_err_deg, vetoes: [..]}`.

**Pick** `RUN/pick/<split>/ep<N>/<obj>.json`: `{cid, variant, tie_set, trace: [rule steps], fallback, flags}`.

**Output** `RUN/out/<split>/ep<N>/`: `<obj>.glb` (packed, ≤ 4096 faces), `<obj>.sim.glb`, `<obj>.coll/*.obj`,
`<obj>.report.json`, `manifest.json`.

## 7. Modules and interfaces

The package lives at `docs/research/mesh-2026-10-26/gmg/` and is imported as `gmg` (the parent folder on
`sys.path`, as for `autokit`). Effort is in hours [E].

| ID | Module | Interface | Effort |
|---|---|---|---|
| M0 | `guard.py` | `open_input(path, role) -> realpath`; `load_npz(path, role, keys)` (key filter); `mode() -> str` ("dev" or "clean", env `GMG_MODE`); `constant(name, value, origin) -> value`; `manifest() -> dict`. Allow-list per role, `pipeline/provenance.deny_reason`, the substrings and the refusals of section 2. | 5 |
| M0r | `tools/roster_public.py` | one-time names-only reader of the public parquets → `roster_public.json` (own audited process) | 2 |
| M1 | `hands_cpu.py` | `run_hands(split, ep, video_a, depth, calib, poses, out) -> path`. Wraps `pipeline/hands_mp.py` in its own Python 3.12 venv (mediapipe has no 3.13 wheel [U]; not installed today [M]). | 3 |
| M2 | `extract_joint.py` | `extract_episode(split, ep, depth, poses, calib, hands, objects, out_dir, *, vox=0.004, cube=0.30, stride=2, seed_masks=None) -> bundle_dir`. Back-projection, edge filter, table band and keep rule from `scripts/obs_points.py`. The passes below. | 10 |
| M2d | `bundle.py` | `load_bundle(path) -> Bundle` (`.objects`, `.obs(obj)`, `.poses`, `.meta`); `from_obs_all(ep, objects) -> Bundle` (dev only, tier DEV, own = 0, contact from tracks; old box from `obs_all` `lo`/`hi`). | 2 |
| M3 | `track_sanity.py` | `check(bundle, obj) -> {good: bool[T], flags: [..], below_table_frac, block_resid_mm, identity_split, identity_cross}`. | 6 |
| M4 | `contact.py` | `census(bundle) -> {(o, p): {contact, separated, sep3d, d3_mm, overlap2d, j_mm, co_moving}}`; `partner_samples(bundle, target, partner, frames) -> (M,3), normals`. Reuses the scratchpad `contact_census.py` and `relmotion_probe.py` logic. | 4 |
| M5 | `structure.py` | `hypotheses(obs, state, sigma) -> {axis, rotc_sigma, lathe_mad_sigma, mirrors: [{n, d, resid_mm, free_viol}], planes, repeats}`. Reuses `scripts/lathe_obs.py` (`fit_axis`, rotational consistency), `parts.axis_search`, `parts.segment_planes`, the obs-first `sym_probe.py` and `rot_probe.py`. | 5 |
| M6 | `markers.py` | `detect_episode(bundle, sigma) -> {r_consensus_mm, balls: {obj: [Ball(c, r, frames, resid, cap_deg, stem)]}}`; `attach(mesh, balls) -> mesh`. Section 10. | 6 |
| M7 | `producers/{shell,sym,prog,hull}.py` | each `produce(ctx, frames=None) -> [Candidate]`; `frames` limits the build to training frames for held-out refits. Section 8. | 20 |
| M8 | `complete.py` | `close(sheet, state, structure, partners, table) -> mesh`; `partner_clip(volume, partner_samples, band) -> volume`, used by every producer. Section 9. | 7 |
| M9 | `gen_inputs.py` | `choose_views(bundle, obj, census, n_max=6) -> [View]` (one-view fallback); `masks(view, bundle, video) -> mask` (exclusive, partner pixels removed); `sam3d_job(view, seeds) -> dir`; `pixal_job(views) -> dir` (≥ 3 views). Section 4, mechanism 2. | 9 |
| M10 | `remesh.py` | `watertight(mesh, pitch=0.0015) -> mesh`. Generalised winding number or SDF voxelisation, marching cubes, largest-component cleanup, then `program.fit_budget(…, 4000)`. Mandatory for every generated mesh (raw outputs watertight: SAM 3D 13/20, Hunyuan 6/20, Pixal3D-MV 0/20, TRELLIS.2 0/20 [M]). | 4 |
| M11 | `place.py` | `fit(mesh, starts, bundle, obj, frames, partners, table) -> (mesh_placed, report)`; `register(mesh, pts, flip_pairs=True) -> T` (24 PCA starts, rigid ICP, no identity start). Section 15. | 13 |
| M12 | `producers/{gen,fuse}.py` | `produce(ctx, frames=None) -> [Candidate]`; GEN loads box outputs, remeshes and places them; FUSE keeps our surface where OBSERVED and the generated surface only in UNKNOWN voxels outside the partner clip. | 8 |
| M13 | `score.py` | `evidence(mesh, obs, heldout_frames, state, sigma, exclude_views=()) -> dict`; `fsv_far(mesh, obs) -> float`; `v2(mesh, bundle, obj) -> dict`; `below_table(mesh, bundle, obj) -> float`; `self_ambiguity(mesh, balls=True) -> dict` (own copy of `scripts/mesh_metric.ambiguity`); `kit_decode(mesh)` (own copy of the kit decode); `obs_flip_margin(mesh, obs) -> float`. | 9 |
| M14 | `select.py` | `pick(cands, feats, variant) -> dict`. Implements S1 exactly as PREREG §A. | 4 |
| M15 | `simcopy.py` | `build(mesh, bundle, obj) -> (sim_mesh, colliders, report)`. Section 14. | 4 |
| M16 | `run_episode.py` | `python -m gmg.run_episode --split SPLIT --ep N --mode MODE --producers SET --variant deploy --out RUN` (SPLIT public or eval; MODE dev or clean; SET cpu or all). | 4 |
| M17 | `validate/{x0_replay,xcheck,xproxy,looo,round,frozen}.py` | X0 replay; X-check against existing labels; cross-episode proxy X; LOOO; frozen scoring manifests for `mesh_metric.py`; `frozen.py` computes t0 and tau. | 11 |
| M18 | `jobs/{gmg_g0,gmg_gen,gmg_retrack}.sh` | Vast box jobs on `ops/box/lib.sh`: stall watchdog, HF store push, self-destroy. | 6 |
| T | `tests/` | `test_guard`, `test_score` (V2 synthetic tests, PREREG B.14), `test_select`, `test_extract`, `test_producers`, `test_remesh`. | 8 |

Total about 150 h [E], of which about 110 h is on the CPU-only path.

**Joint extraction details (M2).** Ownership and the census need each other, so the passes run in this order.
1. **Crop.** A ±0.30 m cube around each track origin, cut by the above-table half-space (table band 8 mm, as in
   `obs_points.py`). Hands: MediaPipe capsules (hand radius 30 mm, forearm 45 mm, as in `obs_points.py`) removed in
   every episode.
2. **Pass 0: persistence without ownership.** For every object o, build `hits_o` and `free_o` in o's frame from all
   samples in o's cube. Each sample gets a persistence ratio r_o = hits/(hits+free) at its voxel in each object's
   frame.
3. **Pass 1: provisional owners and census.** Provisional owner = the object with the highest r_o among objects whose
   keep rule (hits ≥ 3, ratio ≥ 0.5) passes there; a tie within 2 binomial standard errors is provisionally shared.
   The contact census (M4) then runs on the provisional owned points.
4. **Pass 2: seeds.** Seeded component: the 3-D connected component (8 mm connectivity) that contains the seed points.
   Phase-1 seed: provisional owned points of o's 3-D-separated frames, within 0.30 m of the track origin; or, if
   frame 0 is 3-D-separated for o, the frame-0 SAM2 proposal from the det dump that contains the projected track
   origin, assigned exclusively (one proposal per object; a proposal containing two objects' origins is not used).
   Phase-2 seed: the exclusive text-prompt mask at the object's start frame (section 16). If the component's box
   exceeds 1.5 times the seed's box on any axis, the crop falls back to the seed box plus max(2 cm, 25 %). This stops
   a static object (the rack) from absorbing static clutter.
5. **Pass 3: final owners.** As pass 1, but only among objects whose seeded component holds the sample. Ties are
   resolved by the **co-moving tie-break**, in this order: (a) exclusive projected masks of that frame (Phase 2:
   text-prompt masks; Phase 1: the frame-0 proposals, only at frame 0); (b) nearest seed: the sample goes to the
   object whose seed set (moved into that frame) is nearer, if the nearer distance is below half the farther; (c)
   otherwise the sample stays shared. If more than half of an object's samples were tied in pass 1, the pair is
   flagged `co_moving`; if (c) decides more than half of them, it is flagged `co_moving_unresolved`.
6. **Pass 4: final census and grids.** The census reruns on the final owned points. Both censuses are saved. If the
   separated-frame set of a pair changes by more than 10 % of its frames, the pair is flagged `census_unstable` (no
   further iteration). Then the grids of section 6 are built, including `pocc`, and the pair jitter j (PREREG A.2).
7. **sigma.** The even/odd-frame split floor. Build a route-A sheet from even frames; sigma is the median distance of
   odd-frame owned points to it, clamped to [0.5, 3] mm (sensor sanity). Measured 0.78-0.97 mm on the current files
   [M, dev].

**Track sanity and identity details (M3).** A frame is bad if more than 5 % of its owned points lie more than
max(3 sigma, 3 mm) below the table plane, or if its block-vs-rest residual exceeds 3 times the episode median. An
object is TRACK_FAIL if fewer than 30 % of its frames, or fewer than 20 frames, are good. Two identity tests run for
every pair of tracked objects (v1's "similar size" condition is dropped):
- **Split test:** the shells of the first and second halves of the episode must match each other better than either
  matches the partner's shell. It catches a mid-episode swap.
- **Cross-object test:** an episode's route-A shell of o must lie nearer to o's shells from its other public
  episodes than to any other object's shells (symmetric chamfer in mm after rigid best-of-24 PCA-start ICP, no scale
  normalisation, so size counts). It catches a swap that lasts the whole episode. Not testable for an object with no
  other good public episode (expected: the lid, the beige cup). On public episodes a failure marks o IDENTITY_SWAP,
  which routes like TRACK_FAIL. On eval the test compares against public builds and only raises a flag; it never
  changes an eval output.

These thresholds and tests are **informed**: they were written after tracks were found bad through scan ADD (ep23
78.7 mm). The old below-table test flagged the ep0 lid, the ep23 boards and ep11 frame 0 [M]. Predictions only:
the new tests are expected to flag the ep0 lid (TRACK_FAIL) and ep23 board 2 (cross-object test) [H].

## 8. Candidate producers

Each candidate is a closed mesh in our tracked frame, with markers attached when detected. Every producer passes its
completed volume through `complete.partner_clip` (mechanism 4).

**Thickness.** Where both faces of a wall are seen, the measured thickness is kept (`shell.two_sided_thickness`). The
unseen-wall default t0 is **fitted from our own observations**: the median over objects of the per-object median of
the two-sided thicknesses measured on the public owned points (PREREG A.1). It is computed in the public clean run and
frozen in `frozen_constants.json` before R1. v1 used 2.5 mm and called it generic; it equals the scan rack wall median
that a brief leaked (work log, 27 Oct). The pick is re-run at 0.6 × t0 and 1.6 × t0 (a change of pick raises the flag
`t_sensitive`); these re-runs cover only the pick's tie set. If t0 cannot be fitted (PREREG A.1 gives the condition),
the fallback is 2.5 mm, labelled scan-coincident, and R1 scores the alternates (PREREG C.3).

| Class | Producer | What it builds | Notes |
|---|---|---|---|
| STRUCT | P-SYM lathe | `parts.lathe_polar` / `fit_lathe` (hollow or solid; open end decided by inner-wall evidence), `fit_sheet_of_revolution` for thin discs | Only if rotational consistency ≤ 3 sigma. Generic windows (below). Solid only if it passes the partner clip. |
| STRUCT | P-SYM mirror | owned points reflected through an accepted mirror plane, kept only where they land in UNKNOWN voxels outside the partner clip, then a route-A shell over the union | A plane is accepted if its reflected residual ≤ 3 sigma, its observed share ≥ 0.7, and less than 5 % of reflected surface lands in FREE voxels. |
| STRUCT | P-SYM rotation | owned points revolved about an accepted axis, same UNKNOWN-only and partner rules, then a shell | Same tests as the lathe. |
| STRUCT | P-PROG | generic grammar: Body ∈ {lathe, sheet of revolution, slab (two faces plus outline), plate set} + up to 2 appendages ∈ {bar or plate (`fit_plate_bar`), `shell_patch` on a residual cluster, `splat`} + markers | Appendages added greedily on points more than 3 sigma outside the body. Ranked by MDL (residual plus 1 sigma² per parameter); top 3 kept. Runs through `autokit/program.py run_program(..., budget=4000)`. |
| SHELL | P-SHELL | `autokit/shell.thin_shell(obs, t0)`, closed by the support plane where the object rests (extrusion to the table section) | Always built. Also the reference s for veto V3 and for the tau null. |
| HULL | P-HULL | all voxels not observed FREE, inside the seeded component, above the table, minus the partner clip: marching cubes | Always closed. Thick where unseen. Fallback only. |
| GEN | P-GEN (GPU) | SAM 3D with our metric pointmap (organiser `v2d_sam3d` `--depth_path` route), one run per chosen view and seed; Pixal3D-MV on ≥ 3 posed views | Remeshed (M10), then placed (M11). TripoSG is not used (mean 0.984 [D]). Hunyuan3D-2.1 and TRELLIS.2 are optional and need a licence check. |
| FUSE | P-FUSE (GPU) | for each GEN mesh: our shell where OBSERVED; the generated surface only in UNKNOWN voxels outside the partner clip; generated surface in FREE voxels removed; SDF union at 2 mm, marching cubes, `fit_budget` | GenPC pattern [H]. Keeps observed detail and lets the generator fill unseen backs and bases. |

**Generic windows of P-PROG and P-SYM** (no per-object values). s = `parts.robust_scale(P)` of the episode's owned
points. Every required window (`Wr`) of a part type is set by its meaning class:
- noise band: 3 sigma;
- sampling step: 2 voxels of the part's grid;
- extent: one of {0.05 s, 0.2 s, 0.6 s, 1.2 s} by meaning. The table that maps each window to its class is frozen in
  PREREG A.6b (v1 left it to be written in `prog.py`);
- thickness clip: [1.5 mm, 8 mm]: the sensor floor (about 2 sigma) and two voxels;
- counts and angles: their full ranges.

Each program is tried at the window table as written and with all extent windows doubled. The four existing JSON
programs are regression tests only, never inputs. The part vocabulary and the extent table were built while looking
at the 10 known objects and the four JSON programs. That is development knowledge, recorded here (informed). The
spoon and the generators are the check that the gmg does not depend on it.

**Not used:** strap, peg rows, rounded-rectangle tubes and the "lip" parts. They encode single objects (lid strap,
rack pegs). Observed detail of that kind enters as `shell_patch` appendages instead.

## 9. Completion and closing rules

1. Completed surface may enter UNKNOWN voxels only. Surface that lands in FREE voxels more than 2 voxels from any
   OBSERVED voxel is removed (symmetric completion) or charged (score), never kept silently.
2. No completed volume may hold a partner sample from a contact frame deeper than the band b (mechanism 4). This
   applies to every producer.
3. Open borders close by the first option that applies:
   a. the body's own structure (lathe, mirror, part), if it passes rule 2;
   b. extrusion to the support plane, for objects at rest on the table, through UNKNOWN voxels only;
   c. the hull bounded by FREE space and by rule 2.
4. Contact openings: section 4, mechanism 4.
5. Thin walls keep thickness t (measured, else t0). Closing never thickens an observed wall.

## 10. Markers and near-symmetry

**Marker balls (M6).** Real objects carry mocap balls on posts. They break near-symmetries: the sweeper flips on 3
of 30 seeds without them and 0 of 30 with the two observed balls [D].
- Host-free sphere voting on 1.5 mm voxels (`obs-first/ball_probe.py`), robust fits (`parts.sphere_fit_ransac`,
  then `sphere_fit_free`).
- Radius free in 1.5-12.5 mm. This is a generic window: commercial passive markers are about 3-25 mm in diameter
  [U]. 15,000 seeds.
- A ball is accepted if: support from ≥ 3 frames; fit residual ≤ 1.5 sigma; observed cap ≥ 90 degrees; convex
  towards the cameras (`parts.ball_support`); seen in both halves of the episode.
- Overlap suppression (`obs-first/v2/ball_nms.py`), then one radius consensus per episode (median of accepted radii,
  pooled over all its objects; one marker type per rig [H]). A second pass at the consensus radius ±10 % raises
  recall. Posts by the existing stem rule (`parts.fit_ball`).
- Observed balls are always attached to every candidate (manifold union). Unobserved balls are never added.
- **Trusted balls.** A ball counts for V5 and for the flip-safety tie-break only if its object's balls passed the
  public repeatability test (PREREG B.4: at least 60 % repeat across episodes). Objects without that test (one usable
  public episode, the spoon, any new object) are judged ball-free for V5 and the tie-break, so a false ball cannot buy
  a pick. The balls stay on the shipped mesh in every case.
- Measured this session, precision unchecked [M, dev]: lid ep2 7 balls at 7.9 mm, sweeper ep31 6 at 7.2 mm, pot ep41 5
  at 6.6 mm. The seed count was raised from 5,000 to 15,000 after a first run by agents who knew the scan catalogue
  (about 7 mm, about 5 balls). So the detector is not independent of that knowledge (informed). PREREG P4 tests its
  repeatability GT-free, and the scan round measures its effect.

**Near-symmetry.** Two GT-free measures per candidate:
- **self-ambiguity**: the gmg's copy of `mesh_metric.ambiguity` (24 non-identity PCA starts, ICP of the mesh onto
  itself): `amb_mm`, the best flip residual, and `amb_floor_mm`, the sampling floor; computed with trusted balls only.
  A candidate is **flip-risk** if `amb_mm − amb_floor_mm < amb_floor_mm`, unless the kit declares the object symmetric
  (beige_cup, blue_cup, white_pot_lid; kit metadata, not authored). This rule was written after seeing these values
  for library and board meshes (informed).
- **observed flip margin** (diagnostic): ICP of the candidate onto our own owned points from 24 PCA starts; residual of
  the best flipped solution minus the identity residual.

Veto V5 removes flip-risk candidates when at least one feasible candidate is not flip-risk. Otherwise the pick is
flagged `flip_risk`, and the scan round's 30-seed flip test measures it.

## 11. GT-free selection (summary; the frozen text is PREREG §A)

Per object and episode, rule **S1**:
1. **Vetoes** (generic, loose by design, so they cannot repeat gates v3's specificity failure: MUST_PASS 1/7 [M]):
   - V1 not watertight after the kit's decode of the shipped ≤ 4096-face mesh;
   - V2 contact (section 4, mechanism 3): partner samples inside the candidate or copied by it;
   - V3 hallucination: `fsv_far(c) − fsv_far(s) > tau`, where s is the route-A shell at t0. **tau is set by a GT-free
     rule**: the 99th percentile of the same difference over the CPU candidates' own fold rebuilds in the public clean
     batch (PREREG A.3). v1 used 0.20. That value scored best among 0.1, 0.2 and 0.3 against existing scan labels in
     the hybrid design's post-hoc log (regret 0.137 cm at 0.1, 0.063 cm at 0.2 and 0.3), and it sits just above the
     good generators' FSV of 0.04-0.20. So it was scan-informed and is withdrawn;
   - V4 below table: more than 1 % of the volume lies more than max(3 sigma, 2 mm) below the at-rest table plane;
   - V5 flip-risk (trusted balls only), when a non-flip-risk feasible candidate exists.
2. **Evidence score E** on held-out time blocks. The frames are split into K = 3 contiguous blocks. Every candidate
   is rebuilt (or, for generators, re-placed) without block k and tested on block k. For each held-out point the ray
   from its camera through the point is cast against the candidate: a surface within 3 sigma of the point costs a
   Huber residual; a surface in front costs the distance (extra surface); no surface, or one behind, costs the
   distance up to 10 sigma (missing surface). E adds `10 × fsv_far`. Lower is better. The standard error uses a
   moving-block bootstrap inside each held-out block, so static stretches do not shrink it as much.
3. **Generator hold-out.** If the pool holds GEN or FUSE candidates, held-out frames whose view lies within 8 degrees
   of any generator input view are removed for all candidates. If that removes more than 80 % of the held-out frames
   (as in static episodes: the 77 separated lid frames lie within 2 degrees of one view), the removal is skipped, the
   pool is flagged `gen_view_overlap`, and GEN and FUSE rank after SHELL in step 5, because their E is then
   optimistic.
4. **Tie band.** Candidates within 1 paired-bootstrap standard error of the best E are tied.
5. **Fixed priors among ties:** class STRUCT > FUSE > GEN > SHELL > HULL; then a self-ambiguity margin larger by at
   least one floor unit; then trusted markers attached; then fewer free parameters; then lower E. The class order is
   **informed**: it follows the [D] results of hand kits against generators.
6. **Thickness** is never chosen by the ranker (section 8).

Why this form: observed-surface-only metrics prefer the thinnest, most incomplete shell; held-out rays charge
missing surface where a held-out block saw it (for example a base seen only in some frames) [H]. In static episodes
every block sees the same cone of directions (camera spread p90 1-17 degrees [M, dev]). There E ties, and the fixed
priors decide: structured completion before generated completion before bare shells.

**What this rule must not inherit.** The hybrid design's argmin-o2m and both of its FSV thresholds (0.3 in its
selector, 0.20 kept by v1 of this spec) were chosen after joining with scan labels. Its own nested
leave-one-object-out choice gave 0.137 cm regret, worse than the 0.120 GT-free baseline [D]. S1 uses none of them.
S1 was written after seeing the existing scores of the candidate pools. Its constants are generic, fitted on our own
observations, or labelled informed (PREREG A.6). PREREG §B.1 states which existing-score tests are therefore weak.

## 12. Validation without scans: leave-one-object-out (LOOO)

Knobs are tuned only on GT-free evidence. Scans only measure a frozen rule (PREREG §C).

- **Cross-episode proxy X.** For an object with two or more public episodes that pass track sanity, a candidate built
  from episode A is **registered onto episode B's owned points** (24 PCA starts, rigid ICP, both members of every
  flip pair tried, no identity start) and then scored by the same ray score on B's owned points. B's points are split
  into those A saw and those A never saw (unseen-in-A). v1 compared A and B through the shared library_v2-templated
  track frame; that made a deny-listed library the cross-episode registration reference, and X chooses the variant
  deployed on eval. Registration removes that, and X now also works in Phase 2, where each episode has its own frame.
  Floor of X: 1.0-1.4 mm [M, comp_probe control, shared frame; to be re-measured with registration].
- **X-check before use.** X is used to choose the variant only if it ranks existing labelled candidates better than the
  old GT-free metric did (PREREG B.13, $0, zero new scorings: Spearman above 0.46 on the pot and blue-cup X0 pools).
- **Objects with X:** pot (9 episodes), rack (5), blue cup (5), dust pan (3), pitcher (2), sweeper (2), board 2 (2, if
  ep23 passes the identity tests). The lid (ep0 expected to fail track sanity), the beige cup (ep11 only) and
  board 1 (ep23 expected to fail) probably have no X; they then get the within-episode score only. Which episodes
  count is decided by the track-sanity and identity gates, never by a hand-written list.
- **Variant menu (8, frozen):** K ∈ {3, 5} × tie band ∈ {1, 2} SE × parameter prior on or off. Default V0 = (3, 1 SE,
  on).
- **Fold.** For each held-out object, pick the variant with the lowest mean X-regret (X of the pick minus the best X in
  the pool) on the other objects. Apply it to the held-out object. Record its X-regret and whether it picked X's best.
- **Deployment variant.** If one variant wins at least 70 % of the folds (5 of 7), it is deployed for every
  object. Otherwise V0 is deployed. It is written to `gmg/deploy_variant.json` and committed before any scan round.

## 13. Fallback and abstain

Selection never falls back to a library_v1-v4 mesh. Coverage is **low** if the object has fewer than 20 good frames
or fewer than 20,000 owned points (flag `low_coverage`). The ladder, in order:
1. **Normal:** the S1 pick among feasible candidates.
2. **ABSTAIN_HULL:** no feasible candidate, and coverage is not low: the P-HULL mesh with balls, flagged.
3. **PRIOR_GEN:** TRACK_FAIL, IDENTITY_SWAP or low coverage, and GPU producers ran: the best-E generated mesh from this
   episode's own separated frames, placed by its layout and M11 using good frames only, flagged. If the object has no
   good frame, its frame is undefined: flag `frame_undefined`, layout start only.
4. **PRIOR_PUBLIC:** otherwise, a public-built mesh: library_v5 where it exists (rack, dust pan, sweeper, blue cup,
   pitcher, beige cup; tier P1), else the gmg pick of the same object on its anchor public episode (PREREG §C.2).
   Flagged. On an eval episode it is placed by GT-free registration onto that episode's owned points on good frames
   (M11 `register`), because public tracks use library_v2 templates and eval tracks library_v3, whose origins may
   differ by mm to cm [R, `eval_contact_proxy.py` docstring]. With no good frame: identity, flag `frame_undefined`.
   PRIOR_PUBLIC breaks the one-episode rule for that pair, so it needs owner decision O2 before submission.

The ep0 lid (2,104 points over a 7 × 33 × 37 mm extent [M, dev]) is the known public case for step 3 or 4.

## 14. Output: watertight, budget, simulator copy

- **Packed mesh:** the pick itself, at most 4096 faces, built with `program.fit_budget(…, 4000)` so the kit's
  `budget_mesh` only welds. It must be watertight after the kit's decode (V1). The kit's `budget_mesh` breaks
  watertightness on most meshes (6/144 [M]); budget-safe output fixes this (27/27 stage-1b shells [M]).
- **Simulator copy:** the same mesh, plus:
  - rest check: `trimesh.poses.compute_stable_poses` against the tracked at-rest pose; error ≤ 10 degrees passes;
  - if it fails and the base is UNKNOWN, the copy closes the base at the table section (`pipeline/support_fill.py` /
    `rest_support.py` logic);
  - CoACD convex colliders (`pipeline/collision_decomp.py`; `coacd` must be installed, MIT licence);
  - interaction carving (`pipeline/interaction_carve.py`) only in this copy, never in the packed mesh (carving the
    packed mesh hurt: lid +0.14 to +0.18 [D]).
- **Report** per object: every candidate, its features, the rule trace, flags (`track_fail`, `identity_swap`,
  `contact_mode`, `shared_contact`, `co_moving`, `co_moving_unresolved`, `census_unstable`, `mv_skipped`,
  `gen_view_overlap`, `flip_risk`, `t_sensitive`, `low_coverage`, `frame_undefined`, `fallback`), constants with
  origins.

## 15. Generator placement (M11)

The old `sim3_fit.py` is refuted: on 17/20 meshes its objective scores the wrong placement lower than the ideal one,
and ADD is 26-29 mm [D]. M11 replaces it.
- **Starts:** SAM 3D's metric layout, mapped by `inv(cam_T_obj[k])` and taken as the median over its views; Pixal3D-MV
  at identity (it generates in our frame); anything else from 24 PCA starts. Both members of a near-symmetric pair
  are always tried.
- **Objective** over about 24 training-block frames: a z-buffered render of the candidate, the table and the
  partners' samples. Per pixel: candidate surface in front of the observed target depth by more than 3 sigma
  costs fully; candidate behind (missing) costs up to a clip; candidate silhouette outside the union of the target,
  hand and partner masks costs; surface hidden behind a hand or partner costs nothing. Penalties: volume below the
  table, V2 violations, distance from the layout prior.
- **Parameters:** Sim(3), then per-axis scale in [0.8, 1.25]. Powell.
- **Known weakness.** The gen-first synthetic probe still preferred a non-ideal pose in 9 of 10 rows, and flipped
  contaminated lid fits by 180 degrees at scale ×1.19-1.50 [M]. So M11 must pass PREREG P10 (a synthetic
  perturbation test with our own shells as stand-in truth) before G2 is run. In-frame candidates also win ties
  (class order).

## 16. Phases and the provenance end state

- **Phase 1 (development, tier P1).** Today's tracks: public sweep on library_v2 templates (frame-0 detection by
  DINOv2 against grey library_v2 renders, size gate from library extents), eval tracks on library_v3. Every Phase-1
  mesh lives in that frame. The eval spoon tracks are templated on `library_v3/wooden_spoon.glb`, whose frame rule
  was fitted to public scan frames (O7). The public rounds R1 and R2 run here. A Phase-1 eval submission is possible
  only under O1.
- **Phase 2 (clean, GPU G3, owner O1).** Per episode:
  1. **Exclusive text-prompt masks.** Grounding DINO proposals per object name, with the Grounding DINO-gated
     re-proposal (`DET_REPROP=1`; without it eval 30's sweeper was detected on the wrist [M, work log]). One proposal
     per object (assignment by score; two objects may not take boxes with IoU above 0.5). SAM2 masks use the other
     objects' chosen pixels as negative point prompts (5 points each). A pixel claimed by two masks goes to neither.
     This matters: at ep2 frame 0 the top boxes for white_pot and white_pot_lid cover the same region ([745, 797,
     1152, 1203] and [744, 797, 1152, 1202]) [M, ep2 `det_f0.npz`].
  2. **A separated start frame per object:** the first frame (stride 2) where its chosen box has IoU ≤ 0.1 with every
     other object's chosen box, its detector score passes, and hands cover at most 25 % of its mask. Frame 0 is a
     contact frame in ep2 [M]; the rule does not assume frame 0. If no such frame exists, the lowest-IoU frame is
     used and flagged `contact_start`.
  3. M0 = SAM 3D with our depth at that start frame, with its metric layout (a P0 anchor).
  4. FoundationPose model-based tracking on M0 from the start frame, forward and backward (`perc2.py`, `MESH_DIR` =
     our meshes, no library renders).
  5. gmg pass 1; re-track with the pass-1 mesh (washout); gmg pass 2.
  6. Submitted poses come from the same final tracks, so mesh and poses share one frame.
  If M0 fails its GT-free checks (PREREG P9), the pass-1 gmg mesh seeds instead; that run stays tier P1 and is flagged.
- **Residual after Phase 2.** Design choices were made while seeing library-era scan numbers and eval tracks. That
  is development knowledge, not an input, and it is recorded.

## 17. Eval-episode path

For each of the 20 eval episodes (1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38):
1. Fetch: eval depth `cache/depth/eval/ep<N>/depths_fs0.5.npy` (HF store), calibration, videos. Needs `HF_TOKEN`.
2. **Eval tracks (frozen):** store run `20261025-evperc-4f596df`, the tracks behind the current pack's poses [M, work
   log]. The run checks each local `data/eval/ep<N>/poses.npz` against the store copy's sha256 and stops on a
   mismatch. The other run, `mesh-20261029-evdepth-92f3d86`, supplies depth only. The manifest records every sha256.
3. MediaPipe hands on CPU (no eval hands exist today [M]).
4. Joint extraction for all tracked objects, including unscored ones (they matter for contact).
5. Track sanity, identity tests (flag only), contact census, including the spoon pairs.
6. CPU producers; GPU producers if G4 ran; the frozen deployment variant of S1 with `frozen_constants.json`; the
   fallback ladder.
7. Packed mesh, simulator copy, report, manifest (commit, input hashes, constants, tier).
8. Pack with `scripts/export_meshes.py` and `scripts/build_eval_json.py`; meshes and poses from the same tracks.
9. Nothing is scored. Eval outputs are never compared with public numbers to change anything.

Pairs: 36 = pot 6, rack 5, blue cup 5, beige cup 2, dust pan 2, sweeper 2, lid 1, pitcher 1, board 1 1, board 2 1, spoon
10. Contact pairs from the roster: section 4.

## 18. Compute and cost

**CPU [E], local 4 cores, 15 GB RAM, 14 GB free disk.**
- Joint extraction: 3-8 min per episode (40-300 s per object-episode today [M]; the passes add about one more grid
  build). Depth is streamed one episode at a time (0.3-2 GB per cache).
- Markers: 4-6 min per object (255-363 s at 15k seeds [M]).
- Builds per candidate: 1 all-frames + 3 folds (K = 3) + 5 folds (K = 5, for the LOOO menu) = 9. Thickness re-runs:
  2 × 4 builds for each candidate in the pick's tie set only. Stage 1b took 38-59 min for 4 families with 4 builds
  [M]. So 70-200 min per object-episode [E].
- One public batch (33 pairs): 45-110 CPU-h, about 12-35 h wall on the local cores. One eval batch (36 pairs, the
  deployed K only): 30-60 CPU-h. v1's 25-50 CPU-h left out the K = 5 folds and the thickness re-runs.
- Option: a 32-vCPU Vast CPU box cuts a public batch to 2-4 h for about $1-3 [E, price U].

**GPU batches [E]** (covered by the owner's standing go-ahead of 30 Oct; each is stated with cost in the work log
before renting; boxes self-destroy at job end; stall watchdog at about 30 min without new log lines or files; results
go to the HF store). Measured anchors: eval depth 20 episodes $2.95; generator probe $4.36 (of which $2.61 was
download); G1 re-track 16 episodes $1.1; eval perception 20 episodes $1.9.

| Batch | Content | Hours | Cost |
|---|---|---|---|
| G0 | Owner-hypothesis probe: SAM 3D with depth on the ep2 lid (best separated view) and the ep2 pot (best lid-off view), 2 seeds each; SAM2 masks for ep2; the mask test of PREREG B.11 runs on the box first | about 1 | $1-2 |
| G1 | Kill test: SAM 3D with depth on M9's views (one view × 4 seeds where views are too similar, else up to 4 views × 2 seeds) for lid ep2, pot ep2 (lid-off frames), pot ep41, sweeper ep18, blue cup ep22, dust pan ep40; Pixal3D-MV × 2 seeds where M9 gives ≥ 3 views; SAM2 masks for those episodes | 1.5-2.5 | $1.5-3.5 |
| G2 | Public generation: 33 pairs × (SAM 3D up to 6 views × 2 seeds, or 1 view × 4 seeds + Pixal3D-MV × 2 where ≥ 3 views); masks for 20 episodes; remesh and placement on the box CPUs | 4-6 | $4-8 |
| G3 | Phase-2 clean re-track: exclusive text-prompt masks, separated start frames, SAM 3D seeds, FoundationPose on 20 public + 20 eval episodes, washout pass | 5-7 | $3-5 |
| G4 | Eval generation: 36 pairs, about 430 SAM 3D runs plus Pixal3D-MV; remesh and placement on the box CPUs | 4-6 | $4-8 |

Total $14-27 [E]. One 48 GB GPU (A6000 or L40S; SAM 3D needs ≥ 32 GB [U, organiser README]) at about $0.5-1.0/h.

## 19. Reuse map

| Existing code | Use in gmg |
|---|---|
| `pipeline/provenance.py` | deny-list (globs and sha256) and tiers, inside M0 |
| `autokit/io_gt.py` | path substrings, hard-link check, input log; ROOTS fixed and deny-list loaded (B0) |
| `scripts/obs_points.py` | back-projection, edge filter, table band, keep rule (M2) |
| `pipeline/recon_mesh.py` | `rectified_K`, `table_plane`, `hand_segments` |
| `pipeline/hands_mp.py` | hands (M1) |
| `autokit/shell.py` | `thin_shell`, `two_sided_thickness`, `surface_patch`, `free_space_clamp`, `fill_holes`, `manifold_clean` |
| `autokit/parts.py` | lathe, sheet of revolution, plates, `segment_planes`, `fit_plate_bar`, `splat`, `shell_patch`, sphere fits, `ball_support`, `robust_scale` |
| `autokit/program.py` | `validate_program`, `run_program`, `fit_budget` |
| `autokit/gates.py` | `depth_render`, `seen_empty`, `_project` (diagnostics and z-buffers only; no thresholds, no library references) |
| `scripts/lathe_obs.py` | `fit_axis`, rotational consistency, revolve |
| `scripts/mesh_metric.py` | copied, not imported: `ambiguity` and the kit decode into `gmg/score.py`; scan scoring only in PREREG rounds |
| scratchpad design probes (`gmg/design/`) | `contact_census.py`, `relmotion_probe.py`, `sym_probe.py`, `rot_probe.py`, `ball_probe.py`, `v2/ball_nms.py`, `comp_probe2.py`, `placement_probe.py`, `x0mini.py`, `feat_L0.py`. Their code is copied into the repo before the scratchpad is lost (orchestrator task); their outputs are refused in clean mode. |
| `gen/gen_sam3d.py`, `gen/sam3d_setup.sh`, `gen/gen_pixal_mv.py`, `gen/mv_views.py`, `gen/box_*.sh` | GPU jobs, with the library_v3 seeds replaced by M9 masks |
| `pipeline/perc2.py`, `det_rules.py`, `ops/jobs/eval_depth.sh` | Phase-2 re-track pattern |
| `pipeline/collision_decomp.py`, `rest_support.py`, `support_fill.py`, `interaction_carve.py` | simulator copy |
| `scripts/export_meshes.py`, `build_eval_json.py` | packing |

**Not reused:** `refine.py` (refuted), `gen/sim3_fit.py` (refuted), gates v3 as a selector, the per-object JSON
programs as inputs, the 7 mm ball prior, the library_v3 ROI and `--others`, `crops.py`'s library seeds, the
library-derived fields of the det dumps.

## 20. Risks

1. **Selection in static episodes.** Held-out blocks share the training view cone, so E ties and the fixed priors
   decide unseen surface. The rack, the pitcher's back and the lid's underside depend on this.
2. **No shape prior in the CPU core.** Without G2 the pitcher stays at about 0.55-0.85 [E] against 0.378 for the
   best generator [D].
3. **Generic windows may misfit.** Earlier generic probes failed: the pot axis came out 5.9 degrees off; the dust-pan
   plate set fragmented, and a gate passed a missing wall [M].
4. **Tracks are tier P1 until Phase 2.** Track jitter smears handles (5.6-9.3 mm between frames vs 3.7-5.5 mm within
   [D]); no per-frame pose fix exists. Phase 2 may lower pose AUC (0.868 was reached with library templates [D]).
5. **Co-moving contact.** If two objects never move apart, persistence ties everywhere; the tie-break may fail and
   leave a shared region missing from both meshes. The spoon pairs were never measured.
6. **Ownership is untested end to end.** The contact census used grids already cleaned with library_v3 `--others`,
   so contamination is under-counted. Dev results overstate separation and are not evidence for the owner's rule.
7. **Marker precision is unknown**, and the detector settings were changed once after a first run (section 10).
   False balls shift the CD-O scale; missed balls leave the sweeper and boards flipping.
8. **CD-O scale against partial scans** can punish correct completion (about 0.07 cm on the cup lathe [D]).
9. **Generator placement is not validated** (section 15). Generator ADD has been 6-35 mm against 2-10 mm for library_v3
   [D].
10. **Contact mode is untested** for pairs that overlap in the image on every frame (rack with cup in ep12 and ep13,
    sweeper and rack in ep31 [M, dev]).
11. **Single-episode objects** (lid, beige cup, board 1) have no cross-episode check. The beige cup is the hardest
    contact case: one public episode, 6 separated hand-free frames, nested in the blue cup 54-67 % of the time [M, dev],
    and paired with the pot (eval 8) and the blue cup (eval 10) on eval (roster). Its R1 result is pre-labelled
    low-confidence.
12. **The spoon** (10 of 36 eval pairs, 7 contact episodes) cannot be validated on public data. It is thin, so the
    4 mm voxels and t0 matter most for it.
13. **CPU time** of 45-110 CPU-h per public batch on a shared 4-core machine.
14. **Scan exposure:** up to 106 counted mesh scorings (126 under the thickness fallback) plus up to 20 pose scorings
    (PREREG §C).
15. **Licences:** SAM 3D under the SAM Licence; Hunyuan3D excludes the EU, UK and KR; the TRELLIS.2 and Pixal3D
    environments may pull nvdiffrast (non-commercial [U]). The gmg repo vendors none of them. Owner check before
    release.
16. **Operations:** `HF_TOKEN` and `VAST_API_KEY` are not set [M]; no public depth is local [M]; mediapipe needs its
    own venv; local disk is tight.
17. **Fitted constants are not yet known.** t0 and tau come from the public clean batch. If tau comes out small, V3
    will veto more generator meshes than v1's 0.20 would have. That is reported, not tuned.
18. **Eval inputs were looked at during design** (section 4). No constant uses them; the disclosure stands.

## 21. What was dropped, and why

| From | Dropped | Reason (judge or review evidence) |
|---|---|---|
| hybrid-selector | argmin o2m and the FSV veto τ 0.3 | chosen after joining scan labels; nested LOOO 0.137 cm worse than the 0.120 baseline [D] |
| v1 of this spec | V3 τ = 0.20 | scored best among 0.1/0.2/0.3 against existing scan regret (`hybrid-selector/looo_L0_veto.log`); replaced by a GT-free rule |
| v1 of this spec | default thickness 2.5 mm | equals the scan rack wall median leaked by a brief; replaced by the fitted t0 |
| v1 of this spec | V2's 2-voxel Chebyshev interface band and its eval-1 justification | blind to nesting (97 % of beige voxels within 8 mm [M, dev]); the 7.6 mm figure is in no saved file |
| v1 of this spec | the "mutual check" of joint generation | no rule existed; each result goes through V2 instead |
| v1 of this spec | the X0 requirement "V3 vetoes both SAM 3D pot-with-lid meshes" | their FSV 0.50-0.52 was known before the rule was written, so it could not fail |
| v1 of this spec | cross-episode comparison through the shared library_v2 frame | a deny-listed library acting as registration reference; replaced by GT-free registration |
| hybrid-selector | per-object variant table | a per-object configuration; replaced by one deployed variant |
| hybrid-selector | up to 200 L1 scorings | replaced by R1/R2 caps of 53 each |
| obs-first | the spoon template privilege | breaks the 22 Oct decision; the spoon frame rule was fitted to public scan frames (O7) |
| obs-first | hull fallback on a broken track | a 2,104-point hull is meaningless; replaced by the fallback ladder |
| obs-first, hybrid | washout seeded by pass-1 meshes as the clean end state | keeps the deny-derived frame; replaced by SAM 3D seeding (Phase 2) |
| gen-first | generator-only pools | capped below library_v3 on rack and sweeper (7 of 26 pairs) [D]; the CPU core is kept |
| gen-first | raw generator meshes into carving and budgeting | not watertight [M]; remesh is mandatory |
| gen-first | hard-coded exclusion of ep0 lid and ep23 board 1 | replaced by the GT-free track-sanity and identity gates |
| neural-recon | compositional neural SDF fit | about 24 h of new GPU code; its own probe shows depth-only refinement gains ≤ 3 % [M] |
| all | `io_gt.py` library_v3 allow-list | fixed first (B0) |

**Kept from each:** obs-first (ownership extraction, structure, grammar, held-out ray score, no-cap rule, constant
origins, GT-free LOOO, t-grid pass), hybrid (producer ensemble, fusion, fallback hull, X0 replay, voxel-owner
exclusion), gen-first (contact-aware views, SAM 3D depth route, layout-started placement, Phase-1 dev-only rule,
SAM 3D-seeded re-track, frozen hashes before scoring), neural-recon (three-state evidence field, missing-surface charge,
contact states from tracks, Apache-2.0 dependency hygiene, table closure).

## 22. Owner decisions

| ID | Decision | Default if no answer |
|---|---|---|
| D1 | Add `HF_TOKEN` and `VAST_API_KEY` to this environment | G0, clean extraction, R1 and eval wait; dev work continues |
| O1 | Accept tier P1 (library-seeded tracks) for a CPU-only submission, or require Phase 2 | Phase-1 output is development only |
| D2 | Go-ahead for GPU batches | **answered 30 Oct 12:20 UTC:** standing go-ahead; each batch is stated with cost in the work log before renting |
| O2 | For an object that fails adoption: submit the gmg mesh anyway, keep the current submission (library_v3 is deny-listed), or use library_v5 | keep the current submission, flagged |
| O5 | The spoon: submit the gmg spoon (unvalidated) | the gmg spoon is built and reported, but the current submitted spoon stays until you answer |
| D3 | Licence check for release (SAM Licence, Hunyuan territory, nvdiffrast) | no Hunyuan; no vendored generator code |

## 23. Key numbers quoted (sources)

- Library_v3 per object (cdo_eval, add_med) [D]: `results/baseline_library.jsonl`.
- Generator pools, 104 meshes [D]: `results/gen-probe/scores.jsonl`, `rows.json`.
- Hand kits [D, provisional, 7 mm ball prior]: `results/prim/potlid/metric_all.jsonl`, `prim/rack`, `prim/boards`,
  `prim/clean`.
- Lathes [D]: `results/lathe_obs.jsonl`.
- Contact census, view spreads, relative motion [M, dev]: scratchpad `gmg/design/gen-first/contact_census.jsonl`,
  `neural-recon/relmotion.jsonl`, `obs-first/v2/RUNS.txt`.
- Hybrid FSV veto log [D, post hoc]: scratchpad `gmg/design/hybrid-selector/looo_L0_veto.log`.
- R3, X0-mini, L0, NR probe [M/D]: scratchpad `gmg/design/{gen-first,hybrid-selector,neural-recon,obs-first}/`.
- Coverage census [M, dev]: `obs_census.jsonl` (this folder). It comes from `obs_all`; the anchor order (PREREG C.2)
  uses its `view_cap60` (low impact: a coverage statistic, not a contact one).
- Thickness leak: `docs/work-log.md` (27 Oct entry, lines near 4503).

## 24. Build plan (ordered; PREREG refers to these step IDs)

The owner's hypothesis is tested early: the skeleton (B1), the $0 mask check (B2) and the G0 probe (B3) come after
about 28 build-hours [E], instead of the 70-100 that v1 needed before G1. Every GPU step is a separate batch, stated
with cost in the work log. G0, B4 and every clean step wait on D1 (`HF_TOKEN`, `VAST_API_KEY`).

| Step | Module(s) | Depends on | Test (pass condition) | CPU/GPU |
|---|---|---|---|---|
| B0 | M0 `guard.py` (allow-list, refusals, det key filter); fix `autokit/io_gt.py` (drop the five mesh roots, load the deny-list); M0r roster | none | `tests/test_guard.py`: every deny path, glob, sha256, refused folder, refused det key and hard-link copy raises; allowed roles pass; strace of a dummy run shows 0 forbidden opens | CPU |
| B1 | **Walking skeleton:** M2d dev bundle; minimal SHELL and HULL producers with the partner clip; minimal M13 (all-frames E, fsv_far, V1-V4); packer (`fit_budget`, kit decode); M16 skeleton | B0 | 3 dev pairs (ep2 pot, ep2 lid, ep11 beige cup) give a packed watertight mesh, report and manifest; 0 forbidden opens; PREREG B.14 (V2 synthetic tests) passes. About 12-16 h | CPU |
| B2 | M9 CPU part: `choose_views`, Phase-1 masks | B1 | PREREG B.11 on the local videos `ep2_a.mp4`, `ep11_a.mp4`, `ep26_a.mp4`: no partner pixel inside any target mask; montage | CPU, $0 |
| B3 | M10 `remesh.py`; M18 `jobs/gmg_g0.sh`; then GPU batch **G0** | B2; G0 also needs D1 | PREREG B.10 (remesh, $0) and B.12 (G0 against K-a and K-b) | CPU, then GPU $1-2 |
| B4 | M2 `extract_joint.py` (passes 0-4), M1 `hands_cpu.py`, M3 `track_sanity.py` (identity tests), M4 `contact.py` | B0, B1; D1 | PREREG B.2a and B.3 on all 20 public episodes, streamed one at a time; B.15 | CPU |
| B5 | M13 `score.py` full (folds, view hold-out, moving-block bootstrap), M14 `select.py` | B1 | synthetic tests: a cylinder missing its base is charged on held-out base rays; a phantom body under a disc gets a high fsv_far; a slab without balls is flip-risk, with trusted balls not; the tie order is deterministic | CPU |
| B6 | M17 `validate/{x0_replay,xcheck}.py`; M11 `register` | B5 | PREREG B.1 (X0) and B.13 (X-check); $0, zero new scorings | CPU |
| B7 | M5 `structure.py`, M6 `markers.py` | B1 | synthetic lathe, mirror and plate recovered within 1 sigma; detector settings frozen as PREREG A.6 | CPU |
| B8 | M7 `producers/{shell,sym,hull}.py` full, M8 `complete.py` | B7 | on 10 dev pairs: every candidate watertight after the kit decode; no completed surface in FREE voxels beyond the band; no completed volume holds a partner sample deeper than b (assert) | CPU |
| B9 | M15 `simcopy.py` (install `coacd`) | B8 | 10 dev picks: watertight after decode, colliders built, rest angle reported | CPU |
| B10 | M16 `run_episode.py` full | B5, B8, B9 | 10 pairs (one per object, anchor episodes; clean bundles if B4 ran, else dev) give mesh, report and manifest; 0 forbidden opens; GT-free report only, nothing scored | CPU |
| B11 | M7 `producers/prog.py` (generic grammar, PREREG A.6b table) | B7, B8 | ≤ 30 min per pair; outputs watertight at ≤ 4000 faces; the 4 old JSON programs run as regression tests | CPU |
| B12 | M17 `validate/{xproxy,looo}.py` | B4, B6, B10, B11 | PREREG B.4, B.5, B.6 (B.6 as a selector only if B.13 passed); commits `deploy_variant.json` | CPU |
| B13 | public clean run of 33 pairs; `frozen.py` computes t0 then tau; SHA256SUMS frozen | B12 | PREREG A.1/A.3 constants committed; B.2b, B.7 and P15; manifests clean | CPU (local 12-35 h, or a rented CPU box $1-3) |
| B14 | scan round R1 (`validate/round.py` + `mesh_metric.py`) | B13 | PREREG C.3 and D (≤ 53 scorings; ≤ 73 under the thickness fallback) | CPU |
| B15 | M9 full, M11 `place.fit`, M12 `producers/{gen,fuse}.py`, M18 `jobs/gmg_gen.sh` | B3, B4, B5 | PREREG B.8 (synthetic placement) before G2; dry run of the box job on CPU | CPU |
| B16 | GPU batch **G1** (kill test) | B15 | PREREG B.9 | GPU $1.5-3.5 |
| B17 | GPU batch **G2** (public generation), public re-run, LOOO re-freeze | B16 passes | pools enlarged; SHA256SUMS frozen; `deploy_variant.json` re-committed | GPU $4-8 + CPU |
| B18 | scan round R2 | B17 | PREREG C.4 and D.2 (≤ 53 scorings) | CPU |
| B19 | eval CPU run (Phase-1 eval bundles, frozen eval tracks) | B14 (gmg adopted at least PARTIAL); D1 | 36 pairs with clean manifests; no eval number used | CPU |
| B20 | GPU batch **G4** (eval generation) | B18, B19 | 36 pairs re-picked with the frozen rule | GPU $4-8 |
| B21 | GPU batch **G3** (Phase-2 clean re-track with exclusive masks and separated start frames), rebuild, R3 | B14; owner O1 | PREREG P14 and D.5 (≤ 20 pose scorings) | GPU $3-5 + CPU |
| B22 | pack, manifests, submission choice | B19 (+ B20, B21) | export via `export_meshes.py`, `build_eval_json.py`; commit of the exact code | CPU |

If the owner wants a clean (tier P0-anchored) submission, B21 runs before B19 and B20, and the eval run uses the new
tracks.

---

## Revision 1 changelog (2026-10-30, before any gmg code and before any new scan scoring)

Why: a design review found 15 must-fix items, several integrity risks and some gaps. No new scan number was seen.
- **F1 freeze:** SPEC and PREREG were untracked; this revision is committed and pushed with both hashes recorded.
- **F2 guard:** clean mode is now an allow-list; the stage-1b, generator, crop, diag and design-probe folders and
  `obs_all` are refused; `det_f0.npz` reads are limited to mask keys; `io_gt.py` loses all five mesh roots (§2).
- **F3 thickness:** the 2.5 mm default (a leaked scan value) is replaced by the fitted t0, with a labelled fallback (§8).
- **F4 V3:** the scan-informed 0.20 is replaced by a GT-free percentile rule; the X0 pot-with-lid requirement is
  removed (§11, §21).
- **F5 eval inspection:** the eval-track analyses are disclosed; the eval-1 7.6 mm justification is removed; contact
  constants are justified from public data and generic reasoning (§4).
- **F6 V2:** sample-based test with a noise-scaled band and a normal-side clause, so nesting and copied surfaces are
  caught; synthetic tests pre-registered (§4, PREREG B.14).
- **F7 completion:** the partner rule now applies to every completion; grid feeding and the `pocc` channel are
  defined (§4, §6, §8, §9).
- **F8 extraction order:** passes 0-4 and the co-moving tie-break are written out (§7).
- **F9 spoon pairs:** added from the roster; a contact-subset adoption guard is pre-registered (§4, PREREG D.1).
- **F10 similar views:** one view × seeds; Pixal3D-MV only with ≥ 3 views; G1 rewritten (§4, §18).
- **F11 B.2:** reference from 3-D-separated frames with a minimum count (PREREG B.2).
- **F12 proxy X:** GT-free registration replaces the shared library_v2 frame; an X-check against existing labels is
  pre-registered (§12).
- **F13 Phase 2:** exclusive text-prompt masks and a separated start frame per object (§16).
- **F14 build order:** walking skeleton, $0 mask check and the G0 probe come first (§24, §18).
- **F15 fallbacks and identity:** TRACK_FAIL and reused meshes are counted in D.1; a cross-object identity test
  is added (§7, PREREG D.1).
- Also: informed choices labelled (class order, track tests, part vocabulary, extent table); D2 recorded as
  answered; the spoon defaults to an owner decision; eval tracks and the roster source frozen; CPU cost re-estimated;
  `mesh_metric` no longer imported at inference; labels [R] and [R, U] added where claims come from reading code.
