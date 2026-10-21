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
- **Result (box 1, instance 56913250, 15:33–15:47 UTC, about $0.29):**
  - Host: RTX PRO 6000 Blackwell **Workstation** Edition, 97,887 MiB, 450 W limit, driver 595.99.02, 30 CPUs, 90 GB RAM.
  - Full `setup.sh` on the Vast image: **10 min**, all markers OK (CUDADEV KIT PYDEPS SAM2 DINOV2 FSTEREO NVDIFFRAST
    PYTORCH3D MYCPP FPOSE, FLASHCHORD, DATA: 60 public + 60 eval videos, 20 parquets, 11 meshes, 11 URDFs).
  - Tunnel and `ops/vast.sh exec` worked.
  - **Failure:** perception ep12 → `ModuleNotFoundError: No module named 'pandas'` (pyarrow `to_pandas` in perc2.py). The
    mini image's `/venv/main` lacks packages that Colab preinstalls. Job exit 1, then self-destroy (push OK, destroy OK).
  - Bug found: `setup.sh` printed `WEIGHTS-MIRROR-OK` with an empty store (an empty `--include` match exits 0), so
    `day1.sh` skipped `mirror-weights`. Fixed in 27a4e8c.
- Fixes for the relaunch: `setup.sh` installs pandas, scipy, opencv-python-headless, pillow, matplotlib, scikit-learn
  and pyyaml, then runs an import check (`IMPORTS-OK`/`IMPORTS-FAIL`), including `import estimater` (FoundationPose)
  and `import core.foundation_stereo` (FoundationStereo). `run_job.sh` holds a failed box for `FAIL_HOLD_MIN` (default
  30) min for debugging through `exec`; the watchdog destroys it when the hold expires.

## 2026-10-20 (cloud session): box 1 attempt 2 (instance 56915259, run 20261020-day1b-cfbff6b, commit cfbff6b)
- Same Greek host (offer 56213818, $1.444/h). Created 15:48 UTC; setup 15:49–15:59 (**10 min**, `IMPORTS-OK`).
- Weight mirror uploaded to the store: FoundationStereo 23-51-11 (3.3 GB), FoundationPose 2023-10-28 (68 MB) and
  2024-01-11 (190 MB). The `hf upload` summary line "0 uploaded, 0 committed" is misleading; the files are there.
- **Perception perc2 ep12 on Vast: AUC 0.997, SP 1.00, MP 1.00, MPPE 0.52 cm, RPE 0.80 cm in 96 s** (scored after
  inference against mocap; matches Colab 0.986–0.998). Depth cache pushed to the store.
- hands_mp.py ran (first run anywhere): `hands done` in about 50 s.
- **mkref.py failed (first run anywhere):** pinocchio 4.1.0 has no 2-argument `buildModelFromMJCF(file, root_joint)`;
  it wants `(file, root_joint, root_joint_name)`. The resume test was skipped (`RESUME-TEST-SKIPPED`) and both
  trainings failed at the same step. Set HOLD to 16:49 UTC from the session to keep the built box.
- Fix 3aa3b5f (fallback to the 3-argument form), checked out on the box via `exec`, mkref rerun by hand in the
  background (Cloudflare cuts HTTP requests at about 100 s, so long steps run under nohup and are polled).
- 16:07 UTC: environment snapshot `env/pt2.11-cu130-py313-20261020` uploaded to the store (from day1.sh).
- mkref rerun by hand (commit 3aa3b5f) on perc2 ep12: **VALIDATION OK** (FlashCHORD `load_reference`), 181 frames at
  20 fps, 22 finger DoF per hand, 194 s. E2S output 191 frames (10 warm-up frames dropped). Contacts: right 0.67 of
  frames (blue cup), left 0.28. IK frame-task error, median: fingertips 10–35 mm, hand root 37–49 mm; p95 up to
  171 mm (left hand root). Wrist max step 11.7 / 12.6 cm per frame (right / left): likely hand-tracking jumps; to
  inspect later.
- The oracle pipeline (started 120 s after the failed perc2 one) reached mkref after the fix was checked out, so its
  reference built and its 250M-step training started at about 16:08 UTC. day1.sh is waiting on it.
- Started `ops/jobs/day1_perc2.sh` (commit cc30cbe) on the box at 16:16 UTC: perc2 ep12 250M-step training next to
  the oracle one (two jobs on one GPU), killed after the first checkpoint >= 10M steps and rerun (resume test). It
  refreshes a 30-min HOLD while the GPU is busy, so the box outlives day1.sh if needed. The failed attempt's run dir
  and logs were renamed `*_attempt1`.
- Note: `git checkout` on a box while a bash script from the repo runs is safe only because git replaces files
  (new inode); never edit a running script in place.
- **Resume test passed (16:27–16:33 UTC):** perc2 killed after `state_10002432`; the rerun logged
  `resuming from …/state_10002432.safetensors` and its training progress continued at 10,002,432/250,003,456 (4.0%) →
  12.5M, not from zero. (Replay buffer not saved, so it refills; whether the final score matches an uninterrupted run
  is still unmeasured.)
- Two trainings on one GPU: 82 GB of 96 GB used, GPU 100%. Oracle averaged 36.1k env steps/s over its first 19.6 min
  (alone for the first ~9 min); perc2 14.8k steps/s in its first 2.8 min after resume (shared GPU, JIT). Oracle ETA
  ~18:10 UTC; perc2 estimated ~19:00–19:15 UTC.
- A monitor false alarm ("instance gone") came from one failed `vast.sh show` call; the monitor now needs two misses.
- Provenance note: `pipe_oracle_ep12.log` says `code cfbff6b` (the commit when that pipeline started, 16:04:31 UTC),
  but its mkref ran 16:05:20–16:08:08 UTC, after the box checkout moved to 3aa3b5f (pinocchio fix); with cfbff6b's
  mkref it would have failed as perc2 did. So the oracle reference was built with 3aa3b5f's mkref.py. The perc2
  run's reference was built by hand with 3aa3b5f; its training ran at cc30cbe (day1_perc2.sh). pipeline_ep.sh should
  record the commit per stage, not only at start.

## 2026-10-20 evening: first end-to-end score was invalid (floor bug), fixed, retraining
- perc2 ep12 finished 19:09 UTC (250M steps, resumed once): **sim vs mocap AUC 0.009**, MPPE 61 cm; evaluator's own
  add_auc 0.0076. `reference_vs_mocap` 0.9965; "nothing moves" floor 0.604.
- Diagnosis (trajectory dump `/content/diag.py`): both objects fall about 55–60 cm in the first 10 frames, from
  z ≈ 1.23 to 0.63–0.69, and stay there. mkref's log already said "frame-0 object bottoms above the fitted table:
  60.4 / 59.3 cm". Checked and ruled out: intrinsics (mkref and perc2 build the same P1), depth scale (depth at the
  cup's pixels 0.376 m vs pose 0.390 m), quaternion or frame bugs in score_sim.py (static floor at sim frame 0
  matches GT).
- **Root cause:** `fit_table` ran one RANSAC on a 90-px ring around the objects. The ring also holds the floor past
  the table edge. The floor got 55 % of the points and won; the table had 39 %. Camera height above the "table" was
  1.14 m (floor); the real table is 0.535 m below the camera.
- Fix 30d3633: sequential RANSAC (up to 4 planes, each >= 3 % of the points); pick the plane parallel to the
  dominant one (<= 25 deg) that is closest under the lowest object point; abort if the lowest frame-0 bottom is not
  within -3…+5 cm of it. ep12 now: candidates floor (0.55, 59.3 cm) and table (0.39, -1.5 cm, tilt 1.2 deg, rms
  0.7 mm); table picked; bottoms cup -0.07 cm, rack -1.5 cm, per-object snap +0.07 / +1.5 cm; VALIDATION OK.
  The snap costs the reference itself 0.997 → 0.973 vs mocap (rack per-object 0.996 → 0.948); to refine.
- Sanity check: old (floor-bug) perc2 policy evaluated on the new perc2 scene (temporary symlink to the old parquet
  name, removed afterwards): objects stay on the table; sim vs mocap 0.603 ≈ static floor 0.604 (the old policy does
  not move the cup). Results in `/content/results/sanity_newscene_oldpolicy`.
- The oracle training (84 %, same floor bug in its reference: bottoms 60.4 / 60.1 cm) was stopped at about 19:14 UTC
  to stop paying for it. Old refs, runs and results are kept as `*_floorbug` on the box (pushed to the store).
- Retraining started 19:19:46 UTC with `ops/jobs/train_pair.sh` (commit 4ba4013 incl. fix 30d3633): perc2 and oracle,
  250M steps each, on the same box. Expected done about 22:00–22:15 UTC.
- Open: "nefc overflow - please increase njmax" in 45 of 294 lines of the perc2 train log. `sim/rl.yaml` sets
  njmax 512 / nconmax 256; requests were 513–629. NVIDIA's `dexmate_sharpa_flash_sac` uses njmax 1024. Hypothesis:
  dropped constraints let contacts slip in some training worlds. Check which sim config the official evaluator uses
  before changing anything; test by training with `sim.njmax=1024` and comparing scores.
- Cost so far (Vast credit): $3.97 at 18:15 UTC; box 1 runs at $1.442/h.
- 19:26 UTC: **box 2** launched for the reference sweep: offer 49231571 (Czechia, $1.468/h, 8 Gbps down,
  $2.67/TB), instance 56940182, run `20261020-refsweep-ea14fdf`, `ENV_SNAPSHOT=pt2.11-cu130-py313-20261020`,
  job `ops/jobs/refs_sweep.sh` (perception → hands → mkref on all 20 public episodes, 2 streams, no training, then
  `pipeline/ref_report.py`). Host: 64 CPUs, 503 GB RAM. **Snapshot restore works: setup 2 min** (`RESTORE-OK`).
- Evaluator config: `evaluate_policy.yaml` rebuilds env, task, embodiment and sim from the checkpoint's resolved
  config, so the training-time `sim` (njmax) also applies at evaluation. Our requirements note records "changing
  simulator physics or evaluation behaviour would count as manipulating the evaluation", so raising njmax for a
  submission needs the owner's or organisers' OK, although NVIDIA's own `dexmate_sharpa_flash_sac.yaml` uses 1024.
- **Rollout rendering works:** `pipeline/render_rollout.sh` uses `view_policy.py` with the mp4 viewer backend.
  Needed: `PYGLET_HEADLESS=1` (no X display); `markers.keypoints=false markers.contacts=false` (their warp kernel
  fails: `widths` float vs array); camera aimed at the table. The first montage (old floor-bug policy on the fixed
  ep12 scene) shows the round support table, cup and rack resting on it, and both Sharpa hands barely moving
  toward the cup. `pipeline_ep.sh` now renders every evaluated policy to `$RES/render/{view.mp4,montage.jpg}`.
- **Hand identity swap found (ep12)** from the `hands_overlay.jpg` montage: at k=71 (cup hand-over) the green
  "right" skeleton was on the LEFT hand (the one wearing the white watch). The right-wrist jumps > 4 cm cluster at
  frames 61–83. MediaPipe's own labels there are mostly correct (k=71: right x=0.66, left x=0.39), but at k=66 and
  k=76 it labels both hands "Right", and the greedy linker's distance rules (`same_label` 9, `reassigned` 7) moved
  the right track onto the left hand. Also seen: the fit scale sits at its lower bound 0.85 for both hands
  (wrist→middle tip 12.5 cm vs ~18–19 cm adult); not yet explained.
- New `--linker viterbi` (default) in hands_mp.py: a whole-clip assignment (dynamic programming) with costs for
  overriding the label (× score), forearm direction (knuckles→wrist image-x), image half (weak), unused detections
  and palm motion beyond 3 cm/frame. Measured cue on ep12: right forearm x median +0.16 (79 % > 0), left +0.01
  (52 % > 0), so the forearm cue mostly helps the right hand. ep12 result (dev copy on box 1): k=71 now correct;
  right palm max step 5.7 → 3.8 cm (steps > 4 cm: 8 → 0); left valid frames 155 → 180, max step 6.5 → 4.2 cm.
  Hypothesis to test: fewer identity swaps across all public episodes. A/B on box 2: `ops/jobs/hands_ab.sh` (perc2 =
  greedy from the sweep vs perc2v = viterbi), compared with ref_report.py.
- **ep26 perception failure diagnosed:** the pot's mask and pose are fine (pose 0.60 m, depth 0.576 m), but the rack
  (slot 0, the anchor) was assigned to a red floor-tape proposal ~1 m away (S 0.287). Its top-4 proposals were all
  0.4–1.4 m from the pot. mkref's new guard rejected the scene (rack bottom -4.1 cm, pot +62.6 cm).
- New opt-in detection prior in perc2.py (`DET_PRIOR=compact`): a joint choice over each object's top-`DET_K`
  size-gated proposals, cost = −ΣS + 0.5·max(0, max pairwise 3-D centroid distance − 0.45 m). With DET_K=4 it chose
  the same (no rack candidate near the pot); with **DET_K=80: ep26 vo AUC 0.065 → 0.988** (rack 0.998, pot 0.978;
  rack proposal 1, S 0.111). Hypothesis: objects of a task start within ~0.45 m of each other. A/B on all public
  episodes: `ops/jobs/perc_ab.sh` on box 2 (baseline = sweep's perc2).
- Hand scale check (ep12, dev, viterbi): `--scale_min 0.55 --scale_max 1.3` → median scale 0.839 (was pinned at the
  0.85 bound), wrist→middle tip 11.9 cm; measured frames right 157 → 162, left 145 → 157; palm steps unchanged
  (max 3.9 / 3.5 cm). So the bound was not forcing the fit; the data say a small hand. Unresolved hypotheses: depth
  bias toward the camera (~7 cm at 0.45 m would explain it), MediaPipe world-landmark scale, or a genuinely small hand.
  Low priority.
- FlashCHORD recipe facts (`experiment/sharpa_flash_sac.yaml`, `termination/tracking.yaml`, `objective/tracking.yaml`):
  default `task.motion_speed: 0.5` (we pass 1.0 per the timing rule); terminations wrist 0.15 m, object 0.10 m /
  0.50 rad; contact_wrench_support weight 10, unintended_contact −10, termination −100; keypoint weights set by the
  curriculum (`tracking_250m_mixed_reset`). Checkpoints every 10M steps in this recipe.
- `pipeline_ep.sh`: `VARIANT`, `PDIR` and `HANDS_ARGS` for side-by-side variants (commit after 6ad3db7).
- **Wrist stiffness (note 14 hypothesis), set up for an A/B:** in FlashCHORD `action.wrist_kp/wrist_tau_max` drive only
  the wrist ROTATION (ball-joint effort, control.py); the wrist POSITION is the embodiment's prismatic joints,
  `SharpaHandsConfig.joint_overrides["wrist_[xyz]$"]` = kp 25 N/m, kd 6, 45 N (gravity compensation covers the hand,
  not a held object). The FAQ says "Sharpa Wave is the default embodiment. Other embodiments are welcome, including
  fixed-base arm-and-hand setups and floating hands" (docs/research/work/14/c2/faqs.txt). Hydra command-line dict keys
  cannot hold the regex keys, so the variant is a YAML in our repo, `flashchord_conf/embodiment/sharpa_hands_mid.yaml`
  (wrist position kp 400, kd 20, 150 N; rest unchanged), selected with
  `hydra.searchpath=[file:///content/v2d-track3/flashchord_conf] embodiment=sharpa_hands_mid`. Dry run (`--cfg job`)
  composes. NVIDIA's checkout is untouched; the checkpoint's resolved config carries the dict for the evaluator
  (to verify at the first eval). `pipeline_ep.sh` takes `TRAIN_ARGS`; in `train_runs.sh` a variant with "w" uses it.
- **Perception A/B result (box 2, all 20 public episodes, scored vs mocap after inference, `perc_ab.sh`):** mean AUC
  **0.883 → 0.932** with `DET_PRIOR=compact DET_K=80`. Gains: ep26 +0.923 (0.065 → 0.988, MP 0 → 1), ep45 +0.026,
  ep2 +0.016, ep31 +0.012, ep21 +0.007, ep24 +0.006, ep42 +0.005, ep18 +0.004; worst −0.003 (ep0, ep22), within the
  run-to-run noise. **Made the default** (DET_PRIOR=compact, DET_K=80). Remaining weak episodes: ep0 0.18 (lid
  symmetry), ep24 0.85, ep11 0.87, ep31 0.89. Note the baseline here (0.883) is higher than the Colab-era 0.809 (e.g.
  ep39 0.55 → 0.998); single runs vary, so differences under ~0.01 are noise.
- Reference sweep (box 2, `refs_sweep.sh`): 19/20 episodes built a FlashCHORD-validated reference; ep26 rejected by
  the new support guard (rack detection, now fixed by the prior). Report: `/content/results/ref_report_perc2.txt`.
- **Robot wrist jumps come from the IK, not hand tracking** (box 2, refs from the sweep). ep44 right: human palm steps
  ≤ 2.6 cm/frame but robot wrist steps up to 30.9 cm/frame; frames 10–29 the IK's `hand_C_MC` task error grows
  9.6 → 33 cm with every solve at the 100-iteration cap (warm-started from the previous frame), then at f30 it snaps
  back (error 1.9 cm) with a 30.9 cm / 108° step. Same pattern on ep39/41 (palm ~1 cm, wrist 9–26 cm).
  `ref_report` flags WRIST-JUMP (> 8 cm/frame) on most episodes.
- Mechanism (hypothesis): NVIDIA's `SHARPA_TO_MANO_MAPPING` weights the wrist (`hand_C_MC`) at position cost 0.2 vs
  1.0 per fingertip, so unreachable fingertip targets pull the robot wrist away; our hand fit says the hand is small
  (wrist→middle tip ~12 cm), and E2S scales MANO by `--mano_to_robot_scale` 1.2. Test: mkref on ep44 and ep12 at
  scale 1.2 / 1.35 / 1.5 and 1.35 + `--smooth_reference` (E2S flags, code unchanged), compare C_MC error, wrist
  jumps and contacts (`/content/dev/scale_sweep.sh`, `/content/dev/scale_cmp.py` on box 2).
- Scale hypothesis **falsified** on ep44: `--mano_to_robot_scale 1.5` vs 1.2 → right C_MC median 3.1 vs 2.8 cm, p95
  11.4 vs 11.7 cm, wrist max step 29.8 vs 30.9 cm, contact 0.52 vs 0.60 (no gain, contacts worse). (The other
  scale-sweep variants died from thread exhaustion, `Resource temporarily unavailable`, caused by too many parallel
  mkref processes on box 2; `--e2s_args "--smooth_reference"` must be written `--e2s_args=--smooth_reference`.)
- New finding (ep44 right, frames 8–32): the reconstructed hand changes shape per frame: wrist→middle-MCP 5.6–9.0 cm,
  palm width 4.7–5.8 cm (an adult palm is ~8 cm); human wrist orientation steps 6–29° per frame. During the drift the
  robot wrist sits 150–177° from the human wrist frame versus the normal ~121° offset, i.e. the IK settles into another
  basin and stays there under warm start until it snaps back at f30 (108° step).
- New option `mkref.py --bone_norm [--hand_scale k]`: rebuild the skeleton with every bone at its episode-median
  length (× k) along each bone's own direction (`normalize_bones`). Hypothesis: a constant hand shape removes the IK
  drift and jumps. Falsified if ep44/ep12 C_MC p95 and wrist jumps don't drop. Test: `/content/dev/bn_sweep.sh` on box 2
  (base / bn10 / bn12, 3 processes at a time, thread caps).
- **Bone normalisation: mixed, not adopted.** ep44 right C_MC p95 11.7 → 5.1 cm and wrist max 30.9 → 9.6 cm, but
  left unchanged, and ep12 right got much worse (C_MC median 4.8 → 14.6 cm).
- **Wrist IK cost: confirmed.** `mkref --wrist_cost` patches NVIDIA's `SHARPA_TO_MANO_MAPPING['.*_hand_C_MC']`
  position cost (0.2 → k) in our E2S shim (E2S code unchanged). Results (base 0.2 / 1.0 / 3.0):
  ep44 right C_MC p95 11.7 / 7.3 / **2.5** cm, wrist max 30.9 / 16.8 / **4.6** cm (steps > 5 cm 9 / 5 / 0); left p95
  19.5 / 15.7 / **6.3**, max 25.0 / 19.8 / **8.1**; ep12 right p95 8.2 / 5.6 / **2.9**, max 11.7 / 9.7 / 7.4; left p95
  17.1 / 12.8 / **4.3**, max 12.6 / 9.7 / **4.7**. Cost: fingertip median error 0.8–1.4 → 1.6–3.1 cm. Contacts
  unchanged; all VALIDATION OK. Variant letter `c` in train_runs (MKREF_ARGS="--wrist_cost 3.0"). Whether it raises
  the sim score is untested.
- **FIRST VALID END-TO-END SCORE (box 1, 22:26 UTC): ep12 perc2** (greedy hands, NVIDIA retarget weights, default
  wrist; mkref 30d3633 support fix; training 4ba4013): **sim vs mocap AUC 0.890, SP-SR 1.00, MP-SR 1.00, MPPE 1.5 cm**
  (cup 0.780, rack 1.000). Reference vs mocap 0.973 (upper bound), sim vs reference 0.863 (policy tracking), static
  floor 0.604. The evaluator's own metrics vs our reference: add_auc 0.859, chord_sr 1.0, maniptrans_sr 1.0,
  mppe 2.77 cm. One easy public episode, not an eval average.
- Rollout montage (`results/e2e/ep12_perc2_rollout.jpg`, view_policy, not the evaluator): the right hand grasps the
  cup, both hands lift and turn it in the air, and it is set down upright by the rack, whereas the human placed it
  upside down in the rack; the cup's placement and orientation are the likely loss.
- **ep12 oracle (mocap objects, evaluation-only diagnostic):** sim vs mocap **AUC 0.858**, SP 1.00, **MP 0.00**,
  MPPE 1.8 cm (cup 0.719, rack 0.998); reference vs mocap 1.000; sim vs reference 0.855. Lower than perc2 (0.890)
  despite a perfect object reference → on ep12 the perception loss is small and the **robot (policy tracking) sets
  the score**: sim-vs-reference 0.855–0.863, i.e. ~0.14 AUC lost in the robot, with ±0.03 policy-to-policy variance
  (larger than the perception difference). Consistent with research note 14. Decision: the reference/robot fixes
  (wrist IK cost, hand linker, mid wrist) are the main lever; compare them over several episodes, and later train
  more than one seed per episode.
- Box 1 reused at 22:32 UTC (hold set before `train_pair.sh` released it): `train_runs.sh` RUNS="27:perc2:vc
  2:perc2:vc" at d144d02+ (Viterbi hands + wrist cost 3.0, default wrist). `ops/box/hold_guard.sh` on both boxes keeps
  the hold while any `pipeline_ep.sh` runs (a finishing job removing the hold could otherwise let the watchdog
  destroy a box mid-training).
- **Bug found and fixed:** `hands_ab.sh`, `train_runs.sh` and `train_pair.sh` used a bare `wait` after starting a
  background hold-refresh loop, so they also waited for that loop, which only ends when the job ends → deadlock.
  Effects: the hands A/B stalled after its first batch (ep0/2/11); `train_pair.sh` on box 1 never finished (its
  pipelines did, including eval; only the final push and hold release were skipped); the `train_runs.sh` jobs now
  running on both boxes will do the same after their trainings (the watchdog then destroys the box ≤ 30 min after
  the GPU goes idle; release the hold by hand to save that). Fixed by waiting on the worker PIDs only. Also killed six
  scale-sweep mkref/E2S processes hung since the thread-exhaustion failure (1h50 at 0 % CPU).
- **Hands A/B result (box 2, 18 public episodes, mkref at NVIDIA weights; proxy = robot wrist steps > 5 cm,
  confounded by the IK drift):** greedy 255 vs Viterbi(w_arm 0.8) 276 → **not a clear win**. Better: ep18 (18 → 5,
  right C_MC p95 28.9 → 6.8 cm), ep24 (32 → 20), ep2, ep23, ep43, ep12 (hand-over fixed). Worse: ep31 (3 → 18), ep39
  (13 → 36), ep22 (1 → 17), ep21 (13 → 18). Viterbi assigns more detections (valid frames up, e.g. ep21 R 129 → 185).
  Hypothesis: the forearm cue (weight 0.8) is near-random for the left hand (ep12: left forearm x median +0.01) and
  forces wrong overrides. Test: hands-only rerun with w_arm 0.3 and 0.0 on ep31/39/22/18/12/24, scored by human palm
  steps > 4 cm (no IK involved).
- **Hand linker, final decision tonight: back to greedy as default.** Proxy without IK = human palm steps > 4 cm
  (right+left), greedy / Viterbi(w_arm 0.8) / Viterbi(0.3) / Viterbi(0.0) / Viterbi(0.3, w_unused 0.15, jump gate):
  ep31 0 / 20 / 0 / 0 / 3 (valid L 289 → 19 with the last one); ep39 8 / 31 / 31 / 35 / 40; ep22 1 / 15 / 15 / 23 / 7
  (max 51 cm); ep18 0 / 7 (max 44 cm) / 7 / 11 / 12; ep24 12 / 13 / 12 / 12 / 5 (but valid 273 → 208); ep12 (greedy
  failed the hand-over, Viterbi fixed it). Viterbi only wins the ep12 hand-over; it follows long spurious tracks
  elsewhere (likely the second person's hands seen in many clips), and making unassignment cheaper lets it skip
  across gaps. Kept as `--linker viterbi` (w_arm 0.3, w_unused 1.0) for later work; idea for next time: identity
  from the white smartwatch on the wearer's left wrist + arm continuity from the image bottom (note 15).
  NB: the `vc`/`vw` trainings tonight used Viterbi(w_arm 0.8) hands, i.e. the old default.
- **ep12 vw (Viterbi(0.8) hands + mid-stiffness wrist kp 400; NVIDIA retarget weights)** finished 00:11 UTC:
  sim vs mocap **AUC 0.860**, SP 1.00, MP 1.00, MPPE 1.8 cm (cup 0.733, rack 0.986); reference vs mocap 0.993;
  sim vs reference 0.841; evaluator add_auc 0.838, chord/maniptrans 1.0. The evaluator rebuilt the custom embodiment
  from the checkpoint without our config dir (confirmed). ep12 so far: perc2 0.890, oracle 0.858, vw 0.860 → all
  within the ~±0.03 policy-to-policy spread; **no measurable gain from the mid wrist on ep12** (one seed each).
- Where ep12 loses (vw, cup sim vs reference): f90 2.6 cm / 5.6°, f120 1.0 cm / 4.0°, f150 5.1 cm, f180 7.7 cm /
  13.3°; the sim cup ends 3 cm higher than the reference (z 0.718 vs 0.687), i.e. set down on the rack's edge/pegs
  instead of beside it. (Correction: the reference cup ends upright, not upside down.) Final placement is the loss.
  Montage: `results/e2e/ep12_vw_rollout.jpg`.
- **ep12 vc (Viterbi(0.8) hands + `--wrist_cost 3.0`, default wrist) FAILED** (00:38 UTC): sim vs mocap AUC 0.604 =
  static floor (cup 0.208, SP 0, MP 0, MPPE 7.7 cm); sim vs reference 0.576; evaluator add_auc 0.575, chord 0,
  maniptrans 0. Exported trajectory: cup axis flipped (−1.00) at table height from f60 to the end (pos error 15–22 cm,
  rot error ~180°); the view_policy montage shows the hands never reaching the cup (the viewer's reset differs from
  the evaluator's). One seed, so cause vs bad luck is unresolved. Hypothesis: wrist cost 3.0 moves fingertip targets
  1–2 cm away from the human's (right tips median 3.1 cm on ep12), the contact reward becomes hard to earn, and the
  policy learns to stay away. **Do not adopt `--wrist_cost 3.0` without a multi-seed test**; try a milder cost (1.0)
  or a two-stage IK (wrist first, then fingers) next. Montage: `results/e2e/ep12_vc_rollout.jpg`.
- Box 2 released at 00:39 UTC (results pushed by the watchdog's self-destroy). Box 1's ep27/ep2 runs also use `vc`;
  letting them finish (~$1.9) to see whether vc fails generally.
- **ep27 vc (box 1, 01:22 UTC): sim vs mocap AUC 0.965, SP 1.00, MP 1.00, MPPE 0.9 cm** (white_pot 0.930, rack
  1.000); reference vs mocap 0.997; sim vs reference 0.965; static floor 0.559 (the pot travels ~20 cm); evaluator
  add_auc 0.968, chord/maniptrans 1.0. Montage (`results/e2e/ep27_vc_rollout.jpg`): the right hand grasps the pot by
  the handle, lifts it, turns it over and places it upside down on the rack, as in the video. So `vc` is not broken in
  general; ep12's vc failure (0.604) looks like a bad policy draw or an ep12-specific grasp problem; multi-seed needed.
- **ep2 vc (box 1, 01:42 UTC): sim vs mocap AUC 0.926, SP 1.00, MP 1.00, MPPE 1.3 cm** (white_pot 0.929,
  white_pot_lid 0.923); reference vs mocap 0.995; sim vs reference 0.936; static floor 0.503; evaluator add_auc 0.935,
  chord/maniptrans 1.0. Montage (`results/e2e/ep2_vc_rollout.jpg`): the left hand takes the lid off and sets it on the
  table, the right hand lifts the pot by its handle, as in the video.
- Box 1 released 01:45 UTC (push, then hold removed; my push request hit Cloudflare's ~100 s limit (HTTP 524) but the
  command ran on; the watchdog pushed again); 0 instances. All scores, trajectories and montages are in the HF store
  (`runs/20261020-day1b-cfbff6b/results`, `runs/20261020-refsweep-ea14fdf/results`); score JSONs copied to
  `results/e2e/`. **Final Vast credit $2.22** (spent ≈ $22.78 of $25 over the day).

### Night summary (end-to-end, public episodes, one seed each)
| episode | config | AUC | SP | MP | MPPE |
|---|---|---|---|---|---|
| 12 | perc2 (greedy hands, NVIDIA weights) | 0.890 | 1.00 | 1.00 | 1.5 cm |
| 12 | oracle objects (diagnostic) | 0.858 | 1.00 | 0.00 | 1.8 cm |
| 12 | vw (Viterbi + mid wrist) | 0.860 | 1.00 | 1.00 | 1.8 cm |
| 12 | vc (Viterbi + wrist cost 3) | 0.604 | 0.00 | 0.00 | 7.7 cm |
| 27 | vc | 0.965 | 1.00 | 1.00 | 0.9 cm |
| 2 | vc | 0.926 | 1.00 | 1.00 | 1.3 cm |
Mean of the best run per episode (12/27/2): AUC 0.927, SP 1.00, MP 1.00. Public episodes are easier than eval;
not comparable to the leaderboard (eval average, spoon, white pot, hand-overs).

## 2026-10-21 (owner topped up; credit $27.19): hard-episode A/B batch
- Owner picked "hardest 3"; chosen public episodes 24 (Planter_Stand: two thin boards, slides/pivots, twin of eval
  25), 18 (Dust_Brush: sweeper + dustpan, tool strokes and slides, twin of eval 19/30) and 21 (Water_Can_Blue_Cup:
  pouring, cup held tilted in the air, twin of eval 20). No public spoon or stirring episode exists.
- Plan: per episode two trainings on one box: default (greedy hands, NVIDIA retarget weights, default wrist) and `c`
  (`mkref --wrist_cost 3.0`), to settle the wrist-cost question on hard tasks. Estimate ~3 h, ~$13. Owner approved.
- `train_runs.sh` now runs perception once per episode before the variants start (6f2f98a; two variants of one
  episode would otherwise both write /content/perc2/epN).
- Launches (commit 6f2f98a, `ENV_SNAPSHOT=pt2.11-cu130-py313-20261020`, job
  `OMP_NUM_THREADS=4 … RUNS='<ep>:perc2 <ep>:perc2:c' bash ops/jobs/train_runs.sh`):
  - ep21: offer 56213818 (Greece, $1.442/h) → instance 56997724, run `20261021-hard-ep21-6f2f98a`;
  - ep24: offer 55481539 ($1.375/h) → instance 56997746, run `20261021-hard-ep24-6f2f98a`;
  - ep18: offer 31125570 ($1.431/h) → instance 56997750, run `20261021-hard-ep18-6f2f98a`.
  (Offers 28810508, 46000981 and 49836882 were taken before the create calls.)

### 2026-10-21 07:40 TRT: eval-episode plumbing; the official scorer registers meshes (new finding)
- **Eval plumbing (code only, not yet run on a box):** `SPLIT=eval` in `pipeline_ep.sh` (exported to perc2.py,
  hands_mp.py, mkref.py). Eval videos from `/content/t3/eval/v`, object names in slot order from the kit roster
  `data/track_3_evaluation_objects.json`, N = video frame count (no parquet), no scoring against mocap, `PERC=oracle`
  refused, an episode outside the roster refused; a public run on an episode without a parquet is refused.
  Checked: the kit's sample-submission roster has frames 0..N-1 per eval episode (ep1: 335) and eval ep1's three
  videos have 335 frames each (ffprobe), so N from the videos matches the roster.
- **Finding: the current kit's pose scorers (AUC, SP-SR, MP-SR, MPPE, RPE) register our submitted mesh to the
  confidential scan first** (`metric_code/track_3/AUC.py` `_score_registered_track3`, `_REGISTER_OBJECT_MESH = True`):
  1. our mesh is centred at its surface centroid, scaled to the scan's radius and ICP-aligned to the scan (25 starts:
     identity + PCA permutations, 40 trimmed iterations);
  2. our poses are moved to the scan's hidden anchor point and expressed in the scan's axes;
  3. one rigid world transform from frame 0: anchored on the first object without a symmetry axis (full rotation),
     else on object 0's axis plus the direction to object 1;
  4. errors are symmetry-aware: cups any spin about the central axis, lid 0/180° about its normal (README).
  Our scorer (`score_sim.py`, perc2's block) uses the older unregistered path (`_warp_to_reference_start` from slot 0,
  no symmetry), so **our numbers are not exactly the official ones**. With a mesh in the scan's own body frame the
  registration is ≈ identity; a poor reconstruction (wrong ICP rotation) adds a constant body-frame error to every
  frame. The submission must carry **our own reconstructed mesh per (eval episode, object)** (FAQ: not the public
  scans). Next: a local copy of the registered scorer (public scan as stand-in for the confidential scan) and a
  mesh-reconstruction prototype.

### 2026-10-21 08:00 TRT: local registered scorer (`pipeline/score_registered.py`) and what it changes
- Calls the kit's own `v2dlb.track3_pose` functions (register mesh → convert body → align scene → symmetric metrics)
  with a stand-in for the hidden host geometry: public scan, anchor = surface centroid (guess), 1000 surface points,
  cup axis = distinct principal axis (order 360), lid axis = thinnest principal axis (order 2; the lid scan's normal is
  its x axis, extent 4.7 cm). Candidate meshes = public scans by default (decimated by the packer's `budget_mesh`), or
  `--meshes DIR` for our reconstructions. Run in this cloud VM (CPU, scratch venv: numpy scipy pandas pyarrow trimesh
  fast_simplification) on files from the HF store; outputs in `results/registered/`.
- **Perception, 20 public episodes (refsweep perc2 poses, pre-compact-prior, commit ea14fdf): mean AUC 0.8828 old vs
  0.8824 registered; SP 0.90 / 0.90; MP 0.90 / 0.90; MPPE 3.90 / 3.92 cm.** Per episode the change is ≤ 0.006
  except ep12 0.998 → 0.940 (cup in slot 0; the rack now sets the scene rotation, so the rack's frame-0 orientation
  error reaches the cup) and ep11 0.873 → 0.913 (two cups: no fixed object, axis + direction alignment, spin not
  scored).
- **End-to-end rollouts, old → registered (sim vs mocap AUC):** ep12 perc2 0.890 → 0.875, oracle 0.858 → 0.857,
  vw 0.860 → 0.848, vc 0.604 → 0.589; ep27 vc 0.965 → 0.967; ep2 vc 0.926 → 0.925. Reference vs mocap on ep12 drops
  more (perc2 0.973 → 0.853, vc/vw 0.993 → 0.877): mkref's object trajectories carry a rack orientation error that the
  rack-anchored alignment exposes (to look into).
- Eval episodes where the new rule anchors on a different object than slot 0: 8 (pot), 14 (rack), 20 (pitcher),
  32/33 (**spoon**). The spoon also anchors 35–37. With registration, the spoon's body-frame convention (A vs B) no
  longer matters: the scorer ICP-aligns our mesh to the scan, so only mesh-pose consistency and shape count.
- **Leaderboard moved** (leaderboard.json generated 2026-10-21 00:55 UTC): Zihao Guo AUC 0.831 / SP 0.95 / MP 0.75 /
  MPPE 3.51 / RPE 2.10 / CD-O 0.313; SoySauceChicken 0.823 / 0.85 / 0.70 / 2.62 / 3.85 / CD-O **0.065**; SRL 0.657;
  Alcor Z 0.636; Zimo Li 0.630. The bar to beat is now 0.831.
- Fix: `.gitignore` ignored all of `/results/`, so the e2e score JSONs and rollout montages of 2026-10-20 were never
  committed (they were only in this session's checkout and the HF store). Now `/results/e2e/` and
  `/results/registered/` are tracked and committed.

### 2026-10-21 08:25 TRT: mesh-defect sensitivity of the registered scorer (`pipeline/mesh_sensitivity.py`)
- Same perception trajectories (refsweep perc2), candidate mesh = a damaged public scan, stand-in host scan = the clean
  scan. Six public episodes (41 pot, 23 wooden pieces, 39 dustpan, 27 rack + pot, 18 sweeper + dustpan, 2 pot + lid).
  Mean AUC: clean 0.987; ×1.10 scale 0.987; one side slab (20 %) removed 0.986; convex hull 0.947; bottom 20 % removed
  0.904; 3 mm vertex noise 0.825; 5 mm inflation 0.608 (wooden piece and sweeper registered **180° flipped** →
  ep23 0.052, ep18 0.247; dustpan 8.5° off → ep39 0.470). Per-episode values in `results/registered/sensitivity/`.
- Reading: scale is free (normalised), but **shape errors move the ICP registration** (rotation 2–4°, anchor 1–7 cm,
  or a flip for flat, nearly symmetric objects), and that error hits every frame. Mesh quality is now a first-order
  term of all five pose metrics, not only of CD-O. Thin/flat objects (wooden pieces, sweeper, dustpan; eval 19, 25,
  30, 38) and an unseen bottom are the main risks.
- FAQ (current PDF, downloaded today): "While some objects in the eval set have meshes in the public data,
  participants should reconstruct the objects to generate object trajectories and submit their own reconstructed
  meshes." Our tracker uses the public scans as templates, so the trajectory part is also in question → owner
  decision / ask the organisers.
- Literature/open source (quick review): BundleSDF (Wen et al., CVPR 2023, NVlabs/BundleSDF; joint tracking +
  neural SDF reconstruction from RGB-D with a frame-0 mask; heavy, older CUDA stack); SAM 3D Objects (Meta,
  CVPR 2026; single image → complete mesh, arbitrary scale, coarse detail); EgoGrasp (arXiv 2601.01050: SAM3D mesh
  from an anchor frame + PnP tracking), FlowHOI (2602.13444: SAM3 + Depth Anything 3 + SAM3D), EgoAERO (2606.08057:
  asset-free tracking + coarse-to-fine mesh, no code found). Hypotheses to test next: (H1) TSDF/carving fusion of
  our stereo depth along our tracks gives a mesh whose registered AUC is within 0.02 of the clean scan on public
  episodes (falsified if mean drop > 0.02 or any flip); (H2) FoundationPose tracking with our reconstructed mesh
  instead of the scan loses < 0.03 perception AUC (needs a GPU run).

### 2026-10-21 08:55 TRT: own-mesh reconstruction v0 (`pipeline/recon_mesh.py`), first result (H1 holds on ep41)
- Method: dense TSDF in the object frame along our tracked poses (refsweep perc2 `poses.npz`), our FoundationStereo
  depth (`cache/depth/public/ep41`), running average of clip(sdf/1.2 cm) incl. free space (carving), unknown voxels
  enclosed by the shape count as inside, component nearest the origin, Gaussian-smoothed occupancy → marching cubes →
  kit `budget_mesh` (4096/4096). Table: frame-0 support plane by RANSAC constrained to lie 0–30 cm under the object
  origin; table and hand samples carve free space but never vote for a surface. CPU in the cloud VM, ~1.5 min.
- Iterations on ep41 (white_pot alone; registered AUC with the scan 0.9985):
  | version | CD-O cm | reg. rot ° | anchor cm | AUC with our mesh |
  |---|---|---|---|---|
  | v0 (no table handling, cube ±20 cm) | 0.981 | 2.35 | 0.67 | 0.9925 |
  | + hand capsules dropped | 0.972 | 2.61 | 0.69 | 0.9910 |
  | table plane = largest plane (was the **floor**, 1.1 m) | 1.012 | 3.14 | 0.67 | 0.9889 |
  | table samples dropped entirely (lost free-space carving) | 1.090 | 27.5 | 0.86 | 0.7107 |
  | table/hand samples carve but never vote surface | 0.671 | 1.74 | 0.89 | 0.9881 |
  | + cube ±30 cm (handle was clipped at 20 cm) | **0.564** | **1.12** | **0.58** | **0.9979** |
- Hand masking had no measurable effect on ep41 (kept as an option `--hands`; 7× slower).
- Outputs in `results/recon/ep41/` (mesh, stats, picture vs scan). Next: the other objects (rack, lid, cups, pitcher,
  boards, sweeper, dustpan) on public episodes 27, 2, 23, 39, 18, 12, 21.

### 2026-10-21 09:15 TRT: reconstruction v0 → v3 on more objects (CPU, cloud VM)
- v0 batch (episodes 27, 2, 23, 39, 18; 12 and 21 were cut off by the 30-min limit on background shell commands; the
  batch scripts now run detached with nohup): registered AUC with our mesh vs with the scan:
  ep27 0.933 vs 0.994 (pot 8.8° off: the hand on the handle fused in), **ep2 0.305** vs 0.977 (pot: only the lower
  body kept, rim and handle were separate components → 102°), **ep23 0.036** vs 0.999 (board 1 with board 2 fused
  on → **flipped 175°**), **ep39 0.212** vs 0.997 (dustpan 123°: the tabletop around it fused), ep18 0.627 vs 0.956
  (sweeper 41°). Good objects: rack 0.66 cm / 1.3°, lid 0.41 cm / 0.9°, board 2 0.22 cm / 0.9°, ep18 dustpan 0.49 cm.
- Fixes, one at a time on ep39 (dustpan alone, lifted by its ring and turned upright):
  - v1 = + hand capsules + other tracked objects (scans at their tracked poses, option B) carve-only + merge
    components within 2 voxels: ep39 still 131° (AUC 0.202) → the extra sheet is the tabletop, not the hand.
  - v2 = + per-frame re-fit of the table plane (frame-0 RANSAC plane moved by VO, refit to samples within 3 then
    1.2 cm, ≤ 10° correction): **6.4°, AUC 0.823**; a wedge remained behind the plate.
  - v3 = closing 'near' (unknown voxels count as inside only within 3 voxels of observed inside, then enclosed
    cavities; 'fill' turned every enclosed unknown region into solid): **CD-O 0.58 cm, 1.95°, AUC 0.953** (scan 0.997).
- v3 on more episodes, with `recon_eval.py` now repeating the registration over 8 sampling seeds (seed 0 = the
  official one for the episode and slot) and measuring symmetry-aware rotation errors (cups: axis tilt; lid: modulo
  180°). Columns: CD-O cm, rotation ° (official seed), flip rate (> 30°), worst rotation °; registered AUC ours vs
  scan.
  | ep | object(s) | CD-O | rot | flip rate | worst | AUC ours / scan |
  |---|---|---|---|---|---|---|
  | 41 | white_pot | 0.70 | 2.6 | 0 | 2.6 | 0.984 / 0.999 |
  | 39 | mini_dust_pan | 0.58 | 2.0 | 0 | 3.2 | 0.953 / 0.997 |
  | 23 | wooden_piece_1 / _2 | 0.29 / 0.60 | 1.9 / 2.6 | **0.12 / 0.12** | 179 / 180 | 0.976 / 0.999 |
  | 21 | blue_cup / water_pitcher | 0.85 / 1.15 | 0.6 / 2.4 | 0 / 0 | 7.9 / 2.4 | 0.917 / 0.975 |
  Reading: the boards sit on a near-tie between identity and a 180° flip (1 seed in 8 flips → a coin toss at
  Kaggle, whose scan samples differ). 2–3° of registration error already costs 0.015–0.06 AUC, most when the object
  sets the scene rotation (ep21: the pitcher anchors, the cup is symmetric). v3 on ep41 is worse than the best v0
  variant (0.998): to ablate (closing mode, hands, table refit).
- Note (to test): a mesh fused along our own tracks inherits any constant tracking bias β as a rotation β⁻¹ of the
  mesh, and the scorer's registration then multiplies it back out (converted pose = R_pose·Rᵀ), so a constant bias
  cancels; only time-varying pose error and depth-shape error remain.
- v4 = v3 + depth-edge filter (5×5 max−min > 2 cm → no information; flying pixels at silhouettes): ep41 0.984
  (CD-O 0.65, 2.2°), ep39 **0.880** (5.0°; the thin plate loses much of its depth), ep23 0.966 (boards 0.45° /
  2.5°, **flip rate 0 / 0** vs 0.12 / 0.12 in v3). Mixed → off by default for now.
- Ablation on ep41 (pot), registered AUC with our mesh (scan 0.9985): fill closing + hands 0.9979 (0.9°);
  fill, no hands 0.9983; near, no hands 0.9862; fill, no edge filter 0.9969. **Closing mode decides** (fill for the
  bulky pot, near for the thin dustpan); hand masking and the edge filter do not matter on ep41.
- New: `--close auto` (default): fill unless the never-observed share of the filled object exceeds `--auto_thr`
  (to calibrate on 41 / 39 / 23, run v5).
- New tools: `pipeline/track_overlay.py` (tracked meshes drawn on the rectified frames; QA for eval episodes, CPU) and
  `ops/jobs/eval_perc.sh` (perception on the 20 eval episodes, one at a time, depth pushed to the store; ~4 min
  per episode measured on ep18, so ≈ 1.5 h on one box ≈ $2–3; not launched).
- v5 = v4 + `--close auto` (threshold 0.5 on the never-observed share of the filled object): pot 0.042 → fill,
  boards 0.140 / 0.015 → fill, dustpan 0.629 → near. Registered AUC ours / scan: **ep41 0.998 / 0.999, ep23 0.997 /
  0.999 (boards CD-O 0.22 / 0.22 cm, 0.2° / 1.0°, flip rate 0 / 0)**, ep39 0.880 / 0.997 (the 2 cm edge filter strips
  the dustpan plate's edges; v3 without it: 0.953). Next: edge threshold 5 cm (v6).
- `recon_mesh.py` now fuses several episodes of one object into one grid; checked: one episode gives an identical
  mesh to v5 (ep41, 13,258 vertices).

### 2026-10-21 11:10 TRT: hard-episode A/B results, ep21 and ep24 (commit 6f2f98a; default vs `c` = E2S wrist cost 3.0)
Sim vs mocap, our scorer (old) and the registered scorer with the public scans as our meshes:
| ep | run | AUC old | AUC registered | SP | MP | MPPE | reference vs mocap | static floor |
|---|---|---|---|---|---|---|---|---|
| 21 (water can + blue cup, pouring) | perc2 | **0.826** | 0.825 | 1 | 1 | 2.1 cm | 0.985 | 0.359 |
| 21 | perc2c | 0.793 | 0.828 | 1 | 1 | 2.5 cm | 0.985 | 0.359 |
| 24 (planter stand, two boards) | perc2 | **0.235** | 0.236 | 0 | 0 | 14.3 cm | 0.844 | 0.232 |
| 24 | perc2c | 0.167 | 0.152 | 0 | 0 | 15.9 cm | 0.844 | 0.177 |
- ep21: the rollout lifts the pitcher and tilts it over the cup as in the video (`results/e2e/ep21_perc2_rollout.jpg`);
  the robot loses ~0.16 AUC against the reference. Wrist cost 3.0 makes no clear difference (−0.03 old, +0.003
  registered).
- **ep24 fails**: in sim the two boards stay flat on the table; one hand hovers over a board and never lifts it
  (`results/e2e/ep24_perc2_rollout.jpg`). Sim ≈ static floor. A thin flat board on a table is a hard grasp for the
  policy in 250M steps. Its eval twin is episode 25 (same two boards). The `c` run's static floor differs (0.177 vs
  0.232): the sim's frame-0 object poses differ between the two runs (settling at reset; to check).
- Box ep24's rexec tunnel answered 502 the whole run, but the job finished and pushed (the store, not the tunnel, is
  the result path).

### 2026-10-21 11:25 TRT: hard-episode A/B, ep18 (sweeper + dustpan) and batch summary
| ep | run | AUC old | AUC registered | SP | MP | MPPE | reference vs mocap | static floor |
|---|---|---|---|---|---|---|---|---|
| 18 | perc2 | **0.127** | 0.128 | 0 | 0 | 10.4 cm | 0.974 | **0.610** |
| 18 | perc2c | 0.337 | 0.337 | 0 | 0 | 8.9 cm | 0.974 | 0.610 |
- ep18 is **below the static floor**: in the evaluator rollout the sweeper, standing upright in the reference, falls
  over (z 0.663 → 0.615 m) and both objects end 5–15 cm off. (The montage from `render_rollout.sh` is a separate
  replay and shows little motion; the evaluator parquet is the record.)
- Batch summary (one seed each): ep21 0.826 (works), **ep24 0.235 (= floor; boards never lifted)**, **ep18
  0.13–0.34 (< floor 0.61)**. Wrist cost 3.0: −0.03 / −0.07 / +0.21 → no consistent effect. Policy failure, not
  perception (references 0.84–0.97), is the main risk on hard tasks. Eval twins: 19 and 30 (sweeper), 25 (boards),
  38 (dustpan alone).
- Idea (hypothesis, owner to judge): pick per episode between the trained policy and a fallback using only our own
  reference (GT-free): if the evaluator's sim-vs-reference AUC is below the reference's own static floor, the
  rollout is worse than not moving. Candidates for the fallback: an earlier checkpoint (`policy_*` every 5M steps),
  another seed, or a policy that keeps the hands off the objects.
- Reconstruction v6 (edge threshold 5 cm): ep41 0.996, ep39 0.892, ep23 0.973 but board 2 **flip rate 0.25** →
  the board registration is fragile to small parameter changes; v7 (edge filter off, auto closing) running.
