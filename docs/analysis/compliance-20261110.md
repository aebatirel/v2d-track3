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
### 1. Weekly submission limit: exceeded in two weeks [M]
Kaggle timestamps converted to Pacific time (PDT until 1 Nov 02:00, then PST):
| Week (Sun-Sat, Pacific) | Our submissions | Limit | Over by | Packs |
|---|---|---|---|---|
| 18-24 Oct | 2 | 5 | 0 | 1, 2 (25 Oct 00:58 UTC = 24 Oct PDT) |
| 25-31 Oct | 7 | 5 | 2 | 3, 4, 5, 6, 7, 9a+, 9b (1 Nov 04:58 UTC = 31 Oct PDT) |
| 1-7 Nov | 17 | 5 | 12 | 10, 11, 12b, 12c, 12d, 13, 13b, 12e, 13e, 13f, 13f1, 13p, 13p2, 14p, 13h, 13i, 13j |

- The limit was known: `docs/research/track3-requirements.md` (4 Oct) records "5 submissions/week per track and tier" from
  the FAQ. Kaggle itself allowed 25 per day, so nothing blocked the uploads. The competitor note of 9 Nov mentioned the
  limit only in passing; this is the correction.
- Our counted files are far past the fifth of their week: 14p is the 14th and 13j the 17th upload of the week of 1 Nov.
- If only the first five per week counted [E]: best AUC 0.84738 (12c) instead of 0.88571; best CD-O 0.29029 (12d)
  instead of 0.23856; 12c's other boards RPE 3.01 cm, MPPE 2.47 cm, SP-SR 0.85, MP-SR 0.75.
- No invalidation or warning has reached us. Ruling 50 says good-faith cases without significant advantage were not
  punished; whether our case counts as that is the organisers' decision.

### 2. Dependence on public data: present in the submitted pipeline [F, from our own records]
- Tracking templates: eval references were tracked with `library_v3` meshes, fused from public-episode videos (and, for
  libraries v1-v4, along scan-templated tracks; disclosed 26 Oct).
- Submitted meshes: the C0 kit-of-parts meshes and later ones "come from public episodes like library_v3"
  (mesh lane, 27 Oct); Tier B, Tier B+, G2, G3 and round R choices were selected by Chamfer distance to the public scans
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
