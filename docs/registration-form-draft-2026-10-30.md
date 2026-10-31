# Draft: V2D Challenge team registration form (2026-10-30)

For the owner to paste into the Google Form and submit
(https://docs.google.com/forms/d/e/1FAIpQLSdZJYNsEPPGDeIRH2yb_Dui-lWcIxWRF2CON7UOIijzCw8zyA/viewform). The agent
cannot sign in to Google or submit the form. Fields in `[brackets]` need the owner's input.

## Registration deadline (checked 30 Oct 2026, ~18:30 UTC)
- No registration deadline is published. The challenge page timeline lists registration from 21 Sep with no end
  date. The FAQ says "Teams may register after launch".
- Kaggle API, all six Track 3 competitions: deadline 2026-11-04 22:00 UTC (17:00 EST; 5 Nov 01:00 TRT).
  `newEntrantDeadline` is unset. `mergerDeadline` is the same date and time. Max team size is 10.
- So the hard limit is the leaderboard freeze. Registering now is the safe choice: the organisers likely use the
  form to tie Kaggle teams to prize eligibility, but that is an inference.
- Kaggle team name on the Track 3 boards is **"Ahmet Ercan Batirel"** (Kaggle's default for a solo team; AUC
  0.81460, 7th, 30 Oct). Teammates who should appear on Kaggle must join each competition's team before
  4 Nov 22:00 UTC.

## Answers

**Email:** aebatirel@gmail.com (tick "Record ... as the email")

**Team Name:** Imitation.Tech (owner's choice, 30 Oct; Kaggle rename done by the owner, verified 31 Oct). Rename the Kaggle team to match on all six Track 3
competitions. Each competition has its own team (IDs: AUC 17196705, SP-SR 17196772, MP-SR 17196773, RPE 17196774,
MPPE 17196776, CD-O 17196777). On each competition page: Team tab → Team Name → Save Changes. The agent could not
do it: the public Kaggle API has no rename call, and the site's `competitions.TeamService/UpdateTeam` endpoint
returned 401 to the API token; it needs a browser login.

**Primary Contact Email:** aebatirel@gmail.com

**Team Members, Contacts, and Affiliation:**
```
1. Ahmet Ercan Batirel - aebatirel@gmail.com - [affiliation]
2. [Name] - [email] - [affiliation]
3. [Name] - [email] - [affiliation]
4. [Name] - [email] - [affiliation]
```

**Team Skill Set:**
> Our team covers 3D computer vision, robot learning in simulation and GPU infrastructure, and we have built a
> complete Track 3 pipeline. Perception: stereo depth (FoundationStereo), open-vocabulary detection (SAM2
> proposals ranked by DINOv2 against rendered meshes), 6-DoF object tracking (FoundationPose), visual odometry for
> the head camera and 3D hand pose from MediaPipe. Reconstruction: object meshes from TSDF fusion along our own
> tracks, plus lathe and part-based fits for thin and symmetric objects. Robot learning: contact-anchored
> retargeting to the Sharpa hands, designed-grasp references, and FlashSAC training in FlashCHORD with pre-registered,
> ground-truth-free model selection. Infrastructure: parallel training on rented cloud GPUs with automated
> provenance, checkpointing and cost control. Our Track 3 entry is 7th on the AUC board (0.815), up from 0.575 on
> the first upload. `[Add each member's background, projects, products and publications.]`

**Tracks:** Track 3: End-to-End Egocentric Transfer

**How does your team plan to approach the challenge?**
> A perception-first pipeline that turns each egocentric clip into an object-and-hand reference, then trains one
> policy per episode to reproduce it in simulation.
> 1. Perception: FoundationStereo depth from the stereo pair; frame-0 object detection by SAM2 proposals matched with
> DINOv2 to renders of our meshes; FoundationPose tracking; visual odometry for head motion.
> 2. Meshes: our own reconstructions, fused from each episode's video along our tracks.
> 3. Hands: MediaPipe on the colour camera, lifted to 3D with stereo depth, then NVIDIA's retargeter to the Sharpa
> Wave hands. Contact-anchored retargeting snaps fingertips to object surfaces without penetration.
> 4. Policies: FlashSAC in FlashCHORD on floating Sharpa hands. We train two learners per episode: standard RL with
> dense object-matching rewards, and a designed-grasp "grasp lock" fine-tune that uses a stiffer floating-wrist servo.
> 5. Selection: for each episode we keep the learner with the better mean of several official evaluations against
> our own reference. No ground truth is used, and nothing is tuned on eval scores.
>
> Next we are working on better reference trajectories, spoon tracking and thin-object meshes.

**Hardware:** Cloud-based GPUs (Vast.ai RTX PRO 6000 96 GB rentals; Google Colab for bring-up)

**Message to organizers:**
> We are registering late. Our Track 3 entries are already on the Kaggle boards under the team name
> "Imitation.Tech" (previously "Ahmet Ercan Batirel"). Please link them to this registration. Our code repository (github.com/aebatirel/v2d-track3) is
> shared with the GitHub account Nvidia-V2D-Challenge. We will send v2d_challenge@nvidia.com a few rules questions
> about the floating-wrist servo setting and mesh provenance. Thank you!

Before sending:
- **Share the repo first.** On 30 Oct ~18:40 UTC `aebatirel/v2d-track3` was private, and its collaborators were
  only `aebatirel`, `ardai` and `BortuceKhan`. `Nvidia-V2D-Challenge` was not among them. A pending invitation
  would not show in that list. Every submission row links a commit in this repo, and the organisers cannot open
  it until they have access. Settings → Collaborators → Add people → `Nvidia-V2D-Challenge`. If you skip this,
  delete the repo sentence.
- The questions sentence assumes the owner sends `docs/organiser-email-draft-2026-10-22.md`, which is still unsent.
  If not, delete it.
- `ardai` and `BortuceKhan` have write access to the repo. If they are teammates, list them as members.
