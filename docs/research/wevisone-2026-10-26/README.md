# WeVisOne-VL for our object detection? (2026-10-26)

The owner asked: "check out WeVisOne-VL and see whether it makes sense to implement it for object detection".

How this was produced:
- workflow `wf_de751fdc-d81`:
  - primary sources of the model;
  - the 2025–26 alternatives;
  - a verdict.
- The investigation of our own detector failed to return structured output, so the verdict agent read the repo
  itself.
- Its claims about our pipeline were then checked by three skeptics (workflow `wf_5af07702-6da`). All decision-relevant
  claims held; the corrections are listed below.
- Raw outputs: `workflow-result.json` and `verification.json`.

Labels:
- **[A]** the authors' own number, not reproduced;
- **[M]** measured in this project;
- **[E]** estimate.

## Verdict: test first, do not build it in yet

- **What it is.** A Tencent model released on 22 Oct 2026 (arXiv 2610.31329; GitHub Tencent/WeVisOne-VL; HF
  tencent/WeVisOne-VL-2B and -4B). It is Qwen3-VL fine-tuned for:
  - text-prompted detection;
  - referring grounding;
  - "not present" answers;
  - pointing and counting;
  - masks and alpha mattes from a 9.6M-parameter pixel decoder.
- **Licence is clean.** Code and weights are Apache-2.0, not gated, with no territorial or use limits. The only third
  party is Qwen3-VL, also Apache-2.0.
- **Better than the helper we use now** [A]. Our frame-0 rule uses Grounding DINO tiny on colour camera a as a 0.2
  vote. The paper benchmarks exactly that model against WeVisOne-VL-4B:

  | Benchmark | WeVisOne-VL-4B | Grounding DINO-T |
  |---|---|---|
  | LVIS mean F1 | 55.3 | 38.8 |
  | RefCOCOg referring | 80.8 | 45.9 |
  | Rejection of absent targets (RefCOCOg-Rej) | 67.4 % | 0 % |
  | COCO | 57.1 | 56.6 |
- **It cannot fix our hardest cases:**
  - it cannot tell the two near-identical boards apart;
  - there is no evidence on grayscale mono frames, and it converts inputs to RGB;
  - it takes no reference-image (exemplar) prompt, only text in one image, so it cannot match our specific object or
    our renders;
  - it outputs no confidence scores, so our G = IoU × score / best and the re-proposal threshold (0.25 × best) would
    need a new rule.
- **Little room left in detection** [M]:
  - the shipped rule gets 97 of 116 labelled public instances right (CPU replay of the dumps, work log 25 Oct 00:28
    UTC);
  - the remaining frame-0 misses are ep23's two boards and ep2's pot mask spilling onto the lid (inferred from the log);
  - the five spoon-anchored eval frame-0s showed no gross error (visual check).
- **Detection is no longer the main loss** [E]. Most of the gap is policies not following our reference (0.088–0.117
  depending on the pack) and hidden-phase tracking (0.063 estimated for the spoon episodes).
- **Too new to trust blind.** It is four days old with no independent reproduction. The headline rejection rate
  (96.4 %) comes from an in-house benchmark.

## Where it could help
- **Pot and lid.** Grounding DINO gave one box for "white pot" and "white pot lid" (ep0, 23 Oct). Public ep2's pot
  mask spills onto the lid. On eval 1, frame 0 gave the pot to its handle and the lid to the whole pot; the tracker
  recovered, and the hidden loss is unmeasured.
- **Fewer wrong grounding votes.** In on-table variant 1, Grounding DINO pulled the ep18 sweeper onto the dust pan.
  WeVisOne can answer "not there".
- **Better recall for re-proposals of partly hidden objects** (eval 30's sweeper in the rack came from Grounding
  DINO's third box). This needs a new rule because it gives no scores.

## Where it would not help
- The twin boards (eval 25 is handled by `pipeline/identity_fix.py` and geometry).
- Mono frames.
- The spoon's roll.
- Policy losses.
- The mesh defects (open pot base, pitcher).

## Pre-registered test (if approved)
1. **Pre-register.** Write the rule and commit it before any output exists ($0). New tool `tools/wevis_boxes.py`
   writes, from camera-a frames and roster names only, the `tools/det_replay.py --g` grounding format:
   `{"jobs": {"ep<N>_f<k>": {"det": {name: {"boxes": [...], "scores": [1.0, ...]}}}}}`.
2. **Inputs.** The 80 dumped public frames (20 episodes × frame 0 + 3 quarter points, store
   `runs/20261024-reprop-88822b2`). Labels: 116 instances (`tools/det_score.py`; ep0 and ep26 excluded by the 2 cm
   rule).
3. **Arms.** Only the grounding source changes; no weights are re-tuned:
   - A: 4B, all names in one call;
   - B: 4B, one call per name;
   - C: 2B, one call per name;
   - D: union of B with Grounding DINO.
4. **Validity check.** Replaying with the existing Grounding DINO JSON must reproduce 97/116, or the test is invalid.
5. **Pass rule** (fixed now): at least 99/116 with **zero** of the 97 lost, and median latency at most 10 s per frame.
   The +2 margin is there because these 116 instances already selected the current rule. Otherwise record the
   negative result and stop.
6. **If an arm passes.** Add it behind a flag. Replay on the 20 eval frame-0 dumps only to list the choices that
   change. The owner approves reruns of those episodes (≈ $3–5 each).
- **Cost** [E]:
  - one GPU box under 1 h, ≈ $1–1.5 (ceiling $3);
  - downloads 19.3 GB (4B is stored as F32) plus 4.9 GB (2B);
  - its own venv (pinned transformers 5.12.1, torch 2.11.0);
  - a $0 CPU route for 2B (≈ 9.8 GB RAM, slow) needs the owner's permission, because the sandbox blocks third-party
    model code.

## Corrections from verification
- The grounding term projects our mono SAM2 proposals into camera a and takes the IoU there. Boxes are not mapped to
  the mono frame (only re-proposal boxes are). The term is switched off for an object if any gated proposal lies
  < 80 % inside camera a.
- The dump run holds 80 public frames plus 20 eval frame-0s ("100 dumps").
- The 97/116 is from a CPU replay that reproduced the shipped choices on 95 of 100 frames, not from a full pipeline
  rerun.
- OWLv2 on mono frames failed on ep0, 2, 18 and 21 and swapped the ep11 cups, but worked on ep12 and ep13
  (13 Oct).
- Loss figures:
  - policy loss is 0.117 in the forensics (sim_vs_ref units) and 0.088 in the pack-4 robustness review;
  - the 0.063 spoon figure is a share of the hidden loss, likely from hidden-phase tracking and depth, not
    specifically frame-0 roll.

## Alternatives
From the survey; the numbers were not re-verified.
- **SAM 3** (text and exemplar prompts, whole-object masks) ranked first for category confusions. It uses Meta's
  custom SAM licence and gated weights, and our token already lacks the SAM 3D gate.
- **For the twins,** geometry (slots, marker layout, multi-frame agreement) rather than any detector.
