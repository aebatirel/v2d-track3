# Learned grasp models the owner pointed to (2026-10-24)

The owner listed four model families; identified and checked from the papers (arXiv abstracts and full HTML read
through `export.arxiv.org` / `arxiv.org/html`; the GraspGen README on GitHub). Code status is from the pages that
could be opened; DemoGrasp's and DexEvolve's project pages did not load from this environment.

| Model | What it outputs | Hands | Training / scale | Code, license | Fit for us |
|---|---|---|---|---|---|
| GraspGen (NVlabs 2025) | 6-DoF gripper poses from a point cloud or mesh (.obj/.stl/.ply/USD) | Franka Panda, Robotiq 2F-140, suction only ("this repo only supports 3 grippers") | diffusion generator + discriminator | github.com/NVlabs/GraspGen, checkpoints on HF; dataset CC BY 4.0 | Low: no multi-finger hand |
| GraspGen-X (arXiv 2606.00998, CVPR 2026) | 6-DoF poses conditioned on the gripper (swept-volume encoding) | 32 procedural grippers; zero-shot on Inspire Hand scores 0.363; "future work: 5-finger dexterous hands" | 2B grasps, 8.7K + 5.2K GPU-h labelling, 80 h on 8 A100 | github.com/NVlabs/GraspGenX (announced) | Low: wrist-pose proposals at most |
| DexGraspNet 2.0 (arXiv 2410.23004, CoRL 2024) | wrist pose + 16 joint angles per seed point; two-stage, diffusion conditioned on local geometry | LEAP hand (16 DoF) | 1,319 objects, 8,270 cluttered scenes, 427M grasps (force-closure synthesis, IsaacGym-filtered); 90.7 % real success | github.com/PKU-EPIC/DexGraspNet2, checkpoints; CC BY-NC 4.0 | Medium: LEAP != Sharpa Wave; needs retargeting or re-synthesis; candidate seeds only |
| DexEvolve (arXiv 2602.15201, RSS 2026) | refined diverse stable grasps, distilled into a diffusion model | a 12-joint hand (+ Shadow / Allegro discussed); Isaac Sim | GA: tournament selection, crossover, mutation (wrist +-0.05 m, joints +-0.5 rad), de-penetration after mutation, archive <= 1024 pruned by score + farthest-point sampling (diversity), population 32 / 128, 10,000 steps, asynchronous; > 120 distinct stable grasps per object, 1.7-6x the analytical seeds; a Handles dataset; diffusion trains ~2 days on one RTX 4090 | project page dexevolve.github.io (code status unconfirmed); paper CC BY-NC-ND | High as a method: the evolutionary refinement loop is what we would run in FlashCHORD with our hand and meshes |
| DemoGrasp (arXiv 2509.22149, ICLR 2026) | edits of ONE demonstration: wrist pose (where) + joint angles (how), as a single-step MDP solved by RL | Shadow 95 % (DexGraspNet); Inspire, Shadow, Schunk SVH, Allegro, DClaw, parallel: 84.6 % average on 6 unseen sets; real: Inspire on Franka, 110 objects incl. small thin items | IsaacGym, reward = binary success + table-collision penalty, 24 h on one RTX 4090 | project page beingbeyond.github.io/DemoGrasp (code status unconfirmed) | High as a method: our human grasp is the demonstration; the edit space is exactly our grasp-lock's |

## What this means for the grasp-lock recipe (hypotheses)
- H1 (DemoGrasp + DexEvolve): per hold, seed with the copied human grasp plus analytical grasps (edge pinch on a
  plate, wrap on a handle), then edit the wrist pose and finger joints with a gradient-free evolutionary search whose
  fitness is a zero-action replay in FlashCHORD (object stays on our perceived path through the hold, lifted, no
  slip, no table or other-hand collision; no ground truth), keeping a diverse archive. Falsified if the best evolved
  grasp on ep39 / ep18 does not lift the dust pan at zero action (sim_vs_ref over the hold frames stays near the
  floor 0.17).
- H2: for one object per episode, a per-episode search (tens of candidates x a few generations) is enough; a
  universal learned policy (DemoGrasp) or a distilled diffusion model (DexEvolve) is not needed, because we know the
  exact mesh and path. Falsified if the search needs more evaluations than a 70M fine-tune costs.
- Pretrained generators (DexGraspNet 2.0, GraspGen-X) only as extra seeds, after retargeting to the Sharpa Wave;
  their hands differ and DexGraspNet 2.0 is non-commercial (CC BY-NC 4.0; the challenge allows public pretrained
  models, owner to confirm the licence is acceptable).
