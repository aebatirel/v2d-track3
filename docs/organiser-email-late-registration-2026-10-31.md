# Draft: late team registration email (2026-10-31)

The registration form closed before the owner submitted it. Its page now reads "Registration is now closed. ... If
you have any questions, please email: V2D_Challenge@nvidia.com". This email asks for late registration and carries
the form answers from `docs/registration-form-draft-2026-10-30.md`. It is saved as an unsent Gmail draft in the
owner's account; the owner fills in the brackets and sends it.

---

To: V2D_Challenge@nvidia.com
Subject: Late team registration request: Track 3, team Imitation.Tech (already submitting on Kaggle)

Hello V2D Challenge team,

We are a Track 3 team, Imitation.Tech, and we missed the registration form before it closed. We joined all six
Track 3 Kaggle competitions, accepted their rules, and have been submitting since 24 October. Our best entry is
8th on the Track 3 AUC board (0.8146, 31 October). Until 30 October our Kaggle team was named "Ahmet Ercan
Batirel"; it is now "Imitation.Tech" on all six.

Could you please register us late, or tell us how to do so, so that our entries count for the leaderboard and the
awards? The details the form asks for are below.

Team name: Imitation.Tech
Primary contact: aebatirel@gmail.com
Track: Track 3: End-to-End Egocentric Transfer
Kaggle team IDs (Track 3): AUC 17196705, SP-SR 17196772, MP-SR 17196773, RPE 17196774, MPPE 17196776, CD-O 17196777
Code repository: https://github.com/aebatirel/v2d-track3 (shared with the GitHub account Nvidia-V2D-Challenge)
[Share the repo first, or delete this line.]

Team members:
1. Ahmet Ercan Batirel - aebatirel@gmail.com - [affiliation]
2. [Name] - [email] - [affiliation]
3. [Name] - [email] - [affiliation]
4. [Name] - [email] - [affiliation]

Team skill set:
Our team covers 3D computer vision, robot learning in simulation and GPU infrastructure, and we have built a
complete Track 3 pipeline. Perception: stereo depth (FoundationStereo), open-vocabulary detection (SAM2 proposals
ranked by DINOv2 against rendered meshes), 6-DoF object tracking (FoundationPose), visual odometry for the head
camera and 3D hand pose from MediaPipe. Reconstruction: object meshes from TSDF fusion along our own tracks, plus
lathe and part-based fits for thin and symmetric objects. Robot learning: contact-anchored retargeting to the
Sharpa hands, designed-grasp references, and FlashSAC training in FlashCHORD with pre-registered,
ground-truth-free model selection. Infrastructure: parallel training on rented cloud GPUs with automated
provenance, checkpointing and cost control. [Add each member's background, projects and publications.]

Approach:
A perception-first pipeline that turns each egocentric clip into an object-and-hand reference, then trains one
policy per episode to reproduce it in simulation.
1. Perception: FoundationStereo depth from the stereo pair; frame-0 object detection by SAM2 proposals matched
   with DINOv2 to renders of our meshes; FoundationPose tracking; visual odometry for head motion.
2. Meshes: our own reconstructions, fused from each episode's video along our tracks.
3. Hands: MediaPipe on the colour camera, lifted to 3D with stereo depth, then NVIDIA's retargeter to the Sharpa
   Wave hands. Contact-anchored retargeting snaps fingertips to object surfaces without penetration.
4. Policies: FlashSAC in FlashCHORD on floating Sharpa hands. We train two learners per episode: standard RL with
   dense object-matching rewards, and a designed-grasp "grasp lock" fine-tune that uses a stiffer floating-wrist
   servo.
5. Selection: for each episode we keep the learner with the better mean of several official evaluations against
   our own reference. No ground truth is used, and nothing is tuned on eval scores.

Hardware: cloud-based GPUs (rented RTX PRO 6000s; Google Colab for bring-up).

We will send a few rules questions (the floating-wrist servo setting and mesh provenance) in a separate email.

Thank you,
Ahmet Ercan Batirel
on behalf of Imitation.Tech
