# PUBOWN: one own-video mesh set per public episode (C0b constants), for the perception re-track test

Written 2026-10-31 ~18:50 UTC, before any PUBOWN build. Updated ~19:55 UTC, after C0b's public box finished
(C0B-DONE rc=0, 19:33 UTC) and before any PUBOWN box build. Step log: `NOTES.md`. Job: `jobs/`.

**What it is.** The public analogue of E0b, at the granularity of one episode. Every public episode gets its own
mesh for each object that has a clean own-video method. That mesh is built only from that episode's observed points,
with C0b's scan-free constants, and picked within the episode. No mesh is chosen across episodes. The score session
re-runs perc2 with these meshes as templates and scores the tracks against mocap with focused-pascal. **Nothing is
scored here.**

Labels: [M] measured, [E] estimate, [H] hypothesis. Paths are relative to `docs/research/mesh-2026-10-26/`.

## 1. Pairs (22)

| Object | Public episodes | Method (C0b family, per episode) | Candidates per pair |
|---|---|---|---|
| white_pot | 0, 2, 26, 27, 41, 42, 43, 44, 45 | `prim_potlid.py pot --c0b` | 4: fit, nostem, nomk, thick |
| white_pot_lid | 0, 2 | `prim_potlid.py lid --c0b` | 8: {a6b1, a6b2} x {fit, nostem, nomk, thick} |
| plastic_dish_rack | 12, 13, 26, 27, 31 | `PRIM_CUP_LEAN=1 prim_rack.py run --episodes <e>` (one run per episode) | 2: full, nomk |
| blue_cup | 11, 12, 13, 21, 22 | `lathe_obs.py` (C0b lathe flags) | 2: g1, g0 |
| beige_cup | 11 | `lathe_obs.py` on the M_sep(own) separated-frame points (C0b PREREG s10, from C1/T1) | 2: g1, g0 |

That is 9 + 2 + 5 + 5 + 1 = 22 pairs and 74 candidates.
- **The lid is expected to fail [M, C0b box].** C0b's public box built 0 of 16 lid candidates on ep0 and ep2. The
  flange selection came out empty: clutter in the cube-ROI lid points gives robust scale s = 107 mm on ep2. C0b
  records this as pre-registered (no candidate, no retry).
  - PUBOWN uses the same code and the same lid points, so lid ep0 and ep2 will almost certainly fail again and keep
    library_v3.
  - The lid builds stay in the job so that the rule is unchanged and the failure is recorded per pair. They cost
    seconds.
  - So the expected deliverable is **20 PUBOWN meshes + 2 library_v3 lids**.
- **water_pitcher** (ep21, 22) joins only if `cdo-sprint/C2/P-pitcher` reports ADOPTED before the PUBOWN box is
  created. Then its own per-episode build command is added as a separate pair list, recorded in NOTES. At 18:32 UTC it
  was not adopted: the obs points were still being built.
- **library_v3 stays** for every other object in these episodes: mini_dust_pan, mini_sweeper, wooden_piece_1/2, the
  spoon, and the pitcher (unless adopted). `manifest.tsv` lists them as `library_v3`.

## 2. Inputs (GT-free) and code

- **Frozen source: C0b's public box run** `mesh-20261031-c0b-00e8584` (code `00e858434419...`). PUBOWN reuses these of
  its outputs, fetched from the store `runs/<c0b run>/results/c0b/<rel>` and checked against C0b's own `SHA256SUMS`:
  - the pass-B observed points `pts/B/ep<e>_<object>.npz`: cube ROI 0.30 m with guard, co-objects carved with their own
    pass-A points, sweep tracks, FoundationStereo depth, G1 hands; beige: `ep11_beige_cup_sep.npz` plus
    `msep_ep11.json`;
  - the thickness rows `thick/*.npy|json`;
  - the gmg A.2 `sigma/*.json` where C0b measured them;
  - the gmg marker detections `markers/ep<e>.json`, reused only when C0b's prim-object set for the episode equals
    PUBOWN's;
  - `t0_c0b.json`, the A.1 statistic over all 33 public object-episodes. This is C0b's frozen GT-free fallback
    thickness, which E0b also uses.
- **Recomputed on the PUBOWN box** with C0b's commands (`c0b_prep.py`):
  - sigma for the pairs outside C0b's candidate pools: pot ep0, blue cup ep11, 12, 13;
  - the ep0 marker detection over {white_pot, white_pot_lid}. C0b detected on ep0 with the lid only, and the pass-2
    consensus radius is pooled over the episode's prim objects.
  - The staging script derives this list from C0b's `SHA256SUMS` and plan, so a C0b stage that failed for some file
    is recomputed rather than silently missing (observed points cannot be: the pair then fails).
- **Tracks:** the sweep base tracks `SCR/data/sweep/ep<e>/poses.npz` (the pack's public perception, store run
  `20261025-sweep-a894083`). The staging asserts that their sha256 equals C0b's input plan.
- **Never an input:** scans, mocap, parquet `observation.objects` poses, `*_align` files, any scan-derived constant
  (`pubown_stage.py` asserts the names; the gmg guard runs in `clean` mode). library_v3 is not read by any PUBOWN
  stage. It only appears as the fallback name in the manifest.
- **Code:** the box extracts every builder, `c0b_prep.py`, `c0b_tasks.py`, the gmg / autokit modules and
  `recon_mesh` from the C0b box commit into a separate tree (`jobs/pubown_freeze.sh`). It runs only that tree, so
  later edits to the shared scripts by other sessions cannot change a PUBOWN build. [M] The working tree's
  `prim_rack.py` already carries uncommitted C2/R options. The tree hashes are written into `plan.json` at staging
  and re-checked on the box.
- **Flags are C0b's, generated by C0b's own code.**
  - `pubown_tasks.py build` runs `c0b_tasks.py build` on a C0b-shaped plan whose candidate episodes are the PUBOWN
    pairs (rack empty, no merged cup). It gets exactly C0b's pot, lid, blue-cup and beige command lines. [M] On the
    dry run, the beige lines equal C0b's dry-run lines after path normalisation, and the beige meshes are
    byte-identical to C0b's.
  - Params: `c0b_tasks.params` (thickness chain C0b 3.3, APP_D = 3 sigma). The merged-cup target is dropped.
  - **One deliberate change, the rack.** C0b runs `prim_rack.py run` once over 5 episodes: one pooled wall thickness
    T and one floor depth from the deepest table cut of all of them. PUBOWN runs it once per episode
    (`--episodes <e>`), so T is that episode's own chain value and the floor depth comes from its own cut. The flags
    are otherwise C0b's: `PRIM_CUP_LEAN=1 --t_wall T --s0_min_t --markers_dir`.
  - The single-episode run also writes `joint`/`joint_nomk` files. They are not candidates, since joint is C0b's
    multi-episode family.

## 3. Pick (per pair; no cross-episode pick)

C0b PREREG section 5, with ALL = **the pair's own C0b observed points** (beige: the M_sep-masked points):
1. **Exclusions:** the raw mesh is not watertight (trimesh, `process=True`); the kit's
   `budget_mesh(path, 4096, 4096)` raises or leaves more than 4096 faces or vertices; there is no fidelity value.
2. **Pick:** the lowest `obs_fidelity.py` `sum_mm` (defaults: trim 0.9, 300 k observed points, 200 k mesh samples,
   seed 0, no ICP). Ties at the printed 3 decimals go to fewer raw faces, then to the label in byte order.
3. **No eligible candidate:** the pair keeps library_v3 and the manifest says so.

The pick is in-sample: the same points build and judge the mesh. That is the E0b analogue, and it is the template
quality the eval meshes will have. Every candidate's own fidelity is in `selection.json` (`table`).

## 4. Outputs (HF store `aebatirel/v2d-store`, `runs/<run id>/results/pubown/`; nothing bulky in git)

| Path | Content |
|---|---|
| `meshes/ep<e>/<object>.glb` | **the deliverable**: the picked mesh per pair, in the object frame of the sweep track (as fitted, no alignment) |
| `manifest.tsv` | episode, object, source (`pubown` or `library_v3`), mesh path, sha256, picked label, for every slot object of the 15 episodes that have a pair (0, 2, 11, 12, 13, 21, 22, 26, 27, 31, 41-45) |
| `selection.json` | per-pair pick, runner-up, exclusions, the full candidate table (own fidelity, faces, watertight, budget) |
| `cand/...`, `check/...`, `fid/...`, `params.json`, `plan.json`, `frozen_code.json`, `logs/`, `status/`, `SHA256SUMS`, `pubown_job.log` | all candidates and the records behind the pick |

The reused C0b files are symlinked into the results folder and are not re-uploaded. `plan.json` names them with their
sha256 and the C0b run.

After the box, the agent pulls `selection.json`, `manifest.tsv` and the 22 meshes (small) and commits
`PUBOWN/RESULTS.md` with the manifest and the sha256s. The mesh files stay in the store unless the score session
asks for them in git.

## 5. Machine and cost (box not created by the prep step)

- **Work:**
  - 4 sigma tasks;
  - 1 marker detection (ep0, pot + lid). This is the long pole. [M] C0b's box: ep2 pot + lid took 1031 s, ep26/27
    1080/1183 s, ep41-45 671-834 s; ep0 [E] about 15-20 min;
  - 42 build tasks, 74 candidates;
  - 74 checks and 74 fidelity runs.
  - The 33 build tasks that need no new marker file run while ep0's detection runs; the 9 pot and lid ep0 tasks run after
    it.
  - No depth download: C0b's points are reused. [M] C0b's pass-B files total 1016 MB over 34 files; PUBOWN fetches
    23 of them plus small rows.
  - [M] Local dry run (ep12, 4 shared loaded cores, nice 19): the single-episode rack run took 447 s and a cup lathe
    66 s. On C0b's box all 32 builds took 2.3 min and 426 fidelity runs 1.8 min.
- **Box:** one Vast CPU box, at least 32 cores and 64 GB, `SETUP=none`, `DISK=40`, at or below
  $0.5/h. Fidelity workers = RAM / 8 GB (C0b's rule). [E] 25-40 min wall including setup (venv about 1 min, fetch
  about 1-2 min, ep0 markers about 15-20 min in parallel with the other builds), **about $0.2-0.4**.
  - Ledger session `mesh-bold`: a planned line before the create, an actual line after. The cap for this job is $2.
  - The box self-destroys; confirm it is gone.
- **Failure hold.** On a non-zero job exit, `run_job.sh` keeps the box 30 min (`FAIL_HOLD_MIN`, not settable through
  `ops/vast.sh`) and then the watchdog destroys it. Destroy it by hand if no debugging is needed.
- **Staged (2026-10-31 ~19:58 UTC):** run id **`mesh-20261031-pubown-ed7171c`**, code commit
  `ed7171caf6c87b792e1da9d8c38e560a18855475`.
  - Inputs are in the store at `runs/mesh-20261031-pubown-ed7171c/inputs/`: 18 files plus `SHA256SUMS`; `plan.json`
    sha256 `90178838...9222`.
  - 97 reused C0b files, 725 MB, are present in `runs/mesh-20261031-c0b-00e8584/results/c0b/`, and their LFS sha256
    equals C0b's `SHA256SUMS` [M].
  - Create:
    `ops/vast.sh SETUP=none DISK=40 V2D_COMMIT=ed7171caf6c87b792e1da9d8c38e560a18855475 create <offer> mesh-20261031-pubown-ed7171c 'bash docs/research/mesh-2026-10-26/cdo-sprint/PUBOWN/jobs/pubown_box.sh'`
  - Watch: `ops/vast.sh exec mesh-20261031-pubown-ed7171c 'grep -v progress /content/results/pubown/pubown_job.log | tail'`.
    The end line is `PUBOWN-DONE rc=0` or `PUBOWN-INCOMPLETE`.

## 6. Known risks [H]

- **Contaminated points (mutual carving).**
  - Blue cup ep11 (nested with the beige cup) and ep12/13 (in the rack): each object's points are carved by the
    co-object's pass-A points, but those can hold the target's own surface from frames where the two were static
    together (C0b PREREG 3.4 [H]). C0b masks only the beige cup.
  - Falsifier: the blue-cup ep11 pick's own fidelity and its re-track error compared with ep21/22.
- **Thin evidence on single episodes.** The rack's floor depth and wall thickness come from one episode. The lid and
  rack had no usable two-sided thickness measurements, so they use t0_C0b. [M] C0b box: t0_C0b = 4.559 mm (fittable;
  the rack had 3 measurements, the lid 0), against C0's 2.5 mm.
- **In-sample pick.** Own fidelity rewards over-fit variants (e.g. `thick` when the points are noisy). The re-track
  test is the out-of-sample check.
- **Frames.** Meshes are in the object frame of the library_v3-seeded sweep track, as fitted, with no alignment
  (C0a-diag). The blue cup's axis differed most on eval in E0 (kit tilt 3.3-7.3 deg). The score session should read
  any frame offset from the re-track, not from this job.
