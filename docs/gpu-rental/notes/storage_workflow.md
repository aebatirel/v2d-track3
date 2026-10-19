# Storage and pay-only-when-used workflow for a short GPU project (Oct 18 to Nov 4, 2026)

All pages below were read on 2026-10-18 unless another date is given. The project window from today to 2026-11-04 is 17 days (408 h, about 0.56 of a 730 h month). "3 weeks" is 504 h (0.69 month). The cost math below is mine. It assumes hourly proration unless a source says otherwise.

Note on sizing: the itemized needs add up to about 150 GB, not 500 GB. That is 70 GB depth caches, 15 GB environments, 10 GB weights, 2 GB dataset, plus checkpoints of about 0.17 GB × ~5 per run × 20-60 runs ≈ 17-51 GB. Totals are therefore given for both 500 GB and a right-sized 150-200 GB.

## Q1. What is the cheapest way to keep ~500 GB available across GPU sessions for 3 weeks, and what does it cost?

### Takeaway
Among GPU-attached options with documented prices, a RunPod standard network volume is the cheapest persistent store: $0.07/GB-month, about $19.60 for 500 GB over 17 days, or about $7.80 for a right-sized 200 GB. It survives pod termination, but it is locked to one Secure Cloud datacenter. GCP pd-standard is cheaper per GB ($0.04/GiB-month, about $11 for 500 GiB over 17 days), but GCP GPU and egress costs apply on top. Never leave data on a stopped RunPod volume disk ($0.20/GB-month idle) or a stopped Vast.ai instance: both cost more while idle, and the GPU may not come back.

### Cited Findings

**RunPod**
- RunPod's storage types are priced as follows ([RunPod pricing](https://www.runpod.io/pricing), [RunPod storage types](https://docs.runpod.io/pods/storage/types)):

  | Type | Price | Persistence |
  |---|---|---|
  | Container disk | $0.10/GB-mo | "Lost on stop or restart" |
  | Volume disk | $0.10/GB-mo running, $0.20/GB-mo stopped | Survives stop/restart; deleted when the pod is terminated |
  | Network volume, standard | $0.07/GB-mo under 1 TB, $0.05/GB-mo over 1 TB | Retained independently of any pod |
  | Network volume, high-performance | $0.14/GB-mo | — |
  | Global volume (beta) | $0.09/GB-mo plus an IOPS charge whose rate is not published | Retained when the pod is stopped or deleted; usable from any datacenter; one global plus one network volume per pod; "Features may change before general availability" |
- Network volume behavior ([RunPod network volumes](https://docs.runpod.io/storage/network-volumes)):
  - Data survives termination: "Data is retained when Pods terminate or Serverless workers scale to zero."
  - Pod use is Secure Cloud only. The volume must be attached at deployment and "cannot be attached or detached later without deleting the Pod."
  - Size can be increased but not decreased. Volumes over 4 TB require contacting support.
  - Datacenter lock-in: one volume restricts deployments to its datacenter, which "can reduce GPU availability". Data does not sync between volumes in different datacenters.
- At a $0 balance, pods are stopped and the data is kept, but storage charges continue. If the balance stays unpaid, "the volume may eventually be terminated" and the data cannot be recovered ([RunPod network volumes](https://docs.runpod.io/storage/network-volumes)).
- Stopping a pod "releases the GPU and preserves data in `/workspace`". On restart, "You may be allocated zero GPUs if capacity has changed." With a network volume, `/workspace` "is preserved whether you stop or terminate the Pod". Terminating "permanently deletes all data not stored in a network volume" ([RunPod manage pods](https://docs.runpod.io/pods/manage-pods)).
- RunPod states it is "not designed for long-term cloud storage" and recommends backing up critical data elsewhere ([RunPod storage types](https://docs.runpod.io/pods/storage/types)).
- An S3-compatible API for network volumes is available in 15 datacenters: EU-CZ-1, EU-RO-1, EUR-IS-1, EUR-NO-1, US-CA-2, US-GA-2, US-IL-1, US-KS-2, US-MD-1, US-MO-1, US-MO-2, US-NC-1, US-NC-2, US-NE-1 and US-WA-1 ([RunPod S3 API](https://docs.runpod.io/storage/s3-api)).
  - It needs a separate S3 API key, whose secret is shown only once.
  - "Using the S3-compatible API does not affect pricing."
  - Files over 500 MB need multipart upload. DeleteObjects and pre-signed URLs are not supported, and `aws s3 sync` may fail on directories with more than 10,000 files.

**Vast.ai**
- Storage is "Billed continuously while your instance exists, regardless of running state." Storage costs "vary by host" and are "typically higher for stopped instances than running instances." Bandwidth "costs vary by host" and are charged "per byte transferred" ([Vast.ai pricing](https://docs.vast.ai/documentation/instances/pricing)).
- "To stop storage billing, you must destroy the instance completely." Volumes are charged independently, persist after the instance is destroyed, and are tied to one physical machine that cannot be changed ([Vast.ai storage types](https://docs.vast.ai/documentation/instances/storage/types)).
- An Inactive instance is "Stopped but data preserved (can restart if GPU available)". A restart "May wait indefinitely for GPU availability". "If stuck >30 seconds, GPU likely rented by another user." The docs advise copying data to a new instance or syncing to cloud storage before destroying an instance ([Vast.ai manage instances](https://docs.vast.ai/documentation/instances/manage-instances)).
- At zero balance, instances are stopped and the GPU is released. Without a saved payment method, "your instances and data will be scheduled for deletion" ([Vast.ai pricing](https://docs.vast.ai/documentation/instances/pricing)).

**Lambda**
- Filesystems are "billed per GiB used per month in one-hour increments", with "no minimum storage period". Billing continues while the filesystem exists, even when unmounted. Lambda does not charge for ingress or egress ([Lambda billing](https://docs.lambda.ai/public-cloud/billing/)).
- The only rate shown is an illustrative $0.20/GiB-month that "might not reflect current pricing". The pricing page lists no filesystem rate ([Lambda pricing](https://lambda.ai/pricing)).
- A filesystem must be in the instance's region and attached at launch, and it "cannot currently be transferred between regions". Texas (us-south-1) is capped at 10 TB ([Lambda filesystems](https://docs.lambda.ai/public-cloud/filesystems/)).
- The docs describe only termination for On-Demand instances, not stopping: "Instances are billed for as long as they're running" ([Lambda billing](https://docs.lambda.ai/public-cloud/billing/)).

**GCP**

Prices are per GiB-hour as rendered on the page, using the server default region, which appears to be Iowa (us-central1). The monthly figure is mine, at 730 h ([GCP disk pricing](https://cloud.google.com/compute/disks-image-pricing)):

| Item | $/GiB-hr | ≈ $/GiB-mo | 500 GiB × 17 days |
|---|---|---|---|
| pd-standard | 0.000054795 (first 30 GiB-month free per account) | 0.04 | ~$11.20 |
| pd-balanced | 0.000136986 | 0.10 | ~$27.90 |
| pd-ssd | 0.000232877 | 0.17 | ~$47.50 |
| Hyperdisk Balanced (capacity) | 0.000109589 | 0.08 | ~$22.40 |
| Hyperdisk Throughput (capacity) | 0.000006849 | 0.005, plus $0.000342466/hr per MBps of throughput | — |
| Standard snapshot | 0.000068493 | 0.05 | — |
| Archive snapshot | 0.000026027 | 0.019 | — |

- Hyperdisk Balanced charges extra IOPS at $0.000006849/hr and extra throughput at $0.000054795/hr only "in excess of the baseline values of 3,000 IOPS and 140 MBps" ([GCP disk pricing](https://cloud.google.com/compute/disks-image-pricing)).
- Archive snapshots have a 90-day minimum plus $0.019/GiB retrieval. Standard snapshots have a 1-hour minimum ([GCP disk pricing](https://cloud.google.com/compute/disks-image-pricing)).
- Charges are prorated to the second, and "After you successfully delete a persistent disk, you are no longer charged for that disk." In other words, a stopped VM's disks keep billing ([GCP disk pricing](https://cloud.google.com/compute/disks-image-pricing)).

### Inferences

**Cost for the 17-day window (my math)**

| Option | 500 GB | 200 GB | 150 GB |
|---|---|---|---|
| RunPod network volume, standard | 500 × $0.07 × 0.559 ≈ **$19.60** (3 weeks ≈ $24.20) | ≈ **$7.80** | ≈ $5.90 |
| RunPod high-performance volume | ≈ $39.10 | — | — |
| RunPod volume disk, stopped 80% of the time | 0.559 × (0.2 × $50 + 0.8 × $100) ≈ **$50** | — | — |
| GCP pd-standard | ≈ $11 (about $10 after the 30 GiB-month free tier) | ≈ $4.50 | — |
| GCP pd-balanced | ≈ $28 | — | — |
| GCP Hyperdisk Balanced | ≈ $22 | — | — |
| Lambda filesystem (if $0.20/GiB-mo is current) | — | — | ≈ $16.80, billed on used space |

- **RunPod volume disk:** keeping 500 GB on a mostly stopped volume disk is about 2.5× the cost of a network volume, and the GPU may not be available on restart. It is the worst RunPod option for this project.
- **GCP:** pd-standard is the cheapest per GB of anything here. However, a GCP GPU VM needs its own quota, GPU pricing and $0.12/GiB Premium egress (see Q3), so it pays off only if the GPUs are rented on GCP too.
- **Right-sizing is the largest saving.** RunPod volumes can grow but not shrink, so start at about 200 GB and grow if needed. This saves about $12 compared with 500 GB.
- **Hidden cost of a RunPod network volume:** it forces Secure Cloud and a single datacenter. If the required GPU is scarce or more expensive in that datacenter, the GPU premium can outweigh the $8-20 storage cost.
- **RunPod global volume (beta, $0.09/GB plus IOPS):** it would remove the datacenter lock-in, but the IOPS rate is unpublished and the feature is beta. Treat its total cost as unknown.
- **Vast.ai:** there is no single storage price to compare. Keeping data on a stopped Vast instance is risky because the restart "may wait indefinitely". Treat Vast storage as ephemeral and keep anything durable in object storage.

### Gaps
- Vast.ai per-GB storage prices are set per host and not published in the docs, so no number is given. The docs do not say whether a stopped instance can be reclaimed by the host. They only say restarts can wait indefinitely.
- Lambda's current filesystem price was not shown on any page I could read; only the illustrative $0.20/GiB-month is documented.
- The RunPod global volume IOPS rate and the network volume billing granularity (hourly or daily) were not found.
- The GCP region default is inferred from the page layout. Hyperdisk Throughput's minimum size and throughput, and which GPU machine series support Hyperdisk, were not verified.
- The RunPod high-performance tier is listed at $0.14/GB-month on the pricing page, but its availability by datacenter was not checked.

## Q2. Is it cheaper to keep a network volume or to re-download and rebuild each session? (pay-only-when-used workflows)

### Takeaway
Storage is cheap compared with GPU time. A right-sized 150-200 GB RunPod network volume costs about $0.35-0.46 per day. Rebuilding from object storage only wins if restores take a few minutes of GPU time per session and the depth caches do not need GPU regeneration. Recommended hybrid: keep regenerable bulk (environments, weights, dataset, caches) on a right-sized network volume, or in R2 as archives. Push the small important artifacts off-GPU to two durable stores after every run. Terminate pods instead of stopping them.

### Cited Findings
- **Terminate vs stop on RunPod:** terminate releases everything except the network volume, while a stopped pod keeps billing its volume disk at $0.20/GB-month and may get "zero GPUs" on restart. CLI: `runpodctl pod stop|start|delete POD_ID` ([RunPod manage pods](https://docs.runpod.io/pods/manage-pods), [RunPod pricing](https://www.runpod.io/pricing)).
- **RunPod S3 API:** it lets you read and write files on a network volume without launching compute ([RunPod network volumes](https://docs.runpod.io/storage/network-volumes)). This lets you pre-stage inputs and pull results home with no GPU running, in the 15 supported datacenters ([RunPod S3 API](https://docs.runpod.io/storage/s3-api)).
- **Vast.ai:** stopped instances keep billing storage. The only way to stop storage billing is to destroy the instance, and the docs recommend syncing to cloud storage first. The "Cloud Sync" feature supports Google Drive, S3 and similar targets ([Vast.ai storage types](https://docs.vast.ai/documentation/instances/storage/types), [Vast.ai manage instances](https://docs.vast.ai/documentation/instances/manage-instances)).
- **Lambda:** instances can only be terminated, not stopped. A filesystem attached at launch is the persistence mechanism, billed on used space, with no ingress or egress fees ([Lambda billing](https://docs.lambda.ai/public-cloud/billing/), [Lambda filesystems](https://docs.lambda.ai/public-cloud/filesystems/)).
- **uv cache placement:** the cache directory is set by `--cache-dir`, `UV_CACHE_DIR` or `tool.uv.cache-dir`. Keeping the cache on the same filesystem as the environment is "important for performance"; otherwise uv falls back to "slow copy operations". `uv cache prune --ci` removes pre-built wheels but keeps wheels built from source, and is recommended at the end of CI jobs ([uv cache docs](https://docs.astral.sh/uv/concepts/cache/)).
- **Useful uv environment variables:** `UV_LINK_MODE` (link mode), `UV_PYTHON_INSTALL_DIR` (where managed Pythons are stored), `UV_PROJECT_ENVIRONMENT` (venv path), `UV_COMPILE_BYTECODE` and `UV_FROZEN` ("run without updating the uv.lock file") ([uv environment variables](https://docs.astral.sh/uv/reference/environment/)).
- **Hugging Face Storage Buckets:** non-versioned, mutable, S3-like object storage with `hf buckets sync` (rsync-like, optional `--delete`) and Xet chunk-level dedup. The docs suggest them for "Training checkpoints and logs" and "Rolling backups"; successive checkpoints with frozen parts upload only the changed chunks ([HF Storage Buckets](https://huggingface.co/docs/hub/storage-buckets)).
- **Network volume restore limits on RunPod:** `aws s3 sync` may fail on directories with more than 10,000 files, and uploads above 500 MB need multipart ([RunPod S3 API](https://docs.runpod.io/storage/s3-api)).

### Inferences

**Break-even model (my math, hypothesis-level)**
- Daily network volume cost is size × $0.07 / 30.4: about **$1.15/day** for 500 GB, **$0.46/day** for 200 GB, **$0.35/day** for 150 GB.
- Rebuild cost per session is restore minutes / 60 × GPU $/hr, plus R2 storage of about $0.04/day for ~97 GB of archives (Q3).
  - Example: a 10-minute restore of ~27 GB (environment, weights, dataset) on a $1/hr GPU costs about $0.17 per session.
  - Restoring the 70 GB depth caches as well might take 15-20 minutes, about $0.30.
  - If the caches must be regenerated on GPU instead of downloaded, the cost is that regeneration time × GPU rate, likely the dominant term.
- At 1-2 sessions per day:
  - Rebuild from R2: about $0.20-0.60/day.
  - 500 GB volume: $1.15/day.
  - Right-sized 150-200 GB volume: $0.35-0.46/day.
- So a right-sized network volume roughly matches rebuild-from-R2 cost. It also removes restore failure risk and wasted GPU minutes, and lets data be staged with no GPU via the S3 API. An oversized 500 GB volume does not pay for itself.
- Restore throughput from R2 or B2 to a pod is not measured here. Measure it once on the first pod with `rclone copy --transfers 16`, then plug it into the formula above.

**Suggested pay-only-when-used pattern (proposed, not tested)**
1. Create one RunPod standard network volume of about 200 GB in a datacenter that both has the target GPU and supports the S3 API. Launch pods with it at `/workspace`, and terminate them (do not stop them) when work ends.
2. Keep `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR` and the project venv (`UV_PROJECT_ENVIRONMENT`) all on `/workspace`, so hardlinks work and `uv sync --frozen` is near-instant on later sessions.
   - Hypothesis: if a network filesystem makes venv imports slow because of many small files, keep the uv cache on the volume, rebuild the venv on the local container disk at startup with `UV_LINK_MODE=copy`, or keep a tarball of the venv on the volume and extract it locally. Measure import time both ways.
3. Keep model weights, the dataset and depth caches on the volume. Also keep a tar or zstd archive of the depth caches plus weights in R2, so a pod in a different datacenter or on a different provider can be bootstrapped without the volume.
4. Write checkpoints to `/workspace/runs/<run>/`. After each run, push the policy (~5 MB), configs, results and logs to two off-GPU stores (Q3), plus your home machine. Prune intermediate 0.17 GB checkpoints once a run's final policy is saved.
5. Use a startup script that does the following:
   - Install or locate rclone and uv.
   - Pull secrets from the pod environment variables, not from files on the volume.
   - Run `uv sync --frozen`.
   - Run `rclone copy r2:bucket/caches /workspace/caches` only if the caches are missing.
   - Write a heartbeat file.
   - Optionally self-terminate when idle, for example by calling `runpodctl pod delete $RUNPOD_POD_ID` at the end of a job script. That last step is a hypothesis: verify that the CLI is available inside the pod.
6. Set low-balance alerts. At $0 balance RunPod volumes can eventually be deleted, and Vast data is scheduled for deletion without a card on file.

**Other workflow notes**
- **On Vast.ai,** treat each instance as disposable. Restore from R2 or B2 at start, and sync results out at the end, using Vast Cloud Sync or rclone. Then destroy the instance. Stopping keeps billing at a higher stopped rate and the restart is not guaranteed.
- **On Lambda,** a filesystem billed on used space removes the over-provisioning penalty. But Lambda has no stop: every session is a fresh launch with the filesystem re-attached, and only in the same region.

### Gaps
- No primary source measured RunPod network volume throughput for many small files, such as Python venvs. The "slow venv on network volume" concern is a hypothesis to test.
- Pod-to-R2 and pod-to-B2 download throughput is unknown for the chosen datacenter.
- No documentation was found on whether `runpodctl` is preinstalled in pods or on how pods self-terminate. Treat both as unverified.
- The cost to regenerate the depth caches on GPU is project-specific and unknown here.

## Q3. Which backup service is cheapest for a few GB to ~100 GB with occasional downloads, including egress?

### Takeaway
For the few-GB "keep safely" set, several services are free: Backblaze B2 (first 10 GB), Cloudflare R2 (10 GB-month), Hugging Face (100 GB private on a free account) and Google Drive (15 GB). Use two of them plus the home machine. For about 100 GB:
- B2 is cheapest for storage, at about $0.63/month, with free egress up to 3× the data stored.
- R2 is best when restores are frequent: about $1.35/month, and egress is always free.
- AWS S3 costs about $2.30/month plus $0.09/GB egress beyond the free tier.
- Wasabi is a poor fit for 3 weeks because of its 1 TB monthly minimum and 90-day minimum retention.

### Cited Findings

**Backblaze B2** ([Backblaze pricing](https://www.backblaze.com/cloud-storage/pricing); the page shows no effective date)
- Storage is $6.95/TB-month (about $0.00695/GB), and the "First 10GB storage is always free."
- Egress is free up to 3× average monthly storage, then $0.01/GB.
- There are no minimum storage duration fees and no minimum file size fees.
- Class A, B and C API calls are free. Class D costs $0.004 per 10,000 calls after 2,500 free per day.
- rclone has a native `b2` backend (Tier 1, sha1 hashes) ([rclone overview](https://rclone.org/overview/)).

**Cloudflare R2** ([R2 pricing](https://developers.cloudflare.com/r2/pricing/))
- Standard storage is $0.015/GB-month. Infrequent Access is $0.01/GB-month, plus $0.01/GB retrieval and a 30-day minimum.
- Class A operations cost $4.50 per million (IA: $9.00). Class B operations cost $0.36 per million (IA: $0.90).
- Egress is free.
- The monthly free tier is 10 GB-month, 1M Class A operations and 10M Class B operations, for Standard storage only.
- Getting started requires completing a checkout flow to add an R2 subscription ([R2 get started](https://developers.cloudflare.com/r2/get-started/)).
- rclone lists Cloudflare R2 as an `s3` provider, with region `auto` ([rclone S3](https://rclone.org/s3/)).

**Wasabi** ([Wasabi pricing](https://wasabi.com/pricing), [Wasabi pricing FAQ](https://wasabi.com/pricing/faq))
- Pay as You Go costs $7.99/TB-month, with "No charge for egress or API requests".
- There is a minimum monthly charge of 1 TB of active storage.
- There is a 90-day minimum storage duration: data deleted early incurs "a Timed Deleted Storage charge equal to the storage charge for the remaining days".
- Free egress applies only "If your monthly egress data transfer is less than or equal to your active storage volume."
- rclone lists Wasabi as an `s3` provider ([rclone S3](https://rclone.org/s3/)).

**AWS S3, us-east-1** ([AWS S3 price list JSON](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-1/index.json), published 2026-10-15)
- S3 Standard costs $0.023/GB for the first 50 TB.
- Standard-IA is $0.0125, One Zone-IA $0.01, and Glacier Instant Retrieval $0.004 per GB-month.
- PUT, COPY, POST and LIST cost $0.005 per 1,000 requests. GET costs $0.0004 per 1,000.
- The IA classes have a 30-day minimum, and Glacier Instant Retrieval a 90-day minimum ([AWS S3 pricing page](https://aws.amazon.com/s3/pricing/)).
- Internet egress is $0.09/GB for the first 10 TB beyond the global free tier ([AWS data transfer price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSDataTransfer/current/us-east-1/index.json), published 2026-09-16). The first 100 GB per month out to the internet is free ([AWS S3 pricing page](https://aws.amazon.com/s3/pricing/)).
- rclone `s3` is Tier 1 with md5 hashes ([rclone overview](https://rclone.org/overview/)).

**Hugging Face Hub** ([HF storage limits](https://huggingface.co/docs/hub/storage-limits), [HF pricing](https://huggingface.co/pricing), [HF storage](https://huggingface.co/storage))
- Private storage is 100 GB on a free account and 1 TB on PRO, plus pay-as-you-go above that. Extra private storage costs $18/TB-month at the base tier. PRO costs $9/month.
- "Egress and CDN included at no extra cost." Bucket egress is included up to an "8:1 ratio of your total storage."
- Bucket pricing matches repository pricing: $18/TB-month private and $12/TB-month public at the base tier.
- In Git-backed repos, deleted large files remain in history and still count toward quota unless the history is super-squashed. Buckets are non-versioned, so deleted data stops counting ([HF storage limits](https://huggingface.co/docs/hub/storage-limits), [HF Storage Buckets](https://huggingface.co/docs/hub/storage-buckets)).
- Repo limits: under 100k files recommended, at most 10k per folder, a 500 GB hard limit per file, and files under 200 GB recommended ([HF storage limits](https://huggingface.co/docs/hub/storage-limits)).
- Tools: the `hf` CLI and Python API, and buckets also offer an S3-compatible API usable with the AWS CLI, boto3 and s5cmd ([HF Storage Buckets](https://huggingface.co/docs/hub/storage-buckets)).
- Hugging Face does not appear in rclone's backend overview ([rclone overview](https://rclone.org/overview/)).

**Google Drive via rclone** ([rclone Drive](https://rclone.org/drive/))
- rclone's shared client_id "is being retired and will stop working during 2026", so you now must create your own OAuth client_id.
- There is an undocumented upload limit of 750 GiB per day.
- Rate limiting holds rclone to "about 2 files per second", which makes many small files slow.
- Headless machines need the manual or remote setup flow, or a service account.

**Google Drive plans**
- Every account gets "up to 15 GB" free ([Google One plans](https://one.google.com/about/plans)).
- The plans page as served to this user (Turkey) lists 100 GB at TRY 84.99/month and 2 TB at TRY 359.99/month ([Google One plans](https://one.google.com/about/plans)).
- A US App Store snapshot from May 2026 lists 100 GB at $1.99/month and 2 TB at $9.99/month. This is a third-party source and not verified on a Google page ([App Pricing Lab](https://apppricinglab.com/iap/apple/1451784328)).

**Egress when copying results home from the GPU cloud**
- **Lambda:** "not charged for ingress or egress" ([Lambda billing](https://docs.lambda.ai/public-cloud/billing/)).
- **RunPod:** its pricing page lists no egress fees ([RunPod pricing](https://www.runpod.io/pricing)). RunPod marketing claims no ingress or egress fees for common workflows ([RunPod Lambda alternative](https://www.runpod.io/lambda-alternative), seen via search summary only, not fetched).
- **Vast.ai:** bandwidth is charged per byte at host-set rates ([Vast.ai pricing](https://docs.vast.ai/documentation/instances/pricing)).
- **GCP:** Premium Tier internet egress to worldwide destinations costs $0.12/GiB for 0-1 TiB and $0.11/GiB for 1-10 TiB. Standard Tier is free for the first 200 GiB per month per account, then $0.085/GiB ([GCP network pricing](https://cloud.google.com/vpc/network-pricing)).

### Inferences

**Approximate cost per month (my math)**

| Service | ~5 GB important set | 100 GB | Egress for occasional downloads |
|---|---|---|---|
| B2 | $0 | (100 − 10) × $0.00695 ≈ **$0.63** | Free up to ~300 GB/month for 100 GB stored, then $0.01/GB |
| R2 Standard | $0 | (100 − 10) × $0.015 ≈ **$1.35** | Always free; operations negligible at this scale |
| HF | $0 (free account) | $0 on a free account; 100 GB is exactly the free cap, so tight | Included |
| Google Drive | $0 | Requires the 100 GB plan ($1.99/month US or TRY 84.99/month); the 15 GB free tier is too small | — |
| S3 Standard | — | **$2.30** | Free within 100 GB/month, then $0.09/GB |
| Wasabi | — | Effectively ≥ $7.99/month for 1 TB, and a 90-day minimum means about $24 for a 3-week project | — |

- **Recommended split:**
  - Small, important set (policies, references, results, logs: a few GB): push to B2 and to HF (private repo or bucket), both free, plus the home machine. Use HF Git repos for final versioned policies and references, and a B2 or HF bucket for rolling logs. Two providers protects against one account problem.
  - About 100 GB of regenerable bulk archives for bootstrapping pods: R2 Standard, at about $0.80 for the 17 days. It is the only option with no egress ceiling, which matters if pods are restored many times.
  - If restores are rare (3 or fewer full downloads per month), B2 is cheaper still.
- **Copying results home** costs effectively nothing for a few GB from RunPod or Lambda. From GCP, Standard Tier is free under 200 GiB/month, while Premium Tier costs about $0.12/GiB.

**API keys and credentials needed**
- **B2:** an application key (keyID plus applicationKey), for rclone `b2` or the S3-compatible API.
- **R2:** an R2 API token, which yields an S3 Access Key ID and Secret, plus the account's S3 endpoint.
- **Wasabi:** an access key and secret key.
- **S3:** an IAM access key.
- **HF:** a write-scoped access token.
- **Google Drive:** your own OAuth client ID and secret plus an OAuth token, or a service account.
- **RunPod network volume S3 access:** a separate RunPod S3 API key.
- On pods, inject all of these as environment variables or provider secrets, never as files on shared volumes.
- The R2 token-to-S3-key flow, the endpoint format and the B2 key types above come from general knowledge. The R2 and B2 pages fetched did not document them, so verify them during setup.

### Gaps
- No Wasabi free-trial terms were found; the FAQ and pricing pages did not state them.
- The current US Google One prices were not confirmed on a Google page; only a third-party App Store snapshot was found.
- Backblaze's page shows no effective date. Its "© 2024" footer is a copyright notice, not a price date.
- No rclone backend for Hugging Face was confirmed. The HF bucket S3-compatible API might work with rclone's generic `s3` provider; this was not tested.
- Whether the R2 checkout requires a payment card even for free-tier use was not stated on the fetched page.
- RunPod's no-egress claim comes from marketing pages via a search summary, not from a fetched pricing or terms page.
