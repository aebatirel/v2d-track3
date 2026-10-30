# Context and decisions from the owner's conversations

The remote agent cannot see the original chat. This file records the owner's goals, preferences and decisions, and
the answers that matter for future work. Dates are 2026.

## Who and what
- The owner (Ahmet Ercan Batirel, GitHub `aebatirel`) is entering **NVIDIA V2D Challenge Track 3** with a team of
  **4+ people**. Goals: **leaderboard placement** and the **Industry Innovation award**. They write in English and
  Turkish and prefer plain-language explanations, often visual.
- A professor, Arda İnceoğlu, reviewed the research. His feedback:
  - Stereo, the provided CAD scans and the mocap markers are dataset-specific and "slightly cheating-leaning". That is
    a scalability concern, which matters for the Innovation award but not for the leaderboard rules.
  - Try models on Colab first.
  - A $1,000–1,500 budget is reasonable.
- The owner's rules for the work:
  - "If it helps with leaderboard anything goes", within the official rules.
  - "Infer and try to figure it out yourself; dig deep where you see treasure."
  - The owner rents GPUs and handles Discord, email, registration and Kaggle.

## Decisions so far
- **Approach:** a perception-first pipeline. Stereo depth + scan-based detection + FoundationPose tracking + visual
  odometry produce object trajectories. MediaPipe hands on the colour camera feed NVIDIA's own retargeter, which
  produces the FlashCHORD reference. Then FlashCHORD training per episode, the official evaluator and the kit packer.
  Background is in `docs/research/notes/10-synthesis.md`, `16-synthesis-round3.md` and `21-synthesis-round4.md`.
  The owner approved it. If it falls short, exhaust the improvements within this pipeline before changing its
  architecture.
- **Compute:**
  - Colab Pro (G4 = RTX PRO 6000) was used for bring-up. It is not persistent and needs a browser, so the main work
    moves to Vast.ai over SSH.
  - The owner set **no spending cap**. They want the agent to rent through the Vast API only while work runs and to
    destroy machines right after: per-second billing, self-destruct at job end, a stall watchdog instead of a fixed
    time limit (never cut a job that is still progressing), and an idle rule.
  - Announce each rental batch with its expected cost before starting it.
  - The first Vast API key was pasted in chat and must be considered exposed. The owner is replacing it and will
    store the new key as a secret (`VAST_API_KEY`), never in the repo.
- **Compute strategy (2026-10-20):**
  - Use **many RTX PRO 6000s in parallel** for batches: same total cost, results in hours instead of days.
  - Use **interruptible machines** for training once checkpoint resume is verified.
  - On the first box, **test two trainings on one 96 GB GPU**.
  - Do not buy faster GPU types: H100/H200/B200 are estimated at no faster for this simulator and cost 2–7× more.
  - **Vast.ai only.** The owner dropped the Google Cloud and Colab options: "no need, you can yolo in Vast.ai".
    Rental batches are still announced with their expected cost first.
- **GPU choice:** RTX PRO 6000 96 GB is the default. 48 GB cards (PRO 5000, 6000 Ada, L40S) work but save little per
  finished policy and leave only ~7 GB of headroom. Interruptible PRO 6000s are the main saving, once checkpoint
  resume is verified. See `docs/gpu-rental/`.
- **Remote work:** the owner will continue with a Claude Code cloud session on this repo. The agent's SSH key on the
  owner's Mac is not in the repo; a cloud agent makes its own key and the owner adds it to Vast.
- **Spoon:** the agent decides the spoon's frame convention itself, from evidence. The owner is available to check
  overlays visually ("I can tell you whether something is working visually"), so send them images when that helps.
  Asking the organisers is no longer the plan.
- **Submission repo:** not decided. The owner may send a cleaned copy rather than this repo; there is no rule for it.
- **Repository rules review (2026-10-20):** the owner reviewed every rule on a review page and chose Keep, Change or
  Remove for each (https://claude.ai/artifact/H8Rp47MHz8kvwe5MKkzw6L).
  - Removed: the clean-room rule (moot: SlamDunk is not in this repo and a cloud session cannot see it), the
    "owner does account actions" rule, the
    ask-before-downloading rule, the Google Cloud plan and the Colab plan.
  - Changed: no fixed time limit on machines; small results and final policies may be committed; spoon frame decided
    by the agent; submission repo undecided.
  - The agent still cannot create accounts, sign in, enter payment details or accept terms, so those stay with the
    owner in practice.
- **Overnight 2026-10-21 → 22 (owner, 01:00 TRT):** topped up $50 (credit $52.69): "you can go crazy, I trust you and
  go to sleep". Mandate: redo the four validation episodes (ep12, ep27 good; ep18, ep24 bad) with contact-anchored
  retargeting, test as much as possible, see what works or not, fix it, and have a reliable setup by morning.
  Budget = the credit; agent's own rule: no box starts unless the credit covers its estimated cost + $3.
- **2026-10-25 (owner, ~03:30 TRT):** "fix the lower scores properly, do whatever it takes, aim for 4th place"
  (board #4 = 0.752 then; us 0.575). Then, asked about a second learner: **"use both"**: the standard FDR RL learner
  is trained next to the grasp lock on the eval episodes below GATE 0.9, and the GT-free choice rule
  (`tools/choose_learner.py`, mean sim_vs_ref over the official repeats) keeps one per episode. This lifts the 24 Oct
  "one recipe" restriction for those episodes. Every other rule stays (public validation first, no tuning on eval).
- **Shared artefacts** (private unless the owner shares them):
  - Explained Colab notebook: https://colab.research.google.com/drive/1rSlDlcC91UggWeCsDS0H8KFrp_C6ygX5
  - Visual explainer page: https://claude.ai/artifact/GJegn8ZZHnb7PFDTnCDpgd
  - Professor document: https://claude.ai/artifact/695886c2-1684-40b0-b3df-f501d9787706. Its package is in
    `docs/professor-package/`.

## Answers the owner already received (keep consistent)
- **Can the perception AUC (0.809) be posted to Kaggle?** No.
  - It is measured on public episodes, while the leaderboard scores 20 hidden eval episodes.
  - Track 3 rows must be official-evaluator rollouts of trained policies, carrying evaluator and checkpoint digests
    and a commit URL.
- **What 0.809 means.** It is a ceiling, not a forecast.
  - The robot stage adds error.
  - Eval episodes have the spoon in 10 of 20, and the pot lid.
  - Doing nothing already scores 0.446.
  - Estimates: tracking on eval 0.72–0.81; first submission 0.60–0.75; after fixes 0.75–0.85. All are guesses until
    the first public end-to-end test.
- **How to raise 0.809.** Fix the failures first:
  - render-and-compare detection check;
  - marker-based spin for symmetric objects;
  - camera drift, via the room map or loop closure;
  - track recovery;
  - rest snap.

  Spoon tracking matters most for the leaderboard.
- **The simulation:** two floating Sharpa hands (22 finger joints each), scanned objects as rigid bodies (0.3 kg
  placeholder mass), a support table and gravity. Physics runs at 100 Hz and the policy at 20 Hz. Training uses
  4,096 worlds with an assist force. The official evaluator uses 1 world with no assist, so the hands must really
  grip the objects.
- **Hardware:** a friend's RTX 5090 laptop (24 GB) is fine for perception and the evaluator, but too small and too
  slow for the 20 trainings.

## Open items
- The owner asked whether hand-overs, flips, twirls and sliding were researched. A dedicated research round on those
  manipulation risks was offered but not run.
- Registration, accepting the Kaggle rules and sharing a repo with the organisers' GitHub account are still open.

- 2026-10-27: the owner manages the leaderboard-freeze deadline; agents should not trade quality for the date or raise
  it as a planning constraint.
- 2026-10-30 ~12:20 UTC: the owner gave a standing spending go-ahead for the mesh work: "you can spend money and go
  ahead in all". Agents no longer wait for approval before each rental batch. They still state the plan and its
  expected cost in the work log before renting, use the shared Vast spend ledger, make every machine self-destroy, and
  log the actual cost and results afterwards.
