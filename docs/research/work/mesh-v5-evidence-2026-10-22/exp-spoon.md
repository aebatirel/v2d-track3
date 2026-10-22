# Spoon reconstruction path: prototype on proxy objects and eval-run spec (2026-10-22)

**Answer:** don't submit a fused spoon mesh. Submit the template with its parameters fitted to that episode's own evidence. If the fit's gates fail, submit the unfitted template. The fused grid is used only as evidence and for checks.

- On proxy objects, a mesh fused from a single episode scores 0.25–0.46 cm CD-O [D].
- The template family scores about 0.10–0.12 cm [M-synthetic]. That gap is worth roughly 0.04–0.09 cm on the 36-pair CD-O mean, because the spoon is 10 of the 36 pairs [E].

Two of the fusion rules you proposed did not hold up:
- **Finger-scale hand masks:** falsified on all four proxies. Keep today's 3 cm hand capsules.
- **Lifting the table band inside the object's own outline:** about neutral on the proxies, but essential for the spoon.

The strongest new rule is a seed band: depth samples more than 6 mm outside the seed mesh may clear space but never form surface. Everything ran on CPU ($0), and no repo file was changed.

## What I ran
- **Working folder:** `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/v5/spoon/`. Scripts are in `code/`, results in `out/`, fusion grids in `grids/`, meshes in `post/`.
- **Run record:** every command with its time is in `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/v5/spoon/COMMANDS.txt`.
- **Data:**
  - I fetched depth for ep18 and ep39 into the shared `interact/v5/depth/` folder. I kept both files because the `obsnew` task uses them (14 GB disk free).
  - Proxies: sweeper ep18 and ep31; dust pan ep18, ep39 and ep40. Tracks are the scan-templated `loc/perc` ones.
- **Scripts:**
  - `spoon_flip_mc.py`: tests whether the kit's registration flips the spoon, using our own models only (no ground truth).
  - `maskacct.py`: counts how much of the object's own depth each mask removes [D]. With `REFINE=1` it first ICP-aligns the scan to each frame.
  - `spoonfuse.py`: a fork of obsfuse3 that accumulates several mask rule sets, for all frames and held-only frames.
  - `fit_spoon_cpu.py`: a working CPU replacement for the `spoon/fit_spoon.py` skeleton. It uses scipy least squares with my own finite-difference Jacobian; scipy 1.18 takes about 1e-8 steps at x=0, so a first run moved no shape parameter. That run is kept and labelled superseded.
  - `xcheck.py`: a cross-registration gate that needs no ground truth.
  - Scoring uses `../metric/mesh_metric.py` (97 proxy meshes).

## Findings
1. **The spoon frame A/B question no longer matters** [M, from reading the kit code].
   - `AUC.py` registers our mesh to the hidden scan (lines 866–869) and converts our poses into the scan's frame. The scene is then aligned in that frame.
   - So our own frame convention is irrelevant. What counts is whether that registration flips and how far off it lands.
   - I suggest dropping the spoon-frame question from the organiser email.

2. **Flip risk is low for any complete spoon-shaped mesh** [M-synthetic]. Results are in `out/flip_mc_summary.md`.
   - I registered 10 candidate meshes against 16 plausible spoons (12 with markers, 4 without) at 5 of the 10 eval seeds, using the kit's registration: **0 flips in 800 registrations**.
   - The template lands 1.9 mm off at the median (90th percentile 3.3, worst 4.2). Against spoons without markers it is 3.7 mm (worst 6.6).
   - Stand-ins for typical fusion defects stay within 1.1–1.7° median rotation and 1.8–3.4 mm median offset (worst 8.1 mm). The defects were: 1.5 mm or 3 mm thicker, bowl filled, no markers, underside closed down to the table, a fist-shaped collar.
   - Self-ambiguity (how well the mesh fits its own 180° rotation, above the noise floor): template 2.00 mm at 177.6°. Losing the markers drops it to 1.28 mm; no markers plus underside closed to the table gives the lowest, 0.89 mm.

3. **Mask accounting** [D, scan pose ICP-refined per frame; held frames]. Results are in `out/acctR_summary.txt`.

   | | Sweeper ep18 | Sweeper ep31 | Dust pan ep18 | Dust pan ep39 | Dust pan ep40 |
   |---|---|---|---|---|---|
   | Own depth removed, 3 cm capsules | 22.1% | 25.5% | 17.1% | 8.4% | 10.9% |
   | Own depth removed, finger masks (12 mm fingers, 18 mm palm) | 5.3% | 8.1% | 2.6% | 2.6% | 3.7% |
   | Hand samples the finger masks let in, per own sample | 0.40 | 0.37 | 0.38 | 0.22 | 0.22 |
   | …of which within 4 mm of the surface | 0.06 | 0.05 | 0.16 | 0.07 | 0.08 |

   - Hand leak means samples near the object that are not its own, that the 3 cm capsules remove but the finger masks keep. In held frames the finger masks let in more hand depth than the own depth they recover.
   - **Table band, object lying free:** the 15 mm band removes 76% / 26% / 77% of the dust pan's own depth (ep18/39/40). Exempting the object's own outline, eroded by 5 px, cuts that to 7.4% / 3.2% / 0.8%.
   - **For the spoon** [M, template geometry]: at rest, 51% of its upward-visible surface and 95% of the bowl lie inside the 15 mm band.
   - **Lost hand detections:** frames where MediaPipe misses a hand have 1.37 unlabelled near-object samples per own sample, against 0.68 in normal held frames. That is the reason for carrying a lost holding hand forward from nearby frames.

4. **Fusion rules compared** [D]. One episode each, 2 mm voxels, the `4c12_adj_g2m` variant, all frames. Cells are CD-O cm / registration offset mm / flips out of 6 seeds. Full table: `out/rule_table.txt`.

   | Proxy | 3 cm capsules + band (today) | Capsules + own-outline exemption | Finger + exemption | Capsules + exemption + seed band | Finger + exemption + seed band |
   |---|---|---|---|---|---|
   | Sweeper ep18 | 0.441 / 5.0 / 0 | 0.457 / 4.9 / 0 | 0.485 / 6.1 / 1 | **0.308 / 2.5 / 0** | 0.323 / 24.4 / 1 |
   | Sweeper ep31 | 0.269 / 1.8 / 0 | 0.272 / 1.8 / 0 | 0.293 / 1.8 / 0 | 0.266 / 2.0 / 0 | 0.278 / 1.6 / 0 |
   | Dust pan ep18 | 0.254 / 4.9 / 0 | 0.254 / 5.1 / 0 | 0.268 / 5.0 / 0 | 0.252 / 5.6 / 0 | 0.269 / 7.1 / 0 |
   | Dust pan ep39 | 0.282 / 4.7 / 0 | 0.279 / 4.9 / 0 | 0.278 / 4.9 / 0 | 0.271 / 4.7 / 0 | 0.272 / 4.8 / 0 |
   | **Mean CD-O** | 0.312 | 0.316 | 0.331 | **0.274** | 0.286 |

   - **Independent seed check:** here the seed was our own single-episode mesh from another episode, not the library mesh.
     - Sweeper ep18: capsules + exemption goes from 0.452 to 0.296–0.300 with the seed band; one of the two variants flips once.
     - Dust pan ep18: 0.254 → 0.251–0.254 (neutral).
     - Finger + exemption with this seed flips 3–5 of 6 on sweeper ep18.
   - **Today's mesher** (12 mm, fill, at 2 mm voxels) is clearly worse: 0.31–0.65 cm, and sweeper ep18 flips 6 of 6.
   - **Held-only fusion** flips 2–5 of 6 on the sweepers. Always fuse all frames.
   - The silhouette free-space step changes CD-O by ≤0.004 cm (≤0.01 on the 3 cm capsule + band column; mostly a slight gain).
   - For reference, the multi-episode library_v2 meshes score 0.316 (sweeper) and 0.331 (dust pan).
   - The evidence gate that needs no ground truth (share of evidence more than 8 mm from the mesh) picks out the bad cases: 0.25–0.37 for the finger rules on the sweepers and 0.31 for today's rules on sweeper ep18, against ≤0.03 with the seed band.

5. **Cross-registration gate** [M against D]. Results are in `out/xcheck_summary.txt`.
   - I registered each mesh to our own independent model in the same track frame, using the kit's routine at the scorer's seeds. It flags a mesh when the registration rotates it past 90°.
   - Across 80 meshes: 7 caught, 0 false alarms, 6 missed, 67 correct passes.
   - It catches every mesh that flips on 5 or more of 6 seeds. It misses partial flips (1–3 of 6 seeds), all of them on the sweeper, whose scan is nearly symmetric.

6. **Fitting the template** [M-synthetic]. 6 synthetic spoons × 2 eval seeds, about 13 s per fit. Results are in `out/fit_synth.jsonl`.

   | Candidate | CD-O cm | Offset median / worst mm |
   |---|---|---|
   | Template, unfitted | 0.119 | 1.70 / 3.3 |
   | Fit, both sides observed | 0.100 | 1.06 / 4.7 |
   | Fit, both sides + 6% hand points | 0.104 | 0.53 / 3.6 |
   | Fit, top views only | 0.132 | 2.82 / 5.8 |
   | Fit, top only + 1.5 mm thickening + hand points | 0.172 | 1.48 / 5.0 |

   - Gate: accept the fit only if no parameter moves more than 3 prior standard deviations.
   - With the gate, the four rows become 0.099 / 0.122 / 0.103 / 0.119. The gate rejects 5 of 6 top-only fits and 6 of 6 biased fits.
   - So the fit helps only when the evidence covers both sides and is unbiased.

## Spec for the eval run (spoon episodes 3, 5, 6, 15, 16, 32, 33, 35, 36, 37)
- **GPU, inside the planned eval perception run:**
  - FoundationStereo depth, saved to the HF store.
  - MediaPipe hands.
  - `perc2` tracking with `spoon/wooden_spoon.glb` as the spoon seed and v5 meshes for the other objects. The frame-0 mask for episodes 35–37 comes from note 20's `r3_flat`.
  - Optional: re-track the spoon with the fitted template if it differs from the seed by more than 1.5 mm or 3°. About $0.1–0.3 per episode [E].
- **CPU, per episode, about 10–15 min:**
  1. Fusion (`spoonfuse` rules): 3 cm capsules plus carry-forward of a lost holding hand (≤6 frames); 15 mm table band except inside the template's outline eroded by 5 px; seed band 6 mm around the posed template; the other objects at 12 mm; 2 mm voxels; 4/6/12 mm truncation; free-space counters; all frames.
  2. Silhouette pass (`maskfuse`) with the template's colour.
  3. Post-pass `4c12_adj_g2m` to get the fused mesh F, plus the evidence gate.
  4. Export the evidence (zero-crossing voxels plus seen-free voxels) and fit the template, giving T_fit.
- **Gates** (no ground truth; to freeze now):
  - Fit: no parameter beyond 3 prior standard deviations; median data residual ≤1.0 mm; both sides of the spoon covered [H, threshold not calibrated].
  - Mesh: watertight, one body, Euler characteristic 2, ≤4096 faces.
  - Flip: registered to the unfitted template T0 at all 10 eval seeds, rotation ≤10° and offset ≤3 mm.
  - Self-ambiguity excess ≥0.9 mm.
  - Template consistency: share of the episode's evidence more than 8 mm from T_fit ≤0.05. If this fails, the real spoon may be outside the template family; flag it for owner review.
- **Selection:** T_fit, else T0. The fused mesh F is never chosen automatically.
- **Then:** build the collision geometry (S5). Put the spoon at its track into the other objects' fusion as an "other object". The spoon must not carve the other objects unless its track passes QA.
- **GPU test:** there is no public spoon episode. I propose adding a perception dry-run on eval 37 and eval 3 to the test batch, producing overlays and a fit report for your visual check (≈$1 [E]).

## Open questions for you
1. **Does a template whose parameters are fitted to our own observations of that episode count as "reconstructing it ourselves"?**
   - The starting dimensions also came from our own stereo measurements on the eval clips (notes 13 and 20).
   - Options: (A) fitted template, which I recommend; (B) mesh fused from that episode, expected 2–4× worse CD-O [D-proxy]; (C) ask the organisers.
2. If an episode's fit fails its gates, may we submit the unfitted template, which is also the tracking seed?
3. May the spoon be fitted jointly over all 10 eval episodes? It is one physical spoon, and pooling guarantees both sides are observed. This departs from "re-fuse each episode from its own video".
4. The seed band uses the seed mesh as a shape prior. For the known objects in S7 that means the v5 library mesh, which goes beyond "tracking seed only". Is that allowed?

## What to port
- **Into `recon_mesh.py`:**
  - the own-outline exemption from the table band;
  - `--seed_band`, a signed distance to the seed posed by the track;
  - hand carry-forward.
  - Keep `hand_r=0.03`; do not port the finger masks.
- **Replace the skeleton:** `code/fit_spoon_cpu.py` (`fit`, `fd_jac`, `residuals`) replaces `spoon/fit_spoon.py`. A grid-to-evidence exporter still needs writing.
- **Gates module:** `xcheck` (cross-registration), `mesh_metric.ambiguity`, `gate_ev`, and the prior gate.
- **As tests/diagnostics, not inference:** `spoon_flip_mc.py` as a test; `maskacct.py` into `mesh_diag.py` (it reads the public scan, so diagnostics only).

## Caveats
- Proxy tracks are scan-templated; per-frame ICP corrections are 2.3–3.9 mm median. I fetched the ep18 own-mesh (perc2m) poses to `in/` but did not run them, because the scoring would need a mesh-to-scan transform for that frame. The rule ranking should be rechecked on perc2m.
- The library_v2 seeds were built with scans as `--others`. The independent-seed runs only partly address this, on two proxies.
- The synthetic spoons come from the template family, so error from a real spoon outside that family is unmeasured.
- The proxies are thicker than the spoon's 5 mm bowl wall.
- The flip test used 5 of the 10 eval seeds.