## 12. Process, cost and infrastructure

### 12.1 GPU spending

All rentals were on Vast.ai (RTX PRO 6000 by default at $1.07-1.76/h; an H200 NVL at $3.90-4.03/h for mesh generation; an RTX 4090 at $0.556/h for the pot network). The pre-campaign estimate (18 Oct) was $110 ($80-155) [E]. Measured or ledger figures:

| Period | Spend | Kind |
|---|---|---|
| 20 Oct (first boxes) | about $22.78 of $25 | [M] credit change |
| 21-22 Oct (overnight A/Bs, 13 boxes) | $49.76 of a $50 top-up | [M] |
| 24 Oct (pack 1 batch) | about $24-30 | [M] chat |
| 25 Oct (pack 3 batch, 13 boxes) | $54.6 | [M] credit $101.82 -> $47.20 |
| 26 Oct (packs 4-6) | about $10.5 + $13 | [M] chat |
| 29 Oct - 1 Nov 09:00 | shared ledger $200.12 against a $325 budget (from $93.21 on 31 Oct 10:50) | [M] ledger |
| night 31 Oct - 1 Nov | about $56 | [E] |
| 2 Nov day (lift batch about $28, tracking lane about $26) | about $54 | [E] from lane totals |
| night 2-3 Nov | about $45 (credit $127.97 -> $82.96), including about $6.5 lost to job bugs or replaced boxes | [M] credit change |
| 3 Nov (G3 $7.47, rack R $5.95, pf-mesh2 about $11, pot network about $0.8) | about $25 | [M]/[E] |

Credit history: the first $25 of credit was nearly used on 20 Oct ($22.78); top-ups on 21 Oct took credit to $27.19; then $50 (22 Oct, "go crazy, I trust you"), $10 and $50 (24 Oct), $100 (25 Oct), $100 (29 Oct), $100 (31 Oct, "lean"), a top-up to $122.85 (1 Nov) and one to $127.97 (2 Nov). Credit was $75.62 on 3 Nov 06:40. **No source gives a project total.** The rows above overlap in places; depending on whether the 1 Nov ledger already includes the October batches, they add up to roughly $330-500 of GPU spend over 20 Oct - 3 Nov [E]. For comparison, the professor had called $1,000-1,500 reasonable. Kaggle uploads cost $0, and from 9a+ on, mesh packs were built on CPU at $0.

Unit costs [M]: an eval box with 3 episodes $3-6; the standard learner about $5.5 per episode for 2 seeds (3.5-4.5 h per box); grasp lock 2 seeds $3.2-4; a pack build $0.5-1.5; a full 20-episode rerun with packing about $50.

**AI assistant usage cost.** The chat sessions report a cumulative list-price cost per session (not a bill): main early session $1,371, builder session $1,289, mesh lane $2,219 (usage $2,249), embodiment lane $349, perfect-following lane $105, perception-accuracy lane $86, others $2-27. These are [M] list-price estimates from the session records and dwarf the GPU spend.

### 12.2 Vast setup and the money-losing bugs

The runbook (20 Oct): boxes clone the repo, download the dataset and weights, write only to the private HF store, never push to git, and destroy themselves at the end. Checkpoints come every 10,000,384 steps (about 3.7 min, not 5M as first documented). A stall watchdog destroys a box after about 30 minutes without progress. The rules forbid fixed time limits.

Bugs and incidents that cost money or results [M]:

- pack-3 `cp -n` into an old folder shipped seed-42 rollouts for 4 evals (about -0.005 AUC [E]); fixed with empty-folder packing and sha checks;
- `vast.sh` defaulted to an old commit ($0.03); a three-pattern `hf download` fetched nothing ($0.45); a stalled download box ($1.30); duplicate batches ($0.90 and about $1-2); preempted interruptible boxes ($0.40; $2.80 on 2 Nov);
- watchdog push vs final push race under `set -e` (two runs lost their final upload; the interim push had saved results);
- `.gitignore` excluded `.npz`, so a GPU job died in 2 minutes; stale asset roots silently ran an old-mesh draw (its "0.931" was invalid); a host at 14.4k instead of about 50k steps/s ($1.45);
- `hard_ab.sh` copied references before the target existed (all variants failed); bare `wait` deadlocks; `pgrep -f` matched its own shell; a ledger helper erased lines; STEPS not a multiple of 4096; missing `pandas`, `rtree`, `fast_simplification` on images; pinocchio and flash_attn version mismatches.

### 12.3 How the multi-session work ran

From 25 Oct the work was split across many parallel cloud sessions on separate branches (20 branches in total): a main GPU/packing session, the builder and pack sessions, a robustness review, a mesh lane, physics and embodiment lanes, perception lanes (tracking, room map, point tracks, hand-aware, pose network), a score-status session, a registration lane, and from 30 Oct a coordinator session that analysed the advisor meetings and relayed work between sessions. One session (keen-heisenberg) became the single uploader.

What worked: one uploader with byte diffs and receipts; pre-registration files on the branches; adversarial verifiers; CPU-first tests ($0) before GPU.

What failed:

- **Duplicate launches.** On 25 Oct the owner's go-ahead reached two chats; one launched 9 boxes, the other 6 duplicates (destroyed in setup). A batch-ownership rule was proposed and not adopted.
- **Crossed messages.** The registration lane's draft said "I've emailed" while the email was a draft; the embodiment lane re-listed checks it had already sent; two sessions worked on ep13 at once; a room-map "camera guard" was requested and then stopped; the perfect-following lane gave the tracking session two wrong store paths.
- **Relayed approvals.** The permission guard rejected owner approvals relayed between sessions (31 Oct 16:40; 1 Nov 08:35 and 11:25; 2 Nov 01:15, 08:58, 19:15), so uploads waited for the owner's own words until "Upload 13b, you dont need my permission to upload anymore" (2 Nov 19:20).
- **Context limits.** The coordinator ran out of context twice (continuation summaries on 1 Nov 02:39 and 2 Nov 14:55); the owner said on 1 Nov: "all of the sessions are getting super crowded and context is getting out of hand".
- **Usage limits.** A weekly limit on 29 Oct 21:00 UTC stopped a 6-agent stage with 0 results; 5-hour limits hit on 30-31 Oct; the robustness review stopped at 18:30 UTC on 26 Oct with 4 of 9 agents done and idled about 8.8 h until the owner typed "Continue".

### 12.4 Integrity

- **No ground truth in inference.** Mocap and scans were read only for scoring and diagnostics; `tools/no_oracle.py` guarded the pack, H5 and submit scripts from 30 Oct. Eval choices used only GT-free measures.
- **GT-informed mesh selections were disclosed and owner-approved:** the C0 blue cup (selector written after public scoring, "For blue cup I give you mey yes"), Tier B / B+ ("Okay I give you permission for all"), G2, G3 and rack round R. They use public scans to pick among GT-free candidates; the builder session flagged that this conflicts with the inference rule unless read as a choice of public assets. Every upload description states it.
- **Earlier provenance problems** were found and disclosed: libraries v1-v4 were fused along tracks templated on the public scans and were put on a deny-list, yet 7 of 11 objects in the early packs were still v1 files (26 Oct ledger); pack 9a used scan-derived marker constants (16 of 163 constants scan-derived, 71 of unknown origin); the October room map was registered with ground-truth constants and was dropped; a detector setting was raised by agents who knew the scan catalogue. The organiser question on mesh provenance was drafted and never sent.
- **No tuning on leaderboard results** with one disclosed exception: the pack-6 revert of the eval-20 pitcher was an owner decision informed by the pack-5 board result. Post-hoc thresholds and coin-flip variants were refused as eval probing. The spoon grasp rules were developed on eval episodes 3 and 35 using GT-free sim_vs_ref; public confirmation was asked for and never done.
- **Disclosed training settings:** the eval-10 policy trained at njmax 1024 and scored at stock limits; the eval-15 clause-c waiver; the kp 400 wrist used in spoon work (owner confirmation not recorded).
- **Registration and rules:** a late-registration email was drafted on 31 Oct (the form had closed); the repository was public from about 11:02 UTC on 31 Oct (a scan found no leaked keys) and had to be shared with the organisers' GitHub account (rule 9.a). An API key once pasted into chat was treated as exposed. The method's working name was kept out of reports from 2 Nov (owner request).

### 12.5 The report incident

On 3 Nov at 12:07 the owner asked for this long report ("I dont want you to miss anything ... this info is very valuable"). The first attempt was cut off: the worker restarted twice (12:49 and 13:01) and the account hit its Claude usage limit. On 6 Nov the owner renewed it and asked for a cheaper way ("We ran out of credits and just renewed, dont destroy all the credits again"). This report was then built from digests of all sources, with the coverage gaps listed in section 14.
