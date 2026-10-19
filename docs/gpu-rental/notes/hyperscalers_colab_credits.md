# Hyperscaler, Google Colab and free-credit options for one >=48 GB NVIDIA GPU (October 2026)

All pages were read on 2026-10-18 unless another date is given. "Spot" prices on GCP, AWS and Azure move over time. GCP's docs say Spot prices "can change up to once every day". Every spot figure below is a snapshot.

Requirement recap from the assignment: one GPU with >=48 GB VRAM (peak use 40.5 GB), Linux x86_64, a CUDA 13-capable driver, SSH, >=16 vCPU and >=64 GB RAM per GPU, ~500 GB persistent storage, and ~100-150 GPU-hours until 2026-11-04 (17 days from today, about 0.56 of a 730-hour month).

Source-quality note: GCP's GPU and VM pricing pages (cloud.google.com/compute/gpus-pricing and /vm-instance-pricing) render their prices in JavaScript. WebFetch and curl both returned no price tables. For Compute Engine VM and GPU prices I therefore used SpareCores. It shows an "observed at" timestamp of 2026-10-18 11:40 UTC and tracks the providers' price APIs. I cross-checked it against other aggregators. GCP disk prices come straight from the official page's HTML. Azure prices come straight from the official public Azure Retail Prices API. AWS prices are from SpareCores and Vantage.

## Q1. Is GCP Spot G4 (RTX PRO 6000) the cheapest reliable per-hour option, and what are the quota and interruption realities for a new account?

### Takeaway
GCP Spot G4 costs about $1.63/h in us-central1 for the whole `g4-standard-48` VM (1x RTX PRO 6000 96 GB, 48 vCPU, 180 GB RAM). That is about 64% below the $4.50/h on-demand price. It is not the cheapest >=48 GB hyperscaler option, though. Azure lists Spot A100 80 GB at $0.68/h and a full Spot RTX PRO 6000 at $1.02/h, and AWS Spot L40S 48 GB starts at $0.96/h (Q2). On GCP itself, Spot G4 is the cheapest full >=48 GB GPU in US regions, but the market moves: GCP A100 80 GB Spot was $1.85/h in us-east5. A new account faces three hurdles. The Free Trial forbids GPUs and quota requests, so you must upgrade to paid. You then need G4 Spot quota (`PREEMPTIBLE_NVIDIA_RTX_PRO_6000_GPUS`) plus the global "GPUs (all regions)" quota. Spot has no SLA, and preemption gives a best-effort shutdown of up to 30 s.

### Cited Findings

**G4 machine types (official docs)** — [GCP accelerator-optimized machines](https://docs.cloud.google.com/compute/docs/accelerator-optimized-machines)
- G4 shapes are `g4-standard-6` (1/8 GPU, 12 GB, 6 vCPU, 22 GB), `-12` (1/4, 24 GB, 12 vCPU, 45 GB), `-24` (1/2, 48 GB, 24 vCPU, 90 GB), `-48` (1 GPU, 96 GB GDDR7, 48 vCPU, 180 GB RAM, up to 1,500 GiB Titanium SSD, 50 Gbps), `-96` (2 GPUs), `-192` (4) and `-384` (8).
- The GPU is the RTX PRO 6000 with "96 GB GDDR7 (1.597 TBps)" on PCIe Gen 5.
- Disks: "Hyperdisk Balanced ... the only type supported for the boot disk". The docs also say: "You can't use Persistent Disk (regional or zonal) on an instance that uses a G4 machine type." Hyperdisk Balanced HA, ML, Throughput and Titanium SSD are also supported. Hyperdisk Extreme works only with 2+ GPUs.
- G4 supports Spot VMs, flex-start, on-demand and future reservations (including calendar mode), and CUDs.
- The fractional shapes (`-6`, `-12`, `-24`) use NVIDIA vGPU. Do not use `--no-service-account` or `--no-scopes` with them, because Compute Engine must verify the VM's identity to authenticate the vGPU drivers.

**G4 prices by region (whole VM, USD/h, observed 2026-10-18 11:40 UTC)** — [SpareCores g4-standard-48](https://sparecores.com/server/gcp/g4-standard-48)

| Region | Spot | On-demand |
|---|---|---|
| us-central1 (Iowa) | 1.6294 | 4.4999 |
| us-west1 | 1.6675 | 4.4999 |
| us-east1 | 1.6675 | 4.4999 |
| us-east4 | 1.7937 | 4.4999 |
| us-south1 | 1.8022 | 4.4999 |
| europe-north1 (Finland) | 2.0543 | 4.9499 |
| us-west3 | 2.0642 | 4.9499 |
| europe-west4 (NL) | 2.2217 | 4.9499 |
| europe-west1 (BE) | 2.2292 | 4.9499 |
| europe-west2 (London) | 2.2385 | 5.3999 |
| asia-northeast1 (Tokyo) | 2.2247 | 5.8499 |
| asia-southeast1 (SG) | 2.2951 | 5.3999 |
| europe-west10 (Berlin) | 2.3515 | 5.3991 |
| europe-west8 (Milan) | 2.4935 | 5.3999 |
| me-central2 (Dammam) | 2.4658 | 5.3991 |
| asia-south1 (Mumbai) | 2.5079 | 5.8496 |

- SpareCores lists G4 in 22 regions covering 90 zones. — [SpareCores g4-standard-48](https://sparecores.com/server/gcp/g4-standard-48)
- Cross-checks, taken from search snippets, not full pages:
  - ComputePrices: G4 Spot $1.71/h in Iowa, "updated October 6, 2026". — [ComputePrices](https://computeprices.com/providers/google/gpus/rtx-pro-6000)
  - Economize: G4 Spot $1.7716/h, -61% vs on-demand. — [Economize](https://www.economize.cloud/resources/gcp/pricing/compute-engine/g4-standard-48/)
  - An earlier SpareCores snapshot in a search snippet showed us-central1 Spot at $1.7429/h, so the price moved within days. — [SpareCores](https://sparecores.com/server/gcp/g4-standard-48)
- On-demand g4-standard-48 is $4.50/h. A third-party October 2026 comparison lists Vast.ai $1.64, Nebius $1.80 and Runpod $2.49 per RTX PRO 6000 hour (search snippet). — [Thunder Compute RTX PRO 6000 pricing (Oct 2026)](https://www.thundercompute.com/blog/nvidia-rtx-pro-6000-pricing)
- The half-GPU `g4-standard-24` (48 GB vGPU, 24 vCPU, 90 GiB) costs $0.9368/h Spot and $2.5875/h on-demand in us-central1, and $1.2776/$2.8463 in europe-west4. — [SpareCores g4-standard-24](https://sparecores.com/server/gcp/g4-standard-24)

**Other GCP GPUs (whole VM, USD/h, observed 2026-10-18)**
- A100 80 GB, `a2-ultragpu-1g` (12 vCPU, 170 GiB, 1x A100-SXM4-80GB). This fails the >=16 vCPU requirement. — [SpareCores a2-ultragpu-1g](https://sparecores.com/server/gcp/a2-ultragpu-1g)
  - us-east5: Spot $1.8545, on-demand $5.5649
  - us-east4: $2.5290 / $5.7077
  - europe-west4: $3.0156 / $5.5809
  - us-central1: $3.0388 / $5.0688
- H100 80 GB, `a3-highgpu-1g` (26 vCPU, 234 GiB): — [SpareCores a3-highgpu-1g](https://sparecores.com/server/gcp/a3-highgpu-1g)
  - us-central1 and us-west1: Spot $6.5993, on-demand $11.0612
  - europe-west1: $6.2560 / $12.1712
  - SpareCores also shows europe-north1 Spot at $1.1422 and europe-west2 at $1.8645 against on-demand of about $12-12.6. These look anomalous; treat them as unverified.
- L4 24 GB, `g2-standard-16` (16 vCPU, 64 GiB). Too small in VRAM; listed only for reference. — [SpareCores g2-standard-16](https://sparecores.com/server/gcp/g2-standard-16)
  - us-central1: Spot $0.6865, on-demand $1.1472
  - asia-northeast3: Spot $0.5243
- G2 shapes run from `g2-standard-4` to `g2-standard-96`. `g2-standard-16` is 16 vCPU / 64 GB with one 24 GB L4. — [GCP accelerator-optimized machines](https://docs.cloud.google.com/compute/docs/accelerator-optimized-machines)

**Quota** — [GCP resource usage / quotas](https://docs.cloud.google.com/compute/resource-usage)
- G4 quota names:
  - standard: `GPU_FAMILY:NVIDIA_RTX_PRO_6000`
  - preemptible/Spot: `PREEMPTIBLE_NVIDIA_RTX_PRO_6000_GPUS`
  - also `COMMITTED_...` and `..._VWS_GPUS` variants
- Other GPU quota names:
  - L4: `GPU_FAMILY:NVIDIA_L4` and `PREEMPTIBLE_NVIDIA_L4_GPUS`
  - A100 80 GB: `NVIDIA_A100_80GB_GPUS` and `PREEMPTIBLE_NVIDIA_A100_80GB_GPUS`
  - H100: `GPU_FAMILY:NVIDIA_H100` and `PREEMPTIBLE_NVIDIA_H100_GPUS`
- Spot VMs consume the preemptible quotas.
- "New accounts and projects have a global GPU quota that applies to all regions" ("GPUs (all regions)"). The page gives no default value.
- Increases are requested on the console Quotas page. Free Trial billing accounts "can't request a change to your quota".
- Free Trial accounts also cannot "Add GPUs to your VM instances" or "Request a quota increase". Upgrading to a paid billing account unlocks GPUs. Remaining trial credit stays usable within the original 90 days. — [GCP Free Trial terms](https://docs.cloud.google.com/free/docs/free-cloud-features)
- Community reports on new accounts (anecdotal):
  - Upgrading "doesn't necessarily mean your quota will automatically be upgraded".
  - Approvals take "a couple of minutes to a week".
  - One user's GPU quota (Cloud Run) stayed at 0 for 50+ hours after upgrading.
  - One personal project could not raise CPUs quota above 8.
  - Sources: [Stanford CS329S GCP tutorial](https://github.com/stanford-cs329s/gcp-tutorials), [Google Dev forum: GPU quota exceeded 0.0 globally](https://discuss.google.dev/t/quota-gpus-all-regions-exceeded-limit-0-0-globally/121596), [Google Dev forum: Cloud Run GPU quota after 50+ hours](https://discuss.google.dev/t/cloud-run-gpu-quota-not-activated-after-50-hours-on-paid-account/323795), [Google Dev forum: CPUs quota above 8](https://discuss.google.dev/t/unable-to-increase-compute-engine-api-cpus-quota-above-8-in-my-personal-gcp-project/145321)

**Spot behaviour and stopped-VM charges** — [GCP Spot VMs](https://docs.cloud.google.com/compute/docs/instances/spot)
- Discounts are "up to 91%", and "Spot prices can change up to once every day".
- "Spot VMs don't have a minimum or maximum runtime".
- The preemption notice is 0 s (default) or 120 s. Shutdown is "best effort and up to 30 seconds".
- The termination action is STOP (default) or DELETE. While a VM is TERMINATED you are not billed for VM hours, but attached disks still incur storage charges.
- "Spot VMs are not covered by any Service Level Agreement."
- Free Tier credits do not apply to Spot VMs.

**Disk prices, us-central1 (the default region shown in the official table; hourly figures converted at 730 h/month)** — [GCP disk and image pricing](https://cloud.google.com/compute/disks-image-pricing)
- Hyperdisk Balanced capacity: $0.000109589/GiB-h, about **$0.08/GiB-month**.
- Above the free baseline of 3,000 IOPS and 140 MBps:
  - IOPS: $0.000006849/IOPS-h, about $0.005/IOPS-month
  - throughput: $0.000054795/MBps-h, about $0.04/MBps-month
- Persistent Disk (not usable on G4):
  - pd-balanced: $0.000136986/GiB-h, about $0.10/GiB-month
  - pd-ssd: about $0.17/GiB-month
  - pd-standard: $0.000054795/GiB-h, about $0.04/GiB-month, with the first 30 GiB-month free per account
- Standard snapshot storage: $0.000068493/GiB-h, about $0.05/GiB-month.
- Disks are billed per second on provisioned (not used) size.

**Images / driver** — [Deep Learning VM images](https://docs.cloud.google.com/deep-learning-vm/docs/images) (page last updated 2026-10-13)
- Current families:
  - `common-cu129-ubuntu-2404-nvidia-580` and `common-cu129-ubuntu-2204-nvidia-580` (CUDA 12.9, NVIDIA driver 580)
  - `pytorch-2-9-cu129-ubuntu-{2404,2204}-nvidia-580`
- No `cu13`/CUDA 13 family is listed, and the page does not mention G4 or Blackwell.
- The CUDA 12.8 / driver 570 families reached end-of-patch on 2026-04-13.

### Inferences
- Cost for this project on GCP Spot G4 us-central1 (my arithmetic):
  - GPU time: 100 h ≈ $163, 150 h ≈ $244.
  - A 500 GiB Hyperdisk Balanced for 17 days (408 h): 500 × $0.000109589 × 408 ≈ $22.4.
  - A right-sized 200 GiB disk: ≈ $9.
  - The same 150 h on-demand ≈ $675.
- Running Spot from Europe (closer to Turkey) costs 25-40% more per hour than us-central1. For batch training, latency does not matter, so US regions are the cheaper choice.
- The half-GPU `g4-standard-24` gives exactly 48 GB at $0.94/h Spot. Per GPU-GB that is more expensive than the full GPU: $0.94 for 48 GB vs $1.63 for 96 GB. It is cheaper per hour, but:
  - it leaves only ~7.5 GB headroom over the 40.5 GB peak;
  - it runs through the vGPU (GRID) driver stack, and CUDA 13 support there is unverified;
  - its 24 vCPU / 90 GB still meet the CPU and RAM requirements.
  - Hypothesis: test it only if quota for full G4s is scarce.
- Driver 580 is the driver branch that ships with CUDA 13.0. So the cu129 DLVM image with driver 580 should run pip-installed CUDA 13 wheels (JAX cuda13, Warp). This is my inference, not verified on a G4 here. Check `nvidia-smi` for "CUDA Version: 13.x" on first boot.
- Twenty parallel 2-hour runs would need `PREEMPTIBLE_NVIDIA_RTX_PRO_6000_GPUS` >= 20 and "GPUs (all regions)" >= 20, plus about 960 vCPUs of CPU quota. That is unrealistic for a days-old account. Plan for 1-4 concurrent GPUs and sequential batches.
- Each 2-hour run must checkpoint frequently, because preemption gives at most ~30 s of shutdown time.

### Gaps
- I could not read the official GCP G4 GPU/VM price tables, because they are rendered in JavaScript. G4 prices rest on SpareCores plus two cross-checking aggregators.
- I found no measured G4 Spot preemption frequency or obtainability data for any zone.
- The default "GPUs (all regions)" quota value for a brand-new paid account is undocumented. Typical approval times come from anecdotes only.
- I could not confirm whether a CUDA 13 DLVM family exists by name. The docs show none; `gcloud compute images list --filter="family~cu13"` would settle it.
- Not checked: whether G4 instances need a specific minimum 580.x driver, and which CPU quota family G4 vCPUs draw from.

## Q2. How do AWS (g6e, g7e, p5) and Azure Spot compare?

### Takeaway
On a per-hour basis, Azure has the cheapest >=48 GB Spot list prices in the official Retail Prices API:

| Azure Spot SKU (eastus/westus2) | GPU | $/h |
|---|---|---|
| NC24ads_A100_v4 | A100 80 GB, 24 vCPU | 0.679 |
| NC72lds_xl_RTXPRO6000BSE_v6 | half RTX PRO 6000, 48 GB | 0.451 |
| NC144lds_xl_RTXPRO6000BSE_v6 | full RTX PRO 6000 | 1.016 |

But Azure GPU quota for new or student subscriptions is effectively zero until you upgrade and file a request.

On AWS:
- L40S 48 GB (`g6e.4xlarge`, 16 vCPU / 128 GiB) costs $3.00/h on-demand. Spot is $0.96 in eu-north-1 but $1.5-2.6 in US regions.
- RTX PRO 6000 (`g7e.4xlarge`) costs $4.00/h on-demand and $1.54/h Spot in us-east-1.
- New AWS accounts start with 0 vCPU quota for G instances.

### Cited Findings

**AWS (USD/h, observed 2026-10-18 11:18 UTC)**
- `g6e.4xlarge`: 16 vCPU, 128 GiB, 1x L40S (45 GiB reported VRAM), 600 GB NVMe. On-demand is $3.0042 in us-east-1, us-east-2 and us-west-2. — [SpareCores g6e.4xlarge](https://sparecores.com/server/aws/g6e.4xlarge)
  - Spot by region: eu-north-1 $0.964, eu-central-1 $1.035, ap-south-2 $1.286, us-east-2 $1.512, me-central-1 $1.509, ap-northeast-2 $1.783, us-east-1 $2.416, us-west-2 $2.564.
- Vantage agrees for us-east-1: g6e.4xlarge on-demand $3.004 and Spot $2.417, page updated 10/18/2026. — [Vantage g6e.4xlarge](https://instances.vantage.sh/aws/ec2/g6e.4xlarge)
- `g6e.xlarge` (4 vCPU, 32 GiB, too few vCPUs for this workload): on-demand $1.861, Spot $1.747. — [Vantage g6e.xlarge](https://instances.vantage.sh/aws/ec2/g6e.xlarge)
- `g7e.4xlarge`: 16 vCPU, 128 GiB, 1x RTX PRO 6000 Blackwell 96 GiB, 1,900 GB NVMe. On-demand is $3.9982 in US regions. — [SpareCores g7e.4xlarge](https://sparecores.com/server/aws/g7e.4xlarge)
  - Spot by region: us-east-1 $1.544, eu-south-2 $1.866, eu-west-2 $2.403, us-east-2 $3.373, us-west-2 $3.764.
  - Other g7e sizes: 2xlarge (8 vCPU / 64 GiB, 1 GPU), 8xlarge (32 vCPU / 256 GiB, 1 GPU), 12xlarge (2 GPUs), up to 48xlarge (8 GPUs).
- `g7e.2xlarge` (8 vCPU, fails the >=16 vCPU requirement): on-demand $3.363 in us-east-1, us-east-2 and us-west-2 (search snippet). The G7e family launched in January 2026. — [Devzero g7e.2xlarge](https://www.devzero.io/instances/aws/g7e.2xlarge), [Vantage g7e.2xlarge](https://instances.vantage.sh/aws/ec2/g7e.2xlarge)
- `p5.4xlarge`: 16 vCPU, 256 GiB, 1x H100 80 GB, 3,800 GB NVMe. On-demand $6.88 in us-east-1, us-east-2 and us-west-2. — [SpareCores p5.4xlarge](https://sparecores.com/server/aws/p5.4xlarge)
  - Spot by region: ap-southeast-2 $3.02, eu-north-1 $3.31, us-west-2 $3.73, us-east-1 $4.41.
- EBS uses an example region rate: gp3 $0.08/GB-month (3,000 IOPS and 125 MB/s included; extra IOPS $0.005/IOPS-month; extra throughput $0.06/MBps-month), gp2 $0.10, st1 $0.045, snapshots $0.05/GB-month. — [AWS EBS pricing](https://aws.amazon.com/ebs/pricing/)
- Quotas:
  - Spot and on-demand G-family quotas are separate vCPU quotas ("All G and VT Spot Instance Requests" and "Running On-Demand G and VT instances"). They are set per account per region.
  - New or low-usage accounts commonly see an applied value of 0 and "might face more scrutiny" on increase requests (re:Post community answers).
  - Sources: [AWS Spot limits doc](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-limits.html), [re:Post: g4dn vCPU limit of 0](https://www.repost.aws/questions/QUdeFs2VrcQ0W5VDZuq51p6A/create-g4dn-xlarge-failed-with-8-applied-quota-value-vcpu-limit-of-0)

**Azure (official Retail Prices API, Linux, retrieved 2026-10-18; spot rows show their `effectiveStartDate`)** — [Azure Retail Prices API](https://prices.azure.com/api/retail/prices)

| SKU | GPU | Spot $/h (eastus) | On-demand $/h (eastus) | Other regions |
|---|---|---|---|---|
| Standard_NC24ads_A100_v4 | 1x A100 80 GB | 0.67877 (eff. 2026-07-01) | 3.673 | eastus2/westus2/westus3 same spot; westeurope 0.882 / 4.775; swedencentral 0.937 / 4.775 |
| Standard_NC144lds_xl_RTXPRO6000BSE_v6 | 1x RTX PRO 6000 (per third-party listing) | 1.0164 (eff. 2026-08-01) | 5.50 | westeurope 1.4535 / 7.865; northeurope and swedencentral 1.3213 / 7.15 |
| Standard_NC144ds_xl_RTXPRO6000BSE_v6 | 1x RTX PRO 6000, more RAM | 1.179 | 6.38 | |
| Standard_NC72lds_xl_RTXPRO6000BSE_v6 | 0.5x RTX PRO 6000, 48 GB (per third-party listing) | 0.4509 | 2.44 | |
| Standard_NC72ds_xl_RTXPRO6000BSE_v6 | 0.5x RTX PRO 6000 | 0.523 | 2.83 | |
| Standard_NC40ads_H100_v5 | 1x H100 | 1.2899 (eff. 2026-08-01) | 6.98 | eastus2/westus2 spot 3.216 (eff. 2026-10-01), so H100 spot varies a lot |

- SpareCores agrees on NC24ads_A100_v4: 24 vCPU, 220 GiB, 1x A100 80 GB, 960 GB NVMe, Spot $0.6788 / on-demand $3.673 in eastus. — [SpareCores NC24ads_A100_v4](https://sparecores.com/server/azure/Standard_NC24ads_A100_v4)
- RTX PRO 6000 size mapping (third-party, not confirmed by Microsoft docs; the Learn page URL returned 404). Northflank lists:
  - NC36lds_xl = 0.25 GPU
  - NC72lds_xl = 0.5 GPU / 48 GB
  - NC144lds_xl = 1 GPU / 96 GB
  - NC288lds_xl = 2 GPUs
  - For NC24lds_xl, Northflank and cloudprice.net conflict.
  - Sources: [Northflank NC144lds](https://northflank.com/cloud/azure/instances/Standard_NC144lds_xl_RTXPRO6000BSE_v6), [Northflank NC72lds](https://northflank.com/cloud/azure/instances/Standard_NC72lds_xl_RTXPRO6000BSE_v6)
- AzureSpeed sizes: NC72lds_xl is 72 vCPU / 132 GB and NC144lds_xl is 144 vCPU / 264 GB. — [AzureSpeed NCRTXPRO6000BSEv6](https://www.azurespeed.com/AzureVmPricing/Series/NCRTXPRO6000BSEv6)
- A third-party comparison says Azure lists this series as "public preview". — [Thunder Compute RTX PRO 6000 pricing](https://www.thundercompute.com/blog/nvidia-rtx-pro-6000-pricing)
- Azure quota (Microsoft Q&A, 2022-2025):
  - "the initial quota for the N series VMs for all subscriptions is set to 0".
  - "Free subscriptions including Azure Free Account and Azure for Students aren't eligible for limit or quota increases".
  - After upgrading to Pay-As-You-Go, a separate GPU quota request may still be needed.
  - Sources: [MS Q&A: unable to deploy a GPU](https://learn.microsoft.com/en-us/answers/questions/693791/why-am-i-unable-to-deploy-not-even-a-single-gpu-in), [MS Q&A: student GPU quota](https://learn.microsoft.com/en-us/answers/questions/2141487/request-for-gpu-enabled-vm-quota-increase-for-azur), [MS Q&A: GPU after upgrading student](https://learn.microsoft.com/en-us/answers/questions/2157302/clarification-on-gpu-access-after-upgrading-azure)

### Inferences
- GPU-time cost for 150 h at today's cheapest qualifying Spot list prices (my arithmetic, before storage and preemption re-runs):

| Option | 150 h cost |
|---|---|
| Azure NC72lds_xl (half RTX PRO 6000, 48 GB) | ≈ $68 |
| Azure NC24ads_A100_v4 | ≈ $102 |
| AWS g6e.4xlarge, eu-north-1 | ≈ $145 |
| Azure NC144lds_xl (full RTX PRO 6000) | ≈ $152 |
| AWS g7e.4xlarge, us-east-1 | ≈ $232 |
| GCP g4-standard-48, us-central1 | ≈ $244 |

- Storage for 500 GB over 17 days costs about $22 on both AWS gp3 and GCP Hyperdisk Balanced.
- Caveats on the cheap options:
  - L40S reports ~45 GiB usable VRAM, which leaves little headroom over the 40.5 GB peak.
  - A100 lacks Blackwell features, but CUDA 13 still supports Ampere. That CUDA 13 support is my inference and was not verified here.
  - The 144-vCPU Azure RTX PRO 6000 size requires a 144-vCPU spot quota, which is hard to get on a new subscription. The 24-vCPU A100 size is far easier to get quota for.
- Hyperscaler on-demand prices ($3.00-6.98/h) are 2-4x the Spot prices. On-demand only makes sense for the ~1-day interactive debugging block, and even there Spot with STOP plus a persistent disk is usually tolerable.

### Gaps
- No AWS Spot interruption-frequency data (Spot Placement Score or Spot Instance Advisor) was retrieved for g6e or g7e.
- No price was retrieved for AWS p4d. It has no single-GPU size; p4d.24xlarge is 8x A100. It is not useful for 1 GPU.
- The Azure spot quota default ("Total Regional Low-priority vCPUs") for a new Pay-As-You-Go subscription was not found on an official page.
- Microsoft's official NCRTXPRO6000BSEv6 size table, its GA/preview status and its driver requirements (vGPU for fractional sizes?) were not retrieved.
- The Azure Retail API spot price is a list price with an effective date. Actual Azure spot prices can also move, and eviction rates were not retrieved.

## Q3. What is Colab's effective $ per G4-hour under each plan, and is it good value with its limits?

### Takeaway
At the user's measured ~8.9 compute units (CU) per G4-hour, Colab costs about **$0.89 per RTX PRO 6000 hour** at the standard $9.99/100 CU rate. Pro+ costs about $0.74/h if it really includes 600 CU (an older figure is 500 CU, which gives $0.89/h). That is about half the price of GCP Spot G4 and it has no preemption, but it comes with real limits:
- no persistent disk;
- runtimes of 12 h (24 h on Pro+);
- background execution only on Pro+ or Google AI Ultra;
- SSH-style remote control discouraged;
- no documented way to run ~20 jobs in parallel.

Colab now also comes bundled with Google AI plans (Pro ≈200 CU/month; Ultra adds background execution and premium GPUs).

### Cited Findings
- Standalone prices: Colab Pro $9.99/month and Pro+ $49.99/month. Article dated 2026-09-25. — [Android Headlines](https://www.androidheadlines.com/2026/09/google-ai-subscription-colab-perks-bundle.html)
- Plan table "last reviewed on October 9, 2026" — [Thunder Compute Colab alternatives](https://www.thundercompute.com/blog/colab-alternatives-for-cheap-deep-learning-in-2025):
  - Pay-as-you-go $9.99 per 100 CU.
  - Pro $9.99/month for 100 CU.
  - Pro+ $49.99/month for 600 CU, with background execution.
  - Extra units $9.99 per 100 CU.
  - Another 2026 summary notes that older articles say Pro+ includes 500 CU.
- CU burn rates measured by mccormickml.com in March 2026 ("not officially published by Google"). — [Thunder Compute](https://www.thundercompute.com/blog/colab-alternatives-for-cheap-deep-learning-in-2025), original [McCormick](http://mccormickml.com/2024/04/23/colab-gpus-features-and-pricing/)

| GPU | CU/h | Implied $/h |
|---|---|---|
| RTX PRO 6000 | ~8.71 | ~$0.87 |
| A100 80 GB | ~7.52 | ~$0.75 |
| A100 40 GB | ~5.40 | |
| L4 | ~1.71 | |
| T4 | ~1.19 | |
| H100 | not published | |

- Official Colab FAQ — [Colab FAQ](https://research.google.com/colaboratory/faq.html):
  - Free notebooks run "at most 12 hours". Paid runtimes also run up to 12 h, but "Colab Pro+ supports continuous code execution for up to 24 hours if you have sufficient compute units".
  - "Runtimes will time out if you are idle", and "Idle timeouts only apply if code execution terminates".
  - Background execution is a feature of "higher plans".
  - When units run out, paid users "revert to the free-of-charge tier policies".
  - On the free tier without a positive CU balance, "remote control such as SSH shells, remote desktops" is disallowed.
  - VMs "are deleted when idle for a while" and have a maximum lifetime.
  - Colab Pro for Education no longer accepts signups.
- Conflict: Thunder Compute's table says Pro has "no idle disconnect; up to 24h sessions", which contradicts the FAQ's 12 h for non-Pro+. — [Thunder Compute](https://www.thundercompute.com/blog/colab-alternatives-for-cheap-deep-learning-in-2025) vs [Colab FAQ](https://research.google.com/colaboratory/faq.html)
- Google AI plans include Colab, announced 2026-09-22 — [Google Developers Blog](https://developers.googleblog.com/colab-is-now-part-of-your-google-ai-plan/):
  - All Google AI subscribers get "priority access to faster accelerators and more powerful machines".
  - Google AI Ultra gets "uninterrupted background execution and Premium GPU access".
  - Benefits can be stacked, and existing Colab subscriptions are unchanged.
  - The rollout takes "the next few weeks" in Colab-supported countries.
- Compute units bundled with Google AI plans (secondary sources):
  - Google AI Pro: "about 200 Colab Compute Units (CCUs) per month". — [aipromonow](https://www.aipromonow.com/en/promos/google-ai-plan-colab-premium-benefits-sep2026)
  - Ultra: 1,000 or 2,000 CU depending on tier, attributed to Google One help pages checked 2026-10-11. — [WebSearch summary citing xenospectrum](https://xenospectrum.com/en/google-ai-colab-gemma-training/)
  - A Threads post claims 400 CU for AI Pro and lists G4, A100, L4, T4 and v6e-1 TPU as available. — [Threads](https://www.threads.com/@sung.kim.mw/post/DeSrwNlD4tK/if-you-have-google-ai-pro-then-you-can-use-compute-units-of-gp-us-per-month-on/)
- Google AI plan prices (US, secondary): Pro $19.99/month; Ultra 5x $99.99/month and Ultra 20x $199.99/month after Google I/O 2026; Plus $4.99 or $7.99 (sources conflict). — [eesel.ai](https://www.eesel.ai/blog/google-ai-ultra), [aipricing.guru](https://www.aipricing.guru/compare/google-ai-pro-vs-google-ai-ultra/)
- Paid Google AI plans "start at $4.99/month". Free-trial users get no Colab benefits until they pay. — [Android Headlines](https://www.androidheadlines.com/2026/09/google-ai-subscription-colab-perks-bundle.html)

### Inferences
Effective $ per G4-hour at 8.9 CU/h (my arithmetic):

| Plan | $/CU | $/G4-hour | G4-hours per month |
|---|---|---|---|
| Pay-as-you-go, Pro, or extra units | $0.0999 | ≈ $0.89 | Pro: 100 CU ≈ 11 h |
| Pro+ (600 CU) | $0.0833 | ≈ $0.74 | ≈ 67 h |
| Pro+ (500 CU, older figure) | $0.0999 | ≈ $0.89 | ≈ 56 h |
| Google AI Pro (~200 CU for $19.99) | ~$0.10 | ≈ $0.89, if all of the plan's value is counted as Colab | ≈ 22 h |
| Ultra 5x / 20x (assuming 1,000 / 2,000 CU) | ~$0.10 | ≈ $0.89 | ≈ 112 h / 225 h |

- For 150 G4-hours (≈1,335 CU):
  - about $133 at $0.0999/CU;
  - about $111 if bought mostly via Pro+;
  - for example, two months of Pro+ (1,200 CU, $100) plus 200 extra CU ($20) ≈ $120.
- This is cheaper than every hyperscaler full-RTX-PRO-6000 Spot option, roughly on par with Azure Spot A100, and with no preemption.
- Value depends on workflow fit:
  - **Interactive debugging day:** a good fit, and the user has already proven G4 works.
  - **20 independent 2-hour runs:** a poor fit without background execution (Pro+ or Ultra).
    - The browser tab must stay connected on Pro.
    - The disk is lost at runtime end, so checkpoints and results must sync to Drive or GCS.
    - Concurrency is undocumented, so runs are effectively sequential: 20 × 2 h = 40 h of wall-clock.
- If Pro+ really gives 600 CU and 24 h background runs, then Pro+ plus top-ups is probably the cheapest single-GPU option overall for this workload, provided runs can be serialized.

### Gaps
- There is no official Google page with the 2026 Pro+ CU allotment (500 vs 600). The Colab signup page renders in JavaScript and returned no content.
- Official CU burn rates for G4 and H100 are not published. 8.9 CU/h is the user's own measurement; 8.71 is McCormick's.
- Not found: a CU expiry rule (often quoted as 90 days), the idle-timeout length, the number of concurrent GPU runtimes allowed per plan, the Ultra background-execution cap, and whether paid users may run SSH tunnels.
- The exact CU allotments for AI Pro (200 vs 400) and Ultra (1,000 vs 2,000), and Turkish-lira prices, were not confirmed on an official page. Turkey prices on the Google One page are rendered in JavaScript.

## Q4. Which free credits can realistically be obtained within days and used for GPUs?

### Takeaway
Nothing reliably yields free >=48 GB GPU time within days for a student team in Turkey:
- **GCP $300 trial:** blocks GPUs. It becomes usable only after upgrading to a paid account and winning GPU quota. If upgraded, the credit (valid 90 days) would cover roughly 150-180 Spot G4-hours, so it is the single most valuable quick option.
- **Google AI Pro/Ultra:** subscriptions also carry Google Developer Program Cloud credits of $10/$40/$100 per month, alongside their Colab units.
- **Azure for Students:** cannot run GPU VMs.
- **NVIDIA Academic Grant:** closed and faculty-only.
- **AWS Activate, NVIDIA Inception:** need a company.
- **Lambda and Google research credits:** take weeks.
- **Kaggle, TRC:** do not meet the VRAM or CUDA needs.
- **V2D challenge:** offers GPU credits only as prizes.

### Cited Findings
- **GCP Free Trial** — [GCP Free Trial terms](https://docs.cloud.google.com/free/docs/free-cloud-features):
  - $300 credit for 90 days. Eligible only if you were never a paying Google Cloud, Maps or Firebase customer.
  - During the trial you cannot "Add GPUs to your VM instances" or "Request a quota increase".
  - After upgrading, "remaining credit stays usable" within the original 90 days, and GPUs become available.
  - "GPUs and TPUs are not included in the Free Tier offer."
- **Google AI plans' Cloud credits:** The Google One plans page (Turkey locale, read 2026-10-18) lists "Google Developer Program Premium — Google Cloud kredisi: Ayda $10 kredi / Ayda $40 kredi / Ayda $100 kredi" for successive paid tiers. The Pro tier text reads "Google Developer Program'dan her ay $10 Google Cloud kredisi". — [Google One AI plans](https://one.google.com/about/google-ai-plans/)
- **Google Cloud research credits** — [Google Cloud research credits](https://edu.google.com/intl/ALL_us/programs/credits/research), [CURC mirror FAQ](https://curc.readthedocs.io/en/latest/cloud/gcp/Google-Cloud-research-credits.html), [grantedai (secondary)](https://grantedai.com/grants/google-cloud-research-credits-faculty-phd-students-nonprofit-researchers-ai-workloads-google-2026):
  - For faculty, PhD students and postdocs at accredited institutions in approved countries.
  - Decisions in "4-6 weeks" (older FAQ mirror).
  - About $5,000 for faculty/postdocs and $1,000 for PhD students (secondary).
  - Credits expire 365 days after redemption.
- **AWS Activate Founders:** about $1,000 (+$350 Developer Support), for self-funded companies with a working website. Portfolio tiers up to $100k-200k need an Activate Provider org ID. All of this is from third-party guides. — [guptadeepak AWS Activate guide](https://guptadeepak.com/startup-offers/guides/aws-activate), [AWS Activate step-by-step (June 2026)](https://aws.amazon.com/aws-startups/learn/applying-for-aws-activate-credits-a-step-by-step-guide)
- **Azure for Students / Free Account:** GPU VMs cannot be deployed. The default student quota is ~3 vCPUs, and "Free subscriptions including Azure Free Account and Azure for Students aren't eligible for limit or quota increases". The fix is upgrading to Pay-As-You-Go. — [MS Q&A](https://learn.microsoft.com/en-us/answers/questions/2141487/request-for-gpu-enabled-vm-quota-increase-for-azur), [MS Q&A](https://learn.microsoft.com/en-us/answers/questions/693791/why-am-i-unable-to-deploy-not-even-a-single-gpu-in)
- **NVIDIA Academic Grant Program:** "currently not accepting new applications". Applicants "Must be a full-time faculty member". Awards are up to 30,000 H100 hours or up to eight RTX PRO 6000 GPUs. — [NVIDIA Academic Grant Program](https://www.nvidia.com/en-us/industries/higher-education-research/academic-grant-program/)
- **NVIDIA Inception:** "up to $100,000 in AWS GPU cloud compute credits" through partners, with no fees or equity (third-party reseller page). The project's own earlier check notes it requires an incorporated company and a business email. — [builtfirst NVIDIA cloud credits](https://oneeleven.builtfirst.com/nvidia-cloud-credits), project note `reports/v2d-challenge/track3-requirements.md` (checked 2026-10-01)
- **Lambda research grant:** "up to $5,000 in Cloud Credits", applications on a rolling basis. Announced December 2024; no 2026 official update found. — [BusinessWire, 2024-12-09](https://www.businesswire.com/news/home/20241209358457/en/Lambda-Launches-Grant-for-AI-Researchers-Expands-Research-Program)
- **Kaggle:** "dynamic GPU quota of 30 hours at minimum" per week, one P100 16 GB or 2x T4. Sessions are 12 h per most sources (page dated 2026-09-21). Too small for a >=48 GB need. — [gpuperhour free GPUs (2026-09-21)](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- **TPU Research Cloud:** accepted researchers get "access to Cloud TPUs at no charge". No GPUs are mentioned, so it is not useful for CUDA, JAX-cuda or Warp. — [TRC](https://sites.research.google/trc/about/)
- **V2D Challenge:** GPU credits appear only as prizes: Track Runner-Up "$3K GPU credits"; Industry Innovation "DGX Spark + $3K GPU credits". The leaderboard freezes "November 4, 2026, at 5:00 p.m. EST" and winners are announced 2026-11-12 at the CoRL 2026 tutorial. — [V2D Challenge page](https://nvidia-isaac.github.io/video_to_data/v2d_challenge/)
  - The project's notes record that the challenge FAQ PDF dated 2026-10-02 says GPU credits are "under review", with replies to participants who request them. — project note `reports/v2d-challenge/track3-requirements.md`, citing `docs/v2d_challenge/assets/v2d_challenge_2026_faqs.pdf`
- **AIcrowd precedent:** A different challenge offered sponsor credits (NVIDIA/AWS/OpenAI, $100 initial package) with a 2025-12-31 deadline. It is not V2D. — [AIcrowd](https://discourse.aicrowd.com/t/how-to-claim-compute-credits/17582)

### Inferences
- The fastest realistic path is to open a GCP account, upgrade it to paid immediately (the $300 credit carries over), and file Spot G4 quota requests the same day. If quota arrives within days, $300 covers about 184 h of us-central1 Spot G4 at $1.63, minus disk costs. That would cover the whole 100-150 GPU-hour budget.
  - Caveat: whether trial credit applies to Spot GPU usage after upgrade is not stated beyond "products covered by the Free Trial". Verify on the billing page after the first hour.
- Emailing the V2D organizers to ask for the "under review" GPU credits costs nothing. It is still pending per the 2026-10-02 FAQ.
- A Google AI Pro subscription ($19.99) gives ~200 Colab CU (~22 G4-h) plus $10/month of Cloud credit. That is marginally better value than Colab Pro alone if the Cloud credit can be used.
- Lambda and Google research credits (weeks to decide) and Activate or Inception (company needed) are unlikely to arrive before 2026-11-04.

### Gaps
- Whether Google Developer Program Premium Cloud credits (from Google AI plans) can pay for Compute Engine GPUs, and which tier maps to $40 vs $100, was not confirmed.
- Not verified: whether GCP Free Trial credit, after upgrade, covers Spot GPU and G4 usage.
- Not found: Hugging Face programs (community GPU grants are for Spaces/ZeroGPU, not SSH VMs), any CoRL 2026 compute-credit program, and the Azure Free Account ($200) terms for 2026.
- Not found on an official 2026 page: AWS Activate Founders eligibility for individuals or students in Turkey, the AWS Cloud Credit for Research program, and NVIDIA Inception credit terms.
- Not determined: Google Cloud research-credit country eligibility for Turkey, and whether undergraduates qualify.
