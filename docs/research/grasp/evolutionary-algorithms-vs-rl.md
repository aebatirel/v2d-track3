# Evolutionary algorithms vs RL for our problem: where they give an edge, where they do not

2026-10-24. Workflow `wf_cdd41283-528`, step "evolutionary algorithms vs RL" (owner's option 2: one recipe, grasp-lock,
with designed grasps). CPU and web only: no rentals, no spending, no commits. Ground truth (mocap) appears only in
numbers quoted from earlier scoring (registered AUC), never in anything computed here.

## Evidence labels
- **[M]** measured here, from files in the repo, the HF store or the lead's search logs (scripts in
  `docs/research/grasp/ea-vs-rl-scripts/`, Appendix A).
- **[M-lead]** measured earlier by the lead or the parallel audits; quoted with `file:line`.
- **[L-full]** primary source I opened in full text (PDF or HTML). **[L-abs]** primary source opened only as abstract or
  publisher/portal record. **[L-2nd]** known only through a full-text source that describes it.
- **[I]** my inference. **[E]** an estimate (numbers derived, not measured). **[H]** a new idea, stated as a hypothesis
  with the experiment that would falsify it (section 12).

---

## 0. Answer

**Short version.** Evolution and RL are not competitors for the same job here. The final artefact (a FlashCHORD policy
checkpoint run from frame 0) needs closed-loop feedback, and SAC supplies it far more cheaply than any evolutionary method
could train a 1.2M-parameter network. The **reference** (where, how and when each hand grasps) is a small, free,
open-loop design problem. Its reward is sparse and deceptive. It can be evaluated GT-free, one candidate per simulator
world. That is exactly the regime where evolutionary search has a documented edge, and our one clean measurement agrees.
The recipe that fits the evidence is the one the owner already chose, made systematic:
**evolve the grasp (robust, repertoire-seeded), then fine-tune with RL.**

| question | verdict | key numbers |
|---|---|---|
| (a) EA instead of SAC for the **policy network** | **No edge expected** [L-full + I] | Our actor has 1.22–1.28M numbers (504/722 obs → 56 actions) [M]. On MuJoCo, ES needed **3.6–8.0×** TRPO's timesteps on Hopper/Walker2d (Salimans 2017, Table 1). Pure CEM at 1M steps reached **31 %** of TD3 on HalfCheetah (2,940 vs 9,630) and **24 %** on Walker2d (CEM-RL, Table 1). A GA "took ∼15 times longer" than ES on Humanoid (Deep GA). ES wins on **wall clock** only with ≥ 720–1,440 CPU workers, against TRPO, not SAC. Our SAC does a 70M-step fine-tune in **18.7 min** [M-lead]. My estimate for ES is ≥ 10× the samples [E]. |
| (b) EA (CMA-ES / CEM / MAP-Elites) for the **grasp/reference** | **Yes**, vs RL-only and vs hand-designed grasps, provided the fitness is robust [M-lead + L] | **ep39:** the CMA-ES grasp edit took zero action from **0.176 → 0.877** sim_vs_ref (CPU), using **224 rollouts = 40,640 world-steps**, about 14 min on 4 shared CPUs. That is ~6,000× fewer steps than the 250M-step standard RL, which reached 0.826 sim_vs_ref / **0.802 ± 0.280** registered [M + M-lead]. **But** ep18's best edit was a chaotic outlier (search 0.584; 1e-5 jitter → 0.18–0.44) [M-lead]. Literature: OmniHOI's CMA-ES trajectory refinement reaches **89 %** success on the Sharpa Wave in **19 min** per trajectory; per-task RL (ManipTrans) took **385 min** for 22–26 % on other hands. SPIDER reports "10× faster than RL". |
| (c) **QD repertoire** of grasps per object | **Yes, as the layer above CMA-ES**: success-prioritised MAP-Elites over grip type × contact site × approach, then robust re-selection [L + I]; not yet measured here | Huber 2023: MAP-Elites variants that select successful solutions first "outperform all the compared methods … by a large margin" (15 methods, 10 grasping domains). In their domains a random trajectory grasps only ~0.06 % of the time, and "sparse interaction can lead to deceptive novelty". DexEvolve: archive + GA gives **> 120 distinct stable grasps per object, 1.7–6×** the analytical seeds. Cost here: ≈ 5k candidates ≈ 10–20 min GPU per hold [E]. |
| (d) **Hybrids** | **Yes**: evolve the reference, let RL fine-tune the residual (Baldwinian split). Add a cheap PBT-style seed/checkpoint selection. ERL/CEM-RL *inside* SAC are not worth building now [M + L] | **Our 18 public grasp-lock runs [M]:** Spearman ρ = **0.73** (p = 0.0007) between zero-action and fine-tuned sim_vs_ref. Every run whose zero-action replay reached ≥ 0.5 ended at ≥ 0.73 after the 70M fine-tune (8/8). Every run below 0.36 ended at ≤ 0.43 (10/10). Fine-tuning **finishes** a working reference and does not **rescue** a broken one. DexPBT: PBT with 8 agents was "the enabling factor" in 3 of its tasks, at 8× the compute. |

**Human-grasp evolution, in EA terms (section 10).** A small repertoire of grips, selected under the hardest loads
and refined gradually, maps onto concrete EA variants:
- **MAP-Elites** with success-prioritised selection: the repertoire.
- **CMA-ES** with IPOP/BIPOP restarts: local variation and selection.
- **NEAT-style complexification and incremental evolution:** the genome grows from wrist only, to synergies, to
  joints, to timing. The fitness window grows from acquisition to the whole hold.
- **Postural synergies / eigengrasps** (Santello 1998: two PCs carry > 80 % of the variance; Ciocarlie 2007): genome
  compression. This matters here because CMA-ES learns its covariance at a rate of ≈ 2/n².
- **Baldwin effect** (DERL): evolution sets the grasp, learning finishes it.

**Recommendation (pipeline in section 12):**
1. Keep SAC for the policy.
2. Make the grasp search the standard step before the fine-tune: GPU, frame-0 or rolling-horizon fitness in evaluator
   physics, λ = 256 × K = 4 robust copies (1,024 worlds), seeded from a small grip-type archive, final pick by fresh
   re-evaluation.
3. Gate the fine-tune on the zero-action result.
4. Train 2 seeds where the episode is variable.

The first GPU tests (X1, X2, X4; ≈ $7) decide whether this becomes the default (section 12).

---

## 1. Our problem, written as an optimisation problem

| element | what it is | size | how it is evaluated | cost per evaluation |
|---|---|---|---|---|
| **Policy** (the submitted artefact) | FlashSAC actor. Obs → Linear 256 → two residual blocks 256↔1024 → mean + log-std heads (56 = 2 hands × (6 wrist + 22 fingers)) [M: checkpoint header] | **1,219,008** numbers (ep35, 504-D obs); **1,275,688** (ep3, 722-D obs) [M] | Official evaluator: 1 world, frame 0, no assist, VOC 0, CUDA [M-lead `work-log.md:2317-2319`] | Training throughput 45–62.5k env-steps/s at 4,096 worlds. 70M fine-tune **18.7 min**; 250M ≈ 1.2–1.6 h [M-lead `work-log.md:2336-2337`, `STATUS.md:363-365`] |
| **Reference** (ours, free) | Per frame and hand: wrist target (7) + 22 finger targets. The policy acts as a residual on it (wrist ±0.2 m / ±1 rad, fingers ±1 rad) [M-lead note 23] | ~420 frames × 2 × 29 ≈ 24k numbers. **Per-hold grasp edit θ: 28** (3 wrist offset in the object frame, 3 rpy, 22 finger offsets) in `tools/grasp_evolve.py` | Zero-action replay in FlashCHORD scored with the kit's ADD-AUC against **our perceived** object path (GT-free) | One 421-frame replay ≈ **34 s incl. setup** on a training GPU (1 world) [M-lead `work-log.md:2073-2074`]. CPU, 8–16 worlds: 16–76 s per generation [M] |
| **Noise / landscape** | Evaluator not deterministic across runs (GPU) | – | Same policy, 8 evaluations: **0.13–0.41** vs mocap [M-lead `STATUS.md:239`]. Same zero-action reference, 3 GPU replays: **0.150 / 0.172 / 0.185** [M-lead `work-log.md:2248`] | CPU replays are deterministic in a fresh process [M-lead `work-log.md:2788-2790`] |
| **Chaos** | Contact-rich, stiff | – | ep18 sweeper best edit: **1e-5 jitter → 0.18–0.44** (nominal 0.374). ep39 pan edit: 1e-3 jitter → mean 0.841 (0.78–0.91); 1e-2 jitter → mean 0.46, 3 of 6 copies fail [M-lead `work-log.md:2788-2792`] | – |

Two consequences [I]:
- The problem has a natural split. A **closed-loop, high-dimensional** part (the network, robust to evaluator noise)
  suits gradient-based RL with replay. A **low-dimensional, open-loop, sparse-reward** part (the grasp design) suits
  population search with one candidate per world.
- Every evolved solution is open-loop on a chaotic, noisy system. Its fitness must therefore be **robust by
  construction**: averaged over perturbations and re-evaluated before selection. Otherwise the search selects lucky
  trajectories (winner's curse; section 8).

---

## 2. What our own search logs show [M]

`tools/grasp_evolve.py` is a hand-written CMA-ES (Hansen's defaults, `grasp_evolve.py:229-232`) plus an optional GA.
I summarised the lead's six CPU search runs and one robust test (`ea-vs-rl-scripts/search_logs.py`, output in `search_logs_output.txt`):

| run (object, window) | worlds × gens | evaluations | world-steps | wall clock | unedited → best (gen) | generation **mean** fitness (first → last) | final σ |
|---|---|---|---|---|---|---|---|
| ep39 pan, f22–122 (round 1) | 16 × 8 | 128 | 12,800 | 136 s | 0.309 → **0.810** (2) | 0.303 → 0.383 | 0.884 |
| ep39 pan, f22–312 (round 2, init = round 1) | 8 × 12 | 96 | 27,840 | 720 s | 0.108 → **0.865** (3) | 0.141 → 0.112 (peak 0.340 at gen 3) | 0.823 |
| ep18 pan, f0–207 | 8 × 10 | 80 | 16,560 | 533 s | 0.211 → 0.404 (7) | 0.216 → 0.357 | 0.885 |
| ep18 sweeper, f10–343 (after the fresh-env fix) | 8 × 12 | 96 | 31,968 | 476 s | 0.375 → 0.584 (7) | 0.368 → 0.372 | 0.820 |
| ep24 board 1, f0–260 | 8 × 10 | 80 | 20,800 | 622 s | 0.194 → 0.513 (**0**) | 0.245 → 0.282 | 0.809 |
| ep24 board 2, f12–264 | 8 × 4 | 32 | 8,064 | 427 s | 0.193 → 0.283 (1) | 0.181 → 0.135 | 0.939 |

Readings [M + I]:
1. **The CMA-ES never adapted.** σ only drifted from ≈ 0.95 to 0.81–0.89. With n = 28 and λ = 8–16, Hansen's default
   learning rates give a covariance time constant 1/(c1 + cμ) of **110–222 generations**
   (`cma_constants_output.md`). The runs used 4–12 generations, so in practice they were an isotropic
   (μ/μ_w, λ)-ES around the seed with best-ever (elitist) bookkeeping. With λ = 64 the time constant is 27
   generations; with **λ = 256 it is 7**. With an 8-D synergy genome at λ = 64 it is 3.5.
2. **The best is an outlier, not the population.** The generation means stay near the unedited value (0.30–0.38 on ep39
   round 1) while single bests jump: 0.81 at gen 2, 0.45 at gen 4, 0.71 at gen 5. In round 2 the mean collapsed back
   to 0.11 by gen 11. The non-elitist CMA mean wandered off the basin, and only the stored best kept 0.865. This is
   best-of-N selection on a noisy, chaotic objective. It worked on ep39 because a real mm-scale basin exists (jitter
   1e-3 keeps 0.84). It failed on ep18, where the "best" was a 1e-5-wide spike.
3. **The fitness window matters.** Round 1 (f22–122) at 0.810 baked to only **0.530** over the full episode. Round 2 on
   the whole hold (f22–312) baked to **0.877** [M-lead `work-log.md:2737-2747`]. This is incremental evolution: fit the
   acquisition first, then the full task.
4. **A tool issue found here.** `--init` converts the previous best to normalised units with the *current* σ and clips
   at ±4σ (`grasp_evolve.py:228, 254`). The robust test `evo/oa/robust_test.json` (σ_fin 0.15) started from round 2's
   best (σ_fin 0.3), so **8 of its 22 finger offsets were clipped from up to 0.98 rad to ±0.60 rad**. The 0.786
   robust mean therefore belongs to a different edit than the 0.877 one. (The CMA mean itself stays unclipped; the
   evaluated starting point and all samples are clipped.) Fix: do not clip the init point, rescale the bound to the
   init, or warn when |init/σ| > 4.
5. **Accounting.** The ep39 result (zero action 0.176 → 0.877) used **224 rollouts and 40,640 world-steps**. The
   standard RL that reached 0.826 sim_vs_ref on the same episode used 250M env-steps, ≈ 6,000× more [M]. The
   comparison is not like for like: the search started from the grasp-lock reference with ILC and only fixes the
   open-loop part. Its result is CPU physics and still unconfirmed on the GPU.

---

## 3. EA as a replacement for RL on the policy (literature)

| method | what it does | numbers that matter for us | source |
|---|---|---|---|
| **OpenAI-ES** (Salimans et al. 2017) | Gaussian parameter perturbations, mirrored sampling, rank fitness; optimises a Gaussian-smoothed objective | **1,440 workers: 3-D humanoid in < 10 min**; Atari ≈ 1 h on 720 CPUs. ES/TRPO timestep ratio at 100 % of TRPO's 5M-step score: HalfCheetah 0.58, Hopper **6.94**, Walker2d **7.88**, Swimmer 0.30 (Table 1). "Invariant to action frequency and delayed rewards, tolerant of extremely long horizons". Steps "scale linearly with the dimension" for non-smooth problems (Nesterov–Spokoiny), but the intrinsic dimension is what matters | [L-full] arXiv 1703.03864 |
| **ARS** (Mania, Guy, Recht 2018) | Random search on **linear** policies, state normalisation, top-b directions | "At least **15 times** more computationally efficient than ES". Humanoid-v1: 142,600 episodes to reach 6,000. SAC beats ARS on HalfCheetah (≈ 11,500 vs 5,024 at 1e7 steps) and Ant. Over 100 seeds, success **70 %** of the time on most tasks, Walker2d 20 % | [L-full] arXiv 1803.07055 |
| **Deep GA** (Such et al. 2017) | Truncation selection + Gaussian mutation on 4M+ parameters, compact seed encoding | Atari in "∼4 hours on one desktop". Humanoid: "∼15 times longer to perform slightly worse than ES" (∼1,500 vs ∼100 generations). Random search beats DQN/A3C/ES on some Atari games | [L-full] arXiv 1712.06567 |
| **CMA-ES** (Hansen 2016 tutorial) | Rank-μ + rank-one covariance learning, step-size path | c1 ≈ 2/n², so the covariance adapts slowly for n ≫ 10. "Increasing λ usually improves the global search capability and the robustness". Restarts with increasing λ are "a useful policy". Decrease α_cov on noisy functions | [L-full] arXiv 1604.00772 |
| IPOP / BIPOP / sep-CMA | Restarts with growing λ; interlaced large/small-λ restarts; diagonal C | IPOP better in 29 of 60 multimodal cases. BIPOP solved 23/22/20 of 24 BBOB functions in 10/20/40-D. sep-CMA: linear time/space, larger learning rate; beats CMA-ES on separable problems and, for n > 100, even on Rosenbrock | [L-abs] Auger & Hansen 2005; Hansen 2009; Ros & Hansen 2008 (ip-paris research-portal records) |
| UH-CMA-ES (Hansen et al. 2009) | Uncertainty handling by re-evaluation and rank-change measurement | "Prevents premature convergence … requires only a small number of additional function evaluations"; used on noisy online controller tuning | [L-abs] IEEE TEC 13:180 |
| **NES / xNES / SNES** (Wierstra et al. 2014) | Natural-gradient search distribution; rank fitness shaping; separable variant for high-D | Fitness shaping makes it invariant to order-preserving fitness transforms | [L-full] arXiv 1106.4487 |
| **PGPE** (Sehnke et al. 2010) | Policy gradient with exploration in parameter space; symmetric sampling | "Lower variance gradient estimates"; beats standard policy gradients, finite differences and population heuristics incl. humanoid standing | [L-full] Neural Networks 23(4) |
| **CEM** | Fit a Gaussian to the elite fraction | At equal 1M steps: CEM 2,940 vs TD3 9,630 (HalfCheetah), 1,055 vs 3,355 (Hopper), 928 vs 3,808 (Walker2d); CEM wins only on Swimmer (351 vs 63). iCEM (planning) needs **2.7–22× fewer samples** than CEM | [L-full] CEM-RL arXiv 1810.01222; iCEM arXiv 2008.06389 |
| Qualitative ES vs PPO (Milano & Nolfi 2022) | Review + experiments | "Existing comparative studies do not provide evidence indicating a general superiority". TRPO beat CMA-ES on 11 of 12 control tasks at equal steps (Duan 2016, via this paper). EAs are less sample-efficient but cheaper per sample and parallelise better | [L-full] arXiv 2205.07592 |
| ES ≠ finite differences (Lehman et al. 2018) | ES optimises the population's mean reward | "Seeking parameters that are robust to perturbation". PG humanoid networks are "significantly less robust to parameter perturbation than ES-based policies" | [L-full] arXiv 1712.06568 |
| Overview (Sigaud & Stulp 2019) | Taxonomy of policy search | Gradient-free methods learn from whole-episode returns. Importance mixing improves sample efficiency "but not large enough to compete with deep RL" | [L-full] arXiv 1803.04706 |

**Applied to our policy [E + I].** ES is a candidate only where RL fails for reasons ES avoids: sparse or delayed
reward, long horizons, needing a policy robust to parameter noise. That list does fit part of our failures. The
fine-tunes that degrade (ep18 0.446 → 0.060) learn contact avoidance under a shaped reward that differs from the
evaluator's frame-0 metric. ES could optimise the evaluator's metric directly. But:
- The network has 1.2M numbers and acts on 56 dimensions at 20 Hz through contact.
- In the literature, wall-clock parity needs ~10³ parallel workers against TRPO (not SAC), and sample parity holds only
  for linear policies on locomotion.
- One ES update with one perturbation per GPU world (≈ 2,000 mirrored perturbations in 4,096 worlds) costs about
  one batched 420-frame rollout. That is ≈ 30–60 s [E, from the 27 s per batched pass of SAC training in section 6].
  OpenAI-style ES needed ≈ 100 generations to pass the Humanoid threshold (Deep GA, SI 7.5). Even that many
  generations here would take ≈ 1–2 h, 3–6× a 70M SAC fine-tune, on a 1.2M-number network and a harder contact
  task [E].

**Verdict:** no edge for the policy network. A low-dimensional *policy polish* (output bias/gain, 112 numbers) or ES on
a reduced action basis is a hypothesis to test only after the grasp work (H7).

---

## 4. Hybrids of evolution and RL (literature)

| method | what it does | numbers / claims | relevance | source |
|---|---|---|---|---|
| **ERL** (Khadka & Tumer 2018) | EA population fills a DDPG replay buffer; the RL actor is periodically inserted into the population | EAs "suffer from high sample complexity and struggle … [with] a large number of parameters"; ERL beats DDPG and the EA on MuJoCo. Its selection operator handles "deceptiveness and sparsity" | Low: our SAC already gets diverse data from 4,096 worlds | [L-full] arXiv 1805.07917 |
| **CEM-RL** (Pourchot & Sigaud 2019) | CEM over actor weights; half the population gets TD3 gradient steps from a shared critic | CEM-TD3 vs TD3 at 1M steps: HalfCheetah 10,725 vs 9,630; Walker2d 4,711 vs 3,808; Hopper 3,613 vs 3,355; Ant 4,251 vs 4,027 (+6 % to +24 %) | Low-medium: modest gains, sizeable build into FlashSAC | [L-full] arXiv 1810.01222 |
| **PBT** (Jaderberg et al. 2017) | Truncation selection + perturbation of hyperparameters and weights during training | Populations of 10–80; "faster wall-clock convergence and higher final performance"; most of the gain comes from copying weights (exploit) | **Medium**: our seed variance is large (ep3 s42 0.965–0.981 vs s43 0.843 at 40M) [M-lead `work-log.md:2344-2350`] | [L-full] arXiv 1711.09846 |
| **DexPBT** (Petrenko et al. 2023) | Decentralised PBT for Allegro + Kuka, Isaac Gym, 8,192 envs per GPU | 5×10⁹ transitions per agent take **30 h** single-arm / **40 h** dual-arm on one V100. With |P| = 8 at equal compute, PBT "becomes the enabling factor" in 3 scenarios. |P| = 16 → 32 keeps improving | Medium as a pattern; full PBT is 8× our per-episode budget | [L-full] arXiv 2305.12127 |
| PBRL (Shahid et al. 2024) | PBT for PPO/SAC/DDPG in Isaac Gym (incl. Shadow Hand) | PBRL agents beat non-evolutionary baselines in cumulative reward; SAC/DDPG not run at 16 agents (memory) | Supports PBT-lite with SAC | [L-full] arXiv 2404.03336 |
| EPO (2025) | Latent-conditioned population sharing one actor-critic; on-policy | Claims better sample efficiency than PPO on dexterous manipulation; notes EvoRL methods are "extremely sample-inefficient" | Low for us (on-policy, new build) | [L-full] arXiv 2503.19037 |
| **DERL** (Gupta et al. 2021) | Evolution over morphologies, RL inside each lifetime | "Evolution rapidly selects morphologies that learn faster" (Baldwin effect) | **High as a principle**: evolve what RL starts from | [L-abs] arXiv 2102.02202 |

---

## 5. Quality diversity and novelty, and their use for grasping

| method | idea | numbers / claims | source |
|---|---|---|---|
| **MAP-Elites** (Mouret & Clune 2015) | Keep the best solution in every cell of a user-chosen behaviour grid | "Significantly outperforms" a traditional EA even on **global performance** (the single best solution); lineages show stepping stones | [L-full] arXiv 1504.04909 |
| **Novelty search** (Lehman & Stanley 2011) | Select for behavioural novelty only | Beats objective search on deceptive maze and biped tasks | [L-full] Evol. Comput. 19(2) |
| **Intelligent Trial & Error** (Cully et al. 2015, Nature) | Offline MAP-Elites map (~13,000 hexapod gaits) + Bayesian-optimisation adaptation | Adapts "in less than two minutes"; damaged legs in 8 [3; 16] physical trials | [L-full] arXiv 1407.3501 |
| CMA-ME / CMA-MAE (Fontaine et al. 2019; Fontaine & Nikolaidis 2023) | CMA-ES emitters inside MAP-Elites; annealed acceptance | CMA-ME "more than doubles" MAP-Elites on QD metrics. CMA-MAE fixes CMA-ME's early abandonment of the objective and flat-objective trouble | [L-abs] arXiv 1912.02400; 2205.10752 |
| QD-RL / QDPG (Pierrot et al.), PGA-ME (Nilsson & Cully 2021), DCG-ME / DCRL-ME (Faldor et al. 2023/24) | Add policy-gradient variation operators to MAP-Elites so it can evolve large networks | MAP-Elites' random mutations "become inefficient in high-dimensional search spaces"; PG operators fix that | [L-full] arXiv 2006.08505 (current title QDPG), 2303.03832, 2401.08632; PGA-ME [L-2nd] via DCRL-ME |
| **QDax / accelerated QD** (Lim et al. 2022; Chalumeau et al. 2023) | MAP-Elites with huge batches on accelerators | Runtimes cut by "two factors of magnitudes, turning days of computation into minutes". **Cutting the number of generations by two orders of magnitude "does not impact the performance"** | [L-full] arXiv 2202.01258, 2308.03665 |
| **QD for grasping trajectories** (Morel et al. 2022, ICRA) | Novelty search + behaviour shaping, open-loop trajectories (3 × n_dof + 1 parameters) | 1,000 generations × 50 offspring (≈ 50k evaluations) per object; repertoires of 13,148 ± 4,574 (Baxter), 3,490 ± 4,706 (Pepper), 3,929 ± 2,262 (Kuka) successful grasps. Some runs found none (bootstrap problem) | [L-full] arXiv 2205.08189 |
| E2R (Huber et al. 2022) | Hierarchical novelty search for grasping repertoires | Same group; prior hand-crafted structure helps bootstrapping | [L-full] arXiv 2210.07887 |
| **QD under sparse interaction** (Huber et al. 2023) | 15 methods × 10 domains (Kuka + WSG50 / Allegro, 5 YCB objects), 100k–400k evaluations | **ME with success-first selection (ME-scs) wins by a large margin**. Random trajectories touch the object 9–54 % of the time and grasp it ≈ 0.06 %. "Sparse interaction can lead to deceptive novelty"; CMA-ME and CMA-MAE were beaten | [L-full] arXiv 2308.05483 |
| QD with priors for 6-DoF grasps (Huber et al. 2024) | Contact-based priors + QD, 2–5-finger grippers incl. Allegro | QD "outperforms commonly used methods by a large margin"; diversity transfers sim-to-real | [L-full] arXiv 2403.06173 |
| **DexEvolve** (2026) | Analytic seeds → asynchronous GA in Isaac Sim (tournament, finger-config crossover, mutation, de-penetration), novelty-gated archive ≤ 1,024 | **> 120 distinct stable grasps per object, 1.7–6×** the seeds. Converges in ≈ 10k sim steps. From random init it recovers stability but loses diversity: seeds matter | [L-full] arXiv 2602.15201 (local HTML copy) |
| **DemoGrasp** (2025/26) | Edit one demonstration (wrist SE(3) + joint deltas) as a single-step RL problem | 95 % (DexGraspNet, state). Ablation: **uniform sampling + BC 77.6 % vs RL 96.2 %**, because sampling yields multimodal data that BC cannot fit. Per-instance search avoids that problem: nothing is distilled | [L-full] arXiv 2509.22149 (local HTML copy) |
| GraspIt eigengrasp planner (Ciocarlie et al. 2007) | Simulated annealing in a 2-D eigengrasp subspace | Low-dimensional posture subspaces make dexterous grasp search tractable; 100,000-iteration annealing example | [L-full] IROS 2007 (Columbia PDF) |
| EvolvingGrasp (2025) | Preference fine-tuning of a grasp generator | "Evolutionary" in name only (no population search) | [L-abs] arXiv 2503.14329 |

---

## 6. GPU-scale evolution (literature)
- **EvoJAX** (Tang et al. 2022): on one accelerator, MNIST 36 → 3 min, cart-pole 37 → 2 min, **Brax Ant
  locomotion 201 min (96 CPUs) → 9 min**; "10 ∼ 20 times faster" [L-full arXiv 2202.05008].
- **evosax** (Lange 2022): JAX ES library (CMA-ES, OpenAI-ES, ARS, PGPE, GA variants) with batched `ask`/`tell`
  [L-full arXiv 2212.04180].
- **Brax** (Freeman et al. 2021): ships ES next to PPO/SAC, but analyses only PPO and SAC ("defer analysis of ES … to
  future work"). There are no published Brax ES numbers to quote [L-full arXiv 2106.13281].

**For us [I]:** FlashCHORD already gives us the GPU batch. The one-candidate-per-world design of `grasp_evolve.py` is the
EvoJAX pattern. The cost of a generation is set by the number of sequential steps (frames), not by the number of
worlds, until the GPU saturates. SAC's 70M steps over 4,096 worlds are ≈ 41 sequential 420-frame passes in 18.7 min,
≈ 27 s per batched pass incl. updates [M-lead, derived]. A search generation over the same frames should therefore
cost tens of seconds whether it has 256 or 4,096 worlds [E]. **Worlds are nearly free; generations are not.** This
favours large λ (CMA-ES learning rates rise with μ_eff, so the covariance adapts in fewer generations) and
large-batch MAP-Elites (QDax: few generations, little loss).

---

## 7. Sampling-based MPC and trajectory optimisation without learning
- **MPPI** (Williams et al. 2017/18) [L-full arXiv 1707.02342]. **Predictive sampling in MuJoCo MPC** (Howell et al.
  2022) [L-full arXiv 2212.00541]: a "surprisingly competitive" elementary sampler. It solves Shadow-Hand in-hand
  cube reorientation "from scratch, in real time", with no learning.
- **DIAL-MPC** (Xue et al. 2024) [L-full arXiv 2409.15610]: diffusion-style annealed MPPI. It cuts standard MPPI's
  tracking error **13.4×** and "outperforms RL policies by 50 % in challenging climbing tasks without any training".
- **Hess et al. 2024** [L-full arXiv 2411.06183]: first sampling-based MPC in-hand manipulation on a physical
  tendon-driven hand (MJPC). Ball rotation at ≈ 0.96–1.01 rad/s. The objective needed VLM tuning, at < 2 min per
  iteration.
- **Jacta** (Brüdigam et al. 2024) [L-full arXiv 2408.01258]: planner demonstrations in the replay buffer let RL learn
  tasks "where traditional reinforcement learning alone only makes little progress".
- **Video-to-dexterous-hand pipelines**, the closest to our task:
  - **SPIDER** (Pan et al. 2025): annealed-kernel sampling with contact guidance; "**10× faster than RL**"; its output
    serves "as feasible reference motion for efficient RL policy learning" [L-full arXiv 2511.09484].
  - **Do As I Do** (2026): Sharpa Wave; MPPI-style annealed sampling, **1,024 samples × 32 iterations** per 0.5 s
    planning step on a 3 s horizon, warm-up steps, **random force perturbations**; **25 → 71 %** success
    [L-full arXiv 2606.19333].
  - **OmniHOI** (2026): **CMA-ES over per-keyframe offsets**, rolling horizon that resumes from the saved simulated
    state of the previous keyframe; cost terms for pose, contact gap, **antagonistic contact-pair force shortfall**,
    penetration and an end-of-window term. **SharpaWave 89 % success, 1.5 cm, 10°**, **19 min** per trajectory (RTX
    4090). SPIDER on the same hand 19 %; per-task RL (ManipTrans) **385 min**, 22–26 % on the other hands. Caveat:
    their hand root is welded to a mocap target, finger kp = 500 [L-full arXiv 2610.10855, Table 2].

**For us [I]:** the evaluator runs *our network*, not a planner, so MPC cannot run at evaluation. It is usable only
offline, to write the reference or as demonstrations. Note 23 already called this route a "SPIDER / Do As I Do-style
optimiser". The literature says such optimisers solve dexterous tracking at ~10–20× less compute than per-task RL, and
that their output is a good start for RL. That is the same split as section 0.

---

## 8. Known failure modes, and where they already bit us

| failure mode | literature | our evidence |
|---|---|---|
| **High dimension** | Steps grow ∝ n for non-smooth problems (Salimans §3.2); CMA-ES c1 ≈ 2/n² (Hansen); random mutations inefficient in high-D (DCRL-ME) | 28-D CMA with λ = 8–16 never adapted C (section 2) [M] |
| **Sample cost** | ES 3.6–8.0× TRPO on hard MuJoCo; CEM at 24–31 % of TD3 at equal steps | Irrelevant for the 28-D grasp (224 rollouts were enough on ep39). Decisive against ES on the 1.2M-number policy [M + E] |
| **Deceptive / sparse fitness** | Novelty search (Lehman & Stanley 2011). In grasping, novelty itself becomes deceptive under sparse interaction (Huber 2023) | Grid search around the copied ep3 pinch: 366 variants, **hold rate 0** for every one [M-lead `work-log.md:2163-2165`]. Local search cannot change the grip type. The built wrap then held 34/36 [M-lead `work-log.md:2194-2196`] |
| **Chaos / noise → winner's curse** | Robustness-seeking ES (Lehman 2018); UH-CMA-ES re-evaluation (Hansen 2009); chaotic gradients (Metz 2021, Suh 2022 [L-full]) | ep18: search best 0.584 vs fresh 0.374, 1e-5 jitter → 0.18–0.44. ep21: one evaluation 0.831 vs 5-repeat mean 0.27 [M-lead `work-log.md:2664-2666`] |
| **Simulator state leaking between evaluations** | – (implementation) | MuJoCo-Warp warm start survived `env.reset`: the same edit scored 0.41–0.59 vs 0.508 fresh. More state leaked across generations; fixed with a fresh environment per generation [M-lead `work-log.md:2768-2780`] |
| **Fitness ≠ evaluation conditions** | OmniHOI rolls the horizon from the *simulated* state of frozen earlier keyframes | `grasp_evolve.py` resets objects and hands to the reference at the window start (`:180`). Later holds are scored from states the evaluator never reaches. ep18 sweeper: search 0.73 vs full replay 0.357 (partly chaos) [M-lead `work-log.md:2763-2766`] |
| **CPU ≠ GPU physics** | – | Search on CPU, evaluator on CUDA; GPU replays of one reference vary 0.150–0.185 [M-lead]. The ep39 0.877 has not been replayed on the GPU |
| **Contact-buffer limits** | – | Training logs are "full of nefc overflow … njmax" [M-lead `work-log.md:2376`]. A many-world search could drop contacts the 1-world evaluator keeps (or the reverse). Check `nacon`/`naconmax` with `GE_CONTACTS=1` on the GPU |
| **Box bounds / restarts** | – | The `--init` clip changed 8 of 22 finger offsets of the ep39 best in the robust test (section 2, item 4) [M] |

---

## 9. Answers in depth

### (a) EA for the policy network vs SAC
- **Expected edge: none, and probably a large loss** [E].
  - Our network is 1.2–1.3M numbers [M].
  - At equal samples, pure CEM reaches 24–31 % of TD3 on hard MuJoCo tasks. ES needs 3.6–8.0× the steps of TRPO, and
    TRPO is itself far behind SAC (ARS Table 3: HalfCheetah at 1e7 steps, SAC ≈ 11,500 vs TRPO ≈ 1,800) [L-full].
  - My estimate for an ES policy matching a 70M-step SAC fine-tune is ≥ 0.7–2.5B env-steps. That is 2–7 h on one GPU
    at an assumed 100k pure-simulation steps/s, vs **18.7 min** measured for SAC [E vs M].
- **Where ES would have an argument:** it can use the official metric directly (frame-0, no assist, whole-episode
  AUC) and it prefers parameter-robust solutions. Two of our recurring failures are a training/evaluation mismatch
  (degrading fine-tunes, noisy checkpoints).
  - The cheaper way to get the same benefit is a selection-level fix inside the RL recipe: choose checkpoints by
    ≥ 3 repeated evaluator rollouts (already adopted, `2fb6cd8`), plus PBT-lite (d).
  - A low-dimensional ES "polish" of the trained actor's 56-D output bias and gain against the evaluator metric is a
    cheap test (H7). I expect it to falsify the edge.

### (b) EA for the low-dimensional grasp/reference design with a simulator fitness
- **Expected edge vs RL-only: yes, on the open-loop part, at 1–2 orders of magnitude less compute, provided the
  search is robust.**
  - Measured on ep39 [M-lead]: a CPU search of ~14 min (224 rollouts) gave zero action **0.877**. Standard RL needed
    250M steps (≈ 1.6 GPU-h, ≈ $2.0–2.3) for 0.826 sim_vs_ref, and one of its 5 rollouts failed (0.241).
  - Literature on the same task family: OmniHOI CMA-ES 19 min vs per-task RL 385 min; SPIDER 10× faster than RL;
    Do As I Do 25 → 71 % without RL [L-full].
  - Where RL-only also fails (ep24 boards: standard 0.25–0.39 [M-lead `STATUS.md:162-164`]), design search is the
    only lever we have.
- **Expected edge vs hand-designed grasps: yes in two ways.**
  1. Where no rule fits (plates, boards, lid), the search finds what the rule missed. ep39 went from 0.176 to 0.877;
     the copied clamp scored 0.164.
  2. Where rules conflict across episodes, a per-episode search chooses per episode. The anatomy closing rule (MCP
     first, slow close, palm press) took ep35 from 0.15–0.27 to 0.521 but cost ep3 0.658 → 0.429
     [M-lead `work-log.md:2300-2328`].

  Hand-designed grasps remain the right **seeds**:
  - DexEvolve: from random init the GA "recovers stability" but loses diversity.
  - Morel / Huber: random grasp exploration rarely bootstraps (≈ 0.06 % success).
  - Our 366 local variants of the wrong grip type never held.
- **Conditions for the edge to hold [I]:**
  1. Robust fitness: K ≥ 4 copies with θ jitter **and** start-state noise (object pose within perception error, small
     random forces as in Do As I Do), mean or a lower quantile.
  2. Final pick by **fresh re-evaluation** of the top 5–10 elites (≥ 16 noisy rollouts each, on the GPU), not the
     best-ever score.
  3. Evaluator conditions: frame-0 start or OmniHOI-style rolling horizon from the saved simulated state; all objects
     in the fitness; GPU physics.
  4. A genome CMA-ES can adapt in 20 generations: λ = 256 (1,024 worlds with K = 4), or an 8–11-D synergy genome, or
     sep-CMA.
  5. Timing genes for the failures that are timing (ep18 sweeper, ep39 carrier): approach start, closure frame,
     closure order/speed, squeeze, which hand.

### (c) QD repertoire per object, then selection by fitness
- **Design [I]:**
  - **Behaviour descriptors:** grip type × contact site × approach. Five grip types are seeded from templates: key
    pinch, hook through a ring or handle, oblique wrap/squeeze, plate pinch (fingers under, thumb on top), and
    three/five-digit chuck/disc. Contact site is ≈ 4 bins along the object's principal axis. Approach has 3 bins: top,
    side, under (hands pass through the table in this simulator). That gives ≈ 60 cells per hold.
  - **Fitness:** robust hold-window AUC vs our reference. Selection is success-first (ME-scs, Huber 2023), not
    novelty.
  - **Search:** CMA-ES emitters inside promising cells (CMA-ME style), then re-evaluation of the top elites under
    fresh noise.
- **Why it helps [L + I]:**
  1. It escapes the seed's grip type. The 0.889 standard-RL ep18 policy found a lateral key pinch and a hook through
     the ring, not the copied clamp (`docs/research/grasp/rl-discovered-grasps.md`).
  2. It hedges chaos: choose the elite with the best *re-evaluated* robustness.
  3. It supports two-hand episodes, where per-hold elites are combined and evaluated jointly in one batch.
  4. It transfers: a public-episode archive seeds the eval twin's search (ep39 → eval 38, ep18 → 19, ep24 → 25,
     ep2 → 1). Fitness uses our perception only, so this is inference-legal. This is Cully-style adaptation from a
     prior map.
- **Cost [E]:** ≈ 5k candidate evaluations × K = 4 ≈ 20k rollouts ≈ 5 batches of 4,096 worlds ≈ 5–15 min of GPU per
  hold, ≈ $0.1–0.4. Morel needed ≈ 50k evaluations from random seeds; our seeds start in contact.
- **Not yet measured.** H4 (experiment X3) in section 12 tests it.

### (d) Hybrids
- **Evolve the reference, RL fine-tunes the residual.** This is the current recipe shape, and our runs measure the
  Baldwin effect directly [M] (`ea-vs-rl-scripts/baldwin_table.py`, `baldwin_table_output.md`):

| ep | run | floor (static) | zero action | fine-tuned sim_vs_ref (5 evals) | registered AUC vs mocap |
|---|---|---|---|---|---|
| 27 | glockpub / sf1227 / w2 (s43) | 0.579 | 0.590 / 0.655 / 0.650 | 0.979 / 0.978 / 0.972 | 0.972 / 0.963 / 0.957 |
| 12 | glockpub / dr12 / sf1227 / w2 (s43) | 0.605 | 0.602 / 0.656 / 0.560 / 0.514 | 0.926 / 0.892 / 0.899 / 0.857 | 0.909 / 0.869 / 0.886 / 0.854 |
| 31 | e2 | 0.587 | 0.607 | 0.731 | 0.767 |
| 26 | w1 (re-plan kept: zero 0.490) | 0.672 | 0.212 | 0.426 | 0.383 |
| 21 | e2 | 0.364 | 0.357 | 0.268 | 0.281 |
| 2 | e3 | 0.506 | 0.185 | 0.326 | 0.306 |
| 18 | glockpub / dr18 / kf18 / rp18 / e1 | 0.619 | 0.239 / 0.214 / 0.066 / 0.093 / 0.135 | 0.290 / 0.206 / 0.248 / 0.353 / 0.310 | 0.320 / 0.220 / 0.219 / 0.405 / 0.302 |
| 24 | glockpub | 0.220 | 0.219 | 0.173 | 0.202 |
| 39 | e3 | 0.176 | 0.175 | 0.173 | 0.174 |
| *eval 3* (spoon, sim_vs_ref only) | spoon3R | 0.439 | 0.658 | 0.968 | – |
| *eval 35* (spoon, sim_vs_ref only) | ft_ep35k | 0.112 | 0.412 | 0.978 | – |

  - **Readings** (the 18 public rows; eval rows from `work-log.md:2315-2342`):
    - Spearman ρ(zero action, fine-tuned) = **0.73**, p = 0.0007.
    - All 8 public runs whose zero action was ≥ 0.5 finished at ≥ 0.73. All 10 below 0.36 finished at ≤ 0.43.
    - The two eval spoons show the same direction: a reference that holds the object (0.41–0.66) is lifted to
      0.97–0.98 by 40–70M steps.
  - **[I]** The RL fine-tune completes a reference whose hands are in the right place and do not disturb the scene. It
    does not invent a grasp that the reference lacks. Where the reference never acquires the object, it learns
    avoidance (ep18 0.446 → 0.060).
  - So evolution must deliver a reference that *already holds*. A zero-action gate (≥ floor + 0.1 and ≥ 0.5, rest
    check passed) decides when to fine-tune. This is H5.
- **PBT over seeds and checkpoints [L + M + E].**
  - Full PBT (DexPBT) costs |P| × compute.
  - A cheap version fits our budget: 4 seeds × 20M steps, keep the best 2 by 3 evaluator rollouts each, continue them
    to 70M, pick by 5 rollouts.
  - Cost ≈ 180M steps ≈ 48 min ≈ $1.2 per episode [E, at 62.5k steps/s].
  - Only for episodes whose first seed is variable: rollout sd > 0.05, or a 40M/70M disagreement. Seed spread already
    measured: ep3 0.965–0.981 vs 0.843; ep12 0.910 / 0.886 / 0.854.
- **ERL / CEM-RL inside FlashSAC:** +6–24 % on MuJoCo at 1M steps, but a substantial build into a pinned trainer. Not
  now [I].
- **Demonstrations into the replay buffer (Jacta, RLPD-style):** cheap. Zero-action rollouts of the evolved reference
  can be inserted as demonstrations, which protects the early fine-tune from forgetting the grasp. This is a candidate
  if H5's gate passes but fine-tunes still degrade.

---

## 10. Human-grasp evolution and the EA variants that embody it

This builds on `docs/research/grasp/evolution-of-human-grasping.md` §5.1. Each process feature is listed with the
algorithm that implements it and its concrete use here.

| feature of hand evolution | EA variant | concrete use in our search |
|---|---|---|
| **A small repertoire of grips** (power, precision, hook, key pinch, chuck; Napier; 33 → 17 types, Feix) selected under task pressure | **MAP-Elites** with success-first selection (Mouret & Clune 2015; Huber 2023); repertoire + fast adaptation (Cully 2015) | Grip-type × site × approach archive per object; adaptation on the eval twin from the public archive |
| **Selection by the most stressful loads**, not average use (hammerstone percussion; our lid lost at the lift onset) | Worst-case / quantile fitness; multi-objective (NSGA-II); re-evaluation (UH-CMA-ES) | Fitness = lower quantile over K noisy copies, weighted at lift onset ± 10 frames and release |
| **Gradual, mosaic complexification** (derived traits arrive stepwise from ~3.4 to < 1.5 Ma) | **NEAT**: "incrementally growing from minimal structure", "protecting structural innovation using speciation" (Stanley & Miikkulainen 2002 [L-full]); IPOP restarts with growing λ; incremental evolution | Genome stages: wrist 6 → + synergy amplitudes 3–5 → + 22 joints → + timing. Fitness window: acquisition → full hold, which measurably helped on ep39 (0.530 → 0.877) |
| **Postural synergies** (Santello et al. 1998: 2 PCs explain > 80 % of 15-joint posture variance [L-abs PubMed 9822764]) | Eigengrasp search (Ciocarlie et al. 2007 [L-full]); sep-CMA | An 8–11-D genome makes CMA-ES adapt in ≈ 3.5–5.6 generations at λ = 64, vs 27 at n = 28 [M: `cma_constants_output.md`] |
| **Exaptation, stepping stones** (climbing grips reused; tools before full anatomy) | MAP-Elites cross-cell offspring; novelty search; POET transfer of stepping stones (Wang et al. 2019 [L-abs]) | Seed the pan from RL's ep18 key pinch, the pitcher handle from the pan-ring hook, the pot handle from the spoon wrap |
| **Juvenile exploration, adult narrowing** | CMA-ES σ adaptation; BIPOP (large-λ global, small-λ local restarts) | Broad σ at generation 0, then shrink; restart with a new template if the generation mean does not rise |
| **Learning finishes what selection starts** (Baldwin) | Evolution + lifetime RL (DERL [L-abs]; Hinton & Nowlan 1987 via the evolution report) | Evolve the reference, RL fine-tune; the measured relation in (d) |

---

## 11. Which failed episodes an evolutionary search can address

Verdicts are from the audits (`audit-plates-ep18-ep39.md`, `audit-boards-ep24-sweeper-rack-ep31.md`,
`audit-starts-ep21-ep2-ep26.md`); the EA column is mine [I].

| ep (eval) | audit verdict | can the grasp search fix it? | what else is needed |
|---|---|---|---|
| 39 (38) dust pan | Reference build (carrier merge dropped the left-hand pick-up) + grasp (no thumb) | **Yes, measured on CPU**: onset anchor + CMA-ES 0.877 | GPU confirmation (X1) |
| 18 (19) pan | Grasp (no opposition; closing from below flicks it) | **Yes**: seed with key pinch / hook (RL's grips), robust fitness | – |
| 18 (19) sweeper | Hold timing (moves from f38, hold from f61) | Partly: onset anchor + timing genes | Robust fitness (chaotic) |
| 24 (25) boards | Grasp (neither board acquired; counterfactual 0.803) | **Yes**: plate-pinch template (fingers under, thumb on top), two hands for board 2 | Possibly a slide-to-edge primitive |
| 2 (1) lid | Grasp (flicked at lift onset in all 5 variants; the start overlap costs only 0.042) | **Yes**: disc/chuck templates, fitness weighted at lift onset | – |
| 21 (20) pitcher | Start first (mesh lacks ~half its base, falls with no hand) | No, not before the mesh is fixed. Afterwards: hook + thumb handle grip | Mesh / support repair |
| 26 (28) pot in rack | Start first (perceived 29 mm too deep, ejected) | No, not before the start is fixed. Afterwards: tolerant handle squeeze | Start-pose repair (search over the start pose within perception error is possible; [H], not proposed first) |
| 31 (30) sweeper in rack | Not a grasp failure (first-step ejection; fixing that frame alone 0.840) | No | Collision-geometry fix |

**Count:** the grasp search is the primary lever in 4 holds (ep18 pan, ep24, ep2, ep39), partial in 1 (ep18 sweeper)
and secondary in 2 (ep21, ep26, after start repair). It does not apply to ep31.

---

## 12. Hypotheses, falsifying experiments and compute

Basis:
- **Measured [M-lead]:** a zero-action replay of 421 frames takes 34 s incl. setup; a 70M fine-tune takes 18.7–25 min;
  snapshot restore ≈ 2 min + setup; GPU $1.45/h.
- **Estimated [E]:** a search generation over a 300-frame window takes 20–60 s for 256–4,096 worlds (overhead-bound;
  includes the fresh environment build); an official evaluation takes ≈ 1–2 min.

Prioritised:

| id | hypothesis [H] | falsifying experiment | est. cost |
|---|---|---|---|
| **X1** | **H1: the CPU-evolved ep39 grasp transfers to the GPU evaluator** and the fine-tune keeps it | Bake the stored ep39 edit. 5 GPU zero-action replays, then the 70M fine-tune (kp 400), then 5 official evaluations, scored sim_vs_ref + registered AUC. **Falsified if** the GPU zero-action mean is < 0.6, **or** the fine-tuned registered AUC is < 0.80 (standard RL 0.802 ± 0.280) | ≈ 50 min ≈ **$1.2** |
| **X2** | **H6: evolved reference + 70M fine-tune ≥ standard 250M RL, at ≤ ½ the GPU time**, on the grasp-failure episodes | GPU robust search (λ = 256 × K = 4 = 1,024 worlds, 20 generations, frame-0 or rolling-horizon fitness, all objects, θ + start-pose noise, template seeds), then fine-tune and 5 evaluations, on ep18, ep24, ep2 (+ ep39 from X1). **Falsified if** ep18 < 0.776 (standard s42) or the 4-episode mean gain over the current grasp-lock results (0.302 / 0.202 / 0.306 / 0.174) is < +0.25 | ≈ 3–3.5 h ≈ **$4.5–5** |
| **X4** | **H2: robust fitness predicts GPU transfer; nominal fitness does not** | For ≈ 10 baked edits from X2/X3, compare search fitness (nominal; robust K = 4; re-evaluated top-k) with the mean of 5 GPU zero-action replays. **Falsified if** Spearman ρ(robust, GPU) ≤ ρ(nominal, GPU), or the robust estimate overshoots the GPU mean by > 0.1 on average | ≈ 30 min ≈ **$0.7** |
| X3 | **H3: an 8–11-D synergy genome (or sep-CMA, or λ = 256) beats flat 28-D CMA (λ = 64) at equal budget**; **H4: success-first MAP-Elites over grip templates finds a holding grasp where CMA from the copied clamp does not** | 4 arms × 3 holds (ep18 pan, ep24 board 1, ep2 lid), 5,120 candidate evaluations each; arms packed into one 4,096-world batch where memory allows. **H3 falsified if** the reduced genome is not ≥ flat on 2 of 3 holds (re-evaluated best). **H4 falsified if** MAP-Elites' best re-evaluated elite is not ≥ CMA's on 2 of 3 holds, **or** it lifts nothing that CMA does not | packed ≈ 40–60 min ≈ **$1–1.5** (unpacked ≈ $4) |
| X5 | **H5 (Baldwin gate): a fine-tune reaches ≥ 0.85 sim_vs_ref iff the zero-action replay holds the object** (≥ 0.5 and ≥ floor, rest check passed) | No new spend: add the X1/X2 runs to the 18-run table in (d). **Falsified if** ≥ 2 runs pass the gate and finish < 0.75, or ≥ 2 fail it and finish ≥ 0.85 | $0 |
| X6 | **H8: PBT-lite adds ≥ 0.02** on variable episodes | ep12 and one spoon-like twin: 4 seeds × 20M → best 2 → 70M, vs single-seed 70M, chosen by repeated sim_vs_ref; 5 evaluations each. **Falsified if** the gain is < 0.02 sim_vs_ref on both | ≈ 1.8 h ≈ **$2.6** |
| X7 | **H9: per-episode search over design knobs resolves the ep3 / ep35 rule conflict** (closing order, close frames, palm press, squeeze, approach) | On eval ep3 and ep35 references (sim_vs_ref only, no GT), search the knob vector. **Falsified if** the search result is not ≥ the better fixed rule on both episodes (ep3 0.658, ep35 0.521) | ≈ 30 min ≈ **$0.7** |
| X8 | **H7: ES on the policy has no edge**: an OpenAI-ES polish of the trained actor's 56-D output bias + 56-D gain against the evaluator metric does not beat 30M more SAC steps | ep12 fine-tuned policy, 1 GPU-hour of ES vs the same wall-clock of SAC. **The no-edge hypothesis is falsified if** ES gains ≥ 0.02 more sim_vs_ref than SAC | ≈ $1.5 + ½ day of tooling; **low priority** |

Recommended first batch: **X1 + X2 + X4 ≈ $7**, then X3 / X7 if X2 shows search quality is the limit, and X6 for the
eval run. The whole programme is ≈ $12–15. Each batch needs the owner's go-ahead (CLAUDE.md).

### Concrete pipeline (recommendation)
1. **Reference:** onset-anchored grasp lock + ILC (as now).
2. **Per hold, on the GPU:**
   - seeds: copied human grasp, the grip templates for the part type, and archive elites from the public twin;
   - success-first MAP-Elites, 1–2 batches of 4,096 worlds;
   - CMA-ES emitters in the best cells (λ = 256, K = 4, 15–20 generations; fitness = lower-quartile AUC over the
     copies, θ + start-pose + small-force noise, frame-0 / rolling-horizon start, all objects);
   - re-evaluate the top 8 elites ×16 under fresh noise; bake the winner.
3. **Gate:** zero-action replay ×5 on the GPU. Fine-tune only if the mean is ≥ max(0.5, floor) and the rest check
   passes. Otherwise re-search with the next template.
4. **Fine-tune:** 70M SAC (kp 400), checkpoints chosen by ≥ 3 evaluations each. Include the zero-action checkpoint
   as a candidate (rules permitting). Use PBT-lite seeds for variable episodes.
5. **Hygiene:**
   - fresh environment per generation (or prove on the GPU that warm-start clearing suffices, since building costs
     time);
   - clear warm starts;
   - log `nacon`/`naconmax`;
   - never clip the `--init` mean;
   - confirm every bake by a fresh GPU replay.

Estimated added cost per eval episode [E]: search ≈ 10–25 min ($0.25–0.6) + gate ≈ 3 min; the fine-tune is unchanged
(≈ 25 min). For 20 eval episodes that is ≈ $5–12 more than the fine-tune-only recipe. That is less than one 250M
standard run per episode (≈ $2.3 × 20 = $46).

---

## 13. Risks
1. **Winner's curse under chaos.** An open-loop optimum on a chaotic contact system may be a spike. Mitigation: robust
   fitness, re-evaluation, and the GPU gate (X4 tests whether this works).
2. **CPU → GPU transfer** of evolved edits is unmeasured (X1).
3. **Fitness mismatch** for later holds (reset-to-reference windows vs frame-0). Mitigation: frame-0 or rolling
   horizon; the cost is longer rollouts.
4. **Optimising against our own perception.** The fitness is our perceived path. A perfect grasp on a wrong path
   scores no better than perception allows (ep39 perception 0.982; ep18 brush drift 5.3 cm at f43
   [M-lead `work-log.md:2609-2610`]). Search cannot fix perception.
5. **The fine-tune can undo a good grasp** (ep18 degradation). Mitigation: the gate, checkpoint choice by repeated
   evaluations, demonstrations in the replay buffer if needed.
6. **Simulator artefacts the search may exploit.** Hands pass through the table (legal in this evaluator, but
   unphysical). Contact-buffer overflow differs between many-world search and the 1-world evaluator.
7. **Evaluator nondeterminism** stays: even standard RL had 1 failing rollout in 5 on ep39. A recipe can lower the
   chance of failure but cannot remove it.
8. **Rules.** A zero-output policy on an evolved reference, if used, must be acceptable to the organisers (open
   question). The fine-tuned policy avoids the question.
9. **Engineering time.** MAP-Elites, templates, rolling horizon and re-evaluation are ≈ 1–2 days of tooling around
   `grasp_evolve.py` [E].

## 14. Open questions
- What does a search generation actually cost on the RTX PRO 6000 for 1,024 / 4,096 worlds × 300 frames, including
  the fresh environment build? (Measure in X1.)
- Do identical worlds on the GPU diverge (atomic-order nondeterminism)? If they do, exact copies already sample
  evaluator noise; if not, explicit noise is needed.
- Does contact-buffer overflow (`njmax` / `naconmax`) occur in a 1,024–4,096-world search?
- Is a policy checkpoint with zero residual output (evolved reference only) an acceptable submission?
- Should the search target registered-AUC-relevant quantities (object pose only) or also hand closeness? (Currently
  object only, which is correct for the score.)

## 15. Not opened (named only, not relied on)
Stulp & Sigaud 2013 (Paladyn; PDF fetch failed), Hinton & Nowlan 1987 (complex-systems.com link dead; cited via the
evolution report), Napier / Feix (see the evolution report), the 2006 Chulalongkorn GA force-closure paper (connection
reset), Rubinstein's original CEM.

---

## 16. References (opened; level in brackets)
- Salimans T, Ho J, Chen X, Sidor S, Sutskever I. Evolution strategies as a scalable alternative to RL. 2017.
  https://arxiv.org/abs/1703.03864 [L-full]
- Mania H, Guy A, Recht B. Simple random search provides a competitive approach to RL (ARS). 2018.
  https://arxiv.org/abs/1803.07055 [L-full]
- Such FP et al. Deep neuroevolution: GAs are a competitive alternative for training deep networks for RL. 2017.
  https://arxiv.org/abs/1712.06567 [L-full]
- Hansen N. The CMA evolution strategy: a tutorial. 2016. https://arxiv.org/abs/1604.00772 [L-full]
- Auger A, Hansen N. A restart CMA-ES with increasing population size (IPOP). CEC 2005.
  https://researchportal.ip-paris.fr/en/publications/a-restart-cma-evolution-strategy-with-increasing-population-size/ [L-abs]
- Hansen N. Benchmarking a BI-population CMA-ES on BBOB-2009. GECCO 2009.
  https://researchportal.ip-paris.fr/en/publications/benchmarking-a-bi-population-cma-es-on-the-bbob-2009-function-tes/ [L-abs]
- Ros R, Hansen N. A simple modification in CMA-ES achieving linear time and space complexity (sep-CMA). PPSN 2008.
  https://researchportal.ip-paris.fr/en/publications/a-simple-modification-in-cma-es-achieving-linear-time-and-space-c/ [L-abs]
- Hansen N, Niederberger A, Guzzella L, Koumoutsakos P. A method for handling uncertainty in evolutionary
  optimization … (UH-CMA-ES). IEEE TEC 13(1):180–197, 2009.
  https://researchportal.ip-paris.fr/en/publications/a-method-for-handling-uncertainty-in-evolutionary-optimization-wi/ [L-abs]
- Wierstra D et al. Natural evolution strategies. JMLR 2014. https://arxiv.org/abs/1106.4487 [L-full]
- Sehnke F et al. Parameter-exploring policy gradients. Neural Networks 23(4), 2010.
  https://www.ias.informatik.tu-darmstadt.de/uploads/Publications/Publications/Neural-Networks-2010-Sehnke.pdf [L-full]
- Pourchot A, Sigaud O. CEM-RL. 2019. https://arxiv.org/abs/1810.01222 [L-full]
- Pinneri C et al. Sample-efficient cross-entropy method for real-time planning (iCEM). 2020.
  https://arxiv.org/abs/2008.06389 [L-full]
- Khadka S, Tumer K. Evolution-guided policy gradient in RL (ERL). 2018. https://arxiv.org/abs/1805.07917 [L-full]
- Jaderberg M et al. Population based training of neural networks. 2017. https://arxiv.org/abs/1711.09846 [L-full]
- Petrenko A et al. DexPBT. RSS 2023. https://arxiv.org/abs/2305.12127 [L-full]
- Shahid AA et al. Benchmarking population-based RL across robotic tasks with GPU-accelerated simulation. 2024.
  https://arxiv.org/abs/2404.03336 [L-full]
- Evolutionary Policy Optimization (EPO). 2025. https://arxiv.org/abs/2503.19037 [L-full]
- Gupta A et al. Embodied intelligence via learning and evolution (DERL). 2021. https://arxiv.org/abs/2102.02202 [L-abs]
- Milano N, Nolfi S. Qualitative differences between evolutionary strategies and RL methods. 2022.
  https://arxiv.org/abs/2205.07592 [L-full]
- Lehman J, Chen J, Clune J, Stanley KO. ES is more than just a traditional finite-difference approximator. GECCO
  2018. https://arxiv.org/abs/1712.06568 [L-full]
- Zhang X, Clune J, Stanley KO. On the relationship between the OpenAI ES and SGD. 2017.
  https://arxiv.org/abs/1712.06564 [L-full; used only as background]
- Sigaud O, Stulp F. Policy search in continuous action domains: an overview. 2019. https://arxiv.org/abs/1803.04706 [L-full]
- Metz L, Freeman CD, Schoenholz SS, Kachman T. Gradients are not all you need. 2021. https://arxiv.org/abs/2111.05803 [L-full]
- Suh HJT, Simchowitz M, Zhang K, Tedrake R. Do differentiable simulators give better policy gradients? ICML 2022.
  https://arxiv.org/abs/2202.00817 [L-full]
- Mouret J-B, Clune J. Illuminating search spaces by mapping elites. 2015. https://arxiv.org/abs/1504.04909 [L-full]
- Lehman J, Stanley KO. Abandoning objectives: evolution through the search for novelty alone. Evol. Comput. 19(2),
  2011. https://www.cs.swarthmore.edu/~meeden/cs81/f17/papers/lehman_ecj11.pdf [L-full]
- Cully A, Clune J, Tarapore D, Mouret J-B. Robots that can adapt like animals. Nature 521, 2015.
  https://arxiv.org/abs/1407.3501 [L-full]
- Stanley KO, Miikkulainen R. Evolving neural networks through augmenting topologies (NEAT). Evol. Comput. 2002.
  https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf [L-full]
- Fontaine MC et al. CMA-ME. 2019/2020. https://arxiv.org/abs/1912.02400 [L-abs]
- Fontaine MC, Nikolaidis S. CMA-MAE. GECCO 2023. https://arxiv.org/abs/2205.10752 [L-abs]
- Wang R et al. POET. 2019. https://arxiv.org/abs/1901.01753 [L-abs]
- Pierrot T et al. QD-RL / Diversity policy gradient for sample-efficient QD optimization. https://arxiv.org/abs/2006.08505 [L-full]
- Faldor M et al. MAP-Elites with descriptor-conditioned gradients (DCG-ME). GECCO 2023.
  https://arxiv.org/abs/2303.03832 [L-full]
- Faldor M et al. Synergizing QD with descriptor-conditioned RL (DCRL-ME). 2024. https://arxiv.org/abs/2401.08632 [L-full]
- Nilsson O, Cully A. Policy gradient assisted MAP-Elites. GECCO 2021. [L-2nd via DCRL-ME; Imperial news
  https://www.imperial.ac.uk/news/225633/three-papers-accepted-gecco-2021/]
- Lim B et al. Accelerated quality-diversity through massive parallelism. 2022. https://arxiv.org/abs/2202.01258 [L-full]
- Chalumeau F et al. QDax. 2023. https://arxiv.org/abs/2308.03665 [L-full]
- Morel A, Kunimoto Y, Coninx A, Doncieux S. Automatic acquisition of a repertoire of diverse grasping trajectories
  through behavior shaping and novelty search. ICRA 2022. https://arxiv.org/abs/2205.08189 [L-full]
- Huber J et al. E2R. 2022. https://arxiv.org/abs/2210.07887 [L-full]
- Huber J, Hélénon F, Coninx M, Ben Amar F, Doncieux S. Quality diversity under sparse interaction and sparse reward:
  application to grasping in robotics. 2023. https://arxiv.org/abs/2308.05483 [L-full]
- Huber J et al. Speeding up 6-DoF grasp sampling with quality-diversity. 2024. https://arxiv.org/abs/2403.06173 [L-full]
- DexEvolve. 2026. https://arxiv.org/abs/2602.15201 [L-full, local HTML copy]
- DemoGrasp. 2025/26. https://arxiv.org/abs/2509.22149 [L-full, local HTML copy]
- Zhu Y et al. EvolvingGrasp. ICCV 2025. https://arxiv.org/abs/2503.14329 [L-abs]
- Ciocarlie M, Goldfeder C, Allen P. Dimensionality reduction for hand-independent dexterous robotic grasping. IROS
  2007. https://www.cs.columbia.edu/~allen/PAPERS/iros2007ciocarlie.pdf [L-full]
- Santello M, Flanders M, Soechting JF. Postural hand synergies for tool use. J Neurosci 18:10105, 1998.
  https://pubmed.ncbi.nlm.nih.gov/9822764/ [L-abs]
- Tang Y, Tian Y, Ha D. EvoJAX. GECCO 2022. https://arxiv.org/abs/2202.05008 [L-full]
- Lange RT. evosax. 2022. https://arxiv.org/abs/2212.04180 [L-full]
- Freeman CD et al. Brax. 2021. https://arxiv.org/abs/2106.13281 [L-full]
- Williams G et al. Information theoretic MPC (MPPI). 2017/18. https://arxiv.org/abs/1707.02342 [L-full]
- Howell T et al. Predictive sampling: real-time behaviour synthesis with MuJoCo (MJPC). 2022.
  https://arxiv.org/abs/2212.00541 [L-full]
- Xue H, Pan C et al. DIAL-MPC. 2024. https://arxiv.org/abs/2409.15610 [L-full]
- Hess A et al. Sampling-based MPC for dexterous manipulation on a biomimetic tendon-driven hand. 2024.
  https://arxiv.org/abs/2411.06183 [L-full]
- Brüdigam J et al. Jacta. 2024. https://arxiv.org/abs/2408.01258 [L-full]
- Pan C et al. SPIDER: scalable physics-informed dexterous retargeting. 2025. https://arxiv.org/abs/2511.09484 [L-full]
- Paliwal B et al. Do As I Do. 2026. https://arxiv.org/abs/2606.19333 [L-full]
- OmniHOI: dexterous hand-object interaction from monocular human video. 2026. https://arxiv.org/abs/2610.10855 [L-full]

Repository sources:
- `docs/work-log.md` (lines cited inline);
- `STATUS.md`;
- `tools/grasp_evolve.py`;
- `ops/jobs/glock_public.sh` (EVOLVE defaults 256 worlds, K = 4, 20 generations);
- `docs/research/notes/23-grasp-controller-and-rl-handoff.md`;
- `docs/research/grasp/{evolution-of-human-grasping, learned-grasp-models, rl-discovered-grasps, audit-*}.md`.

---

## Appendix A. Reproduction

Python: `scratchpad/venv/bin/python -I` (numpy, scipy). The scripts are in `docs/research/grasp/ea-vs-rl-scripts/`.

```
# search-log summary (lead's CPU runs; logs in the session scratchpad evo/ dirs)
python -I search_logs.py <scratchpad>/evo/oa/cma_ep39.json <scratchpad>/evo/oa/cma2_ep39.json \
  <scratchpad>/evo/oa/robust_test.json <scratchpad>/evo/oa18/cma_p0.json <scratchpad>/evo/oa18/cma_p1f.json \
  <scratchpad>/evo/oa24/cma_p0.json <scratchpad>/evo/oa24/cma_p1.json > search_logs_output.txt
# CMA-ES time constants
python -I cma_constants.py > cma_constants_output.md
# Baldwin table: zero_score.txt + best/summary.json of every glock_public run, downloaded from the HF store
#   (runs/*/results/glock_public/ep*/{zero_score.txt,best/summary.json}) into <work>/store
python -I baldwin_table.py <work>/store > baldwin_table_output.md
# policy size
python -I param_count.py results/e2e/spoon_20261023/ep35_ft_k400_s42_policy_40M.safetensors
```

Scratch work dir (downloads, paper texts):
`/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/ea-vs-rl/`
(`dl/` raw PDFs/HTML, `txt/` extracted text, `store/` HF-store summaries, `scripts/fetch.sh`).
