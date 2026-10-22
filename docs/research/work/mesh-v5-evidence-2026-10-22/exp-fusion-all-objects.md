# Observation-first fusion on the untested objects, the episode-weighting test, and watertight decimation (2026-10-22)

**Bottom line:**
1. **S1 fails its own falsification test.** Observation-first fusion (O, `4c12_adj_g2_f0_cont`) fails the GT-free G2 gate (unexplained evidence) on 3 of the 4 named objects: blue cup, pitcher and rack. It works on the beige cup and the mini sweeper.
2. **Weighting episodes by the unsupported share is falsified.** The pre-registered rule beat all-episode fusion on 1 of 4 objects.
3. **The kit decimation breaks watertightness on almost every mesh; open3d quadric decimation keeps it.** It does so on 15/15 meshes and is neutral on CD-O.

Everything ran on CPU, cost $0, and the repo is unmodified. All scan-based numbers are [D] (kit CD-O and ADD at the scorer's eval seeds, via `v5/metric/mesh_metric.py`). GT-free numbers are [M].

**Input caveat.** The tracks are the scan-templated loc/perc ones. ROI, `--others`, band mask and colour source are library_v2, the same as the earlier Design O prototypes. Critique #10 calls these inputs scan-contaminated, so this round is diagnostic only, not a production build.

## What I ran
Full run record: `…/interact/v5/obsnew/COMMANDS.txt` (times, commands, logs).

- **Depth.** Fetched 11 episodes (11, 12, 13, 18, 21, 22, 26, 27, 31, 39, 40) into `v5/depth`, float16, every 2nd frame, ~4.0 GB. ep18 and ep39 had been fetched by another agent and I reused them. I deleted my 9 episodes afterwards. 15 GB of disk is free.
- **Fusion, one grid per object and episode** (18 object-episode pairs):
  - `scripts/obsfuse4.py` is obsfuse3 plus two additions: an NB counter, so the below-table votes can be removed exactly afterwards, and band-mask deltas. One pass therefore yields four grid modes.
  - `maskfuse.py` added silhouette counters wherever video exists (all episodes except ep26).
  - **Finding:** the ego_cam_c video is effectively grayscale (a and b channels about 127/129), so the silhouette test can only use brightness.
- **Post-pass.** `scripts/obspost5.py` built the required variants: today's rules at 2 mm, O default (`4c12_adj_g2_f0_cont`), O with silhouette (`g2m`), local fallback (`fb`), and fallback with silhouette. I also built the grid modes nobc, bm, bmnb and nbk.
- **Fixes added after seeing results (post-hoc):**
  - `@lc25` changes how the main body is picked: the piece nearest the centre, but only among pieces at least 25% the size of the largest. GT-free, this changes only the pitcher and the rack. The meshes of the other 8 objects are byte-identical.
  - `libeps` uses the library_v1 episode lists (blue cup 12, 13, 21, 22; rack 12, 13, 27) to separate the effect of the fusion rule from the effect of episode choice.
- **Episode-weighting test.** `scripts/loeo.py` wrote down the rules in its header at 13:40, before any scoring. Primary rule R_w weights each episode by min(u)/u_e. Secondary rules: R_sel keeps episodes with u_e ≤ 1.5·min u; R_loo drops one episode. The test passes only if R_w beats all-episode fusion on both metrics for at least 3 of pot, dust pan, blue cup and rack.
- **Scoring.** 105 meshes went through `mesh_metric.py` (`metric/results_{p1,r2,r3,r4}.jsonl`). Identical files were matched by content (sha) and scored once. Labels in `results_r4.jsonl` have a stray filename prefix from grep; the analysis maps them by sha, so the numbers are right.
- **Decimation study.** `scripts/decim.py` compared 7 methods on 15 full-resolution meshes.
- **Tables.** Everything is in `…/v5/obsnew/tables.md`, produced by `scripts/analyze5.py`.

## Results

### S1 on the untested objects
Values are CD-O cm / ADD mm, with library_v2 first.

| Object (eval pairs) | library_v2 | Today's rules at 2 mm | O default | Local fallback (fb) | G2 [M] (O) |
|---|---|---|---|---|---|
| beige cup (2) | 0.856 / 6.5 | 0.731 / 6.2 | **0.732 / 5.7** | 0.738 / 6.7 | 0.008 pass |
| mini sweeper (2) | 0.316 / 25.1, 2 flips | 0.455 / 8.1 | **0.282 / 3.2, 0 flips** | 0.273 / 3.0 | 0.038 pass |
| dust pan (2), replication | 0.331 / 5.6 | 0.311 / 5.6 | 0.252 / 3.6 | **0.226 / 3.1** | 0.025 pass |
| blue cup (5), all episodes | 0.523 / 10.0 | 0.511 / 7.0 | 0.677 / 9.0 | 0.556 / 10.7 | 0.175 **FAIL** |
| blue cup, libeps | – | 0.500 / 7.8 | 0.521 / 6.6 | 0.530 / 8.0 | 0.172 FAIL |
| pitcher (1) | 0.894 / 7.6 | 0.881 / 8.4 | 4.545 / 198 (degenerate); 0.848 / 8.0 with @lc25 | 0.842 / 8.7 (@lc25) | 0.120 FAIL |
| rack (5), all episodes | **0.555 / 6.0** | 1.102 / 21.0 | 3.757 / 201 (degenerate); 1.664 / 37.8 with @lc25 | 0.965 / 22.9 | 0.455 FAIL |
| rack, libeps | – | 0.742 / 9.3 | 0.887 / 10.5 | 0.864 / 10.3 | 0.112 FAIL |

- **Two real bugs, measured [M]:**
  - *Main-component choice.* The original rule picked a ~1 cm³ fragment near the grid centre over a 921 cm³ body on the hollow pitcher and on the open-lattice rack. `@lc25` fixes this.
  - *Per-frame below-table carving.* It removes most of the rack's real material: 83 cm³ of fine inside voxels with it, 353 cm³ without. This is the same mechanism as board 2.
- **No variant at 2 mm reaches the 4 mm library rack** (best 0.742). The rack decides the weighted result: it has 5 eval pairs.
- **Silhouette and band mask are nearly inert here** [M]: at most 1.2 cm³ of silhouette-free volume and |ΔCD-O| ≤ 0.013 on the new objects. The grayscale camera is the likely reason.
- **nbk** (below-table hits only block closing, as the plan proposes) makes the dust pan worse (0.345 vs 0.252) and does not save the rack.
- **Blue-cup cavity hypothesis (adj closing opens the interior) [D]: not falsified.** Interior fill drops from 37% (v2) to 22% (O) and 28% (fb). The mesh is still 226–239 cm³ against 136 cm³ in the scan.

**Global choice over 10 objects, weighted by eval pairs, versus v2 [D]:**

| Rule | ΔCD-O (cm) | ΔADD (mm) |
|---|---|---|
| O ungated | +0.29 | +5.4 |
| fb ungated | +0.050 | +1.5 |
| O, gated, falling back to today's rules at 2 mm (the plan's S1(b)) | +0.083 | +0.8 |
| O, gated, falling back to v2 (stand-in for a 4 mm mesher) | **−0.016** | **−1.6** |

- In the last row, using the boards' no-below-carve grids gives −0.021 / −1.6 with no new flips. The board grids that include below-table carving add flips (wp1 1/6, wp2 2/6).
- **The fallback must be a 4 mm mesher, not today's rules at 2 mm.**

### Episode weighting (N6/8)

| Rule | Objects beaten (pre-registered base) | With @lc25 (post-hoc) |
|---|---|---|
| R_w (primary) | **1/4** (pot only) | 2/4 |
| R_sel | 3/4 (pot, blue cup, rack) | 3/4 |
| R_loo | 1/4 | 1/4 |

- **R_w is falsified.**
- **R_sel is exploratory and unconfirmed.**
  - It loses on the dust pan (0.319 vs 0.252).
  - I wrote down a confirmation test before scoring it: sweeper and pitcher. There it keeps every episode, so it cannot beat all-episode fusion.
- **[D] On all 6 objects tested, one single episode beats all-episode fusion on CD-O:**

  | Object | Best single episode | All episodes |
  |---|---|---|
  | blue cup | ep13: 0.407 | 0.677 |
  | pot | ep27: 0.322 | 0.725 |
  | rack | ep31: 0.888 | 1.664 |
  | pitcher | ep21: 0.819 | 0.848 |
  | sweeper | ep31: 0.271 | 0.282 |
  | dust pan | ep18: 0.246 | 0.252 |

- **Neither GT-free statistic picks that best episode reliably** [M]: the unsupported share u does about 3/6 times, unexplained8 about 3/6.
- **[H]** Fusing several episodes at 4 mm truncation is limited by mismatch between episodes. Falsification test: align each episode's grid by GT-free ICP of its single-episode mesh before summing. The hypothesis is falsified unless this beats all-episode fusion on both metrics for at least 4 of 6 objects.

### Watertight decimation (N5)
- **Kit `budget_mesh`:** after removing the packer's padding faces it is watertight on only 6/144 S1 meshes, and 0/15 in the study. That is 1–5 bodies, not the 21–146 N5 reported, which probably counted the padding.
- **Every full-resolution mesh is watertight**, but with many tunnels through the 2 mm walls (Euler numbers down to −944).

| Method | Watertight, topology kept | Self-intersecting faces (median) | p95 deviation (median) | CD-O vs kit (8 meshes) | ADD vs kit |
|---|---|---|---|---|---|
| open3d `simplify_quadric_decimation(4096)` | 15/15 | 24 | 0.49 mm | −0.004 cm | +0.35 mm (noise) |
| pymeshlab QEC, preservetopology, halving stages | 15/15 | 8 | 0.61 mm | +0.010 cm | ≈ 0 |
| manifold3d `simplify` | never reached 4096 | – | – | – | – |

- **The packer keeps such a mesh unchanged.** It is already within 4096 faces and vertices, so the packer only welds it and adds zero-area padding.

## What to port
1. **Decimation.** Use open3d quadric decimation to 4096 faces, check watertightness, bodies and Euler number, and fall back to pymeshlab QEC with preservetopology in halving stages. Build collision geometry from the full-resolution mesh. pymeshlab needs the system library `libopengl0`; I installed it here with apt, and pymeshlab itself went into a private pip `--target` folder.
2. **`@lc25` main-component rule.** Port it in place of the nearest-the-centre rule. It is neutral on 8 objects and fixes the pitcher and the rack.
3. **O as the mesher, behind the G2/G1 gate (unexplained8 ≤ 0.05, seen-free volume ≤ 0.5 cm³), with fallback to a compliant 4 mm `recon_mesh` (pass 0, `--others` none).** O alone works only on thin, well-observed objects. The −0.016 cm gain is estimated with v2 standing in for that 4 mm rebuild [E]. The rebuild has not been scored yet and is the next experiment.
4. **Do not port:**
   - weighting by unsupported share, or R_sel;
   - nbk mode;
   - the silhouette for this grayscale camera;
   - today's rules at 2 mm as the fallback.

Files are in `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/v5/obsnew/`:
- `tables.md`
- `COMMANDS.txt`
- `scripts/`
- `out/` (meshes, `post.jsonl` per object, `loeo_*.json`, `decim/decim.jsonl`)
- `metric/` (`results_*.jsonl`, `alias.json`)
- `grids/` (fusion grids)
- `logs/`