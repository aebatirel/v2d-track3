# Dedicated GPU clouds: pricing and terms for one 48 GB+ GPU, October 2026

Scope: Lambda, Hyperbolic, Thunder Compute, Paperspace (DigitalOcean), Jarvislabs, Verda (formerly DataCrunch), Massed Compute and CoreWeave, plus Nebius and Hyperstack, which list RTX PRO 6000 Blackwell 96 GB.

Requirement filter used throughout (from the brief):
- one GPU with at least 48 GB of VRAM;
- Linux x86_64 with a CUDA 13 driver (580 or newer);
- SSH access;
- at least 16 vCPU and 64 GB of RAM per GPU;
- about 500 GB of persistent storage;
- 100–150 GPU-hours in total by 2026-11-04.

Unless stated otherwise, all official pages were fetched on **2026-10-18**. Prices are USD per GPU-hour, excluding tax.

---

## Which provider has the cheapest reliable ≥48 GB GPU, billed per minute or per hour, with no long commitment?

### Takeaway
The cheapest verified options that meet every hardware spec are:
- **Hyperstack L40 48 GB at $1.00/h**, billed per minute (up to 28 vCPU and 120 GB RAM per GPU);
- **Massed Compute A100 80GB 1x at $1.35/h** (16 vCPU, 96 GB RAM, 512 GB disk);
- **Hyperstack A100 80GB PCIe at $1.35/h**.

Thunder Compute's A100 80GB is nominally $1.09/h, or about $1.41/h with 16 vCPU. However, Thunder uses network-attached, CUDA-layer-virtualized GPUs, which makes a CUDA 13, JAX or Warp stack risky there.

Several cheap 48 GB offers fail the vCPU or RAM requirement:
- Thunder A6000 $0.35 (max 8 vCPU);
- Massed Compute A6000 $0.57 (6 vCPU), RTX 6000 Ada $0.79 (12 vCPU) and L40S $0.97 (12 vCPU);
- Hyperstack A6000 $0.50 (58 GB RAM);
- Lambda A6000 $1.09 (14 vCPU);
- Verda RTX 6000 Ada and A6000 (10 vCPU) and Verda L40S (60 GB RAM).

At 150 GPU-hours, compute alone comes to about $150 (Hyperstack L40), $203 (A100 80GB at Massed Compute or Hyperstack), $270 (Nebius RTX PRO 6000) or $329 (Massed Compute or Jarvislabs RTX PRO 6000).

### Cited Findings

#### Master table: on-demand (OD) and spot prices per GPU-hour

"—" means the provider does not list that GPU. ✓ or ✗ marks whether a single-GPU configuration meets ≥16 vCPU and ≥64 GB RAM.

| Provider | RTX PRO 6000 96GB | RTX 6000 Ada 48GB | L40S 48GB | RTX A6000 48GB | A100 80GB | H100 | Source |
|---|---|---|---|---|---|---|---|
| **Lambda** | — (not listed) | — | — | $1.09 OD, 1x: 14 vCPU / 100 GiB / 512 GiB SSD ✗ | 1x not offered. 8x A100 SXM 80GB $2.79/GPU. 1x A100 40GB is $1.99 but under 48 GB | H100 PCIe 1x $3.29 (26 vCPU / 225 GiB / 1 TiB) ✓. H100 SXM 1x $4.29, 8x $3.99/GPU | [lambda.ai/pricing](https://lambda.ai/pricing), [lambda.ai/instances](https://lambda.ai/instances) |
| **Thunder Compute** | — | — | L40 (not L40S) 48GB $0.79; 6 vCPU included, max 12; 48–96 GB ✗ | $0.35; 6 vCPU included, max 8; 48–64 GB ✗ | $1.09; 8 vCPU included, max 16; 64–128 GB. Extra vCPU $0.04/h, so 16 vCPU ≈ $1.41 | H100 SXM $3.20; 4 vCPU included, max 16 | [thundercompute.com/pricing](https://www.thundercompute.com/pricing) ("list prices checked Oct 16, 2026") |
| **Jarvislabs** | **$2.19 OD** (28 vCPU / 160 GB) ✓. $1.89 until Oct 4, 2026. Spot $1.15 and 12-month reserved $2.01 per getdeploying | — | — | — | $1.49 (16 vCPU / 112 GB) ✓ | H100 SXM $3.49 (16 vCPU / 200 GB). H200 $4.59 | [jarvislabs.ai/pricing](https://jarvislabs.ai/pricing), [Oct 2026 price change](https://jarvislabs.ai/updates/gpu-pricing-october-2026), [getdeploying](https://getdeploying.com/gpus/nvidia-rtx-pro-6000) |
| **Verda (ex-DataCrunch)** | **$2.371 OD / $1.186 spot** (30 vCPU / 90 GB) ✓ | $1.342 / $0.671 spot (10 vCPU / 60 GB) ✗ | $1.755 / $0.8775 spot (20 vCPU / 60 GB) ✗ RAM | $0.749 / $0.3745 spot (10 vCPU / 60 GB) ✗ | A100 SXM4 $2.056 / $1.028 spot (22 vCPU / 120 GB) ✓ | H100 SXM5 $4.296 / $2.148 spot (30 vCPU / 120 GB) | [verda.com/pricing](https://verda.com/pricing) |
| **Massed Compute** | **$2.19 OD** at 1x/2x/4x/8x. 1x: 16 vCPU / 144 GB / 725 storage ✓. Same price with reduced storage (350) | $0.79; 1x: 12 vCPU / 72 GB / 350 ✗ vCPU | $0.97; 1x: 12 vCPU / 72 GB / 625 ✗ vCPU | $0.57; 1x: 6 vCPU / 48 GB ✗. ALT config $0.55. NVLink pairs $0.62 | **$1.35**; 1x: 16 vCPU / 96 GB / 512 ✓. SXM4 $1.38 | H100 $2.73; 1x: 20 vCPU / 128 GB / 1250 ✓. SXM5 $3.14. NVL $3.11 | [vm.massedcompute.com/pricing](https://vm.massedcompute.com/pricing) |
| **Hyperstack** | "RTX Pro 6000 SE" **$1.85 OD / $1.48 spot**; reserved from $1.30 (up to 31 vCPU / 180 GB per GPU). getdeploying showed OD and spot **out of stock** on Oct 18, 2026 | — | L40 (not L40S) **$1.00 OD / $0.80 spot** (up to 28 vCPU / 120 GB) ✓ | $0.50 OD / $0.40 spot (up to 28 vCPU / **58 GB**) ✗ RAM | PCIe $1.35; NVLink $1.40; SXM $1.60. Spot $1.08 (up to 28 vCPU / 120 GB) ✓ | PCIe $2.50 (spot $2.00); NVLink $2.60; SXM $3.20 | [hyperstack.cloud/gpu-pricing](https://www.hyperstack.cloud/gpu-pricing), [getdeploying](https://getdeploying.com/gpus/nvidia-rtx-pro-6000) |
| **Nebius** | **$1.80 OD; preemptible from $0.79** (24 vCPU / 218 GB) ✓ | — | Intel CPU from $1.55 (8–40 vCPU / 32–160 GB); AMD from $1.82. Preemptible from $0.74 / $0.90 | — | — | $4.50 OD (16 vCPU / 200 GB); preemptible from $0.79 | [nebius.com/prices](https://nebius.com/prices) |
| **CoreWeave** | 8x only. $20.00 per instance-hour = **$2.50/GPU** (128 vCPU / 1 TB RAM). Spot $11.09 per instance-hour | — | 8x only, $2.25/GPU | — | 8x only, $2.70/GPU | 8x HGX ~$6.16/GPU | [coreweave.com/pricing](https://www.coreweave.com/pricing) |
| **Paperspace (DigitalOcean)** | — | — | — | "A6000" $1.89/h; Growth plan required | A100-80G $3.18/h; Growth plan required | H100 $5.95/h | [DO Paperspace pricing](https://docs.digitalocean.com/products/paperspace/pricing/) ("Last verified 13 Jul 2026", so possibly stale) |
| **Hyperbolic** | Not listed | — | — | — | Not listed | H100 SXM from $3.19. H200 $3.99, B200 $5.99 | [hyperbolic.ai/marketplace](https://hyperbolic.ai/marketplace), [UsagePricing Aug 4, 2026](https://usagepricing.com/blueprint/activity/hyperbolic-2026-08-04-price-change) |

#### Commitments and minimums
- **Lambda:** no minimum is stated for on-demand instances. 1-Click Clusters run 2 weeks to 1 year, and reserved pricing is by contacting sales ([lambda.ai/pricing](https://lambda.ai/pricing)).
- **Jarvislabs:** "Per-minute billing, no commitments". Commitment discounts are tiny: 2% for 1 month up to 9% for 1 year ([jarvislabs.ai/pricing](https://jarvislabs.ai/pricing)).
- **Verda:** reserved discounts are 2% (1 month), 3% (3 months), 4% (6 months), 8% (1 year) and 25% (2 years) ([verda.com/pricing](https://verda.com/pricing)).
- **Massed Compute:** "No long-term commitments" and "No bandwidth overcharges" ([vm.massedcompute.com/pricing](https://vm.massedcompute.com/pricing)).
- **CoreWeave:** committed usage can get up to 60% off on-demand. The public price list only shows 8-GPU instances ([coreweave.com/pricing](https://www.coreweave.com/pricing)).
- **Hyperbolic:** on-demand has "no minimum term or contract". You are not charged for instances that fail ([hyperbolic.ai/marketplace](https://hyperbolic.ai/marketplace)).

#### Billing granularity
- **Lambda:** billed hourly "in one-minute increments". Billing starts when the instance passes health checks and ends when you terminate it ([Lambda billing docs](https://docs.lambda.ai/public-cloud/billing/)).
- **Thunder:** billed per minute while running ([thundercompute.com/pricing](https://www.thundercompute.com/pricing)).
- **Jarvislabs:** billed per minute ([jarvislabs.ai/pricing](https://jarvislabs.ai/pricing), [docs.jarvislabs.ai](https://docs.jarvislabs.ai/)).
- **Hyperstack:** "billed per minute" ([hyperstack.cloud/gpu-pricing](https://www.hyperstack.cloud/gpu-pricing)).
- **Verda:** billed in "pre-paid 10-minute increments". Unused prepaid time on a terminated resource is refunded ([Verda pricing & billing](https://docs.verda.com/welcome-to-verda/pricing-and-billing/)).
- **Paperspace:** billed "on a per-hour basis" from create to destroy ([DO Paperspace pricing](https://docs.digitalocean.com/products/paperspace/pricing/)).
- **Nebius:** the standalone-applications docs bill per second against an hourly price ([Nebius standalone pricing](https://docs.nebius.com/applications/standalone/pricing)). Plain VM granularity was not confirmed (see Gaps).
- **Not stated:** Massed Compute, CoreWeave and Hyperbolic.

#### Spot and price volatility
- Nebius spot prices "may increase or decrease based on available capacity" and can change as often as every 15 minutes ([nebius.com/prices](https://nebius.com/prices)).
- Hyperbolic refreshes prices weekly from third-party supplier rates. Its H100 rose from $1.50 (June) to $2.89 (July) to $3.19 (Aug 2026) ([UsagePricing](https://usagepricing.com/blueprint/activity/hyperbolic-2026-08-04-price-change)).
- Jarvislabs raised prices from Oct 5, 2026, citing a "global shortage of GPU memory" ([Jarvislabs update](https://jarvislabs.ai/updates/gpu-pricing-october-2026)).

#### Thunder Compute caveats
- Thunder GPUs are **network-attached over TCP**, with virtualization at the CUDA layer. A GPU is dedicated to an instance only while a process uses it, and the company admits TCP is slower than PCIe ([Thunder blog](https://thundercompute.com/blog/how-thunder-compute-works-gpu-over-tcp)).
- Its "production mode" is described as a standard VM with these optimizations disabled. It costs more per hour than prototyping mode ([Thunder production-mode docs](https://www.thundercompute.com/docs/production-mode), via search snippet; the page returned 404 on direct fetch on 2026-10-18). The current pricing page shows only one rate per GPU and does not mention modes ([thundercompute.com/pricing](https://www.thundercompute.com/pricing)).
- Known incompatibilities: managed memory/UVM, CUDA MPS, GPU FFmpeg and GPU profilers ([Thunder compatibility](https://www.thundercompute.com/docs/docs/compatibility)).
- A search snippet of the same docs said "CUDA 12.9 installed … Do not attempt to reinstall CUDA" (page date unknown; [Thunder compatibility](https://www.thundercompute.com/docs/docs/compatibility)).
- Thunder's A100 80GB price is inconsistent across sources:
  - $0.78 "as of 6/26/2026" on a mirror of its pricing page ([discord.thundercompute.com/pricing](https://discord.thundercompute.com/pricing));
  - $1.09 in an August 2026 write-up ([Spheron](https://www.spheron.network/blog/thunder-compute-pricing-2026/));
  - $1.09 on the live page checked Oct 16, 2026 ([thundercompute.com/pricing](https://www.thundercompute.com/pricing)).
- Thunder also has per-second "sandboxes" (A100 80GB $1.95/h, H100 $2.95/h), which require requesting access ([thundercompute.com/pricing](https://www.thundercompute.com/pricing)).

#### OS images and driver/CUDA versions
- **Nebius:** an official boot image family **`ubuntu24.04-cuda13.0`** ("Ubuntu 24.04 LTS for NVIDIA GPUs (CUDA 13)") exists, alongside `ubuntu24.04-cuda12`. The driver version is not stated ([Nebius boot disk images](https://docs.nebius.com/compute/storage/boot-disk-images)).
- **Driver/CUDA pairing elsewhere:** third-party Ubuntu 24.04 CUDA 13 images ship 580-series drivers:
  - Alibaba: driver 580.126.09 with CUDA 13.0 ([Alibaba Cloud](https://help.aliyun.com/en/ecs/user-guide/ubuntu-pre-installed-nvidia-gpu-driver-image));
  - immers.cloud: 580.82.07 with CUDA 13 ([immers.cloud](https://en.immers.cloud/marketplace/linux/cuda/ubuntu_24043_300925_cudnn_cuda_13)).
- **Lambda:** on-demand instances come with **Lambda Stack** preinstalled ("no driver installs"). The pages publish no driver or CUDA version numbers ([lambda.ai/instances](https://lambda.ai/instances)).
- **Jarvislabs:** offers templates (PyTorch, TensorFlow and others) and "VMs include root and SSH access", plus `jl ssh`. CUDA and driver versions are not stated ([docs.jarvislabs.ai](https://docs.jarvislabs.ai/)).

#### SSH access
- Lambda: yes, VMs with Lambda Stack ([lambda.ai/instances](https://lambda.ai/instances)).
- Thunder: via VS Code/Cursor Remote-SSH plus console ([Thunder docs](https://www.thundercompute.com/docs)).
- Jarvislabs: SSH and `jl ssh` ([docs.jarvislabs.ai](https://docs.jarvislabs.ai/)).

#### Egress
- Free at Lambda ([billing docs](https://docs.lambda.ai/public-cloud/billing/)), Thunder ($0.00/GB, [pricing](https://www.thundercompute.com/pricing)), Hyperstack ([pricing](https://www.hyperstack.cloud/gpu-pricing)), CoreWeave ([pricing](https://www.coreweave.com/pricing)) and Paperspace ([DO pricing](https://docs.digitalocean.com/products/paperspace/pricing/)).
- Jarvislabs: free in-region ([pricing](https://jarvislabs.ai/pricing)).
- Nebius: general networking is free, but Standard object-storage egress is $0.015/GiB ([nebius.com/prices](https://nebius.com/prices)).
- Massed Compute: "No bandwidth overcharges" ([pricing](https://vm.massedcompute.com/pricing)).
- Verda: not stated on its pricing page.

#### Multi-GPU availability
- Massed Compute: RTX PRO 6000, A100 and others at 1x/2x/4x/8x for the same per-GPU price, though vCPU per GPU drops to about 15 at 2x and above ([Massed pricing](https://vm.massedcompute.com/pricing)).
- Jarvislabs: 1, 2, 4 or 8 GPUs ([pricing](https://jarvislabs.ai/pricing)).
- Lambda: A6000 at 1x/2x/4x ([pricing](https://lambda.ai/pricing)).
- Verda: RTX PRO 6000 at 1x/2x per getdeploying ([getdeploying](https://getdeploying.com/gpus/nvidia-rtx-pro-6000)).

### Inferences
- **Recommended shortlist for a CUDA 13 x86 single GPU with ≥16 vCPU and ≥64 GB RAM, cheapest first (my ranking):**
  1. Hyperstack L40 at $1.00 (only if in stock; L40 is Ada with 48 GB, so peak 40.5 GB fits with about 7 GB headroom).
  2. Massed Compute A100 80GB at $1.35.
  3. Hyperstack A100 PCIe at $1.35.
  4. Jarvislabs A100 80GB at $1.49.
  5. Nebius RTX PRO 6000 at $1.80.
  6. Hyperstack RTX Pro 6000 at $1.85 (reported out of stock).
  7. Massed Compute or Jarvislabs RTX PRO 6000 at $2.19.
  8. Verda RTX PRO 6000 at $2.37.
- **Thunder Compute is the riskiest cheap option.** The UVM and profiler incompatibilities, the note not to reinstall CUDA (12.9 per snippet), and the CUDA-layer virtualization suggest a host driver of 580 or newer with CUDA 13 cannot be self-installed in prototyping mode. Production-mode pricing is unclear.
- **Lambda is not cost-competitive** for this job:
  - no RTX PRO 6000, no L40S, no RTX 6000 Ada, and no 1x A100 80GB;
  - its 1x A6000 has only 14 vCPU;
  - its cheapest qualifying single GPU is the H100 PCIe at $3.29;
  - its GH200 at $2.29 is an ARM (Grace) host, so it fails the x86_64 requirement.
- **CoreWeave** ($20/h minimum instance) and **Paperspace** ($3.18 A100-80G plus a Growth plan) are not competitive for 1 GPU. Hyperbolic now starts at $3.19 for an H100 and lists no 48 GB-class card.
- **Cost per run may differ by GPU.** A100 (sm_80) and L40 (sm_89) have different throughput from RTX PRO 6000 (sm_120), so cost per completed 2-hour run may not track price per hour. A short benchmark on the cheapest candidate is advisable before the 20-run batch.
- **Parallelism does not change the price.** Twenty independent runs can go on separate 1x instances at the same per-GPU-hour price. Massed Compute and Jarvislabs price multi-GPU linearly.

### Gaps
- None of these pages confirm a 580+ driver or CUDA 13 image at Lambda, Verda, Hyperstack, Massed Compute or Jarvislabs. This needs to be checked with `nvidia-smi` on a live instance or with support. On full VMs with root (Verda, Hyperstack, Massed Compute, Lambda), installing driver 580+ is normally possible, but that is not confirmed.
- I could not confirm whether Thunder's current price table is for prototyping (virtualized) or production mode. Its live CUDA and driver versions are also unverified.
- RTX PRO 6000 is not on Lambda's or Hyperbolic's public price list as of 2026-10-18. I found no announcement of Lambda RTX PRO 6000 on-demand instances.
- Not found:
  - Massed Compute billing granularity, stopped-instance policy and storage add-on prices (its FAQ page had no billing details);
  - Hyperbolic vCPU/RAM, storage and billing increments;
  - CoreWeave self-serve sign-up terms;
  - Verda egress pricing;
  - Nebius VM billing granularity (as opposed to standalone applications).
- Not verified: the Hyperstack per-GPU vCPU/RAM figures are "max per GPU", and the actual 1x flavor sizes and live stock status were not checked.
- Not covered in this pass: Crusoe, Voltage Park, FluidStack, Genesis Cloud, OVHcloud and Scaleway. The getdeploying list of RTX PRO 6000 providers (updated Oct 18, 2026) does not include any of them.

---

## Who offers the RTX PRO 6000 96 GB, and at what price?

### Takeaway
Among major named providers, verified on-demand single-GPU RTX PRO 6000 prices (2026-10-18) are:

| Provider | On-demand | Spot / preemptible | Single GPU spec | Note |
|---|---|---|---|---|
| Nebius | **$1.80** | from $0.79 | 24 vCPU / 218 GB | |
| Hyperstack | $1.85 | $1.48 | | Reported out of stock |
| Massed Compute | $2.19 | | 16 vCPU / 144 GB / 725 storage | |
| Jarvislabs | $2.19 | $1.15 (per getdeploying) | | Up from $1.89 on Oct 5, 2026 |
| Verda | $2.371 | $1.186 | | |
| CoreWeave | $2.50/GPU | | 8x only | |

Lambda, Thunder, Paperspace and Hyperbolic do not list it. Aggregators show cheaper marketplace-style offers (RunPod Community $1.69, UpCloud $1.88, Beam $1.09), but those were outside this assignment's scope.

### Cited Findings
- **Nebius:** RTX PRO 6000 on-demand $1.80, preemptible from $0.79, 24 vCPU / 218 GB RAM ([nebius.com/prices](https://nebius.com/prices)).
- **Hyperstack:** "RTX Pro 6000 SE" 96 GB at $1.85 on-demand, $1.48 spot and reserved from $1.30, with up to 31 vCPU and 180 GB RAM per GPU ([hyperstack.cloud/gpu-pricing](https://www.hyperstack.cloud/gpu-pricing)). getdeploying (updated Oct 18, 2026) marks the Hyperstack on-demand and spot offers out of stock ([getdeploying](https://getdeploying.com/gpus/nvidia-rtx-pro-6000)).
- **Massed Compute:** RTX PRO 6000 Blackwell at $2.19/GPU-h for 1x, 2x, 4x and 8x ([vm.massedcompute.com/pricing](https://vm.massedcompute.com/pricing)).
  - 1x: 16 vCPU / 144 GB RAM / 725 storage.
  - 8x: 120 vCPU / 1152 GB / 5800.
  - A "Reduced Storage" variant costs the same with half the disk.
- **Jarvislabs:** $2.19/h on-demand, 28 vCPU / 160 GB RAM, configurations of 1, 2, 4 or 8 GPUs ([jarvislabs.ai/pricing](https://jarvislabs.ai/pricing)). The price rose from $1.89 to $2.19 effective Oct 5, 2026 00:00 IST ([Jarvislabs update](https://jarvislabs.ai/updates/gpu-pricing-october-2026)). getdeploying lists Jarvislabs spot at $1.15 and 12-month reserved at $2.01 ([getdeploying](https://getdeploying.com/gpus/nvidia-rtx-pro-6000)).
- **Verda:** RTX PRO 6000 Blackwell 96 GB at $2.371 on-demand and $1.186 spot, 30 vCPU / 90 GB RAM ([verda.com/pricing](https://verda.com/pricing)). An aggregator listing showed Verda at $1.98 (spot $0.99), but it was undated; Verda says prices vary by data-center location ([computeprices](https://computeprices.com/providers/google/gpus/rtx-pro-6000); [Verda billing](https://docs.verda.com/welcome-to-verda/pricing-and-billing/)).
- **CoreWeave:** the RTX PRO 6000 Blackwell "High Memory" instance is 8× 96 GB with 128 vCPU and 1,024 GB RAM ([coreweave.com/pricing](https://www.coreweave.com/pricing)).
  - On-demand: $20.00 per instance-hour, or $2.50/GPU.
  - Spot: $11.09 (NA) or $11.01 (EU) per instance-hour.
  - The Standard Memory variant is contact-sales only, with spot at $9.56 per instance-hour.
- **Not listed:** Lambda's pricing and instances pages do not list RTX PRO 6000 ([lambda.ai/pricing](https://lambda.ai/pricing), [lambda.ai/instances](https://lambda.ai/instances)). Neither do Thunder ([pricing](https://www.thundercompute.com/pricing)), Paperspace ([DO pricing](https://docs.digitalocean.com/products/paperspace/pricing/)) or Hyperbolic ([marketplace](https://hyperbolic.ai/marketplace)).
- **Cross-check from aggregators** (getdeploying, Oct 18, 2026; [getdeploying](https://getdeploying.com/gpus/nvidia-rtx-pro-6000)):
  - median on-demand price is about $2.30/GPU-h;
  - lowest verified in-stock offer is $0.66 (Packet·ai);
  - RunPod $1.69 Community to $2.49 Secure (16 vCPU / 188 GB);
  - UpCloud $1.88 (spot $1.41);
  - Sesterce $2.41 (16 vCPU / 192 GB);
  - Hetzner $2.16 (checked Aug 31, 2026);
  - AWS g7e.2xlarge $3.36 (8 vCPU);
  - Google Cloud $4.50 (48 vCPU), spot $1.79.
- **Conflicting Google Cloud figure:** computeprices claims Google Cloud is cheapest at $0.647/GPU-h single-GPU on-demand. This likely reflects a different instance shape or accounting ([computeprices](https://computeprices.com/providers/google/gpus/rtx-pro-6000)); getdeploying gives $4.50.

### Inferences
- **Nebius at $1.80** is the cheapest RTX PRO 6000 from a mainstream, self-serve, x86 provider that meets the vCPU and RAM spec and has an official CUDA 13 image family. It is the leading RTX PRO 6000 choice if sign-up from Turkey works (unverified).
- **Massed Compute and Jarvislabs ($2.19)** are the cheapest RTX PRO 6000 options with clearly published per-minute or no-commitment terms from this assignment's named list. Verda's spot ($1.186) is about half its on-demand price but preemptible.
- **Hyperstack's $1.85** may be unavailable in practice (out-of-stock flags).

### Gaps
- Live stock was not verified at any provider. getdeploying itself warns that availability was checked at various times.
- No evidence was found of RTX PRO 6000 at Crusoe, Voltage Park, FluidStack, Genesis Cloud, OVHcloud or Scaleway. A targeted search returned no provider pages for them.

---

## How does persistent storage work when instances are terminated, and what does it cost? (including stopped-instance charges)

### Takeaway
**Cheapest per GB-month:**
- Nebius block volumes at about $0.053/GiB-mo (no replication) or its shared filesystem at $0.08/GiB-mo;
- CoreWeave Distributed File Storage at $0.07/GB-mo;
- Hyperstack at about $0.071/GB-mo.

**Mid-range:** Jarvislabs at about $0.10/GB-mo.

**Most expensive:**
- Lambda filesystem (the docs give $0.20/GiB-mo only as an example);
- Verda block or shared filesystem at $0.20/GiB-mo;
- Thunder disk at $0.219/GB-mo, billed only while running, with $0.05/GB-mo snapshots.

**500 GB for about one month:**

| Provider | Approx. cost |
|---|---|
| Nebius | $27–40 |
| Hyperstack | $35 |
| Jarvislabs | $50 |
| Lambda / Verda | $100 |
| Thunder (snapshot only) | $25 |

The big pitfall is "stopped" states:
- **Verda's shut-down instances keep billing**, as do **Hyperstack's SHUTOFF VMs**.
- **Lambda cannot pause**; you must terminate and keep data on a filesystem.
- Jarvislabs and Hyperstack (hibernate) stop compute billing while keeping storage.

### Cited Findings

**Lambda**
- Instances cannot be paused; you can only terminate. Persistent filesystems "imitate some of the benefits" of pausing ([Lambda getting started FAQ](https://docs.lambda.ai/public-cloud/on-demand/getting-started)).
- Filesystems are billed per GiB-month in 1-hour increments, as long as the filesystem exists (even unattached), with no minimum period. "$0.20 per GiB-month" is given only as an example; the actual price is shown at creation ([Lambda billing](https://docs.lambda.ai/public-cloud/billing/)).
- A filesystem must be attached before the instance starts and cannot be mounted remotely via NFS ([Lambda FAQ via search](https://docs.lambda.ai/public-cloud/on-demand/getting-started)).
- Instances "are billed for as long as they're running, regardless if they're actively being used" ([Lambda billing](https://docs.lambda.ai/public-cloud/billing/)).

**Verda**
- "Shutdown instances continue to charge your account." Hibernate was removed because it "was the same as Delete while keeping all storage" ([Verda shutdown/delete](https://docs.verda.com/cpu-and-gpu-instances/shutdown-hibernate-and-delete/)).
- On delete, "All storage not marked for deletion will continue to charge your account". Detached volumes can be attached to new instances (same page).
- NVMe block storage and the NVMe shared filesystem are each $0.20/GiB-mo ($200/TiB) ([verda.com/pricing](https://verda.com/pricing)).
- If your prepaid balance reaches zero, "instances will be discontinued and your volumes (data) will be deleted". Volumes can be restored for up to 96 hours ([Verda billing](https://docs.verda.com/welcome-to-verda/pricing-and-billing/)).

**Jarvislabs**
- Pausing stops compute billing and keeps `/home` data. Storage is billed while paused; deleting stops all billing ([docs.jarvislabs.ai](https://docs.jarvislabs.ai/)).
- Paused storage costs $0.00014/GB-h (about $0.10/GB-mo; the example given is 50 GB = $5.04/mo) ([Jarvislabs FAQ](https://docs.jarvislabs.ai/faqs/), [file storage](https://docs.jarvislabs.ai/filestorage/)). The pricing page lists storage at $0.10/GB per month ([jarvislabs.ai/pricing](https://jarvislabs.ai/pricing)).
- Shared filesystems attachable to multiple instances and S3-compatible object storage are also offered ([docs.jarvislabs.ai](https://docs.jarvislabs.ai/)).
- Data is kept "as long as you have balance" ([Jarvislabs FAQ](https://docs.jarvislabs.ai/faqs/)).

**Hyperstack**
- Storage costs $0.000096774/GB-h, about $0.071/GB-mo ([hyperstack.cloud/gpu-pricing](https://www.hyperstack.cloud/gpu-pricing)).
- Hibernating a VM stops all billing except public IP and storage. SHUTOFF VMs continue to incur standard charges ([Hyperstack VM state docs](https://infrahub-doc.nexgencloud.com/docs/virtual-machines/manage-vm-state/), [Hyperstack 2023 release notes](https://docs.hyperstack.cloud/docs/release-notes/2023)).
- Ephemeral-disk data is lost on hibernate, resize or delete unless it is copied to a Shared Storage Volume (same sources).
- After the prepaid balance is depleted and a grace period passes, resources may be terminated, then permanently deleted after one week without a recharge ([hyperstack.cloud/gpu-pricing](https://www.hyperstack.cloud/gpu-pricing)).

**Thunder Compute**
- Instance disk costs $0.219/GB-mo, metered hourly and **billed only while running**, with the first 100 GB per GPU included ([thundercompute.com/pricing](https://www.thundercompute.com/pricing)).
- Snapshots cost $0.05/GB-mo until deleted (same page).
- Each instance has 100–500 GB of disk (same page).

**Nebius** ([nebius.com/prices](https://nebius.com/prices))

| Storage type | Price per GiB-month |
|---|---|
| Block, no replication | $0.053 |
| Block, erasure coding | $0.071 |
| Block, 3x mirroring | $0.118 |
| Local SSD | $0.065 |
| Shared filesystem | $0.08 |
| WEKA filesystem | $0.10 |
| Object storage, Standard | $0.0147 |

**Massed Compute**
- Storage is bundled per configuration, e.g. RTX PRO 6000 1x has 725 and A100 1x has 512; units are not stated ([vm.massedcompute.com/pricing](https://vm.massedcompute.com/pricing)).
- No separate persistent-volume pricing or stopped-instance policy was found (same page).

**CoreWeave** ([coreweave.com/pricing](https://www.coreweave.com/pricing))
- Distributed File Storage costs $0.07/GB-mo.
- AI Object Storage costs $0.06 (hot), $0.03 (warm) or $0.015 (cold) per GB-mo.
- Storage is billed in GiB.

**Paperspace** ([DO Paperspace pricing](https://docs.digitalocean.com/products/paperspace/pricing/), verified Jul 13, 2026)
- Compute stops when a machine is powered off, but attached storage and public IP keep billing.
- Block storage ranges from $0.0074/h (50 GB, capped at $5/mo) to $0.1786/h (2 TB, capped at $120/mo).
- Shared drives start at $16/mo for 250 GB.

### Inferences
- **The cheapest pattern** is a provider with a separate network volume or filesystem plus per-minute compute and a true "terminate/hibernate without GPU charge" state:
  - Nebius filesystem or block plus VMs;
  - Hyperstack shared volume plus hibernate;
  - Jarvislabs pause.
- **Verda trap:** "shutdown" keeps charging, so instances must be deleted while keeping the volume.
- **Lambda trap:** terminate after each session; filesystems must be attached at launch.
- **Estimated storage cost through 2026-11-04** (about 0.6 month for 500 GB):
  - Nebius: about $16–24;
  - Hyperstack: about $21;
  - Jarvislabs: about $30;
  - Lambda or Verda: about $60.
  - These are small relative to 100–150 GPU-hours of compute.
- **Massed Compute's bundled local disk** (512–725 GB on 1x) may be enough if instances are kept and stopped. Its stopped-instance billing is unknown, so data persistence across termination needs to be confirmed.

### Gaps
- Not found:
  - Lambda's current actual filesystem price (the docs show only the $0.20 example);
  - Massed Compute's stopped-instance and persistent-storage pricing;
  - Nebius stopped-VM charges and per-second VM billing;
  - CoreWeave block-storage price (not listed).
- Lambda's "no pause" FAQ may be outdated; one source described pausing as "in the works".

---

## Are there free-credit programs we could realistically get quickly? (including sign-up friction and non-US cards)

### Takeaway
No program yields meaningful credit quickly:
- **Nebius free trial:** $5 for 30 days (individuals only, eu-north1).
- **Thunder:** a reported $20 student credit (unverified).
- **Verda:** credits in exchange for a published blog post or video, amount discretionary, with a 1–2 business-day review.
- **Nebius research grants:** academic only, with decisions in late Q3 to early Q4 2026.
- **Lambda research grant:** up to $5,000, announced Dec 2024, status in 2026 unknown.

None can realistically fund 100–150 GPU-hours before 2026-11-04. On payment and country: **Lambda explicitly lists Turkey** as a supported billing country but takes only major credit cards (no debit or prepaid), with a $10 pre-authorization. Most others are prepaid wallets funded by card (Jarvislabs via Stripe, Verda by card or SEPA, Hyperstack prepaid balance).

### Cited Findings

**Lambda**
- The supported billing regions include Turkey, along with the US, EU (except Lithuania), UK, Israel, UAE and others ([Lambda manage billing](https://docs.lambda.ai/public-cloud/manage-billing/)).
- "Lambda only accepts major credit cards." Prepaid and debit cards are common decline reasons, and there is a $10 pre-authorization (same page).
- Purchases through a VPN may be declined ([Lambda payment FAQ](https://beta-docs.lambdalabs.com/cloud/problem-processing-payment-method)).
- Research Grant: up to $5,000 in Cloud Credits, announced Dec 9, 2024 ([BusinessWire](https://www.businesswire.com/news/home/20241209358457/en/Lambda-Launches-Grant-for-AI-Researchers-Expands-Research-Program)). No 2026 confirmation was found.

**Nebius**
- Free trial: $5 credit for 30 days, individuals only (not companies), once per user and card, eu-north1 only. Continuing charges a $25 initial top-up ([Nebius free trial](https://docs.nebius.com/signup-billing/free-trial)).
- Pay-as-you-go is available to individuals; commitment discounts are company-only ([Nebius billing models](https://docs.nebius.com/signup-billing/billing-models/overview)).
- Research grants: for academic and non-profit researchers in the 2026–27 cycle, with notification in late Q3 to early Q4 2026. Amounts are set per proposal, and Nebius support must be acknowledged in publications ([Nebius research grants](https://nebius.com/nebius-research-grants)).

**Verda**
- Credits for original content (a blog post of 1,000–2,000 words or a 5–10 minute video), agreed with Verda before publishing. Review takes 1–2 business days, the amount "will depend on the quality and depth of your content", and credits do not expire ([Verda credits](https://docs.verda.com/resources/obtaining-free-credits/how-to-receive-credits/)).
- Payment is prepaid via card top-up (one-time or auto) or SEPA bank transfer. Invoice top-ups have a minimum of 1,000 EUR/USD ([Verda billing](https://docs.verda.com/welcome-to-verda/pricing-and-billing/)).

**Jarvislabs**
- Payments go through Stripe and accept "all major credit/debit cards". PayPal and UPI are not accepted. You fund a prepaid wallet ([Jarvislabs FAQ](https://docs.jarvislabs.ai/faqs/)).
- Customers outside India are billed in USD ([jarvislabs.ai/pricing](https://jarvislabs.ai/pricing)).
- No free-credit program is stated (same page).

**Hyperstack**
- Runs on a prepaid balance with depletion alerts at 50–100%; enterprise contracts go through sales ([hyperstack.cloud/gpu-pricing](https://www.hyperstack.cloud/gpu-pricing)).

**Thunder Compute**
- A payment method must be added before use ([Thunder docs](https://www.thundercompute.com/docs)).
- Thunder raised a $13M Series A on Aug 19, 2026, per a third-party report ([wavect.io](https://wavect.io/de/blog/thunder-compute-gpu-virtualization-series-a.md)).

**Paperspace**
- A6000 and A100-80G require the Growth plan ($0.058/h, capped at $39/mo) ([DO Paperspace pricing](https://docs.digitalocean.com/products/paperspace/pricing/)).

**Hyperbolic**
- Requires account sign-up and pays by credit card or Stripe ([hyperbolic.ai/marketplace](https://hyperbolic.ai/marketplace)).

**General**
- Credit programs typically require an application, eligibility gates and a multi-day review ([Spheron 2026 roundup](https://www.spheron.network/blog/free-gpu-cloud-credits-2026/)).

### Inferences
- **Realistically, plan to pay list price.** The Nebius $5 trial is enough to smoke-test the `ubuntu24.04-cuda13.0` image with JAX and Warp, but not for training.
- **Lowest-friction paths from Turkey:**
  - Lambda: Turkey is explicitly listed, but you need a real credit card, not a debit card.
  - Stripe-based prepaid wallets (Jarvislabs, Verda card top-up): likely to work with Turkish credit cards, but not confirmed.
- **Prepaid wallets carry a data-loss risk:** at Verda and Hyperstack, volumes are deleted after the balance hits zero (Verda restores within 96 h; Hyperstack deletes after one week). Enable auto top-up or low-balance alerts.

### Gaps
- No source confirms that Turkish-issued cards work at Nebius, Verda, Jarvislabs, Hyperstack, Massed Compute, Thunder or Hyperbolic.
- Not found:
  - KYC or business-verification requirements for Hyperstack, CoreWeave and Massed Compute (searches returned nothing relevant);
  - CoreWeave self-serve sign-up terms (likely sales-led, unverified);
  - Hyperstack startup-credit programs.
- Thunder student credit: a search snippet claimed "$20 of credit" with a student email, and an April 2025 claim said "$20 every month". Neither was confirmed on a current official page.
- Lambda's 2026 research-grant status is unknown; the latest evidence is the Dec 2024 press release.
