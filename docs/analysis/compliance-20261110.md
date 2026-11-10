# Track 3 compliance check against the organisers' Discord rulings (10 Nov 2026)

Source: the Track 3 channel of the challenge Discord (NVIDIA Omniverse server), pasted in full by the owner on 10 Nov.
Our submission list: Kaggle API, `v2d-challenge-track3-auc`, 26 submissions, all status `complete` (none invalidated
as of 10 Nov 08:30 UTC). Labels: [F] fact from a source, [M] measured, [E] estimate.

## Rulings that apply to us [F]
| # | Date | Ruling (Mrinal Verghese unless noted) |
|---|---|---|
| 12 | 20 Oct | The 5-submissions-per-week limit is a calendar week, Sunday to Saturday, Pacific time. |
| 13 | 20 Oct | "We only consider one final submission." |
| 17, 19 | 21 Oct | Do not use the public GT meshes; reconstruct every object. Public meshes are for development only; "the final pipeline shouldn't depend on the public meshes". Submissions are checked. |
| 25 | 22 Oct | Do not use public videos for reconstruction; "your final submission should not depend on the public data directly". Several eval videos of the same object may be combined (declare it). |
| 29 | 22 Oct | Camera intrinsics from the public split are the one allowed exception. |
| 38 | 26 Oct | Checks run during the challenge; flagged submissions are invalidated and teams notified; disqualification only after repeat offences. |
| 39 | 26 Oct | Per-sequence manual intervention should be avoided; agentic intervention is fine. Physics values within an order of magnitude of reasonable are fine; clearly unrealistic ones are flagged. |
| 43 | 28 Oct | Submissions beyond 5 per week are flagged and invalidated; repeated abuse can bring warnings and disqualification. |
| 44 | 28 Oct | The verification container must reproduce the results "starting from the track 3 inputs, and have no dependency on the public data". |
| 47 | 3 Nov (April) | Third-party non-commercial code is fine for awards; released code must be Apache 2.0. |
| 50 | 5 Nov | Clear abuse was warned and invalidated; good-faith cases with no significant advantage were not punished. |

## Where we stand
### 1. Weekly submission limit: exceeded by 2 in one week; the counted files are inside the unlimited final days [M]
**Correction (10 Nov, after the owner's note "last 4 days were unlimited"):** the kit's written policy
(`config/tracks.json`) is "five (5) Submissions per week, with unlimited Submissions during the final three (3) days of
the Competition Period" (freeze 4 Nov 2026, 5:00 p.m. EST = 22:00 UTC). The first version of this section ignored that
window and overstated the problem.

Kaggle timestamps converted to Pacific time (PDT until 1 Nov 02:00, then PST):
| Week (Sun-Sat, Pacific) | Our submissions | Outside the final-days window | Over the limit |
|---|---|---|---|
| 18-24 Oct | 2 | 2 | 0 |
| 25-31 Oct | 7 | 7 | **2** (6th 9a+, 31 Oct 18:13 UTC; 7th 9b, 1 Nov 04:58 UTC = 31 Oct PDT) |
| 1-7 Nov | 17 | 2 or 3 (10 and 11, plus 12b at 2 Nov 06:37 UTC if the window starts at midnight Pacific) | 0 |

- The final-days window starts on 1 Nov 22:00 UTC (72 h before the freeze) or at midnight of 2 Nov (EST: 05:00 UTC;
  Pacific: 08:00 UTC). Under every reading, 12c onwards (2 Nov 08:38 UTC), including both counted files 14p and 13j,
  fall inside it.
- So the only excess is 2 uploads in the week of 25-31 Oct (packs 9a+ and 9b). Neither is a counted best file.
  The limit was known (`docs/research/track3-requirements.md`, 4 Oct; work log 30 Oct: "already above the written weekly
  figure; Kaggle did not block them").
- Ruling 50 (5 Nov): good-faith cases without significant advantage were not punished. No warning has reached us.
- The strict-counting estimate in the first version (AUC 0.847, CD-O 0.290) is withdrawn: it assumed no final-days window.

### 2. Dependence on public data: present in the submitted pipeline [F, from our own records]
- **What is not the problem:** every submitted mesh is our own reconstruction or generation; no public scan was ever submitted as a mesh (the case the organisers check for in ruling 32). Under the FAQ text we worked from ("submit their own reconstructed meshes") we were compliant. The Discord rulings of 21-28 Oct, which we did not see during the challenge, set a stricter bar: no public videos as reconstruction input and no dependency on public data in the final pipeline.
- **What is the problem: the inputs and the selection.** Our meshes were built from public-episode data, and the eval-built alternatives (E0, E0b) were not adopted because they were less accurate:
- Tracking templates: eval references were tracked with `library_v3` meshes, fused from public-episode videos (and, for
  libraries v1-v4, along scan-templated tracks; disclosed 26 Oct).
- Submitted meshes: the C0 kit-of-parts meshes and later ones "come from public episodes like library_v3"
  (mesh lane, 27 Oct); the generated meshes (G2, G3, round R) were generated from public-episode images (e.g. the 13j rack
  `hy21 ep12`: Hunyuan3D-2.1 on public episode 12); Tier B, Tier B+, G2, G3 and round R choices were selected by Chamfer distance to the public scans
  (GT-informed, owner-approved, stated in every upload description); 13p chose meshes by public pose CV.
- Development uses (detection rules, gates, public-twin tests) are allowed by ruling 19.
- So, as built, the verification container could not reproduce our counted files "from the track 3 inputs" with "no
  dependency on the public data" (ruling 44). Rebuilding without public data would give different files and scores.

### 3. One final submission [F]
Ruling 13 says one final submission is considered. Our plan counted two files (14p for the five pose boards, 13j for
CD-O). The container guide's fallback (best per board) applies only if no Final Submission is selected. Unresolved.

### 4. Other items [F]
- Physics and embodiment: stiffer floating-wrist servo (kp 400), contact buffer njmax 1024 in training only for
  eval 10, masses at the kit default 0.3 kg: within ruling 39 as read; declare them.
- Manual intervention: decisions were agentic, with a few per-episode owner decisions (pack 6 pitcher revert informed by
  the board; eval 15 clause-c waiver; blue-cup mesh approval). Declare them.
- Licence: the repository has no LICENSE file; released code must be Apache 2.0 (ruling 47). Owner decision.

## Options for the owner
1. Disclose all of the above in the technical report and in the reply thread with the organisers (recommended: it is
   all recorded in this repository, which they will read).
2. Ask the organisers which file they count and whether the entry stays on the leaderboard.
3. If pursuing the award, only a rebuilt pipeline without public data could pass the container check, and its results
   would not match the counted files. This is unlikely to be worth it.
