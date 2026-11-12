# 28 — Gemini Decisions API: where it could sit in our pipeline (2026-11-12)

Status: IDEAS ONLY. Nothing was called or run; we have no Gemini API key in this environment. Every claim about what
the model would do on our data is a hypothesis until the tests in §5 measure it.

Owner's question: look into the Gemini Decisions API and ideate how to implement it into the workflow. It follows the
earlier question on replacing the LLM in weight-space repair with "decision models" (note 27); §6 answers that with
this product in mind.

Labels: [V] read in the primary text, [C] computed here, [E] estimate, [H] hypothesis.

Sources read on 2026-11-12:
- Announcement, 11 Nov 2026: https://blog.google/innovation-and-ai/technology/developers-tools/gemini-decisions-api/
- Docs: https://aistudio.google.com/docs/decisions-api, plus the model, pricing, rate-limit and media-resolution pages
  under https://aistudio.google.com/docs/

## 1. What it is [V]

- A new endpoint (`POST /v1beta/decisions`, model `gemini-decision-1`) that answers closed questions only.
- One shared input: text, images, audio, video or PDF, up to 262,144 tokens.
- 1 to 1,000 independent questions about that input, of three types:
  - yes/no: a probability from 0.01 to 0.99;
  - choice: one of 2–255 options, with a probability for every option;
  - score: an ordered rubric of 2–255 levels, with an expected score and per-level probabilities.
- Every answer carries a confidence from 0 to 1. Google calls the probabilities calibrated.
- It generates no text. So it gives no explanation, no number, no coordinate, no code and no multi-step reasoning.
  Questions cannot see each other. Question text is text only; images go in the shared input.
- Speed and price: 150–250 ms per request; $0.10 per 1M input tokens; output is free. An image costs 280 / 560 /
  1,120 / 2,240 tokens at low / medium / high / ultra-high resolution; a video frame 70 (280 at high).
- No batch mode and no caching. Paid tier 1 allows 1,500 requests per minute and 50,000 per day.
- Free tier data is used to improve Google's products; paid tier data is not.
- Google's own benchmarks: best or near best on 9 routing, ranking and multimodal tests; top-1 calibration error
  0.025 on 7 of them; Video-MME 69.1%. None of them tests centimetre-level geometry.
- The docs say to set thresholds from labelled examples of your own data.

## 2. What that means for us

It can be an **automatic visual judge**: we show it frames, crops and our own renders, and it answers fixed questions
with a probability. It cannot produce poses, meshes, references or policies.

That matches a real gap. Our ground-truth-free checks are geometric and several are weak or dataset-specific:
- the depth audit was falsified (AUROC 0.600; it cannot see our typical 2–3 cm errors);
- the mesh selector is weak (Spearman 0.46; it picked the best mesh on 2 of 10 objects);
- the board identity rule relies on mocap marker knobs (`pipeline/identity_fix.py`);
- MANO contact labels time a hold 24 frames early to 22 late and end it 26–116 frames after placement
  (`pipeline/object_events.py`);
- a human looking at eval overlays is not allowed to choose anything (work log, 23 Oct VLM review).

A frozen automatic judge, with thresholds set on public episodes only, is the same kind of gate as `pipeline/qa.py`.

## 3. Ideas, ranked

| # | Where | Call design | What it replaces or adds | Public test and bar |
|---|---|---|---|---|
| 1 | Track audit | one cropped overlay from `track_overlay.py` per object-frame; score rubric: aligned / slightly off / clearly off / wrong object | the falsified depth audit | same labels and rule as the depth audit: informative at AUROC ≥ 0.75, falsified below 0.65 |
| 2 | Mesh selection | real crops plus same-pose renders of one candidate; score rubric for shape match; rank candidates by expected score | the Spearman-0.46 selector | the 104 scored meshes: Spearman above 0.46 and the best mesh picked on more than 2 of 10 objects |
| 3 | Frame-0 detection | frame with numbered SAM2 proposals; one choice question per object, with an "other" option and written criteria (spoon vs pot handle) | step 5 of the VLM plan (a local Qwen3-VL selector) | `tools/det_replay.py` grid and rule: no public regression, then most hits |
| 4 | Identity and 180° flips | real crop next to render A (as tracked) and render B (swapped or flipped); two-option choice | the marker-knob rule | synthetic swaps and flips on public episodes; accuracy against the known answer |
| 5 | Contact timeline | labelled frames; yes/no per frame: "is the hand holding the <object> off the table?" | a cross-check on hold phases and release timing | timing error against mocap-derived lift-off and settle, compared with the 24/22/26–116 frame errors above |
| 6 | Rollout vs video | key frames of the source video beside the rendered rollout; rubric: same object held, same place reached | a check against the video itself; every current check compares our output with our own reference | public twins: does it flag the episodes the official score marks bad? |

Smaller ideas, not ranked: a grip-type prior for `pipeline/grip_types.py` (choice over the portfolio's types); log
triage for the stall watchdog (the rule-based watchdog already does this).

**Why idea 2 may work where geometry failed [H].** The geometric metric cannot see the unobserved side of an object.
A missing wall passed the gate. A model that knows what a pot looks like can judge a render of the unseen side.

**Why idea 1 is uncertain [H].** Half of our bad frames are 2–3 cm off. The model may catch lost tracks, wrong
objects and flips but miss those. The test decides.

## 4. Constraints

- **Our integrity rules.** Inputs are video frames and our own renders only, never ground truth. Thresholds are set
  on public episodes and frozen; eval episodes only get the frozen gate. Rules are pre-registered as usual.
- **Competition rules. Open.** Our docs record no rule on a hosted proprietary model inside the pipeline. Check the
  kit rules or ask the organisers before any gate affects a submission.
- **Reproducibility.** The model is hosted, in beta (`v1beta`), and can change. Store every request and answer in
  the run folder.
- **Data.** Use the paid tier. Check the dataset licence allows sending frames to a third party.
- **Access.** Needs a Gemini API key from the owner, stored as an environment secret.
- **Calibration.** Google's calibration numbers are on its own benchmarks. Ours must be measured.

## 5. Proposed first test (not started; needs the owner's go-ahead)

Two offline tests on public data we already have, CPU plus API:
- **A, mesh selector (idea 2):** 104 meshes × about 8 images ≈ 0.9M tokens ≈ $0.09 [C].
- **B, track audit (idea 1):** 7,835 object-frames × about 1,300 tokens ≈ 10M tokens ≈ $1 [C].

Bars are in the table. Both rules would be written to the work log before any answer is scored. If both fail, the
product has no place in the pipeline and ideas 3–6 are dropped unless a new reason appears.

## 6. In the weight-space repair loop of note 27

This product is a ready-made version of note 27's design B selector, with no training. It could do two of the LLM's
four jobs [H]:
- label each failed rollout (choice: never touches, closes on nothing, hovers short, hovers over the goal, enters the
  zone), from key frames or a clip;
- pick the fix family from the library (choice with written criteria), and gate keep-or-drop decisions.

It cannot write weights or invent a new fix, because it produces no text. So the split stays: library and tuner for
the numbers, this model for routing, a full LLM only for new structures.
