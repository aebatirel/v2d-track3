# gmg I: INTERLOCK stage (slot / seat / cavity geometry) — working notes

Started 2026-10-31 ~09:10 UTC. Owner (31 Oct ~09:00 UTC): "how do you expect the wooden blocks to interlock in a
physical simulation without the slot?" Deliverables: `INTERLOCK.md` (design, owner-readable first page) and a dated
PREREG section F entry; commit + push to `claude/bold-albattani-6qmxsv`. Design only in this step. Build 1 owns
B2-B7 files; the placement slot (P workflow, `PLACEMENT.md`) runs in parallel: coordinate, do not duplicate.

## Log
- 09:10 read STATUS head, SPEC 0-16, PREREG A, B.7-B.15, E, F; P.md (placement slot started 08:45). No I.md existed.

## ORCHESTRATOR NOTE (31 Oct 08:47 UTC): the Embodiment session replied; read `build/embodiment-reply-20261031.md`
Use their proposed intrusion export fields (or state ours), their sim-copy layout (`DIR/<obj>/<obj>.glb + piece_*.obj`
for `make_assets.py --pieces`), jittered-mean judging, and add a minimum frame count + relative-motion check to the
carve rule.
- 08:50 (agent of wf_c7bae0ea-5c5; earlier entry times above are approximate) read work log 1460-1575, 3190-3200, 3705-3812, 4010-4065, 4436-4510, tail; ledger
  boards/XCarve rows and lessons; README 90-125, 285-350; SPEC 0-18; PREREG B.7-B.15, E, F; the Embodiment reply
  (`embodiment-reply-20261031.md`): use their export fields (frame, target, partner, pts_local, depth_m,
  pushed_residual_m), their sim-copy layout DIR/<obj>/<obj>.glb + piece_*.obj, jittered-mean judging, and add a
  minimum frame count + relative-motion test to the carve rule. Next: interaction-meshes design docs, the pipeline
  carve code, other sessions' branches, dev data probes.
- 08:58 probes (dev, GT-free; scratchpad `interlock/`): ep24 dev bundle (obs_all + our tracks) + B5 dev candidates.
  [M, dev] board 1 <- board 2: 56 of 79 contact frames enter board 1's HULL (f164-274), partner travel 118.6 mm,
  straightness 0.91, along board 1's width axis; entered region (>= 10 frames) sits at 0.53-0.58 of the long axis,
  12.5 mm wide (7.1 mm at >= 28 frames), spans the full width; its entry half spans 0.01-0.48 of the width (one edge to
  the middle). Board 2 <- board 1: same frames, travel 118.9 mm, straightness 0.92, entry half 0.49-1.05 (the other
  edge). 100 % of entered voxels are OBSERVED in the dev depth grid (stereo bridging and/or obs_all contamination):
  a naive "never carve observed-solid" rule would block every slot -> silhouette / bridging-prone clause needed.
  [M, dev] V2 does not catch it: HULL n_median 8 / 13 vs thresholds 39 / 65 (median over all 79 contact frames dilutes
  the 56 intrusion frames); board 2 shell is V5 flip-risk (amb 4.12 vs floor 2.34) -> HULL picked.
  [M, dev, generator outputs] SAM 3D boards (4 runs): slot centred at 0.50 of the long axis, from one edge to 0.42-0.48
  of the width, width 1.2-3.0 % of the long axis (narrower than a board: SAM gives side/length, motion gives width).
  Pixal3D-MV board 2 copied the partner board (a perpendicular plate: V2 (b) case).
- 09:02 pair probe (dev, `interlock/probe_pairs.py`, partner samples deeper than the V2 band b inside the candidate):
  ep24 b = 8.0 / 7.7 mm -> 0 deep samples in either board's shell or hull, although the partner passes through in 56
  frames: a sample inside a 10-20 mm plate is at most half the thickness deep, so any depth-below-surface test with
  b >= half thickness is blind to plate crossings -> the interlock check must be volume/through-crossing based.
  ep2 pot <- lid: HULL deep entry in 54 frames, travel 20.2 mm, straightness 0.61 (a seat, not an insertion), region
  1.6 cm3 OBSERVED, depth 6-7 mm (push-feasible); shells 0. ep11 cups: 0 at b = 8 mm (dev overstates separation).
- 09:04 design decisions: carve rule splits a region into R_U (FREE/UNKNOWN: mechanism-4 logic + persistence +
  topology guard, no motion needed) and R_O (OBSERVED: needs insertion sweep + push-infeasible + silhouette see-through
  or generator+motion agreement on a narrow gap + budget). Submitted mesh only via ICARVE candidates judged by S1
  (VI veto, VF flip guard, paired E exclusion) at tiers with two agreeing sources incl. an observational one; sim copy
  always. V5 clarification: HULL never counts as the non-flip-risk alternative (SPEC section 8 "fallback only").
  Writing INTERLOCK.md now.
- 09:15 INTERLOCK.md written (sections 0-15) and PREREG F-I1 appended (F-I1.1-F-I1.14). Probe code and outputs copied
  to `build/I/` (commands: `GMG_MODE=dev GMG_RUN=<scratch>/gmg/runs-dev/20261030-b5pool24-edba5b3 <scratch>/venv/bin/python
  build/I/probe_ep24.py` (and `probe_ep24b.py`); `probe_pairs.py <devrun> <ep>` for 20261030-b5pool11-edba5b3 11,
  20261030-b1ep2-a7d4d64 2, 20261030-b5pool24-edba5b3 24; `sam_slot.py` on the 29 Oct generator outputs; machine:
  this cloud container, 4 shared cores; code base de64bd3; dev tier, no scan). Rule changes during writing: carve rule
  reordered (O share > 25 % -> PUSH first), push test = median over the frames R is entered, R_O needs >= 75 % SIL/GAP
  and carves only those; GAP no longer needs (a) (stereo-solid narrow notch, silhouette absent, topology kept) but
  submitted candidates still need T2/T3; V4t conditional like V5. Next: commit + push.
