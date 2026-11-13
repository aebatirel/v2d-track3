# The winner's "follow the reference" recipe: CPU part (13 Nov 2026)

Owner: "sure" (build the CPU part, then ask for the GPU batch).
Recipe from the winner's slides: (1) metric-aligned reward + reward centring; (2) a physically consistent reference
(at rest level on the support, delayed release); (3) best of many official runs.

## 1. Reward: built and CPU-tested
- Centroid keypoints, σ 3 cm: `FC_FDR_OBJ_MODE=centroid FC_FDR_OBJ_SIGMA=0.03` (`tests/test_fdr_centroid.py`).
- Reward centring: `FC_RC=1` with the absorbing-state termination correction (`tests/test_reward_centering.py`).
  - The optimal policy is unchanged by construction.
  - Expected benefit low [H]: FlashSAC scales returns by the lifetime maximum.
- The GPU test is `docs/research/work/reward-ab-20261113/` (arms c and cr vs test A's control).

## 2a. "At rest, level on its support": already in production; extra levelling fails
- Our production references (variant `mck`) have used `contact_retarget.py --rest_settle 1` since 22 Oct: objects
  seated on the table and turned onto their nearest stable pose.
  - It fixed the start on ep12 and ep27.
  - With the flattened sweeper it took ep18 0.345 → 0.715 (work log 22 Oct).
- Extra levelling = refine S1 + S3 + S5 on the 20 public control tracks (CPU; pre-registered safety rule):
  - mean reference ΔAUC −0.0146, worst −0.059 (pitcher eps 21 / 22), 15/20 worse;
  - SP/MP-SR unchanged;
  - **FAILS** (needs ≥ −0.005 and no episode < −0.02). Not adopted.

## 2b. "Delayed release": tool built; automatic use not reliable
- `tools/release_fix.py` runs a drop test per placement release:
  - the scene is reset explicitly at the release, VOC 0, zero action;
  - the object's drift from its reference rest pose is measured;
  - the releasing hand is held longer (D frames, then a blend) until the drop test passes.
- **Results** (`testA_refs_ep*.json`, `glock_physS1_ep*.json` here):
  - Old 20 Oct references (test A, no rest settling):
    - lid on the open table: stable (0.33 cm), so the test works on an easy case;
    - cup into rack: 14 cm; dust pan: 17 cm; pot: 2.5 cm.
    - Delays rarely fix these: the rest pose itself is not physical.
  - Grasp-lock references (physS1, kp 400):
    - pot flung 126 cm;
    - cup 5.4 cm, and longer holds make it worse (28–33 cm);
    - ep18 releases stable (1.1–1.7 cm).
  - [I] A cold reset in the middle of a designed wrap grasp creates contact impulses, so the drop test mixes "reset
    pop" with "unstable release". Not reliable enough to edit references automatically.
- **Proven so far:** only the hand-picked hold-to-end (`tools/hold_freeze.py`, eval 16: 10 official draws 0.850 →
  0.974). A reliable automatic version needs the drop test to start from a settled state, e.g. a replay of the trained
  policy up to the release. That is future work.

## 3. Best of many official runs
No new code is needed (`ops/jobs/h5_reeval.sh`, `tools/choose_learner.py`). It applies at packing time.
