# V2D Challenge Track 3 — research package

Prepared by Ahmet Ercan Batırel, October 2026. Every page links back here; notes link to each other in reading order.

## Start here

- [00 — Research summary and proposed direction](00-summary.md) — the short version (about 10 minutes).
- [Challenge requirements and logistics](track3-requirements.md) — data, rules, compute, costs.

Latest syntheses, in order: [10](notes/10-synthesis.md) → [16](notes/16-synthesis-round3.md) (corrects parts of 10) → [21](notes/21-synthesis-round4.md) (current architecture).

## Round 1 — baseline, error budget, literature

- [01 — NVIDIA V2D baseline dissection (Track 3)](notes/01-baseline-dissection.md)
- [02 — Track 3 error budget (public mocap + official scorer)](notes/02-error-budget.md)
- [03 — Perception literature / open-source survey for V2D Track 3](notes/03-lit-perception.md)
- [04 — Literature: transfer half (noisy HOI reconstruction -> simulated dexterous policy)](notes/04-lit-transfer.md)
- [05 — Alternative architectures for V2D Track 3 (beyond "baseline + better parts")](notes/05-alternatives.md)

## Round 2 — correctness audits and architecture panels

- [06 — Track 3 timing and row-alignment audit (FlashCHORD Sharpa policy to kit packer)](notes/06-timing-audit.md)
- [07 — Track 3 scan-frame convention and the unscanned wooden spoon](notes/07-mesh-frame-convention.md)
- [08 — Track 3 candidate architectures: maximum-accuracy lens (design + adversarial review)](notes/08-architectures-accuracy.md)
- [09 — Resourceful + innovation architectures for V2D Track 3 (design + adversarial review)](notes/09-architectures-resourceful.md)
- [10 — V2D Track 3: research synthesis, candidate architectures and plan (2026-10-04)](notes/10-synthesis.md)

## Round 3 — deep dives

- [11 — Placement priors, room memory and the mocap-world link (DIG 11, final)](notes/11-placement-priors.md)
- [12 — Spin observability of near-symmetric objects (cups, lid, pot, pitcher)](notes/12-symmetry-observability.md)
- [13 — The wooden spoon: appearance, frame-sign rules, reconstruction, roll decision](notes/13-spoon.md)
- [14 — Policy tracking error (e_track) of FlashCHORD Sharpa and its training budget](notes/14-policy-tracking-error.md)
- [15 — Eval video survey: risks and design needs for the 20 eval episodes (agent 15) — COMPLETE (2026-10-06)](notes/15-eval-video-survey.md)
- [16 — Round-3 addendum: corrections, AUC re-ranking, next digs (2026-10-06)](notes/16-synthesis-round3.md)

## Round 4 — enablers and architecture v3

- [17 — Marker tracking feasibility (DIG 17)](notes/17-marker-tracking.md)
- [18 — Persistent room map registered to mocap (DIG 18)](notes/18-room-map.md)
- [19 — Collision hulls: can the CoACD inflation be removed on the asset side? (2026-10-06/07; stages A-C done, final)](notes/19-collision-hulls.md)
- [20 — camera sync, spoon frame, first-contact detector](notes/20-sync-spoon-contact.md)
- [21 — Round-4 synthesis: architecture v3 (2026-10-07)](notes/21-synthesis-round4.md)

## Conventions

- Claims are tagged [V] verified, [E] estimate, [H] hypothesis. Later syntheses supersede earlier notes where they disagree (see 16 §1).
- Paths such as `/Users/aebatirel/...` or `work/NN/` refer to analysis scripts and outputs on our machine; the small analysis scripts for notes 02 and 07 are in [scripts/](scripts/).
- Ground truth from public episodes was used only for analysis and scoring, never as inference input.
