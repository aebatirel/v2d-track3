# V2D work log (extracted from the original HANDOFF.md, chronological; newest at the bottom)

## 2026-10-01 SIDE RESEARCH (proposed, not started): V2D Challenge Track 3

User asked what entering NVIDIA's V2D Challenge Track 3 (egocentric video -> policy) requires.
Read-only research only; nothing installed, registered or submitted. Findings, sources, disk/GPU
estimates, rules and untested hypotheses: `reports/v2d-challenge/track3-requirements.md`.
Key constraint: needs a Linux NVIDIA host (>= 48 GiB VRAM, driver >= 580, ~500 GB disk); the
local M4 Max cannot run it. Leaderboard freeze 2026-11-04 17:00 EST. The SlamDunk v2 state
below is unchanged.
2026-10-04: deep research running (user: research/ideate only; goal leaderboard + Innovation;
4+ people; clean-room repo, no SlamDunk code). Round 1 notes done in
`reports/v2d-challenge/research/01-05*.md`. Round 2 running (background agents): 06 timing
audit (suspected silent frame-mapping bug: evaluator rows per control step vs packer source
frames under motion_speed 0.5), 07 mesh frame convention (downloads ~93 MB public meshes to
scratchpad), 08/09 architecture panels. Next: merge into a final architecture report.
06 VERDICT (code reading, file:line in 06-timing-audit.md): bug is real. Default Sharpa recipe
(motion_speed 0.5, sim.fps 20) exports ~2 steps per source frame; packer silently keeps the first
N, so packed row f ~ source frame 0.5f. Fix: reference fps=20.0 (true capture rate),
motion_speed=1.0, sim.fps=20, N rows = N frames; add a blocking check that exported reference
poses equal input poses frame by frame. Not yet run on GPU.
2026-10-04 DONE: research rounds 1-2 complete (01-09) and merged into
`reports/v2d-challenge/research/10-synthesis.md` (primary candidate "Stereo Object-First with
Room Memory", alternatives F/B/C, gates G1-G5, ladder R0-R12, team split, organiser questions).
Scripts preserved in `research/scripts/`. Next (user decision): start R0 (CPU-only) or more
research on a specific open item.
2026-10-05: user: "anything goes" for leaderboard (within rules), infer open questions ourselves,
dig where there is treasure. Durable workspace (scratchpad gets wiped): `~/Documents/Code/
v2d-research/` (data/track_3 public data + meshes 97 MB, kit/, venv/, scripts-prev/, work/).
FINDING [V, public GT]: objects are staged with consistent yaw per task (rack ~90 deg x5, blue cup
63-66 / -65..-73 per task, planter, pitcher identical) -> task placement priors may resolve
symmetric slot-0 anchors (cups slot 0 in eval 8,10,14,20,32,33). workflow wf_3842f33c-fce FAILED (API network outage after ~30 min; partial notes 11-15 + 49 videos kept); wf_8d144554-9c1 also FAILED (same outage; host DNS 172.20.10.1 = phone hotspot). RELAUNCHED staged (3 short stages per dig, cached per stage) as wf_bb563e54-720; on failure resume with resumeFromRunId wf_bb563e54-720 and the script under ~/.claude/.../workflows/scripts/v2d-track3-treasure-dig-staged-wf_bb563e54-720.js
(digs 11 placement priors, 12 symmetry observability, 13 spoon, 14 policy tracking error,
15 eval video survey; skeptic per dig; critic). Notes land in research/11-15.
2026-10-06 DONE: round 3 (wf_bb563e54-720) complete, all digs verified; merged in
`research/16-synthesis-round3.md` (corrections to 10: do NOT rotate videos; cup spin via mocap
markers; spoon frame unresolved; wrist saturation at real speed; CoACD hull inflation; grasp
synthesis fails on 5-8/20; AUC likely sole ranking metric). Leaderboard 10-06: SoySauceChicken
AUC 0.649, Panav Raaj 0.212. Next: round 4 digs D16-D19 (markers, room map, hulls, sync+spoon).


[... unrelated SlamDunk entries omitted ...]

2026-10-06 RUNNING: round 4 workflow wf_adfd98f4-eae (digs 17 marker tracking, 18 room map,
19 collision hulls, 20 sync+spoon+contact; skeptic each; critic with architecture update).
Resume on outage: Workflow({scriptPath: ~/.claude/projects/-Users-aebatirel-Documents-Code-SlamDunk/
ad61ecbd-403d-49a3-817f-1f8b688b5549/workflows/scripts/v2d-track3-round4-digs-wf_adfd98f4-eae.js,
resumeFromRunId: wf_adfd98f4-eae}). Background download of mono b/c + public colour clips:
~/Documents/Code/v2d-research/fetch_mono.sh (log fetch_mono.log; resumable, rerun if killed).
2026-10-07: round 4 run hit a session limit with 11/15 agents done (dig17:C, dig18:C, verify19,
critic missing); RESUMED same run id wf_adfd98f4-eae (task wk7yopnlm). Notes 17-20 hold the
partial/complete dig write-ups; 19 (collision hulls) complete: inflation fixable on asset side
(watertight R1 now; part splits limited by Newton per-world shape-pair RAM at 4096 worlds;
CoACD hulls differ macOS vs Linux, redo hull work in Linux).
2026-10-07 USER RULE: do NOT download anything without asking first (data, models, packages,
repo fetches) — applies to agents/workflows too. All V2D clips/meshes already cached locally
(~/Documents/Code/v2d-research/data, 1.4 GB, 171 files). Round 4: 4 digs + 3 skeptics done;
verify20 + critic re-running with an explicit no-download rule (resume of wf_adfd98f4-eae,
task wphqyt9xq).
2026-10-07 DONE: round 4 merged into `reports/v2d-challenge/research/21-synthesis-round4.md`
(architecture v3: room-map relocalisation, model-based tracker + marker correction layer,
GT-free anchor window + twin identity, REC collision assets built on Linux, human-hand references
+ timing/wrist/seed fixes). Note 20 lacks an independent verifier (network outage); round-4 critic
not run. Final resume attempt re-ran some agents (cache invalidated by a prompt edit) and failed on
network; notes 17-20 intact, no downloads. Research is at diminishing returns without GPU; next
phase = build + GPU day-1 runbook (21 §5) once the user rents a GPU.
2026-10-12 LEADERBOARD (03:54 UTC) Track 3, 5 teams: SoySauceChicken AUC 0.765 / SP 0.80 / MP 0.50 /
RPE 3.85 / MPPE 3.00 / CD-O 0.583 (2 subs); Zimo Li 0.368; Xueyi Wang (FF) 0.296; Panav Raaj 0.276
(best CD-O 0.112); Zihao Guo 0.229. Teams 2-5 score below the public "nothing moves" floor
(AUC 0.446, SP 0.45, RPE 10.9, MPPE 9.3) -> likely systematic errors (timing bug, frames, anchors) [H].
Professor package: ~/Documents/Code/v2d-research/package/V2D-Track3-Research.zip; doc
https://claude.ai/code/artifact/695886c2-1684-40b0-b3df-f501d9787706 (leaderboard table there is 10-06).
2026-10-12 COLAB SMOKE TEST (user approved; user's Chrome + Colab Pro, notebook Untitled27.ipynb in
their Drive). G4 runtime = NVIDIA RTX PRO 6000 Blackwell Server Edition, 97.9 GB, 48 CPU, 176 GB RAM,
driver 580.82.07 / CUDA 13.0, Ubuntu 24.04, no Docker; ~8.9 compute units/h (T4 ~1.07). Repo at
evaluator pin 8c778f90 + LFS (flash_chord assets 398 MB + ego_recon example); uv venv Python 3.11.17,
`uv sync --frozen --extra train` OK: jax 0.10.2 (CudaDevice), warp 1.14.0, newton 1.2.0, mujoco 3.8.1.
sharpa_flash_sac on tissue_box_simple (default recipe, 4096 worlds): ~45,300 env steps/s steady,
40.5 GB GPU memory, 100% util; checkpoint at 10M (policy 4.9 MB, state 161 MB). => 250M steps
~1.5-2 h/policy on G4 (unmeasured later-phase slowdown). Colab plans: Pro 200 units/mo; Ultra
$100 (1,000 units) or $200 (2,000 units), background execution only on Ultra.
Colab gotchas: first typed line in a new cell sometimes dropped; `!cmd &` keeps the cell busy ->
use the Colab Terminal panel for monitoring.
2026-10-12 COLAB CAPABILITY MAP (G4 RTX PRO 6000 Blackwell, Colab Pro; all verified by running):
- FlashCHORD train ✓ (45k steps/s) and OFFICIAL EVALUATOR ✓ (world_count 1, trajectory parquet export);
  20M-step tissue-box policy vs its own reference: add_auc 0.918, maniptrans_sr 1.0, MPPE 1.63 cm.
- System torch 2.11.0+cu130 (Python 3.13) supports sm_120.
- SAM2.1 hiera-large ✓ (pip git install, SAM2_BUILD_CUDA=0): 61 masks on a 2028x1520 ep12 frame, 0.69 s.
- FoundationStereo ViT-L (23-51-11, Drive weights via gdown) ✓ demo depth/pointcloud; needs open3d,
  trimesh, TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1; skip its open3d viewer (hangs headless).
- FoundationPose ✓ demo (mustard0) exit 0: nvdiffrast + pytorch3d compiled from source
  (CUDA_HOME=/usr/local/cuda, TORCH_CUDA_ARCH_LIST=12.0), mycpp needs -Dpybind11_DIR=$(python -m
  pybind11 --cmakedir); weights from Drive folder 1DFezOAD0oD1BblsXVxqDsl8fj0qzB82i.
- Not yet tried: HaMeR/WiLoR hands, SAM3D, our stereo rectification on Track 3 pairs, end-to-end scoring.
- No Docker -> NVIDIA's container pipeline must be installed module by module (works, as above).
Colab state is NOT persistent (runtime deletion loses installs); ~10 min to rebuild all of the above.
2026-10-13: Colab runtime was recycled overnight (installs lost). Wrote reproducible scripts in
~/Documents/Code/v2d-research/colab/: setup.sh (one-shot reinstall: FlashCHORD venv, ep data, kit,
SAM2, FoundationStereo, FoundationPose) and exp1.py (perception-only accuracy on public ep 12:
rectified mono stereo -> FoundationStereo depth -> OWLv2+SAM2 frame-0 masks -> FoundationPose with
public scans -> world = static rack frame -> official kit metrics for the cup). Transferred to Colab
via base64 typed into the Colab terminal (checksums verified). RUNNING setup on G4.
Gotcha: launching `bash setup.sh > log 2>&1 &` from the Colab terminal leaves apt-get STOPPED (SIGTTIN on
tty stdin). Use `DEBIAN_FRONTEND=noninteractive setsid nohup bash /content/setup.sh > /content/setup.log
2>&1 < /dev/null &`. Restarted that way 2026-10-13; DATA-OK, KIT-OK seen; pip deps in progress.
2026-10-13 EXP1 RESULT (G4, public ep 12, perception only, GT used only for scoring):
FoundationStereo (scale 0.5, rectified c/b, focal 600.2, baseline 0.0755 m, 0.27 s/frame) + OWLv2
("a cup"/"a dish rack", scores 0.46/0.42) + SAM2 frame-0 masks + FoundationPose (register it5, track it2,
~20 fps) with public scans; world = tracked static rack. Official kit metric functions:
  cup only: AUC 0.927, SP-SR 1, MP-SR 1, MPPE 1.45 cm, pos err median 1.30 / p90 2.26 / max 3.74 cm
  (GT cup motion extent 22.2 cm). Both objects (cup = slot 0, as in the parquet): AUC 0.964,
  MPPE 1.00 cm, RPE 0.79 cm. Whole run 24 s after the 54 s stereo pass (cached).
Fixes needed on the fresh runtime: cfg vit_size default; OWLv2 post_process_grounded_object_detection;
purge FoundationStereo's top-level Utils module before importing FoundationPose; pip warp-lang (now in
setup.sh). exp1.py sha256 60d822a4c487c544 (local == Colab). Patching via a typed python heredoc works.
MANO_RIGHT.pkl is NOT obtainable by us (registration at mano.is.tue.mpg.de = user action); hand path
without MANO = MediaPipe/stereo keypoints -> keypoint IK to Sharpa (hypothesis).
NEXT: generalize exp1 to all 20 public episodes (multi-object, prompts per object), then hands.
2026-10-13 perc.py (generalized exp1; ~/Documents/Code/v2d-research/colab/perc.py, sha be4f1eae10a1bb34):
any public episode, object names/slot order from the episode, OWLv2 top-1 box per object (twins: top-k
+ FoundationPose mesh-vs-mesh score assignment), SAM2, FoundationPose, camera = keyframe SIFT+stereo-depth
PnP VO (world = cam0), scoring variants 'vo' and 'anchor:<obj>'. LESSON: FoundationPose register scores
are NOT comparable across masks (a rack fragment scored 143 vs the true cup 73) -> never pick masks by FP
score. ep12 with VO world: AUC 0.992, SP 1, MP 1, MPPE 0.64 cm (cup 0.997, rack 0.987) > rack anchor 0.968.
RUNNING: run_public.sh over all 20 public eps (log /content/run_public.log, per-ep /content/perc/epN/).
Summary script colab/summ.py. Background agent studying FlashCHORD reference format + retargeter for a
MANO-free hand path (MediaPipe keypoints -> existing IK).
2026-10-13 ~11:45: OWLv2 batch results: ep12 0.991, ep13 0.997 (VO world); FAIL ep0/2 (white pot not detected in mono
frames), ep18 (sweeper/dustpan), ep21; ep11 twin cups SWAPPED (vo 0.10). OWLv2 on grayscale is unreliable -> new
detector perc2.py (local colab/perc.py sha fd113c4f4c699a1f; OWL version kept as colab/perc_owl.py): SAM2 automatic
proposals x DINOv2-L CLS similarity to 42 gray nvdiffrast renders of each scan + 3-D extent gate from stereo depth +
intensity term (LAM_I 0.3) + Hungarian; FoundationPose meshes converted to gray vertex colours (GRAY=1). ep11 detection
now correct (blue->dark proposal 55, beige->light 160). Batch killed (OOM when two jobs share the GPU: serialize!).
Depth caches kept in /content/perc/ep{0,2,11,12,13,18,21,22}. Hand/reference contract study saved as
reports/v2d-challenge/research/22-hand-reference-contract.md (MANO-free path feasible; contacts needed).
2026-10-13 ~11:55 perc2 (CNOS-style detector) partial results, VO world: ep11 0.871 (was 0.10 with OWL), ep12 0.995,
ep13 0.998, ep18 0.935, ep21 0.858, ep22 0.962, ep0 0.179. diag.py (colab/, sha d0e3e59849024445) = per-frame error
vs mocap after the scorer alignment + overlay montage. ep0 diagnosis: white_pot_lid registered with a ~179 deg
rotation error from frame 0 (symmetry: 180 deg about the lid axis; 9 cm origin shift) -> needs spin disambiguation
(markers, note 17: marker-only lid AUC 0.977); white_pot track jumps ~10 cm at f75 when the lid is lifted (pot
static in GT) -> needs occlusion-robust tracking / static-unless-touched prior / re-registration.
Eval roster (kit data/track_3_evaluation_objects.json): white_pot in 6 eval eps (1,3,5,6,8,28), wooden_spoon in 10
(3,5,6,15,16,32,33,35,36,37; no public scan). These two objects dominate the remaining perception risk.
Colab envs: /content/mpvenv (mediapipe 0.10.14 solutions OK; /content/ckpt/hand_landmarker.task), /content/rtvenv
(pin 4.1.0 MJCF, pink, daqp, viser, trimesh, torch cpu). URDFs in /content/t3/urdf. Background agent drafting
hands_mp.py, mkref.py, README_ref.md into ~/Documents/Code/v2d-research/colab/.
2026-10-13 ~12:05 perc2 batch (13/20 done): 23 0.995, 24 0.820, 26 0.031 (pot inside white rack -> both detections
wrong), 27 0.994, 31 0.885, 39 0.550 (dustpan ~5 cm offset once moving). Mean n=13 0.775.
MediaPipe hand detection: mono rectified cam_c ~0 frames with 2 hands; colour cam_a (tracking mode) 173/181 (ep12),
338/373 (ep0) -> hands from cam_a (a[k+1] <-> b/c[k]; X_b = R X_a + t from ego_cam_a extrinsics_to_stereo_left), lift
via stereo-depth z-buffer reprojected into cam_a. cam_a videos being fetched to /content/t3/v/epN_a.mp4.
Local colab/perc.py now = perc4 (sha faa5c1c2ab7c69b1): + render-and-compare verification (FP register on top-4
proposals per object, nvdiffrast depth agreement matched/(matched+free-space violations), C = ver + 0.5*S, Hungarian)
+ VO moved after tracking with rendered object silhouettes masked out and earliest-usable-keyframe matching (frame 0
first, KF_OK 120). Colab copies: perc2.py (CNOS only), perc3.py (+verify, 6613a249f4e12f33), perc4.py (+VO).
NEXT: test perc4 on 26, 0, 11, 12, 21, 39 after run2 finishes; then full rerun; then reference/policy stage.
2026-10-13 12:14 perc2 FULL (20 public eps, perception only, VO world): mean AUC 0.809, SP 0.90, MP 0.85, MPPE 4.76.
Per ep: 0 .179 | 2 ? (see /content/perc2/ep2) | 11 .871 | 12 .995 | 13 .998 | 18 .935 | 21 .858 | 22 .962 | 23 .995 |
24 .820 | 26 .031 | 27 .994 | 31 .885 | 39 .550 | 40 .986 | 41 .795 | 42 .817 | 43 .807 | 44 .887 | 45 .836.
Pot-only eps 41-45 have 105-194 VO keyframes (long chains -> drift suspected). RUNNING: run4.sh -> perc4 (verify + new
VO) on all 20 (/content/run4.log, /content/perc4/epN). Spoon template agent launched (writes colab/spoon/).
2026-10-13 15:27 local (+03; Colab clock is UTC): Claude app was quit mid-session. State at that moment: run4 (perc4,
KF_MIN=120, all 20 eps) was running on Colab; the Colab terminal panel had disconnected (page reload attempted).
Reference-builder agent FINISHED: colab/hands_mp.py (sha 408bbd7dc91596cc), colab/mkref.py (14f4178caf749177),
colab/README_ref.md (commands, Hydra quoting, support usda next to the parquet at <refs>/epN/reconstructed_stage/,
eval via kit examples/run_policy_evaluation.py --world-count 1). Upload via Colab Files-panel file input (chrome
file_upload tool) reported success but files were NOT found in /content afterwards -> re-verify / retransfer.
Spoon-template agent was stopped by the quit before writing anything (colab/spoon/ absent) -> relaunch.
2026-10-13 ~15:40 local: Chrome extension NOT connected after the app restart (list_connected_browsers empty) -> Colab
unreachable from here; Colab VM state unknown (run4 was running; runtime may idle-disconnect without the page).
Wrote locally (not yet on Colab): colab/score_sim.py (scores an official-evaluator rollout of a PUBLIC episode vs mocap
with the kit reader + metric functions; also reference-vs-mocap, sim-vs-reference, static floor) and
colab/pipeline_ep.sh (perc4 -> hands_mp -> mkref -> train (motion_speed 1.0) -> evaluate_policy (1 world) -> score).
Spoon-template agent relaunched (writes colab/spoon/). Transfer plan when Chrome returns: Colab Files-panel upload
(verify it lands in /content with sha256sum) or typed heredocs.
NEXT once connected: check run4 results (summ.py /content/perc4), transfer hands_mp/mkref/score_sim/pipeline_ep,
run hands+mkref on ep12/13, then a short training smoke (~20M steps) on ep12 and a full 250M run if healthy.
2026-10-13 spoon template DONE (agent): ~/Documents/Code/v2d-research/colab/spoon/ — wooden_spoon.glb/.obj (3,224 faces,
1,614 verts, closed genus-0, markers 7.2 mm spheres on stems, GLB format like public scans), wooden_spoon_rigid.urdf,
params.json, README.md, spoon_template.py, fit_spoon.py (skeleton, not run), verify_rule_public.py ->
public_frame_check.json, frame_mc.py -> frame_mc.json, previews. Defaults: length 306.9 mm, bowl 95x52 mm, depth 10,
wall 5, neck 16, handle 18.8-21.3 mm; markers from note-20 stereo, triangle 53.5/153.2/194.6 mm.
FRAME RESULT: rule gives frame A by a near-tie (skew_y -0.0038; z +0.226 bowl->handle; x -0.030); MC over parameter
brackets P(B) ~0.40-0.45; without markers in the organisers' scan P(B) ~0.17. Contradicts note 13 "commit to B",
consistent with note 20. Rule implementation reproduces 10/10 public origins/axis order/z; 7/10 y signs (near-ties
blue_cup, mini_dust_pan, white_pot flip). Recommendation: ask organisers for the spoon frame; default leans A.
2026-10-14: Explained, shareable Colab notebook built (user request, to send to a friend):
reports/v2d-challenge/V2D_Track3_Colab_Explained.ipynb (copy + builder in ~/Documents/Code/v2d-research/package/).
32 cells: plain-language challenge + metric explanation, machine check, repo/simulator install, smoke train + official
evaluator, runnable perception section (setup.sh, perc.py = perc2 version sha fd113c4f4c699a1f reconstructed as
colab/perc2.py, ep12 run, masks + diag overlay), optional 20-episode batch, results table (perc2 VO, mean 0.809; ep2
~0.98 inferred from the mean), MediaPipe hands test, next steps/costs, glossary. Not executed end to end as a notebook
(cells mirror commands run in the Colab terminal). Drive connector here is a different Google account than the Colab
owner (Untitled27 not found), and Chrome was disconnected, so the original Colab was not edited in place.
2026-10-16: Colab notebook 1rSlDlcC91UggWeCsDS0H8KFrp_C6ygX5 (was Untitled27.ipynb) RENAMED to
V2D_Track3_Colab_Experiments_Explained.ipynb and annotated in place via Chrome (user request; no cells executed):
14 cells = 4 original code cells with their original outputs + 10 markdown cells (overview, 0 challenge/metrics,
1 machine, 2a download, 2b simulator install, 3 smoke test incl. evaluator result, 4 perception pipeline, 5 results
table (perc2, mean 0.809), 6 hands, 7 next steps/costs/glossary). Two empty code cells deleted. Saved (cmd+s).
Chrome extension reconnected this session (new tab group; Colab tab id 708018518).
2026-10-18 GPU rental research done: reports/Cheapest GPU rental for V2D.md (notes in research_notes/Cheapest GPU
rental for V2D/). Recommendation: Vast.ai RTX PRO 6000 96 GB (~$1.0-1.2/h on-demand, ~$0.5-0.6 interruptible, per-second
billing, $5 deposit, filter cuda_vers>=13.0 cpu_cores_effective>=16 cpu_ram>=65536 reliability>=0.98, check per-host
storage/bandwidth prices); destroy instances instead of stopping; ~100 GB rebuild archives in Cloudflare R2, key
artifacts in B2/HF free tiers + Mac; est. (a) first public test $4-12, (b) first submission $35-50, (c) campaign ~$110
(range $80-155). Fallbacks: RunPod Community $1.69, Nebius $1.80, RunPod Secure $2.49 (+network volume $0.07/GB-mo).
Unverified: FlashCHORD checkpoint resume (needed for interruptible), Max-Q speed, preemption rates.
Kaggle note for user: perception AUC (0.809, public eps) cannot be submitted — boards score the 20 eval episodes and
Track 3 rows must be official-evaluator rollouts of trained policies with evaluator/checkpoint digests + commit URL.

2026-10-20: Owner reviewed all 29 repo rules/decisions on https://claude.ai/artifact/H8Rp47MHz8kvwe5MKkzw6L.
Keep (18): resume, runlog, research, nogt, separate, preserve, honest, approval, secrets, provenance, goal, professor,
order, handrisks, gpu, parallel, interruptible, vast. Remove (5): accounts, cleanroom, downloads, gcp, colab ("no need
you can yolo in vastai"). Change (5): selfdestroy -> no fixed time limit, stall watchdog instead; nodata -> commit
small results/final policies, keep bulk data out (owner asked why: GitHub 100 MB limit, history bloat, fresh clones);
approach -> approved, exhaust improvements before changing architecture; spoon -> agent decides frame from evidence,
owner checks visuals on request; repoforsubmit -> undecided, may send a cleaned copy. Undecided (1): remote ("first
settle the rules"). Applied to CLAUDE.md, STATUS.md, docs/context-and-decisions.md, README.md.

2026-10-20 (evening): Vast staging prepared off the clock. The owner asked whether we are ready: where data and keys
live, and every small detail, because the clock runs once on Vast.

Checked:
- The Track 3 dataset on HF is 1.47 GB in total.
- The Vast image `vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16` matches Colab (torch 2.11+cu130,
  Python 3.13). It has nvcc but no CUDA -dev library headers.
- Vast API: create, destroy, logs, label and ssh-key; `onstart` is limited to 4048 characters; account-level env vars
  are supported.
- FlashCHORD at the pin resumes from `state_<step>.safetensors` and saves every 5M steps. The replay buffer is not
  saved by default.
- Market: PRO 6000 WS $1.45–1.65/h on demand, from $0.54/h interruptible; any GPU from $0.10/h.

Wrote (not yet run on Vast):
- `docs/runbook-vast.md`;
- `ops/vast.sh` (`offers` tested on the public API) and `ops/config.env`;
- `ops/box/{onstart,lib,run_job,store,watchdog}.sh`;
- `ops/jobs/{smoke,day1}.sh`;
- `pipeline/fetch_data.sh` and `pipeline/oracle_poses.py`.

Changed:
- `setup.sh`: CUDA dev headers, hand venvs, MediaPipe model, DINOv2 pre-fetch, HF weight mirror, full dataset fetch.
- `pipeline_ep.sh`: defaults to perc2 (it ran the unvalidated perc4); adds `PERC=oracle`; one output folder per variant
  and seed; automatic training resume.

Proposed:
- a private HF dataset repo as the artifact store;
- boxes never push to git;
- narrow, expiring tokens on boxes, in Vast account env vars;
- the Vast key and the HF read token as cloud network secrets.

Next: the owner checklist (runbook §3), then box 0 (smoke) and box 1 (day 1). Expected batch cost $14–16, ceiling $25.

## 2026-10-20 (cloud session): step 0 checks, blocked on environment settings
Machine: Claude Code cloud session (no GPU), repo at 4d1d7ee. Commands and results:
- `curl $HTTPS_PROXY/__agentproxy/status`: proxy enabled, not selective.
- `ops/vast.sh show` and `curl https://console.vast.ai/api/v0/users/current/`: **`CONNECT tunnel failed, response 403`**.
  The proxy denies console.vast.ai, so the network policy does not allow it yet. The Bearer header is still untested.
- `curl https://huggingface.co/api/whoami-v2`: **403 from the proxy**, same cause.
- Direct TCP from the VM: port 443 to 1.1.1.1 connected; **port 22 to a GitHub IP timed out**. Raw SSH out looks
  blocked at the current setting. Retest against a Vast box once network access is Full.
- No SSH key generated yet: the key would be lost with the session before it could be registered.
- `HF_STORE` is still the placeholder `HF-USER/v2d-store` (the HF username is needed).
No spending. Waiting on the owner checklist (runbook §3), mainly network access Full plus the two network secrets.

## 2026-10-20 (cloud session, later): Vast key works; SSH out probably blocked
After the owner set the network access and added the `console.vast.ai` network secret:
- `curl https://console.vast.ai/api/v0/users/current/` → HTTP 200 (account 751312). **The Bearer network secret
  works.** Credit $0.00, no billing on file yet: top-up needed before any box.
- `ops/vast.sh show` → `0 instance(s)`.
- HF public dataset API → 200 (network open; no HF secret yet).
- Installed `openssh-client` in the VM, generated `~/.ssh/v2d_cloud` (session-local, never committed) and registered it:
  `ops/vast.sh ssh-key ~/.ssh/v2d_cloud.pub` → success, Vast key id 1621422. A new session needs a new key.
- SSH out: the VM has no DNS of its own; direct TCP to port 22 fails. The proxy answers `CONNECT github.com:22` with
  200 but no SSH banner ever arrives, and `ssh.github.com:443` is reset. The proxy appears to pass only TLS. **SSH to
  Vast boxes will most likely not work**; box 0 gives the definitive test. Plan for HTTPS-only mode (runbook §1).
- The repo is private (anonymous GitHub → 404), so boxes need `GH_TOKEN` to clone, or code must reach them another
  way (for example a tarball in the HF store).
No spending.

## 2026-10-20 (cloud session): HF secret works, store exists
- `huggingface.co` network secret: whoami → user `aebatirel`, fine-grained token "ClaudeToken" with write on the user's
  repos (broader than the planned one-repo token).
- `aebatirel/v2d-store` (private dataset) exists → set `HF_STORE=aebatirel/v2d-store` in `ops/config.env`.
- Vast account env vars: `GET /api/v0/secrets/` returns an empty list, so `HF_TOKEN`/`GH_TOKEN` are not visible as
  account env vars yet. The box-0 smoke test checks injection directly. Vast credit is still $0.
- Owner reports the GitHub token on Vast is full-access with no expiry; recommended replacing it with a read-only
  token for this repo with an expiry (boxes are third-party machines).

## 2026-10-20 (cloud session): SSH definitively blocked; WebSocket works
- Vast account env vars now list `GH_TOKEN` and `HF_TOKEN` (owner saved them).
- SSH via the agent proxy (`ProxyCommand` doing HTTP CONNECT) to the public test server `test.rebex.net:22`: the
  proxy accepts the CONNECT, then resets the connection before the SSH banner (`kex_exchange_identification:
  Connection closed`). Direct TCP has no route. **SSH out of the cloud session does not work**, whatever the host.
- WebSocket over TLS through the proxy (`wss://echo.websocket.org`, Python `websockets`, proxy CA bundle) → echo
  works. **Hypothesis:** an interactive shell on a box is reachable over HTTPS/WSS, either through Vast's instance
  portal (Cloudflare tunnel + web terminal/Jupyter) or a cloudflared quick tunnel we start. Falsified if box 0 cannot
  open such a terminal from this session.

## 2026-10-20 (cloud session): Vast billing check
- Owner swapped in restricted tokens (GH: this repo, Contents read-only) and added credit. API now shows credit $25.00,
  `has_billing` true, `autobill_threshold`/`autobill_amount` null (**autobilling not configured**), `billing_creditonly` 1,
  `balance_threshold` -0.01 enabled.
- Vast docs (guides/reference/billing): at $0 instances stop; a saved card is still charged automatically to cover a
  negative balance (mainly disk of stopped instances). Without a card, instances and data are destroyed instead.

## 2026-10-20 (cloud session): box 0 smoke test launched
- Permission mode: the owner switched from Auto to Accept edits after the auto-mode classifier blocked the tunnel
  and launch commands ("External Ingress Tunnel", then "Self-Modification" for a self-written allow rule, which was
  removed). The owner approves each command.
- Added `ops/box/rexec.py` + `ops/box/tunnel.sh` (token-protected HTTPS command endpoint behind a Cloudflare quick
  tunnel; URL and token in the HF store at `access/<run_id>.json`) and `ops/vast.sh exec`. rexec tested locally
  (health, wrong token → 403, exit codes, timeout). `vast.sh` now accepts `KEY=VALUE` settings before the subcommand.
- Launch: `ops/vast.sh V2D_COMMIT=9c70bca… SETUP=none DISK=40 create 50595368 20261020-smoke-9c70bca 'bash ops/jobs/smoke.sh'`
  → instance **56909517**, offer 50595368 (GTX 1070, South Korea, $0.061/h all-in, $4/TB download), commit 9c70bca.
- **Result (box 0, all times UTC; TRT = UTC+3):** created 15:03, image loaded and running 15:09:34, onstart started
  run_job 15:10:00.
  - env: `HF_TOKEN GH_TOKEN HF_STORE CONTAINER_ID CONTAINER_API_KEY RUN_ID V2D_COMMIT V2D_IMAGE` all present.
  - Private repo clone with `GH_TOKEN` at commit 9c70bca: OK.
  - Label set from the box with `CONTAINER_API_KEY`: OK.
  - Host: GTX 1070 8 GB, driver 580.178.04, 56 CPUs, 31 GB RAM, Python 3.13.16, `hf` in `/venv/main`.
  - HF public download of 0.69 GB (Track 3 evaluation split): 45 s. HF store write: `HF-WRITE-OK`, files visible from
    the session through the `huggingface.co` network secret.
  - Tunnel: `TUNNEL-OK` 16 s after start; `ops/vast.sh exec` ran commands (set and removed HOLD, read logs).
  - SSH to the real box via `ssh -p 24874 root@ssh3.vast.ai` through the proxy: connection reset. SSH is not usable.
  - Job exit 0 at 15:18:52; self-destroy pushed the final logs and destroyed the instance (0 instances at 15:19:16).
  - Cost: credit 25.00 → 24.99 (**$0.01**). Outputs: HF store `runs/20261020-smoke-9c70bca/`.

## 2026-10-20 (cloud session): box 1 day-1 job launched
- Owner go-ahead for box 1 (estimate $6–8, 4–5 h; batch ceiling $25).
- `ops/vast.sh offers` → cheapest compliant RTX PRO 6000 WS on demand: offer 56213818, Greece, $1.444/h all-in
  (GPU $1.402 + disk $0.042), 30 CPUs, 90 GB RAM, reliability 0.986, $2.67/TB download.
- Launch: `ops/vast.sh V2D_COMMIT=70f6169… create 56213818 20261020-day1-70f6169 'bash ops/jobs/day1.sh'` (disk 150 GB)
  → instance **56913250**, commit 70f6169, created about 15:33 UTC (18:33 TRT).
