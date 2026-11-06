## 10. Noise, standard deviations and how we decided

### 10.1 Measured spreads

**Draw-to-draw spread of one checkpoint** (eval episodes, sim_vs_ref; 10 fresh draws unless stated):

| Eval | Before fix: mean +/- sd | After fix: mean +/- sd | What fixed it |
|---|---|---|---|
| 1 | 0.822 +/- 0.239 (H5) | 0.9241 +/- 0.017 (20 draws, min 0.884) | carved pot/lid collision |
| 14 | 0.6152 +/- 0.1989 (H5) | 0.875 (fails 1/10) -> 0.933 (14p) | guard bridge, then Tier B collision |
| 30 | 0.7984 +/- 0.2552 (H5) | - | not fixed (sweeper inside the rack mesh) |
| 33 | 0.854 +/- 0.137 (H5) | 0.934 +/- 0.008 | curriculum scale 0.4 (arm B) |
| 25 | 0.850 +/- 0.099 | - | five runs 0.802, 0.815, 0.797, 0.811, 0.335 (one in five fails) |
| 16 / 3 / 32 | sd 0.077 / 0.072 / 0.068 | - | - |
| 10 | 0.450 +/- 0.007 | 0.9034 at stock (njmax-1024 training) | contact overflow fix |
| 20 | 0.8933 (packed) | 0.9259 +/- 0.018 | lift-window retrain |

**Public spreads** [D]:

| Measurement | Spread |
|---|---|
| eight repeat evaluations of one ep18 policy | mean 0.332, sd 0.08, range 0.131-0.410 |
| contact retargeting, 6 evaluations | ep12 base 0.725 +/- 0.067 -> 0.790 +/- 0.023 |
| two seeds on hard twins | differ by 0.04-0.10 |
| one re-run of a recipe cell | moved by up to 0.07 AUC |
| ep2 masses, two seeds x 10 draws | 0.559 +/- 0.349, 0.648 +/- 0.358, 0.813 +/- 0.307 |
| perception run-to-run | mean absolute change 0.0012 per episode; holdout noise 0.0015 |
| CD-O eval-seed spread | about +/- 0.002 cm |
| registration seeds, library pitcher | 0.667-0.833 over 30 seeds |
| zero-action replay | a 2 mm control change moved the result as much as a centre-of-mass change (+0.109 / -0.005 / -0.116 / +0.151) |

**Board-level noise and luck** [M/E]:

- H5 (29 Oct): packed draws 0.9164 vs a 10-draw mean of 0.8755; packed-rank sums 69 and 80 vs 40 expected (z about 3.2). Pack 4 had about +0.027 of draw luck. A re-run of pack 6 would have scored about 0.78 [E].
- Per-swap board noise bound: about +/- 0.008 AUC (corrected from +/- 0.0025).
- Transfer from proxy to board: 74-78 % (pack 4: +0.0216 vs +0.0285 predicted).

**Host effects** [M]: box draws vs fresh draws on another host: eval 14 lift 0.923 -> 0.826 (-0.097); eval 30 0.938 -> 0.768 (-0.170). One faulty host ran at 14.4k env steps/s instead of about 50k. The evaluator-gap test did not reproduce the gap. A clean-evaluator vs training-box check on 24 Oct matched within 0.04 (eval 35 0.949 vs 0.9915); packing was then done on the same GPU type used for training.

**Bootstrap intervals** [D]: physics stack F1P1 +0.00298, 95 % CI +0.0008 to +0.0059; depth audit AUROC 0.600, CI 0.40-0.78; GRASP test B +0.024, CI -0.071 to +0.115; mass transfer ep2 +0.157 (SE 0.105).

### 10.2 Decision rules and why each came in

| Rule (date) | What it says | Why it was introduced |
|---|---|---|
| Static-floor sanity check (20 Oct) | compare every score to "nothing moves" | the floor-fit bug gave AUC 0.009 |
| Learned policies only (22 Oct) | no zero-action or hand-made trajectories | rules; zero action beat training in 15 of 64 results |
| Pre-registration (from 24 Oct) | gate, falsifier and analysis committed before results; amendments labelled "post hoc" | a plain re-proposal failed no-regression while a gated one passed; avoid choosing rules after seeing scores |
| One change per A/B (23 Oct) | three simultaneous changes were stopped | confounded results |
| 5-evaluation mean for checkpoint choice; no cherry-picking (25 Oct) | owner: "we cannot pick and choose" | eval 25's five runs ranged 0.335-0.815 |
| sha256 check on packed rollouts (26 Oct) | empty folder, checksum, byte diff before upload | the pack-3 `cp -n` bug (about -0.005) |
| Two twins or a reference-free argument for mesh swaps (26 Oct) | single-twin swaps forbidden | lathe pitcher +0.098 on its twin, -0.0045 on the board |
| No best-of-N draw packed (29 Oct, rule d) | the packed draw must be a fresh draw of the chosen checkpoint | draw luck, z about 3.2 |
| Leak guard `no_oracle.py` (30 Oct) | the pack refuses non-stock or GT-touched inputs; exceptions by owner word only | integrity; the njmax-1024 checkpoint got one sha-specific exception (1 Nov 11:32) |
| Swap rule a/b/c/s (1 Nov) | 10 fresh draws vs packed; gain at least +0.02 on both references; no more fails; median RPE not worse | 9b: a +0.0018 proxy gain became -0.0008 |
| D1 no-flip veto (2 Nov) | 0 flips at the eval seed and at least 6 seeds, in raw and budget reference modes | the Tier B board-2 flip; an earlier "no flip" sign-off was wrong |
| Mesh rules A / B / C (2 Nov) | A: CD-O -0.020 with flip rate W30 at most +0.05; B: W30 -0.20 with CD-O at most +0.005; C (G2 only): ADD -2 mm with CD-O at most +0.005 | make GT-informed best-of-N selection auditable; SHA freeze before any scan read |
| Leave-one-episode-out pose CV with 10 seeds (2 Nov) | pose meshes chosen by held-out public pose gains | scan-CD-O choices hurt pose boards (G3 pot ADD 6.8 vs 2.7 mm) |
| Two-host confirmation (3 Nov) | a swap must pass on fresh draws on a second host | box-to-fresh drops of 0.10-0.17 |
| Mesh entry rule (3 Nov) | new collision shapes only where zero-shot is within 0.02 of control | 6 of 7 mesh retrains failed |
| Source-episode exclusion (3 Nov) | a generated mesh's source episode is excluded from its held-out score | 14p1 and pitcher #29 leakage |
| Skip uploads under board noise (1 Nov) | do not upload when the expected change is below about +/- 0.008 | "When the expected gain is within noise, a swap is a coin flip on the board" |
| Training-step extension gate (25 Oct) | extend only if 3+ evaluations, last two means each up by over 0.03, lift at least 50 %; then +50 % once | low starts are structural: 22 curves below 0.5 gained a median +0.04 by 250M |

Two cautions recorded in the sources: a near-miss under a strict gate is still a fail (physics, -0.00002), and post-hoc thresholds or best-per-board coin-flip variants were refused as eval-set probing. Two rules were bent with explicit owner approval and disclosure: the eval 15 clause-c waiver (median RPE 0.47 mm worse) and the hand-aware lane's gate addendum before holdout scoring (recorded, but should be checked against the original text).
