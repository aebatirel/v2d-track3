# GPU perf-per-dollar for FlashCHORD-style GPU-parallel physics + RL (MuJoCo-Warp 4,096 worlds + FlashSAC)

Research date: 2026-10-18. Baseline is the user's measurement: RTX PRO 6000 Blackwell 96 GB, Server Edition, ~45,300 env steps/s, 40.5 GB VRAM peak, 100% nvidia-smi utilization. At that rate 250M steps take 250e6 / 45,300 / 3600 = **1.53 h** of steady-state stepping (the user reports 1.5-2 h wall clock including overhead).

Labelling convention: **[MEASURED]** = a number published by a source. **[ESTIMATE]** = my own calculation or judgement. Every cited number has a URL. Estimates are derived only from the cited numbers plus stated assumptions.

Scope note: I found **no public source named "FlashCHORD"**. Searches only returned FlashSAC (arXiv 2604.04539) and FlashDexRetarget (arXiv 2610.01849), which builds on FlashSAC and compares against a method called CHORD. All throughput estimates below therefore rest on the user's own PRO 6000 measurement, not on a published FlashCHORD benchmark.

## Q1. What are the key specs per GPU (FP32, bandwidth, VRAM, SMs, L2, TDP)?

### Takeaway
The RTX PRO 6000 Blackwell leads every candidate on FP32 (120-125 TFLOPS), SM count (188) and L2 size (up to 128 MB on the die). HBM datacenter parts lead on memory bandwidth: H100 SXM has 2.1x, H200 3.0x and B200 5.0x the PRO 6000 Server Edition's 1,597 GB/s. They have only 0.16x (A100) to 0.62x (B200) of its FP32. Which of these two dimensions binds MuJoCo-Warp determines the ranking, and that has not been published (see Q2).

### Cited Findings

Spec table. Ratios are versus the PRO 6000 Server Edition (120 TFLOPS, 1,597 GB/s). Sources are listed per row below the table.

| GPU | SMs | FP32 TFLOPS (non-tensor) | Mem BW (GB/s) | VRAM | L2 | TDP / max power | FP32 ratio | BW ratio |
|---|---|---|---|---|---|---|---|---|
| RTX PRO 6000 Blackwell **Server Ed.** | 188 (derived) | 120 | 1,597 | 96 GB GDDR7 ECC | 128 MB on GB202 die (product not confirmed) | up to 600 W, configurable | 1.00 | 1.00 |
| RTX PRO 6000 Blackwell **Workstation** | 188 (derived, same GB202 config) | 125 | 1,792 | 96 GB GDDR7 ECC | as above | 600 W | 1.04 | 1.12 |
| RTX 6000 Ada | 142 (derived) | 91.1 | 960 (third-party) | 48 GB GDDR6 ECC | 96 MB (inferred from L40) | 300 W | 0.76 | 0.60 |
| L40S | 142 (derived) | 91.6 | 864 | 48 GB GDDR6 ECC | 96 MB (inferred from L40) | 350 W | 0.76 | 0.54 |
| RTX A6000 | 84 (inferred, GA102) | 38.7 | 768 | 48 GB GDDR6 | 6 MB (inferred, GA102) | 300 W | 0.32 | 0.48 |
| A100 80GB SXM | 108 | 19.5 | 2,039 | 80 GB HBM2e | 40 MB | 400 W | 0.16 | 1.28 |
| A100 80GB PCIe | 108 | 19.5 | 1,935 | 80 GB HBM2e | 40 MB | 300 W | 0.16 | 1.21 |
| H100 SXM | 132 | 67 | 3,350 | 80 GB HBM3 | 50 MB | up to 700 W | 0.56 | 2.10 |
| H100 PCIe (80 GB) | 114 | 51.2 | ~2,000-2,039 | 80 GB HBM2e | 50 MB | 350 W | 0.43 | ~1.25 |
| H100 NVL (94 GB) | n/a | 60 | 3,900 | 94 GB | n/a | 350-400 W | 0.50 | 2.44 |
| H200 SXM | 132 (assumed, GH100) | 67 | 4,800 | 141 GB HBM3e | n/a | up to 700 W | 0.56 | 3.01 |
| B200 | 148 | 74.45 | 8,000 | 180 GB HBM3e | not verified | 1,000 W | 0.62 | 5.01 |
| RTX 5090 (reference) | 170 | 104.8 | 1,792 | 32 GB GDDR7 | 96 MB | 575 W | 0.87 | 1.12 |
| L4 (reference) | 58 (whitepaper) / 60 (Wikipedia) | 30.3 | 300 | 24 GB GDDR6 | 48 MB | 72 W | 0.25 | 0.19 |

Per-row sources:
- RTX PRO 6000 Server Edition: 120 TFLOPS FP32, 96 GB GDDR7 with ECC, 512-bit, 1,597 GB/s, 24,064 CUDA cores, 188 RT cores, "Up to 600W (configurable)", FP16/BF16 tensor "1 PFLOP" — [NVIDIA RTX PRO 6000 Server Edition page](https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition/). Blackwell RTX SMs have 128 CUDA cores per SM. The full GB202 die has 192 SMs and "131,072 KB L2 cache" (the RTX 5090 enables 96 MB) — [NVIDIA RTX Blackwell architecture whitepaper](https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf). Wikipedia lists the RTX PRO 6000 under the GB202 128 MB die — [Wikipedia: Blackwell](https://en.wikipedia.org/wiki/Blackwell_(microarchitecture)).
- RTX PRO 6000 Workstation: 125 TFLOPS FP32, 96 GB GDDR7 ECC, 1,792 GB/s, 600 W. NVIDIA's page lists no Max-Q specs — [NVIDIA RTX PRO 6000 Workstation page](https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000/).
- RTX 6000 Ada: 91.1 TFLOPS, 48 GB GDDR6 ECC, 300 W — [NVIDIA RTX 6000 Ada page](https://www.nvidia.com/en-us/products/workstations/rtx-6000/). 960 GB/s and 384-bit come from third parties — [Flopper spec sheet](https://flopper.io/gpu/nvidia-rtx-6000-ada-48gb/spec-sheet), [Lenovo Press LP1940](https://lenovopress.lenovo.com/lp1940-thinksystem-nvidia-rtx-6000-ada-48gb-pcie-active-gpu). 18,176 CUDA cores and 142 RT cores — [Wikipedia: Quadro](https://en.wikipedia.org/wiki/Quadro).
- L40S: 91.6 TFLOPS, 48 GB GDDR6 ECC, 864 GB/s, 18,176 CUDA cores, 142 RT cores, 350 W — [NVIDIA L40S page](https://www.nvidia.com/en-us/data-center/l40s/). The L40 has the same 142 SMs, 18,176 cores and 864 GB/s, with "98304 KB" L2 and 300 W — [NVIDIA Ada architecture whitepaper, Appendix C](https://images.nvidia.com/aem-dam/Solutions/geforce/ada/nvidia-ada-gpu-architecture.pdf).
- RTX A6000: 10,752 cores, 38.709 TFLOPS, 48 GB GDDR6, "768 GiB/s", 300 W — [Wikipedia: Quadro](https://en.wikipedia.org/wiki/Quadro). The GA102-based A40 has 84 SMs, 10,752 cores and 6,144 KB L2 — [Ada whitepaper, Table 4](https://images.nvidia.com/aem-dam/Solutions/geforce/ada/nvidia-ada-gpu-architecture.pdf).
- A100 80GB: 19.5 TFLOPS FP32, 80 GB HBM2e. Bandwidth is 1,935 GB/s (PCIe) and 2,039 GB/s (SXM). TDP is 300 W (PCIe) and 400 W (SXM) — [NVIDIA A100 page](https://www.nvidia.com/en-us/data-center/a100/). The A100 has 108 SMs and a 40 MB L2 — [NVIDIA Hopper whitepaper (GTC22)](https://www.advancedclustering.com/wp-content/uploads/2022/03/gtc22-whitepaper-hopper.pdf).
- H100: the SXM has 67 TFLOPS FP32, 80 GB, 3.35 TB/s and up to 700 W. The NVL has 60 TFLOPS, 94 GB, 3.9 TB/s and 350-400 W — [NVIDIA H100 page](https://www.nvidia.com/en-us/data-center/h100/). The SXM5 has 132 SMs and the PCIe 114 SMs, both with 50 MB L2. The whitepaper's preliminary figures are FP32 60/48 TFLOPS, bandwidth 3,000/2,000 GB/s and TDP 700/350 W — [Hopper whitepaper](https://www.advancedclustering.com/wp-content/uploads/2022/03/gtc22-whitepaper-hopper.pdf). H100 PCIe: 114 SMs, 14,592 cores, 51.2 TFLOPS, 80 GB HBM2E, 2,039 GB/s, 350 W — [Wikipedia: Nvidia Tesla](https://en.wikipedia.org/wiki/Nvidia_Tesla).
- H200: 67 TFLOPS FP32 (SXM) and 60 (NVL), 141 GB, 4.8 TB/s, up to 700 W (SXM) and 600 W (NVL). These are marked "Preliminary specifications" — [NVIDIA H200 page](https://www.nvidia.com/en-us/data-center/h200/). Conflict: Wikipedia's table lists H200 SXM bandwidth as 3,360 GB/s — [Wikipedia: Nvidia Tesla](https://en.wikipedia.org/wiki/Nvidia_Tesla). I use NVIDIA's 4.8 TB/s.
- B200: 148 SMs, 18,944 cores, 74.45 TFLOPS FP32, 180 GB HBM3E, 8,000 GB/s, 1,000 W — [Wikipedia: Nvidia Tesla](https://en.wikipedia.org/wiki/Nvidia_Tesla). This is not from an NVIDIA primary page. I found no B200 L2 figure; Wikipedia's Blackwell page gives "60 MB" without assigning it to a die — [Wikipedia: Blackwell](https://en.wikipedia.org/wiki/Blackwell_(microarchitecture)).
- RTX 5090: 170 SMs, 21,760 cores, 2,407 MHz boost, 104.8 TFLOPS FP32, 1,792 GB/s, 98,304 KB L2, 575 W TGP — [Blackwell whitepaper](https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf). 32 GB GDDR7 — [NVIDIA RTX 5090 page](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/).
- L4: 58 SMs, 7,424 cores, 300 GB/s, 49,152 KB L2, 72 W — [Ada whitepaper, Appendix D](https://images.nvidia.com/aem-dam/Solutions/geforce/ada/nvidia-ada-gpu-architecture.pdf). 30.3 TFLOPS and 24 GB GDDR6 — [Wikipedia: Nvidia Tesla](https://en.wikipedia.org/wiki/Nvidia_Tesla). Conflict: Wikipedia lists 60 SMs, the whitepaper 58.

### Inferences
- [ESTIMATE] Derived SM counts. Blackwell and Ada RTX parts have 128 FP32 cores per SM and one RT core per SM. That gives 24,064 / 128 = 188 SMs for the PRO 6000 and 18,176 / 128 = 142 for the L40S and RTX 6000 Ada.
- [ESTIMATE] Implied boost clocks, from FP32 = cores x 2 x clock: about 2.49 GHz for the PRO 6000 Server Edition, 2.52 GHz for the L40S, 2.51 GHz for the RTX 6000 Ada and about 1.98 GHz for the H100 SXM. The RTX cards' advantage in per-thread latency-bound kernels therefore comes from both clock and SM count.
- The A100 has only 64 FP32 lanes per SM. Its 19.5 TFLOPS understates what it can do on latency- or occupancy-bound kernels relative to its SM count x clock. I use an SM x clock proxy of 0.32x the PRO 6000 alongside the FP32 ratio of 0.16x.
- The Server Edition is power-configurable ("up to 600W"). Different clouds may ship it at different power limits, so measured steps/s can differ between providers for the "same" GPU. This is a hypothesis; check with `nvidia-smi -q -d POWER`.

### Gaps
- No NVIDIA primary source for B200 FP32, L2 or SM count, or for the RTX 6000 Ada's memory bandwidth. Product-level L2 for the RTX PRO 6000, L40S and RTX 6000 Ada is inferred from die-level or sibling-product data.
- No RTX PRO 6000 Max-Q (300 W) specs were found. Community clouds list Max-Q variants (see Q4), and their throughput is likely lower but unquantified.

## Q2. Do published MuJoCo-Warp / MJX / Warp / Isaac Lab / Newton / Brax / IsaacGym benchmarks show which spec dominates, and are H100s faster than RTX-class cards for physics sims?

### Takeaway
No public benchmark runs MuJoCo-Warp (or Newton) on an H100, H200, B200 or A100 next to an RTX-class card. The MuJoCo-Warp developers' own published benchmarks run on RTX-class workstation GPUs: RTX 6000 Ada nightly, RTX PRO 6000 Blackwell in recent PRs. The cross-GPU evidence that exists is indirect and confounded. Isaac Lab's RTX 4090-vs-L40 results track memory bandwidth (but also differ in CPU). MuJoCo Playground's MJX shows 8x H100 only about 3x faster than one RTX 4090 on a contact-rich LEAP-hand task. A per-card H100 > RTX PRO 6000 advantage for this workload is therefore unproven, and roughly parity with the H100 SXM is the most defensible prior.

### Cited Findings
**MuJoCo-Warp / MJX (closest to our stack)**
- [MEASURED] The MuJoCo-Warp nightly benchmarks run on a workstation with an "NVIDIA RTX 6000 Ada Generation", "VRAM: 48 GB". The chart values did not render in the fetch — [MJWarp nightly benchmarks](https://google-deepmind.github.io/mujoco_warp/nightly/).
- [MEASURED, from a search-result excerpt; PR pages not fetched in full] October 2026 MuJoCo-Warp PRs benchmark on an "otherwise idle RTX PRO 6000 Blackwell" with 8,192 worlds:
  - humanoid at about 7.9-8.07M steps/s
  - Franka Panda at about 37M steps/s
  - aloha_clutter at about 0.45M steps/s
  - unitree_g1_flat at about 3.8M steps/s

  Sources: [mujoco_warp PR #1748](https://github.com/google-deepmind/mujoco_warp/pull/1748), [mujoco_warp PR #1769](https://github.com/google-deepmind/mujoco_warp/pull/1769). These are physics-only and use simpler scenes than dexterous hands. They show a ~80x spread in steps/s across scenes on the same GPU, so scene complexity dominates absolute throughput.
- The MJWarp docs say it is "optimized for throughput: the total number of simulation steps per unit time". They say "Simulation throughput is often limited by memory requirements for large numbers of worlds", and that "Improving performance for single connected mechanisms beyond ~60 DoFs remains an active priority". No GPU recommendations or cross-GPU numbers are given — [MuJoCo docs: MJWarp](https://mujoco.readthedocs.io/en/latest/mjwarp/index.html).
- [MEASURED] MuJoCo Playground (MJX), LeapCubeReorient (contact-rich LEAP hand), same hyperparameters (8,192 envs): "1x 4090 takes ∼2080 (s) to train and 8x H100 takes ∼670 (s) to train". The paper states "GPUs with higher theoretical performance and larger topologies can reduce training time by a factor of 3x". On the Go1 joystick (few contacts), "Different devices and topologies do not make material difference in training wallclock time". It reports A100 LeapCubeReorient PPO throughput of 76,354 ± 143 steps/s — [MuJoCo Playground, arXiv 2502.08844](https://arxiv.org/html/2502.08844v1).
- [MEASURED] GPUSimBench used only an RTX 5070 12 GB. MuJoCo Warp reached 3.54M FPS at 2^19 envs on Franka with a 9.83 GB memory increment. On free-fall it reached 166k FPS at 2^11 envs with a 5.87 GB increment. MJX on Franka reached 1.91M FPS at 2^19 envs. There was no cross-GPU or bottleneck analysis — [GPUSimBench, arXiv 2607.13059](https://arxiv.org/html/2607.13059).

**Isaac Lab (PhysX, different engine, but the only same-task cross-GPU tables found)**
- [MEASURED] The official Isaac Lab benchmarks compare a single RTX 4090 (Ryzen 9 7950X) with a single L40 (Xeon Platinum 8362). Figures are env-step FPS, then step+inference+train FPS:
  - Isaac-Repose-Cube-Shadow-Direct-v0 (Shadow hand, 8,192 envs): RTX 4090 200,000 / 170,000; L40 170,000 / 120,000.
  - G1 rough (4,096 envs): 94,000 / 82,000 vs 72,000 / 62,000.
  - Cartpole: 1,100,000 vs 620,000 env-step FPS.
  - VRAM for the Shadow task at 8,192 envs is only 6.4 GB.

  Source: [Isaac Lab performance benchmarks](https://isaac-sim.github.io/IsaacLab/main/source/overview/reinforcement-learning/performance_benchmarks.html).
- [MEASURED] The Isaac Lab paper's GPU study used the L40 (2x EPYC 7763), RTX Pro 6000 (2x EPYC 9554) and GeForce 5090 (8-core 9800X3D, single-core performance "more than double that of the L40 server"). The 5090 "comes close in performance to the two GPU RTX Pro 6000 server in the Franka cabinet drawer task, but is only about 25% faster in the DextrAH task". Throughput "can also be dependent on single-core CPU performance due to bottlenecks in some parts of PhysX simulation and the main training loop". Eight GPUs with 16,384 envs give the DextrAH teacher "over 900,000 frames per second" — [Isaac Lab paper, arXiv 2511.04831](https://arxiv.org/html/2511.04831).

**Anecdotal / general**
- An NVIDIA developer-forum user saw an H100 PCIe and an L40S run slower than an RTX 4090 on a simple benchmark (via search excerpt). A reply said "the RTX 4090 is the fastest card for 'ordinary' calculations", and the original poster suspected the test was flawed — [NVIDIA forum: H100/L40S performance](https://forums.developer.nvidia.com/t/gu-h100-l40s-performance/314400). This is anecdotal and not physics-specific.
- nvidia-smi "GPU" utilization is the "Percent of time over the past sample period during which one or more kernels was executing on the GPU" — [nvidia-smi docs](https://docs.nvidia.com/deploy/nvidia-smi/index.html). Our "100% utilization" therefore means the GPU is never idle. It does not mean the SMs or memory bus are saturated.

**FlashSAC (our RL algorithm)**
- [MEASURED] FlashSAC's wall-clock results were "measured on a single RTX 5090 GPU" with an "AMD Ryzen 9 9950X3D CPU". Sim-to-real training "was completed in approximately 4 hours using a single NVIDIA A100 GPU". It uses "mixed-precision throughout training" and "a 2.5M-parameter, 6-layer network for both the actor and critic". The main setup uses 1,024 parallel envs and the sim-to-real setup 4,096. The paper does not say whether simulation or updates dominate, and reports no GPU memory use — [FlashSAC, arXiv 2604.04539](https://arxiv.org/html/2604.04539v1).
- FlashDexRetarget, which builds on FlashSAC, reports about 29 GPU-hours for XHand versus 2,847 GPU-hours for CHORD. Its Sharpa hand policy trains for 400M env steps (search excerpt) — [FlashDexRetarget, arXiv 2610.01849](https://arxiv.org/html/2610.01849v1).

### Inferences
- [ESTIMATE] Isaac Lab Shadow hand, L40 vs 4090 env-step ratio: 170k / 200k = 0.85. That matches the bandwidth ratio (864 / 1,008 = 0.86). It does not match the FP32 ratio (90.5 / 82.6 = 1.10, so the L40 should have been faster if FP32-bound). This is consistent with bandwidth- or latency-bound physics, but the CPU confound (Xeon vs Ryzen) is documented by the same team, so it is not proof.
- [ESTIMATE] MJX LEAP cube: 8x H100 at 2,080 / 670 = 3.1x a single 4090 implies under 0.4x 4090-equivalent per H100 under perfect scaling. The split gives only ~1,024 envs per GPU plus gradient sync, so this mostly shows that multi-GPU at fixed env count scales poorly. It is weak evidence about per-card speed, but no evidence that an H100 is dramatically faster than an RTX card on contact-rich sims.
- [HYPOTHESIS] With 4,096 worlds, many MuJoCo-Warp kernels have one thread per world, per contact or per constraint row. That is far fewer threads than the PRO 6000 can hold resident (188 SMs). Such kernels tend to be latency- or occupancy-bound, so SM count x clock and L2 hit rate matter more than peak HBM bandwidth. Larger constraint-Jacobian and contact arrays are bandwidth-bound, which favours HBM parts. Without a profile, the split between these two classes is the key unknown. It can be measured with Nsight Systems or `mjwarp-testspeed --event_trace` on our scene ([MJWarp README](https://github.com/google-deepmind/mujoco_warp)).
- [HYPOTHESIS] FlashSAC's fp16 networks run on tensor cores, where Hopper and Blackwell datacenter parts are much stronger than RTX parts. This shifts the comparison somewhat toward the H100, H200 and B200, but only for the update fraction of runtime, which is unpublished. Small 2.5M-parameter networks are often launch- or latency-bound rather than tensor-throughput-bound.
- Practical reading: physics devs (DeepMind/NVIDIA MJWarp, FlashSAC authors) benchmark on RTX workstation or consumer cards. Nothing published suggests datacenter HBM cards give better perf per dollar for this class of workload.

### Gaps
- No published MuJoCo-Warp, Newton or Warp-sim benchmark on an A100, H100, H200 or B200, so there is no direct answer to "H100 vs RTX PRO 6000" for our engine.
- No profile of the FlashCHORD/FlashSAC time split (physics vs SAC update), and no public FlashCHORD source at all.
- Playground's per-device wall-clock figure (Fig. 15, Appendix C.3) exists, but its values are only in an image and were not extractable.
- IsaacGym / Brax cross-GPU datacenter-vs-RTX benchmarks were not found.

## Q3. Which GPUs fit 4,096 worlds in 48 GB (given 40.5 GB measured)? How should world count be reduced for smaller cards?

### Takeaway
All 80 GB+ cards fit 4,096 worlds comfortably: A100 and H100 80 GB, H100 NVL 94 GB, H200 141 GB, B200 180 GB and PRO 6000 96 GB. The 48 GB cards (L40S, RTX 6000 Ada, A6000) should fit with about 7 GB of nominal headroom, but only if JAX's allocator is configured. JAX's default 75% preallocation is 36 GB on a 48 GB card, below our 40.5 GB peak, and it may also starve Warp's separate allocations. Verify with a short dry run before renting for long. The 32 GB RTX 5090 and 24 GB L4 need fewer worlds, roughly 2,048 and 1,024-2,048 respectively [ESTIMATE], and that changes the RL configuration.

### Cited Findings
- JAX "will preallocate 75% of the total GPU memory when the first JAX operation is run". `XLA_PYTHON_CLIENT_PREALLOCATE=false` allocates on demand but is "more prone to fragmentation". `XLA_PYTHON_CLIENT_MEM_FRACTION=.XX` changes the fraction. `XLA_PYTHON_CLIENT_ALLOCATOR=platform` frees memory but is "very slow" — [JAX GPU memory allocation docs](https://docs.jax.dev/en/latest/gpu_memory_allocation.html).
- MJWarp memory:
  - "The maximum number of contacts for all worlds is `nconmax * nworld`".
  - "the number of constraints per world is strictly limited by njmax".
  - "Memory and computation scales with the values of these parameters". "For best performance, the values of these parameters should be set as small as possible".
  - Tune with `mjwarp-testspeed --measure_alloc` and `--overflow_behavior=error`. Inline CCD and solver allocations show as "Other memory" in `testspeed --memory`.
  - Sparse Jacobians cut the Aloha-clutter `efc.J` (2,048 worlds) from "~408 MB" dense to "~84 MB".
  - `nvmax` with the compact solver "significantly reduces GPU memory usage and improves throughput".

  Source: [MuJoCo docs: MJWarp](https://mujoco.readthedocs.io/en/latest/mjwarp/index.html).
- Overflowing fixed contact or constraint buffers leads to undefined behaviour, per the MJWarp docs as summarised in search results — [MuJoCo docs: MJWarp](https://mujoco.readthedocs.io/en/latest/mjwarp/).
- VRAM capacities: L40S 48 GB ([NVIDIA](https://www.nvidia.com/en-us/data-center/l40s/)); RTX 6000 Ada 48 GB ([NVIDIA](https://www.nvidia.com/en-us/products/workstations/rtx-6000/)); RTX 5090 32 GB ([NVIDIA](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/)); L4 24 GB ([Wikipedia: Nvidia Tesla](https://en.wikipedia.org/wiki/Nvidia_Tesla)); H200 141 GB ([NVIDIA](https://www.nvidia.com/en-us/data-center/h200/)).

### Inferences
- [ESTIMATE] 48 GB cards: 40.5 GB of 48 GB is 84%. Headroom is about 7.5 GB nominal, less the CUDA context and fragmentation, so it should fit but is tight. On the 96 GB PRO 6000, default JAX preallocation would be about 72 GB. A measured peak of 40.5 GB therefore suggests preallocation was already disabled or capped, or that the 40.5 GB was measured inside JAX/Warp. Confirm which, because:
  - If 40.5 GB is an nvidia-smi reading with `PREALLOCATE=false`, the 48 GB cards should work as-is (set `XLA_PYTHON_CLIENT_MEM_FRACTION` around 0.90 or keep preallocation off).
  - If Warp/MuJoCo-Warp allocates outside JAX's pool, then JAX's default 36 GB pool plus Warp's buffers could OOM on 48 GB.
- [ESTIMATE] Linear-scaling budget. If all 40.5 GB scaled with nworld, that is about 9.9 MB per world.
  - RTX 5090: about 29-30 GB usable gives at most ~2,900-3,000 worlds. Use 2,048 (≈20 GB).
  - L4: about 22 GB usable gives at most ~2,200 worlds. Use 1,024 safely (≈10 GB), or 2,048 at the edge (≈20 GB).

  The SAC replay buffer may be a large fixed share that scales with buffer capacity rather than nworld. If so, cutting replay capacity, storing observations in fp16, or tightening `nconmax`/`njmax`, sparse Jacobians or `nvmax` could keep 4,096 worlds on a 32 GB card. Measure this with `testspeed --memory` and JAX memory profiling.
- Reducing nworld changes the RL data distribution (parallel-env count, update-to-data ratio, batch statistics) and lowers GPU occupancy. Results on the 5090 and L4 at fewer worlds are therefore not the same experiment, and their speed estimates in Q4 are optimistic.
- [HYPOTHESIS] Run packing. Because "100% utilization" does not mean saturation, running 2 independent seeds on one 96 GB PRO 6000 (2 x 40.5 GB), 3 on an H200 (141 GB) or 4 on a B200 (180 GB) could raise aggregate policies per hour. If kernels are latency- or occupancy-bound, this could lower cost per policy by more than any GPU switch. This is cheap to test on the current PRO 6000 by launching two runs at once and comparing aggregate steps/s.

### Gaps
- How the 40.5 GB splits between JAX (networks, replay buffer, optimizer) and Warp (MuJoCo-Warp data, contact and constraint buffers), and how it was measured, is unknown. This determines whether the 48 GB cards and the 32 GB 5090 work without code changes.
- ECC-enabled usable capacity on the GDDR6 48 GB cards was not verified.

## Q4. Estimated relative speed and cost per 250M-step policy at October 2026 prices

### Takeaway
[ESTIMATE] On a time-additive model, the RTX PRO 6000 (Server or Workstation) stays the fastest or near-fastest card per unit of money for this workload. The model assumes half of the baseline time is compute- or latency-bound (scaling with SM x clock) and half bandwidth-bound (scaling with memory bandwidth). At the cheapest October 2026 listings (about $0.65-0.79/h) a 250M-step policy costs about **$1.0-1.2**, versus about $3.4 at the ~$2.2/h median. The RTX A6000, RTX 6000 Ada and L40S give similar or slightly worse cost per policy at their cheapest prices, about $1.3-1.5, and take 1.5-2.6x longer per policy. The H100, H200 and B200 are 2-10x more expensive per policy. They would only beat the PRO 6000 if the workload is strongly bandwidth-bound or several runs are packed per GPU. A 10-minute benchmark on each shortlisted GPU (under $1 each) would replace these estimates.

### Cited Findings — October 2026 prices (per GPU-hour, on-demand unless stated)

| GPU | Cheapest listing (computeprices, 2026-10-18) | Cheapest / median (getdeploying, accessed 2026-10-18) | User's assumed range | Verdict |
|---|---|---|---|---|
| RTX PRO 6000 | $0.79 (Nebius, 1x) | $0.65 (Hostinger) / $2.30, 53 providers | $0.8-2.1 | confirmed; median slightly higher |
| L40S | $0.55 | $0.55 (Novita) / $1.57, 37 providers | $0.8-1.0 | low end lower ($0.55), median higher ($1.57) |
| RTX A6000 | $0.33 | $0.45 (GPU.ai) / $0.68, 20 providers | $0.4-0.5 | low end confirmed; median $0.68 |
| RTX 6000 Ada | not on index page | $0.65 (GPU.ai) / $1.07, 12 providers | $0.7-0.8 | close; median $1.07 |
| A100 80GB | $0.74 (A100 SXM) | $0.89 (Jarvislabs) / $1.84, 47 providers | $1.2-2.0 | low end lower; median confirmed |
| H100 | $1.38 (H100 SXM) | $1.78 (Lium) / $3.53, 57 providers | $2-3 | low end lower; median higher |
| H200 | $1.67 | $2.09 (Beam) / $5.15, 50 providers | — | — |
| B200 | $3.60 | $3.75 (Packet.ai) / $7.99, 38 providers | — | — |
| RTX 5090 | not on index page | $0.35 (HyperAI) / $0.69, 20 providers | — | — |
| L4 | $0.296 | $0.33 (Theta EdgeCloud) / $0.87, 21 providers | — | — |

Sources: [computeprices.com GPU index](https://computeprices.com/gpus) (timestamp 10/18/2026; per-GPU price excluding CPU, disk and network); [getdeploying.com cloud GPU reference](https://getdeploying.com/reference/cloud-gpu) ("Updated 13 minutes ago" at fetch on 2026-10-18; does not split SXM/PCIe; "medians are not rates you can book").

- RTX PRO 6000 detail: 75 listings from 40 providers, dated Oct 12-18, 2026 — [computeprices RTX PRO 6000](https://computeprices.com/gpus/rtx-pro-6000).
  - Single-GPU on-demand: Nebius $0.79 and $1.80; UpCloud $0.979; Spheron $1.11; Vast.ai $1.14; Lium $1.19; Verda $1.20; Hyperstack $1.30, $1.48 and $1.85; Runpod Community $1.64; Runpod Secure $2.49; Jarvis Labs $2.19; Google Cloud (Iowa) $1.63 and $4.50; Modal $3.03; Oracle $4.50.
  - CoreWeave lists $1.20 and $2.50 per GPU, but only as 8x nodes.
  - The page does not label Server vs Workstation edition. Some rental URLs indicate Max-Q (Vast.ai, Runpod Community Cloud, AtmosCompute) and WS variants (Vast.ai, AtmosCompute).
  - Median across all 75 listings ≈ $2.19 (my computation from the listing).
- Hyperscaler RTX PRO 6000 Server Edition rates, via search excerpt from an aggregator: AWS g7e.2xlarge $3.36/GPU, Google g4-standard-48 $4.50, Azure NC RTX PRO 6000 BSE v6 $5.50, Hyperstack Server Edition $1.85 — [Flopper RTX PRO 6000 pricing](https://flopper.io/pricing/nvidia-rtx-pro-6000-blackwell). CoreWeave's 8-GPU node is $20.00/h on-demand, about $11.09/h spot — [CoreWeave pricing](https://www.coreweave.com/pricing).

### Inferences — relative speed and cost per policy [ALL ESTIMATES]

Model:
- rel = 1 / (f / r_compute + (1 - f) / r_bandwidth).
  - r_compute = (SMs x boost clock) relative to the PRO 6000 Server Edition. This equals the FP32 ratio for every card except the A100, whose FP32 ratio is half its SM x clock ratio.
  - r_bandwidth = memory-bandwidth ratio.
- Central f = 0.5. The range sweeps f = 0.2 to 0.8, and for the A100 the low end also uses the FP32 ratio.
- Hours = 1.533 h / rel (steady state). Multiply hours and cost by about 1.3 if the baseline is the 2.0 h wall-clock figure.
- Prices: "low" is the cheapest listing (computeprices, or getdeploying where computeprices lacks the GPU). "median" is the getdeploying median, except for the PRO 6000, where it is the ≈$2.19 computeprices median.
- Reproducible from the formula above plus the cited specs and prices. The script was a throwaway in the session scratchpad and is not saved in the repo.

| GPU | r_compute | r_BW | rel. speed, central (range f=0.8…0.2) | h per 250M steps, central (range) | $/policy @ cheapest | $/policy @ median | Fits 4,096 worlds? |
|---|---|---|---|---|---|---|---|
| RTX PRO 6000 Server Ed. (baseline, measured 45.3k sps) | 1.00 | 1.00 | **1.00** (measured) | **1.53** | **$1.21** ($0.79/h) | $3.36 ($2.19/h) | yes, 96 GB |
| RTX PRO 6000 Workstation (600 W) | 1.04 | 1.12 | 1.08 (1.06-1.11) | 1.42 (1.39-1.45) | $1.12 | $3.11 | yes |
| RTX 6000 Ada | 0.76 | 0.60 | 0.67 (0.63-0.72) | 2.28 (2.13-2.44) | $1.49 ($0.65/h) | $2.44 ($1.07/h) | likely, 48 GB (verify) |
| L40S | 0.76 | 0.54 | 0.63 (0.57-0.71) | 2.42 (2.17-2.67) | $1.33 ($0.55/h) | $3.80 ($1.57/h) | likely, 48 GB (verify) |
| RTX A6000 | 0.32 | 0.48 | 0.39 (0.35-0.44) | 3.97 (3.50-4.44) | $1.31 ($0.33/h) | $2.70 ($0.68/h) | likely, 48 GB (verify) |
| A100 80GB SXM | 0.32 (FP32 0.16) | 1.28 | 0.52 (0.20-0.81) | 2.96 (1.90-7.79) | $2.19 ($0.74/h) | $5.45 ($1.84/h) | yes |
| A100 80GB PCIe | 0.32 (FP32 0.16) | 1.21 | 0.51 (0.20-0.78) | 2.99 (1.96-7.80) | $2.21 | $5.51 | yes |
| H100 SXM | 0.56 | 2.10 | 0.88 (0.65-1.35) | 1.74 (1.13-2.35) | $2.40 ($1.38/h) | $6.14 ($3.53/h) | yes |
| H100 PCIe | 0.43 | 1.25 | 0.64 (0.49-0.90) | 2.41 (1.70-3.12) | $3.32 | $8.50 | yes |
| H200 SXM | 0.56 | 3.01 | 0.94 (0.67-1.60) | 1.63 (0.96-2.30) | $2.72 ($1.67/h) | $8.39 ($5.15/h) | yes (could pack ~3 runs) |
| B200 | 0.62 | 5.01 | 1.10 (0.75-2.07) | 1.39 (0.74-2.04) | $5.00 ($3.60/h) | $11.09 ($7.99/h) | yes (could pack ~4 runs) |
| RTX 5090 32 GB (reference) | 0.87 | 1.12 | 0.98 (0.91-1.06), *at 4,096 worlds* | 1.56 | $0.55 ($0.35/h) | $1.08 ($0.69/h) | **no**, ~2,048 worlds; different experiment |
| L4 24 GB (reference) | 0.25 | 0.19 | 0.22 (0.20-0.24), *at 4,096 worlds* | 7.12 | $2.11 ($0.296/h) | $6.19 ($0.87/h) | **no**, ~1,024-2,048 worlds |

Interpretation:
- **Best $/policy at cheapest listings:** RTX PRO 6000 at about $1.1-1.2 is roughly tied with the A6000 ($1.31), L40S ($1.33) and RTX 6000 Ada ($1.49). The PRO 6000 also has the shortest wall clock and the most memory headroom.
- **At median prices:** the RTX 6000 Ada ($2.44) and A6000 ($2.70) edge out the PRO 6000 ($3.36). Shopping for sub-$1.20/h PRO 6000 listings (Nebius, UpCloud, Spheron, Vast.ai, Lium, Verda) beats switching GPU type.
- **H100 / H200 / B200:** even the optimistic f=0.2 case (80% bandwidth-bound) gives H100 SXM ≈ $1.57 and H200 ≈ $1.60 per policy at their cheapest prices. That is still above the PRO 6000 at $0.79/h. Datacenter HBM cards win only if (a) the workload proves strongly bandwidth-bound and the cheapest H100/H200 listings are used, or (b) several runs are packed per GPU (Q3 hypothesis).
- **A100:** the widest uncertainty of all candidates, because FP32 is only 0.16x. Cost per policy runs from $1.4 to $14, and it is unlikely to be a good choice.
- **RTX 5090:** the cheapest per policy on paper (about $0.55-1.1), but it cannot run the 4,096-world configuration in 32 GB. Treat it as a different experiment.
- **Caveats:** the cheapest listings are often marketplaces or community clouds (Vast.ai, Runpod Community) that are interruptible, unverified or Max-Q. Some are multi-GPU-node-only (CoreWeave $1.20 requires 8x). The Nebius $0.79 vs $1.80 pair may be preemptible vs on-demand (unverified). Costs exclude CPU/RAM/disk/egress, JIT compile time and evaluation.
- **Falsification test (recommended):** run the exact FlashCHORD config for about 10-20M steps after JIT warm-up on each shortlisted GPU. Shortlist: PRO 6000 at a sub-$1.2 provider, L40S, RTX 6000 Ada, A6000, H100 SXM. Record steps/s, peak memory (JAX + Warp) and `nvidia-smi -q -d POWER,CLOCK`. Each costs under $1 and would replace the model above. Also test 2 concurrent runs on the PRO 6000 to check the packing hypothesis.

### Gaps
- No measured FlashCHORD/MuJoCo-Warp throughput exists on any GPU other than the user's PRO 6000. Every relative-speed number above is a spec-based model, and the f parameter (compute vs bandwidth share) is unknown. The Isaac Lab L40-vs-4090 data loosely suggests bandwidth matters, but is CPU-confounded.
- Price sources do not distinguish RTX PRO 6000 Server Edition, Workstation and Max-Q, or A100/H100 SXM vs PCIe (getdeploying). Median figures come from aggregators and may include multi-GPU-only or committed-term listings.
- The share of runtime spent in fp16 SAC updates (which would favour Hopper/Blackwell tensor cores) is unknown.
