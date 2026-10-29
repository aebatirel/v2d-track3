**Sceptical review of the "How innovative is our Track 3 approach?" draft (2026-10-22)**

Labels: [M] measured in this repo, [L] verified literature or code, [G] guess. I opened every link below: arXiv abstracts through export.arxiv.org, and code from the local clones in `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/repos/` (SPIDER at commit 4471700, 2026-09-22; Do as I Do at commit 824591b, 2026-08-02).

## (a) Novelty claims that are overstated, understated or stale

1. **Overstated: the flat-base fix and the assist-off drop test are already in the closest released toolchains, under the same function name.** [L]
   - **SPIDER.** `add_flat_base=True` is the default. It appends a 3×3 cm support plate fixed to the object, under its lowest point at the first-frame recorded world pose (`flatten_base`).
     - https://github.com/facebookresearch/spider/blob/main/spider/preprocess/_decompose_common.py
     - https://github.com/facebookresearch/spider/blob/main/spider/preprocess/decompose_fast.py
   - **SPIDER's start check.** It holds the controls at the first reference frame for 3 s. The run fails if the object drifts more than 1 cm or 0.3 rad (`sanity_check_*` in `config.py`).
     - https://github.com/facebookresearch/spider/blob/main/spider/simulators/mjwp.py
   - **Do as I Do** (Sharpa hand, MuJoCo Warp) has `flatten_base` behind the `add_floor` flag.
     - https://github.com/malik-group/do-as-i-do/blob/main/retargeting/retargeting/pipeline/decompose_mesh.py
   - **NVIDIA mesh_to_usd** has the recorded-support mode and a drop test.
   - **The one real difference:** SPIDER's plate exists only in the collision pieces and sits inside the object's lower bounding box, so the visual (scored) mesh is unchanged. Ours edits the submitted mesh, which costs registered AUC and CD-O.

2. **Overstated: "the measured link between physical validity and the score of a policy built from video" is CRISP's headline result.** [L]
   - CRISP (ICLR 2026): noisy reconstructed geometry makes tracking-RL policies fail. Sim-ready planar primitives, plus geometry inferred from contact, cut the failure rate from 55.2 % to 6.9 %. https://arxiv.org/abs/2512.14696
   - HA-HOI states the same gap for hand-object references used in simulation. https://arxiv.org/abs/2605.14462
   - Ours is a replication in the dexterous, registered-ADD setting, on one episode with one seed.

3. **Overstated: the ep18 evidence is weaker than the draft presents it.** [M]
   - **The ablation is confounded.** kri (0.368) and kfi (0.715) differ in two things: the mesh (library_v2 → v3) and the settling mode (height-only → stable pose). See `docs/work-log.md`, 2026-10-22 08:00 entry. "The same setup with the rounded sweeper" is therefore inaccurate.
   - **Small sample.** One seed; one of the six rollouts scored 0.179.
   - **Static floor.** Leaving every object where it starts scores 0.637 on ep18 (`docs/forensics-2026-10-21.md` §0). So the fix mostly removed harm: it is +0.078 over doing nothing. On ep24 the best is 0.318 against a floor of 0.229.
   - **The gate predicts little.** The drop test flagged 3 of 4 references, but acting on the flag helped only ep18. ep12 fell by 0.05 (kr 0.740 vs k 0.790); ep24 was unchanged.

4. **Overstated: "collision check identical to the evaluator's" as something that is ours.** [M/L]
   - The code check holds: MjPen runs CPU MuJoCo collision on the same `mj_model` that Newton passes to MuJoCo Warp (`pipeline/contact_retarget.py`, `class MjPen`).
   - But retargeting against the target simulator's own collision is standard: mink's `CollisionAvoidanceLimit`, SPIDER, and Do as I Do (which targets Sharpa in MuJoCo Warp).
   - EgoCPT found that contact and pose refinement without force allocation did not beat plain retargeting (1/10 vs 2/10) https://arxiv.org/abs/2610.17572. That matches our flat 4-episode mean (0.577 → 0.587).
   - EgoCPT also already reports a sweep-dustpan task on Sharpa (54.5 %).
   - Keep MjPen as reproducibility engineering, not as a contribution.

5. **Overstated: the "cheap, licence-light stack" angle for Industry Innovation.**
   - **Cost.** About $2–2.5 per policy is the organisers' FlashCHORD recipe. CHORD reports about 2 h per policy on one L40S (`docs/research/track3-requirements.md`). It is not a saving we made.
   - **Licences.** FoundationPose and FoundationStereo are NVIDIA licences for research or evaluation only ("non-commercially"). They are the core of stages 1 and 3. https://github.com/NVlabs/FoundationPose/blob/main/LICENSE and https://github.com/NVlabs/FoundationStereo/blob/master/LICENSE [L]
   - The only licence-light choice is MediaPipe instead of MANO.

6. **Overstated: stage-8 novelty.** Three of its four ingredients have direct precedents, and one is already built.
   - **Support patches:** SPIDER's plate, mesh_to_usd recorded-support, CRISP's planar primitives, and REST3D's gravity-support scene tree https://arxiv.org/abs/2605.30338.
   - **Contact as constraints on occluded geometry:** CRISP rebuilds an occluded chair seat from body posture; Open-CHOIR https://arxiv.org/abs/2605.20992; AGILE (contact-aware, sim-ready hand-object reconstruction) https://arxiv.org/abs/2602.04672.
   - **Swept volumes:** already built. `recon_mesh` carves the hand capsules on every frame, as BundleSDF does with free space. Listing it again under stage 8 counts it twice.
   - **Non-overlap between objects in unseen regions:** ObjectSDF++'s object-distinction regulariser https://arxiv.org/abs/2308.07868; TSDF++, a multi-object TSDF that keeps surfaces occluded by nearby moving objects https://arxiv.org/abs/2105.07468.
   - **The only gap I found no direct precedent for:** at co-located frames (assembled or nested) of independently moving rigid objects across a whole video, assign the overlap to one object by evidence, to recover slots and cavities for simulator validity. It is a hypothesis and is not built.

7. **Stale: the spoon is not a coin-flip on its frame convention.**
   - The work log of 2026-10-21 notes that under the registered scorer the spoon's body-frame convention no longer matters, because the scorer aligns our mesh to the scan by ICP.
   - **The real risks:**
     - It is a thin, near-symmetric object. Our damaged-scan test shows such objects can register flipped.
     - `spoon/wooden_spoon.glb` is a parametric template, not a reconstruction from video. CD-O requires our own reconstructed meshes. If a person fits any parameter on eval frames, that runs into the no-hand-labelling rule.
   - The spoon is in 10 of 20 eval episodes and is the alignment anchor in episodes 32, 33 and 35–37.

8. **Understated.**
   - **Ground-truth-free harm detection.** `pipeline/qa.py` already computes `floor_vs_ref` and a "harmful" verdict without ground truth. Together with the validated sim_vs_ref proxy, this is a self-checking pipeline and our most defensible piece of methodology.
   - **A benchmark-design finding.** Registered scoring is very sensitive to mesh quality: 5 mm inflation drops AUC to 0.608 and flat objects register flipped. So leaderboard AUC partly measures how well a mesh registers. That is worth reporting to the organisers, and with our 8–15 mm walls it is also a larger score risk than the draft says.
   - **Eval composition** [G]. The eval set has 4/20 hard twins, 10/20 spoon episodes and 11/20 episodes with no public analogue; our validation set is 50 % hard. "Hard manipulation accounts for almost the whole gap" holds only on the validation set. On eval, fixing all four hard twins to 0.84 adds at most about 0.07 to the mean. The 16 unvalidated episodes decide whether we reach 0.84.

## (b) Directions that are unrealistic in 13 days or break the rules

9. **#8 (persistent room map) breaks this repo's own integrity rule as described.**
   - Note 18's map is registered to mocap with public ground truth: gravity tilted by the lean of resting objects in the ground truth, and the ground-truth table height of 0.6012 m (`docs/research/notes/18-room-map.md`, lines 94–108).
   - Using it at eval inference uses "anything derived from" ground truth, which CLAUDE.md forbids.
   - "About 2 mm" was agreement with bundle-adjusted poses on public held-out frames. It was never measured on eval clips.
   - Only a rebuild without ground truth would be admissible (stereo scale, table-plane gravity, the scorer's frame-0 alignment), and its gain is bounded because perception is already at 0.932. Drop it for this freeze.

10. **Generative completion was dismissed for the wrong reasons.**
    - **Licences:** TRELLIS.2 is MIT (https://github.com/microsoft/TRELLIS.2/blob/main/LICENSE); SAM 3D Objects is under the SAM License. Our own stack already depends on NVIDIA non-commercial models, so the licence argument would rule out our pipeline first.
    - **The Apache-2.0 rule** applies to the code we release. How non-Apache dependencies count is a question for the organisers; the professor package already raised it.
    - **Rules:** the FAQ allows pretrained models, and the organisers' own baseline reconstructs meshes with SAM 3D (Do as I Do does too). Run on the eval video, it is not a grey zone.
    - **The actual grey zone:** retrieving or fine-tuning on the public scans, or a person choosing outputs per eval episode.
    - The hallucination risk is real (tianny0078 used TSDF plus SAM 3D and scored 0.22, though that result is confounded). Reclassify it as feasible in 2–3 days if restricted to never-observed space (item 17).

11. **MANO "whose licence we do not have":** MANO is a free non-commercial registration, the same licence class as FoundationPose. It is an account action for the owner, not a blocker. It is still not worth doing in 13 days, but the reason is time, not licence.

12. **#1 (automatic standing faces) is needed for compliance as well as scale.**
    - Hand-picked `flatten_base` frames applied to eval-only objects or eval episodes would be human intervention on test records (Kaggle: no hand labelling).
    - The same applies to STATUS step 3 ("visual QA of the eval tracks, fix the worst") and to the owner checking spoon overlays on eval clips.
    - **Try the cheaper variant first:** a SPIDER-style support plate in the collision geometry only. It keeps the scored mesh, so the "registered AUC drops by more than 0.01" falsifier never triggers. Ask the organisers whether collision geometry may differ from the submitted mesh.
    - "+0.3 per episode" comes from one confounded episode; label it as an upper bound.

13. **#4 (physics-in-the-loop) is the riskiest item next to the 40–60-training prerequisite.**
    - It can be de-risked: MjPen already gets the exact FlashCHORD scene as a MuJoCo model (`env.solver.mj_model`). SPIDER's or Do as I Do's MuJoCo Warp sampler could run on the evaluator's own scene without porting to Newton.
    - Scope it to ep24 and its eval twin 25.
    - Its output must still become an RL reference, because scored trajectories must come from learned policies.

14. **#2, #3 and #7: realistic but limited for eval.**
    - **#2:** run the organisers' `v2d_bundlesdf` on our poses, depth and masks as the baseline before writing a new sparse TSDF. Stereo noise is about 1.5–3 mm at 0.5–0.7 m, so 1.5–2 mm voxels are optimistic.
    - **#3:** it helps one eval episode (25) plus the nested cups. It also needs relative pose error at the assembled frames below the slot width, while our hand–object relative error on hard episodes is 1–2 cm [M] (contact-retargeting note §6).
    - **#7:** it targets the pot and lid, but perception is not the binding constraint.
    - Defer all three behind #1, the first step of #2, and #5.

## (c) Directions the draft is missing

15. **A do-no-harm floor guard** (hours, no ground truth).
    - `auto_ep.sh` publishes the best attempt even when every attempt is "harmful".
    - The fallback candidates are already listed in the work log (2026-10-21) and STATUS step 6 but are absent from the draft: an earlier checkpoint, another seed, or a policy that keeps the hands away. Choose by sim_vs_ref against floor_vs_ref.
    - ep18's base policy scored 0.345 against a floor of 0.637 [M].
    - It must still be a learned FlashCHORD checkpoint. Falsified if, on public episodes, the guarded choice ever scores below the unguarded one.

16. **Reusing policies across twin episodes, or training one policy on many references.** This is FlashDexRetarget's core idea (https://arxiv.org/abs/2610.01849); the draft ports only its reward.
    - 9 of 20 eval episodes have a public analogue (for example 25↔24, 19/30↔18, 20↔21).
    - Warm-start eval policies from their public twins. FlashCHORD supports resume, though `validate_resume_reference_config` may need a patch so it loads weights only.
    - Public-only test: ep23↔ep24 (both Planter_Stand), warm start vs from scratch at equal steps, 2 seeds × 6 evaluations. Falsified if the gain is ≤ 0.03.
    - It also fits the "reuse across episodes" Innovation pitch.

17. **A generative prior used only where we saw nothing.**
    - Complete unseen undersides, edges and cavities with SAM 3D or TRELLIS.2 from colour-camera crops. Accept geometry only in never-observed voxels, never against our free-space carving.
    - This targets exactly the defect class we diagnosed.
    - Falsified if registered AUC on ep39, ep21, ep11 and ep31 does not beat library_v2 by more than 0.01, or if the sweeper and boards still fail the drop test.

18. **The learning side of the hard twins.**
    - The overnight report calls ep24 learning-limited, yet only the reward has been changed. The assist fades out by 123M of 250M steps.
    - Test 500M steps, a slower assist decay, and a backward curriculum from the stand-up window (Gen2Dex, https://arxiv.org/abs/2610.24392). About $8 per A/B.
    - Falsified if ep24 stays at or below 0.33.

19. **A different embodiment** (the FAQ allows it). The primitive-collision hand gave +0.03 on ep18 and −0.015 on ep24 [M]. A Dexmate+Sharpa config exists. A gripper is untested and its rule status is uncertain. Mention it and deprioritise it.

## Corrected verdict

The built system rates about 1.5–2 out of 5. It is a careful, well-measured integration, but even its "measured adaptations" have precedents in released code:
- the flat base and start-stability check are in SPIDER and Do as I Do, both targeting the same Sharpa hand;
- the simulator-collision retargeting is in mink, SPIDER and Do as I Do;
- the occluder-aware carving is in BundleSDF and TSDF++.

The diagnosis that physically invalid reconstructed geometry, not perception, makes a tracking policy fail with the assist off is a replication of CRISP's finding in the dexterous, registered-ADD setting. It rests on one confounded episode with one seed, and mostly removed harm: +0.08 above the do-nothing floor on ep18. What is defensibly ours is benchmark-specific evidence:
- registered scoring is very sensitive to mesh quality;
- a self-check without ground truth (sim_vs_ref plus floor_vs_ref plus the drop test), validated against the true score and with its noise measured;
- the engineering.

The Industry Innovation case is weaker than drafted: the per-policy cost is the organisers' recipe, and the core models are NVIDIA non-commercial. Stage 8 can become a "new combination" only in its narrow multi-object form (overlap at co-located frames, assigned by evidence, to recover slots and cavities), and even that needs CRISP, ObjectSDF++, SPIDER and REST3D cited as the closest prior. For the score, the largest risks are not novelty but:
- 16 eval episodes we have never validated, including 10 with the spoon;
- the prerequisite run of 40–60 eval trainings;
- compliance fixes: drop the map registered to ground truth, stop manual per-episode patches and visual fixes on eval clips, and settle the spoon template and the A-lite provenance with the organisers.

The cheapest high-value additions are the floor guard (15), a collision-only support plate or an automatic flat base (12), warm starts from twin episodes (16), and the reward plus training-budget test on ep24 (18).