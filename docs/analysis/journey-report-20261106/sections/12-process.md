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

**Spending detail from the chat sessions** (the agents' statements or ledger lines; they fill gaps in the table above and overlap with it):

- **20-21 Oct.** The first smoke test cost $0.01 and the first failed real box $0.29. By 18:15 on 20 Oct $3.97 of $25 was spent; the day ended at about $22.80. The hard-episode test of 21 Oct cost about $16.60 and the store cleanup $0.25, so about $39.60 had been spent by 21 Oct 10:35, with $10.35 left. Credit read $18.39 before the 13:35 relaunch on 21 Oct and $2.69 at 20:04; after a top-up it stood at $52.69 and fell to $7.55 by 22 Oct 03:55 (the agent's figures), over 12 boxes and 15 trainings. Three boxes on 22-23 Oct cost $13.40.
- **23-24 Oct.** The public check (five runs on four episodes) cost about $3.90 and left $5.15 (23 Oct 19:20). The overnight batch cost $12.72 and left $4.08; the owner topped up $10 at 09:47 on 24 Oct (credit $14.08). A standard-recipe episode costs about 1.8 h at 250M steps; the new spoon recipe about $0.80-1.10 per episode [E].
- **29-30 Oct.** The shared ledger started 29 Oct 21:32 with a $100 line (a $60 hard cap for that night). Credit was $3.51 at 21:07, $16.17 at 04:47 on 30 Oct and $41.17 after the owner's top-up at 04:51. The builder's own spend was about $21.28 at 04:52, about $28 at 08:01 and about $36 at 12:05 against a $45 session cap; the ledger at 10:09 read $35.48 spent and $14.20 planned. A video machine stuck on Hugging Face rate limits burned about $4.30 over 3 h 20 min of downloads. At 14:28 the ledger read $51.78 spent and $17.50 committed of $100.
- **Credit trail from the coordinator chat:** $69.22 (31 Oct 21:20), $35.80 (1 Nov 01:47), $23.67 (08:54), $122.85 after a top-up (1 Nov 19:34), $127.97 after a second top-up (2 Nov 20:13), $101.05 (23:16), $82.96 (3 Nov 03:17), $75.62 (05:57), about $59 (11:38). The perfect-following lane started with $110 (cut to $102 to keep a $10 reserve); the perception and GRASP lanes got $8 together for cheap Vast CPUs.

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

- **Duplicate launches.** On 25 Oct the owner's go-ahead reached two chats; one launched 9 boxes, the other 6 duplicates (destroyed in setup). A batch-ownership rule was proposed and not adopted. On 31 Oct the opposite happened for uploads: the builder's upload of pack 9a was refused by the permission check (16:36) while the score-status session, with the owner's word, uploaded 9a+ at 18:13 and told the builder not to upload too. The lesson recorded was one upload channel per pack with a note in the chat of who uploads; from 1 Nov the coordinator was the single uploader. On 29 Oct three sessions drew on one budget, which led to the shared ledger with planned and actual lines.
- **Crossed messages.** The registration lane's draft said "I've emailed" while the email was a draft; the embodiment lane re-listed checks it had already sent; two sessions worked on ep13 at once; a room-map "camera guard" was requested and then stopped; the perfect-following lane gave the tracking session two wrong store paths.
- **Relayed approvals.** The permission guard rejected owner approvals relayed between sessions (31 Oct 16:40; 1 Nov 08:35 and 11:25; 2 Nov 01:15, 08:58, 19:15), so uploads waited for the owner's own words until "Upload 13b, you dont need my permission to upload anymore" (2 Nov 19:20).
- **Context limits.** The coordinator ran out of context twice (continuation summaries on 1 Nov 02:39 and 2 Nov 14:55); the owner said on 1 Nov: "all of the sessions are getting super crowded and context is getting out of hand".
- **Usage limits.** A weekly limit on 29 Oct 21:00 UTC stopped a 6-agent stage with 0 results; 5-hour limits hit on 30-31 Oct (windows seen: 22 Oct 10:19-10:50 in the early session; 29 Oct 23:51 to about 00:25 and again to about 04:45; 30 Oct 10:23-10:30 and 15:13 to about 17:00); the robustness review stopped at 18:30 UTC on 26 Oct with 4 of 9 agents done and idled about 8.8 h until the owner typed "Continue".

### 12.4 Integrity

- **No ground truth in inference.** Mocap and scans were read only for scoring and diagnostics; `tools/no_oracle.py` guarded the pack, H5 and submit scripts from 30 Oct. Eval choices used only GT-free measures.
- **GT-informed mesh selections were disclosed and owner-approved:** the C0 blue cup (selector written after public scoring, "For blue cup I give you mey yes"), Tier B / B+ ("Okay I give you permission for all"), G2, G3 and rack round R. They use public scans to pick among GT-free candidates; the builder session flagged that this conflicts with the inference rule unless read as a choice of public assets. Every upload description states it.
- **Earlier provenance problems** were found and disclosed: libraries v1-v4 were fused along tracks templated on the public scans and were put on a deny-list, yet 7 of 11 objects in the early packs were still v1 files (26 Oct ledger); pack 9a used scan-derived marker constants (16 of 163 constants scan-derived, 71 of unknown origin); the October room map was registered with ground-truth constants and was dropped; a detector setting was raised by agents who knew the scan catalogue. The organiser question on mesh provenance was drafted and never sent.
- **No tuning on leaderboard results** with one disclosed exception: the pack-6 revert of the eval-20 pitcher was an owner decision informed by the pack-5 board result. Post-hoc thresholds and coin-flip variants were refused as eval probing. The spoon grasp rules were developed on eval episodes 3 and 35 using GT-free sim_vs_ref; public confirmation was asked for and never done.
- **Disclosed training settings:** the eval-10 policy trained at njmax 1024 and scored at stock limits; the eval-15 clause-c waiver; the kp 400 wrist used in spoon work (owner confirmation not recorded).
- **Registration and rules:** a late-registration email was drafted on 31 Oct (the form had closed); the repository was public from about 11:02 UTC on 31 Oct (a scan found no leaked keys) and had to be shared with the organisers' GitHub account (rule 9.a). An API key once pasted into chat was treated as exposed. The method's working name was kept out of reports from 2 Nov (owner request).

### 12.5 The report incident

On 3 Nov at 12:07 the owner asked for this long report ("I dont want you to miss anything ... this info is very valuable"). The first attempt was cut off: the worker restarted twice (12:49 and 13:01) and the account hit its Claude usage limit. On 6 Nov the owner renewed it and asked for a cheaper way ("We ran out of credits and just renewed, dont destroy all the credits again"). This report was then built from digests of all sources, with the coverage gaps listed in section 14.

### 12.6 Mistakes, corrections and crossed messages (from the chat sessions)

Most of these were small and were corrected in the chat; they are listed because they show where the process leaked.

- **Early session (20-24 Oct).** An earlier message wrongly said a launcher fix had been pushed (20 Oct; the agent admitted it). The first end-to-end score (AUC 0.009, 61 cm) came from a floor fit, and two trainings of about three hours ran on a broken scene. A box was destroyed after its hold expired with its upload unconfirmed (23 Oct 14:31). Box A nearly chose a checkpoint from stale scores (24 Oct 10:55). The 0.584 search number was a warm-start artefact. The agent's 20-eval estimate (0.74-0.77) was well above the first board score (0.575). The choice rule "use both recipes per eval" was contested until the owner ruled on 25 Oct.
- **Builder (26-31 Oct).** The first carry plan priced about 55 GPU-hours before a CPU/physics-replay step that was cheaper; the owner's prompt corrected it. A ledger helper erased lines. A first estimate of +0.003 for the eval 33 swap was corrected to +0.0003 once it was clear that the leaderboard scores the submitted trajectory. Four frames of eval-3 depth were viewed before the depth audit's bar was set, so eval 3 was excluded from the spoon test (disclosed 30 Oct 07:39). An independent review of `audit_ref.py` found six bugs, including one that made the lowest object always read 0 cm.
- **Coordinator (30 Oct - 3 Nov).**
  - Also corrected in the chat and described in section 4 or 5.7: the overlap claim of 1 Nov, the smoother cross-check, the video labels, the clock offset and the 3 Nov cost misquote ($400-900 revised to $40-70).
  - Pack 9b (1 Nov 05:02): a +0.0001 expected swap lost 0.0008; the swap threshold became 0.02.
  - Eval 1 retrain (2 Nov 20:25): reported as running but it had stopped during setup (about $0.10); the slot went to eval 14 and a correction was posted.
  - Setup bugs (2 Nov 20:45, 21:29): retrain boxes for evals 20, 28 and 30 started without a needed folder, and eval 14's test silently ran with old meshes; about $6.50 lost.
  - Ep27 (3 Nov 09:59): an earlier message said the tracker failed the ep27 pot lift; that error belonged to the failed pot-network lane.
  - Crossed messages (2 Nov): the spoon-anchor test was stopped at 20:09 (a coin flip and a probe of the hidden set), but at 20:15 the perfect-following lane had a spoon-test box ready to launch if it did not hear back, and the coordinator's "don't launch" crossed with that plan.
  - Approval routing (1 Nov 11:17) and approval date (1 Nov 11:46): see section 4 and 7.4. The permission check also blocked Kaggle uploads for pack 10 (1 Nov 08:19), pack 12 (2 Nov 01:06), pack 12d (2 Nov 08:55) and pack 13b (2 Nov 19:03); each time the coordinator reported it, did not retry, and waited for the owner's direct word. From 19:07 on 2 Nov the owner said no further permission was needed, and each pack was still checked.
  - Rank claims: rank sums were recomputed at each check (58, then 54 tied with DSAIL for 9th/10th, 47, 46, 45) but positions were not always re-verified against live boards.
  - Open question: on 2 Nov 14:56 the coordinator asked whether to stop a report-only perception box (saving about $2.70-3.50). No answer appears in the transcript.
  - Name: the owner gave the algorithm a codename, which the coordinator wrote into STATUS; on 2 Nov 07:11 the owner asked that it be removed from the report and the current entries. Older commit messages still carry it. It is not reproduced here.
- **Projection record:** most next-rank estimates were close (pack 10 estimated +0.002 against +0.0016 measured; CD-O estimates within 0.0007 cm); the larger misses were the first board result (0.74-0.77 expected, 0.575 scored) and the Tier B pose-board gain that was not predicted at all.
