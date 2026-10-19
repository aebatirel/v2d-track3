# GPU marketplaces and community clouds: RunPod, Vast.ai, TensorDock, Lium, Salad, Shadeform (as of 2026-10-18)

Scope and method notes, for the report writer:
- Researched on 2026-10-18. Live prices come from public, unauthenticated JSON endpoints, captured between about 15:27 and 15:45 UTC that day:
  - Vast.ai offer search: `https://console.vast.ai/api/v0/bundles/`
  - Shadeform instance types: `https://api.shadeform.ai/v1/instances/types`
  - Lium executors: `https://lium.io/api/executors`
  - RunPod GraphQL `gpuTypes`: `https://api.runpod.io/graphql`
- Marketplace prices (Vast, Lium, Shadeform availability) change minute to minute. Treat them as a snapshot, not quotes.
- "Meets our spec" means all of the following: driver >= 580 (CUDA 13), >= 16 vCPU, >= 64 GB RAM, >= 500 GB disk available, and Vast host reliability >= 0.97.
- Vast `dph_total` includes only a default ~8 GB disk. I added 500 GB at each host's own storage rate separately.
- Terminology used below:
  - RTX PRO 6000 "WS" = Workstation Edition.
  - "S" or "Server" = Server Edition.
  - "Max-Q" = Max-Q Workstation Edition.
  - All three variants have 96 GB.

---

## Q1. What is the cheapest reliable hourly price for a >=48 GB GPU at each provider, and what is the cheapest RTX PRO 6000 96 GB?

### Takeaway
On list price, Vast.ai is clearly the cheapest marketplace.
- **RTX PRO 6000 96 GB on Vast, on demand, meeting all our specs:**
  - ~$0.99/hr (Max-Q, unverified host) to $1.12/hr (WS), before storage.
  - Verified datacenter hosts cost ~$1.47–1.61/hr.
  - Interruptible (bid) prices are ~$0.43–0.53/hr.
- **RunPod (fixed prices):**
  - RTX PRO 6000: $1.69/hr on Community Cloud, $2.49–2.59/hr on Secure Cloud.
  - Cheapest compliant 48 GB cards: RTX 6000 Ada at $0.74 (Community) / $0.99 (Secure), and L40S at $0.79 / $1.09.
- **Lium:** RTX PRO 6000 Server at $1.68–1.99/GPU-hr, on 8-GPU hosts only.
- **Shadeform:** the only RTX PRO 6000 actually in stock is Massed Compute at $2.19, which comes with a CUDA 13.0 image.
- **TensorDock:** current per-GPU prices could not be verified; its pricing API needs a login.
- **Salad:** has no GPU of 48 GB or more.

### Cited Findings

#### RunPod (fixed list prices; pricing page "Updated October 8, 2026")

| GPU | Secure Cloud $/hr | Community Cloud $/hr | Listed vCPU / RAM per GPU (pricing page) | Source |
|---|---|---|---|---|
| RTX PRO 6000 96 GB (page row) | 2.49 | 1.69 | 16 vCPU / 188 GB | [runpod.io/pricing](https://www.runpod.io/pricing) |
| RTX PRO 6000 Server Edition (API) | 2.49 | 1.69 | min 16 vCPU / 157 GB at lowest price; stock "Medium" | [RunPod GraphQL gpuTypes](https://api.runpod.io/graphql) |
| RTX PRO 6000 Workstation Edition (API) | 2.59 | 1.69 | min 21 vCPU / 125 GB; stock "Low" | [RunPod GraphQL](https://api.runpod.io/graphql) |
| RTX PRO 6000 Max-Q WS (API) | 0.50 (appears to be a placeholder; not on the pricing page) | 1.64 | n/a | [RunPod GraphQL](https://api.runpod.io/graphql) |
| RTX PRO 6000 MIG 2g.48gb (48 GB partition) | 1.29 | 1.00 | 8 vCPU / 62 GB (below our 16 vCPU / 64 GB spec) | [runpod.io/pricing](https://www.runpod.io/pricing) |
| RTX 6000 Ada 48 GB | 0.99 | 0.74 | page: 10 vCPU / 167 GB; API lowest offer: min 16 vCPU / 188 GB | [runpod.io/pricing](https://www.runpod.io/pricing), [GraphQL](https://api.runpod.io/graphql) |
| L40S 48 GB | 1.09 | 0.79 | 16 vCPU / 94 GB (API: 16 / 125) | [runpod.io/pricing](https://www.runpod.io/pricing) |
| RTX A6000 48 GB | 0.59 | 0.33 | 9 vCPU / 50 GB (below spec) | [runpod.io/pricing](https://www.runpod.io/pricing) |
| RTX PRO 5000 Blackwell 48 GB | 0.96 | 0.82 | n/a | [RunPod GraphQL](https://api.runpod.io/graphql) |
| A40 48 GB | 0.59 | 0.35 | min 9 vCPU / 50 GB | [RunPod GraphQL](https://api.runpod.io/graphql) |
| A100 PCIe 80 GB | 1.79 | 1.19 | 8 vCPU / 117 GB (below the vCPU spec) | [runpod.io/pricing](https://www.runpod.io/pricing) |
| A100 SXM 80 GB | 1.79 | 1.39 | 16 vCPU / 125 GB | [runpod.io/pricing](https://www.runpod.io/pricing) |
| H100 PCIe 80 GB | 2.89 | 1.99 | 16 vCPU / 188 GB | [runpod.io/pricing](https://www.runpod.io/pricing) |
| H100 SXM 80 GB | 3.99 | 2.69 | 20 vCPU / 125 GB | [runpod.io/pricing](https://www.runpod.io/pricing) |
| H100 NVL 94 GB | 3.19 | 2.59 | 16 vCPU / 94 GB | [runpod.io/pricing](https://www.runpod.io/pricing) |
| RTX 5090 32 GB (too small; reference only) | 1.19 | 0.69 | 9 vCPU / 35 GB | [runpod.io/pricing](https://www.runpod.io/pricing) |

Notes on the RunPod rows:
- **Tier labels:** The pricing page's visible table does not label which tier each price belongs to. The page's structured data maps $2.49 to Secure and $1.69 to Community. The GraphQL `securePrice` and `communityPrice` fields agree.
- **Spot / interruptible:**
  - The pod-create API still has an `interruptible: true` flag: "rents at a lower cost but can be stopped at any time" ([RunPod API: POST /pods](https://docs.runpod.io/api-reference/pods/POST/pods)).
  - However, the public GraphQL query returned `secureSpotPrice` and `communitySpotPrice` = null and `minimumBidPrice` = null for every GPU on 2026-10-18 ([RunPod GraphQL](https://api.runpod.io/graphql)).
  - The pricing page shows no spot prices ([runpod.io/pricing](https://www.runpod.io/pricing)).
  - Third-party spot prices are dated March 2026: DeployBase listed H100 SXM spot at $2.69 and H100 PCIe at $1.99 ([deploybase.ai](https://deploybase.ai/articles/runpod-gpu-pricing)). These are now equal to today's Community on-demand rates, so they are probably stale or mislabelled.
- **Minimum to deploy:** You need at least one hour of credits for the chosen configuration ([docs.runpod.io/pods/pricing](https://docs.runpod.io/pods/pricing)). The default spend limit is $80/hr across all resources ([RunPod billing info](https://docs.runpod.io/references/billing-information)).
- **2026 price trend:** RunPod raised Secure Cloud prices repeatedly in 2026. In the Oct 5 → Oct 12, 2026 diff:
  - H100 SXM $3.49 → $3.99
  - A100 $1.59 → $1.79
  - H200 $4.59 → $5.29
  - B200 $6.79 → $7.99
  - RTX 4090 $0.74 → $0.89

  Earlier increases recorded by the same tracker: Sep 7 (H100 to $3.49), Aug 17 (nine tiers), and Jul 27 (RTX 6000 Ada, RTX A6000) ([pricingsaas RunPod 2026W42](https://pricingsaas.com/companies/runpod/diffs/2026W42)).
- **Unfetched tracker snippets:**
  - UsagePricing reportedly logged a Sep 20, 2026 Secure Cloud hike: 11 of 19 Secure rates raised, Community rates unchanged ([usagepricing.com](https://www.usagepricing.com/blueprint/activity/runpod-2026-09-20-secure-cloud-price-hike); search snippet only, not fetched).
  - A July 2026 trim of the RTX Pro 6000 Secure rate ($2.09 → $1.99) was also reported ([usagepricing.com](https://usagepricing.com/blueprint/activity/runpod-2026-07-14-price-change); search snippet only). The rate is now $2.49, so it has risen again since July.

#### Vast.ai (live marketplace; snapshot from the public offers API, 2026-10-18 15:27 UTC; single-GPU, currently unrented offers)

[Vast offers API](https://console.vast.ai/api/v0/bundles/). Columns:
- **N** = number of offers.
- **Min / median, all hosts** = across all offers of that type.
- **Cheapest meeting spec** = driver >= 580, >= 16 vCPU, >= 64 GB RAM, >= 500 GB disk, reliability >= 0.97. It shows the GPU price, then the host, then (+500 GB storage at that host's rate = total).

| GPU (Vast name) | Type | N | Min / median $/hr (all hosts) | Cheapest meeting spec | Cheapest verified host meeting spec |
|---|---|---|---|---|---|
| RTX PRO 6000 WS | on-demand | 29 | 1.002 / 1.607 | 1.122; AU; drv 595.84; 32 vCPU; 121 GB RAM (+500 GB @ $0.20/GB-mo = $1.26/hr) | 1.606; US-PA; storage $0.533/GB-mo (= $1.97/hr incl. 500 GB) |
| RTX PRO 6000 WS | interruptible (min bid) | 23 | 0.533 / 1.033 | 0.533; US-VA; verified; drv 595.84; 24 vCPU; 63 GB RAM (just under 64) | same |
| RTX PRO 6000 S (Server) | on-demand | 14 | 1.336 / 1.482 | 1.336; JP (unverified); drv 595.91; 16 vCPU; 189 GB (+500 GB = $1.47/hr) | 1.471; FR; 64 vCPU; 283 GB (+500 GB = $1.75/hr) |
| RTX PRO 6000 S | interruptible | 13 | 0.468 / 0.933 | 0.468; JP (unverified) (+500 GB = $0.61/hr) | 0.748; US-VA (storage $0.72/GB-mo) |
| RTX PRO 6000 Max-Q | on-demand | 20 | 0.989 / 1.330 | 0.989; US-CA (unverified); drv 595.91; 16 vCPU; 123 GB; storage $0.173/GB-mo (+500 GB = $1.11/hr) | 1.344; CA-BC (storage $1.00/GB-mo → $2.03/hr) |
| RTX PRO 6000 Max-Q | interruptible | 17 | 0.400 / 0.733 | 0.427; FR; verified; drv 580.178; 26 vCPU; 101 GB (storage $0.60/GB-mo → $0.84/hr) | same |
| RTX 6000 Ada | on-demand | 7 | 0.535 / 0.669 | 0.566; EE; verified; drv 580.178; 21 vCPU; 84 GB (storage $0.533/GB-mo → $0.93/hr) | same |
| RTX 6000 Ada | interruptible | 5 | 0.200 / 0.400 | 0.200; US-NY (unverified) | 0.295; US-OK |
| L40S | on-demand | 7 | 0.429 / 0.801 | 0.749; CA-QC; verified; 43 vCPU; 336 GB (+500 GB = $0.89/hr) | same |
| L40S | interruptible | 5 | 0.373 / 0.613 | 0.467; ZA; verified | same |
| RTX A6000 | on-demand | 4 | 0.281 / 0.402 | none with >= 500 GB disk; $0.281 SK host has 80 GB disk | none |
| A100 PCIe 80 GB | on-demand | 11 | 0.443 / 0.735 | 0.683; DE (unverified) | none |
| A100 SXM4 80 GB | on-demand | 19 | 0.430 / 0.802 | 0.430; US-CA (unverified); 24 vCPU; 63 GB | 1.591; US-NC |
| A100 SXM4 80 GB | interruptible | 15 | 0.134 / 0.548 | 0.396; US-NC; verified (storage $0.655/GB-mo) | same |
| H100 SXM | on-demand | 10 | 1.335 / 2.401 | 3.467; CZ; verified | same |
| H100 SXM | interruptible | 8 | 0.654 / 1.100 | 0.654; CZ; verified | same |
| H100 PCIe | on-demand | 1 | 2.403 | 2.403; ZA | none |
| H100 NVL 94 GB | on-demand | 3 | 2.308 / 2.670 | 2.670; BG; verified | same |
| RTX PRO 5000 48 GB (extra) | on-demand | 17 | 0.593 / 0.781 | 0.601; US-FL; 64 vCPU; 251 GB | 0.736; US-NE |
| RTX 5090 32 GB (too small; reference) | on-demand | 82 | 0.414 / 0.702 | 0.522; SE | 0.795; SK |

Other Vast observations:
- **Multi-GPU (4x or more), on-demand, cheapest per GPU** ([Vast offers API](https://console.vast.ai/api/v0/bundles/)):

  | GPU | Offers | Cheapest per GPU | Configuration |
  |---|---|---|---|
  | RTX PRO 6000 WS | 7 | $1.32 | 4x, 96 vCPU, 251 GB |
  | RTX PRO 6000 S | 13 | $1.27 | |
  | RTX PRO 6000 Max-Q | 4 | $1.00 | 4x, 48 vCPU, 212 GB |
  | L40S | 4 | $0.47 | |
  | A100 SXM4 | 14 | $0.43 | |
  | A100 PCIe | 13 | $0.44 | |
  | H100 SXM | 9 | $1.92 | |
  | RTX 6000 Ada | 0 | n/a | |
  | RTX A6000 | 0 | n/a | |
- **The official pricing page shows no prices:**
  - The "Live GPU Prices" widget on vast.ai/pricing rendered empty when fetched ([vast.ai/pricing](https://vast.ai/pricing)).
  - The RTX PRO 6000 WS GPU page said "No current offers" ([vast.ai/pricing/gpu/RTX-PRO-6000-WS](https://vast.ai/pricing/gpu/RTX-PRO-6000-WS)), while the API listed 29 rentable offers at the same time. The marketing page appears stale; use the console or API.
- **Interruptible discount:** Vast advertises interruptible as "50%+ cheaper" than on-demand, and reserved as up to 50% off on 1/3/6-month terms ([vast.ai/pricing](https://vast.ai/pricing)).
- **Minimum deposit:** $5 ([Vast quickstart](https://docs.vast.ai/guides/get-started/quickstart)).

#### Lium (Bittensor subnet 51 marketplace; snapshot from the public API 2026-10-18; only 28 executors listed)

| GPU | $/GPU-hr | Configuration / host | Driver / max CUDA | Source |
|---|---|---|---|---|
| RTX PRO 6000 Blackwell Server | 1.68 | 8-GPU host, Hong Kong, 208 CPUs, ~1 TB RAM (~26 vCPU / ~125 GB per GPU), 8 of 8 free | 595.91.07 / 13.1 | [lium.io/api/executors](https://lium.io/api/executors) |
| RTX PRO 6000 Blackwell Server | 1.99 | 8-GPU host, US, 256 CPUs, ~1 TB RAM, reliability score 94.1 | 580.178.04 / 13.0 | [lium.io/api/executors](https://lium.io/api/executors); [lium.io](https://lium.io) shows the 8x pod at $15.92/hr |
| RTX PRO 6000 Blackwell WS | 1.19 "reference" | 0 pods available | — | [lium.io/gpu/rtx-pro-6000-blackwell-workstation-edition](https://lium.io/gpu/rtx-pro-6000-blackwell-workstation-edition) |
| RTX PRO 6000D / RTX 6000D 96 GB | 0.82 "reference" | not available | — | [same page](https://lium.io/gpu/rtx-pro-6000-blackwell-workstation-edition) |
| RTX 6000 Ada | 0.75 "reference" | no pod free | — | [lium.io/pricing](https://lium.io/pricing) |
| L40S | 0.38 "reference" | no pod free | — | [lium.io/pricing](https://lium.io/pricing) |
| RTX A6000 | 0.42 "reference" | no pod free | — | [lium.io/pricing](https://lium.io/pricing) |
| A100 SXM4 80 GB | 1.68 | 3 × 8-GPU US hosts | 580.105.08 / 13.0 | [lium.io/api/executors](https://lium.io/api/executors) |
| A100 80 GB PCIe | 0.45 "reference" | no pod free | — | [lium.io/pricing](https://lium.io/pricing) |
| H100 80 GB HBM3 | 1.75–2.10 | one 1x US host at $1.75; 8x hosts; one spot 8x host in Finland at $1.75 (reliability score 82.1) | mostly 580.x / 13.0; one host 570.148 / 12.8 | [lium.io/api/executors](https://lium.io/api/executors), [lium.io/pricing](https://lium.io/pricing) |
| H100 PCIe | 2.10 | 3 × 1-GPU US hosts, 26 CPUs | 580.105.08 / 13.0 | [lium.io/api/executors](https://lium.io/api/executors) |
| RTX 5090 | 0.40 "reference" | no pod free | — | [lium.io/pricing](https://lium.io/pricing) |

- Lium labels prices as "reference" when no pod is free, so those rates are not currently rentable ([lium.io/pricing](https://lium.io/pricing)).
- **Billing:**
  - Billed per second, no minimum, no reservation.
  - Starting a pod requires a balance covering 15 minutes.
  - Crypto, TAO and alpha top-ups get a 2.5% bonus.

  ([lium.io/pricing](https://lium.io/pricing))
- **Conflicting granularity:** GetDeploying says Lium bills per minute ([getdeploying.com/lium](https://getdeploying.com/lium)). This conflicts with Lium's own page.
- **Aggregator cross-check:** On Oct 18, 2026, GetDeploying listed Lium RTX PRO 6000 at $1.99 for 8x ([getdeploying RTX PRO 6000](https://getdeploying.com/gpus/nvidia-rtx-pro-6000)).

#### Shadeform (zero-markup aggregator of ~20 clouds; snapshot from the public instance-types API, 2026-10-18; 1x configurations)

| GPU | Cloud | $/GPU-hr | vCPU / RAM / disk (GB) | OS image (CUDA) | Available now? | Source |
|---|---|---|---|---|---|---|
| RTX PRO 6000 96 GB | imwt | 1.25 | 16 / 144 / 725 | ubuntu22.04 cuda12.6 | No (0 of 2 regions) | [Shadeform API](https://api.shadeform.ai/v1/instances/types) |
| RTX PRO 6000 | hyperstack | 1.85 | 28 / 225 / 3400 | cuda12.8 | No | same |
| RTX PRO 6000 | latitude | 1.90 | 16 / 128 / 500 | cuda12.4 | No | same |
| RTX PRO 6000 | verda | 1.95 | 30 / 90 / 250 | cuda12.8 | No | same |
| RTX PRO 6000 | massedcompute | 2.19 | 16 / 192 / 750 | **ubuntu22.04 cuda13.0** | **Yes (2 of 4 regions)** | same; also [computeprices (updated Oct 18, 2026)](https://computeprices.com/providers/shadeform/gpus/rtx-pro-6000) |
| RTX 6000 Ada | massedcompute | 0.97 | 12 / 80 / 350 (below 16 vCPU) | cuda13.0 | Yes | [Shadeform API](https://api.shadeform.ai/v1/instances/types) |
| RTX 6000 Ada | verda / digitalocean | 1.10 / 1.57 | 10 / 60; 8 / 64 | 12.x | No | same |
| L40S | latitude | 0.74 | 16 / 128 / 500 | cuda12.4 | No | same |
| L40S | massedcompute | 0.88 | 12 / 72 / 625 (below 16 vCPU) | cuda13.0 | Yes | same |
| L40S | scaleway | 1.70 | 8 / 96 / 1000 | cuda12.8 or **cuda13.0** | No | same |
| RTX A6000 | hyperstack | 0.50 | 28 / 58 / 100 (below RAM and disk spec) | cuda12.8 | Yes | same |
| RTX A6000 | massedcompute | 0.57 | 12 / 64 / 256 | cuda13.0 | Yes | same |
| A100 80 GB | hyperstack | 1.35 | 28 / 120 / 850 | cuda12.8 | Yes | same |
| A100 80 GB | massedcompute | 1.38 | 16 / 160 / 1000 (meets spec) | cuda13.0 | Yes | same |
| H100 80 GB | latitude | 1.66 | 16 / 128 / 500 | cuda12.4 | No | same |
| H100 80 GB | hyperstack | 2.50 | 28 / 180 / 850 | cuda12.8 | Yes | same |
| H100 80 GB | scaleway | 3.30 | 24 / 240 / 1000 | cuda12.8 / **cuda13.0** | Yes | same |
| RTX 5090 | excesssupply | 0.65 (4x only) | 60 / 480 / 3400 | cuda12.8 | Yes | same |

- **Fees:** Shadeform says it "charges the same rate as going direct to the cloud provider" ([Shadeform FAQ](https://docs.shadeform.ai/getting-started/faq)). GetDeploying describes it as "Free to use, zero mark-up fees" ([getdeploying.com/shadeform](https://getdeploying.com/shadeform)).
- **Spot:** Only 3 of 761 region-availability rows in the API are `spot`, all 8x configurations from excesssupply, for example 8x L40 at $3/hr spot in Casper, WY ([Shadeform API](https://api.shadeform.ai/v1/instances/types)). The FAQ says spot and persistent volumes were "recently shipped" ([Shadeform FAQ](https://docs.shadeform.ai/getting-started/faq)).
- **4x RTX PRO 6000 per GPU:** imwt $1.25, hyperstack $1.85, verda $1.96, massedcompute $2.19 (768 GB RAM, 60 vCPU, CUDA 13.0 image). None was marked available in the snapshot except possibly Massed Compute regions ([Shadeform API](https://api.shadeform.ai/v1/instances/types)).

#### TensorDock (Voltage Park–owned marketplace of independent hosts)

- **Homepage prices:**
  - H100 SXM5 "From $2.25/hr"
  - A100 SXM4 "From $1.80/hr"
  - RTX 4090 "From $0.35/hr"
  - consumer GPUs "From $0.12/hr"

  The homepage lists no RTX PRO 6000, RTX 6000 Ada, L40S, A6000 or 5090 prices ([tensordock.com](https://www.tensordock.com/)). Its competitor-comparison page is marked "Last Updated: July 24, 2024" ([tensordock cloud-gpus](https://marketplace.tensordock.com/cloud-gpus.html)).
- **Live prices could not be retrieved:** The v2 hostnodes API returned HTTP 401 without an API key, and `/api/v2/locations` returned an empty list unauthenticated ([dashboard.tensordock.com/api/v2/hostnodes](https://dashboard.tensordock.com/api/v2/hostnodes)).
- **Third-party (Spheron, a competitor, "2026", rates marked live 18 Oct 2026)** ([spheron.network](https://www.spheron.network/blog/tensordock-pricing-2026/)):
  - H100 on-demand $1.90–2.50 (commonly $2.25)
  - Marketplace bid $1.30–1.91
  - $5 minimum deposit
  - "hourly by default" billing
  - Voltage Park acquired TensorDock in March 2025.
- **Third-party, undated:** RTX 6000 Ada "$0.86/hr" 1x on-demand ([getdeploying L40 vs RTX 6000 Ada](https://getdeploying.com/gpus/nvidia-l40-vs-nvidia-rtx-6000-ada), via search snippet). An RTX A6000 figure of $0.56 appeared in a search snippet with an unclear table context.
- **Not in the aggregator:** TensorDock is absent from GetDeploying's Oct 18, 2026 RTX PRO 6000 provider list ([getdeploying RTX PRO 6000](https://getdeploying.com/gpus/nvidia-rtx-pro-6000)).

#### Salad (SaladCloud)

| GPU | High priority $/hr | Lowest (batch) $/hr | Source |
|---|---|---|---|
| RTX 5090 32 GB (largest listed) | 0.50 | 0.25 | [salad.com/pricing](https://salad.com/pricing) |
| RTX 4090 24 GB | 0.33 | 0.16 | [salad.com/pricing](https://salad.com/pricing) |
| Any GPU of 48 GB or more | not offered | — | [salad.com/pricing](https://salad.com/pricing): no card of 48 GB or more is listed; reserved capacity is quoted under "Salad Dedicated" |

- vCPU and RAM are included with the GPU at no extra charge. Billing is per second, only while running, with no minimum ([salad.com/pricing](https://salad.com/pricing)).

#### Aggregator cross-check (RTX PRO 6000)
- **GetDeploying (footer dated Oct 18, 2026)** ([getdeploying RTX PRO 6000](https://getdeploying.com/gpus/nvidia-rtx-pro-6000)):
  - RunPod $1.69 (1x Community) and $2.49 (Secure)
  - Lium $1.99 (8x)
  - Massed Compute $2.19 (1x)
  - Vast, TensorDock, Shadeform and Salad not listed
  - Cheapest verified in stock anywhere: Packet·ai at $0.66 (a sponsor)
  - Cheapest in-stock spot: Spheron at $1.14
- **Computeprices:** ranks Shadeform's RTX PRO 6000 #24 of 40 providers; cheapest tracked is Nebius at $0.79/hr ([computeprices Shadeform RTX PRO 6000](https://computeprices.com/providers/shadeform/gpus/rtx-pro-6000)).

### Inferences
- **Cheapest RTX PRO 6000 96 GB among the six marketplaces:**
  - **On demand:** Vast at ~$0.99–1.12/hr GPU-only (Max-Q or WS, unverified hosts that meet the spec), or ~$1.11–1.26/hr with 500 GB of disk.
  - **Interruptible:** Vast at ~$0.43–0.53/hr.
  - **Fixed-price option:** RunPod Community at $1.69/hr. This is roughly 50–70% more expensive than Vast but has fixed, known pricing and no per-host storage or bandwidth surprises.
- **Cheapest >= 48 GB card meeting all specs at a fixed price:** RunPod Community RTX 6000 Ada at $0.74 (16 vCPU / 188 GB at the lowest-price offer), or Secure RTX 6000 Ada at $0.99. A 48 GB card leaves only ~7.5 GB of headroom over the 40.5 GB peak, and Ada and L40S cards are slower than Blackwell. Per-hour savings could be partly offset by longer runs. This was not measured.
- **Rough 150 GPU-hour budget, plus 500 GB kept for ~17 days until Nov 4** (my arithmetic from the cited prices; excludes egress and interruption losses):

  | Option | Compute | Storage | Total |
  |---|---|---|---|
  | RunPod Secure RTX PRO 6000 + network volume | 150 × $2.49 = $374 | ~$20 | **~$393** |
  | RunPod Community RTX PRO 6000 + 500 GB volume disk kept stopped | $254 | ~$56 at $0.20/GB-mo stopped | **~$310** |
  | RunPod Secure RTX 6000 Ada + network volume | $149 | ~$20 | **~$168** |
  | Vast RTX PRO 6000 Max-Q on-demand, unverified US-CA host | $148 | ~$48 | **~$197** |
  | Vast RTX PRO 6000 S interruptible, JP host | ~$70 | ~$56 | **~$126**, before rework from preemptions |
  | Shadeform → Massed Compute RTX PRO 6000 | $329 | disk included while the VM exists; stopping is not documented | **~$329** |
  | Lium RTX PRO 6000 Server | $252–299 | volume rate unpublished | **$252–299 + volume** |
- **Parallel runs (20 at once):**
  - Vast had ~63 unrented single-GPU RTX PRO 6000 offers plus 24 multi-GPU (4x or more) offers in the snapshot, so 20 in parallel is plausible but on heterogeneous hosts.
  - RunPod reports "Low" or "Medium" stock for RTX PRO 6000.
  - Shadeform had only Massed Compute available.
  - Lium had only two 8-GPU RTX PRO 6000 hosts.

### Gaps
- TensorDock current per-GPU prices for every target GPU: the API needs authentication; only stale or third-party figures were found.
- Whether RunPod spot/interruptible pods are still sold, and at what price. The API flag exists, but no spot prices were exposed publicly on 2026-10-18. An authenticated `gpuTypes` query or the deploy UI would settle it.
- Whether Lium lets you rent 1 GPU of an 8-GPU RTX PRO 6000 host. The API field `min_gpu_count_for_rental` is null for those hosts and per-GPU pricing is shown, but this is not confirmed.
- Vast prices are live auctions and asks; the snapshot may differ within hours. Unverified "CN"/"JP" hosts may have network or latency or legal considerations that were not assessed.

---

## Q2. How does storage persist when instances are stopped or terminated, what does it cost, and what are the billing granularity and egress fees?

### Takeaway
- **RunPod** has the clearest model: per-second compute, network volumes at $0.07/GB-mo that survive termination (Secure Cloud only), volume disks at $0.10 running / $0.20 per GB-month stopped, and no egress fees.
- **Vast** bills per second but storage and bandwidth are priced per host. Storage was a median $0.20/GB-mo but ranged $0.02–$1.00; bandwidth was a median $2.67/TB down and $4.00/TB up, with some hosts above $50/TB. Storage keeps billing while stopped, and a stopped instance may not be able to restart if its GPU gets rented.
- **TensorDock** has host-rate storage, with network storage in "Core Compute" locations.
- **Lium** includes local disk and offers at-cost volumes with no published rate.
- **Shadeform** depends on the underlying cloud.
- **Salad** has only ephemeral storage.

### Cited Findings

#### RunPod
- **Billing granularity:** Compute, container disk and volume disk are billed per second; network volumes are billed hourly ([docs.runpod.io/pods/pricing](https://docs.runpod.io/pods/pricing)).
- **Storage rates** ([docs.runpod.io/pods/pricing](https://docs.runpod.io/pods/pricing); [runpod.io/pricing](https://www.runpod.io/pricing)):

  | Storage | Running | Stopped | Notes |
  |---|---|---|---|
  | Container disk | $0.10/GB-mo | not charged | erased when the pod stops |
  | Volume disk | $0.10/GB-mo | $0.20/GB-mo | kept until the pod is deleted |
  | Network volume, standard | $0.07/GB-mo under 1 TB; $0.05 over 1 TB | same | |
  | Network volume, high-performance | $0.14/GB-mo | same | |
- **Network volumes (Secure Cloud only):**
  - Network volumes for Pods are "only available for Pods in the Secure Cloud."
  - A volume pins pods to its datacenter, so available GPU types depend on that datacenter. One volume per datacenter; volumes over 4 TB need support.
  - Data is retained when pods terminate.
  - Volumes must be attached at deploy time.
  - NVMe throughput is 200–400 MB/s, with up to 10 GB/s peak.

  ([RunPod network volumes](https://docs.runpod.io/storage/network-volumes))
- **Stopping a pod with a local volume disk:** The volume stays on that physical machine. If someone rents the GPU meanwhile, the restart comes up with **zero GPUs**, usable only to copy data off. RunPod's recommended prevention is network volumes ([RunPod zero-GPU troubleshooting](https://docs.runpod.io/pods/troubleshooting/zero-gpus)).
- **Egress:** "no fees for data ingress or egress" ([docs.runpod.io/pods/pricing](https://docs.runpod.io/pods/pricing)).
- **At a $0 balance:** Pods stop. Pods with a network volume keep their data; pods without one are terminated and their data is unrecoverable. Unpaid network volumes may eventually be terminated ([docs.runpod.io/pods/pricing](https://docs.runpod.io/pods/pricing); [RunPod billing info](https://docs.runpod.io/references/billing-information)).
- **Not long-term storage:** RunPod says it "isn't designed for long-term storage" and recommends backing up critical data elsewhere ([docs.runpod.io/pods/pricing](https://docs.runpod.io/pods/pricing)).

#### Vast.ai
- **Billing:**
  - Billed per second while active.
  - When stopped, GPU charges stop but **storage charges continue**.
  - Offline hosts charge nothing.
  - Bandwidth is charged per TB in **and** out, whatever the instance state, at rates set per machine.

  ([Vast billing](https://docs.vast.ai/documentation/reference/billing))
- **Snapshot of host-set rates** across 414 offers for the target GPUs ([Vast offers API](https://console.vast.ai/api/v0/bundles/)):
  - Storage: min $0.02, median $0.20, max $1.00 per GB-month.
  - Download: median $2.67/TB, max $53.33/TB.
  - Upload: median $4.00/TB, max $81.92/TB.
  - Example: the cheapest *verified* RTX PRO 6000 WS that meets our specs (US-PA) charges $0.533/GB-mo for storage and $53/$82 per TB for bandwidth.
- **Disk persistence and sizing:**
  - Container disk size is fixed at creation and cannot be changed.
  - Volumes are persistent local storage that survive instance deletion but can only reattach to instances on the **same physical host**.
  - Stopped instances "may also carry higher storage rates than running ones."

  ([Vast storage types](https://docs.vast.ai/documentation/instances/storage/types); [Vast quickstart](https://docs.vast.ai/guides/get-started/quickstart))
- **Restarting a stopped instance:**
  - It "enters SCHEDULING status"; "If stuck >30 seconds, GPU likely rented by another user."
  - It "May wait indefinitely for GPU availability."
  - Destroyed instances lose all data.
  - Use Cloud Sync only on datacenters with the Secure icon.

  ([Vast manage instances](https://docs.vast.ai/guides/instances/manage-instances))
- **At a $0 balance:** Instances stop. With a saved card, the card is charged and instances can be resumed without data loss. Without a card, "instances and stored data are destroyed" after a grace period ([Vast billing](https://docs.vast.ai/documentation/reference/billing)). A search summary noted a conflicting quickstart statement ("stopped but not destroyed"), so the exact policy is uncertain.

#### TensorDock
- **Spot storage example:** Storage is billed at the host's standard rate on top of compute. The docs' example: a $0.35/hr bid plus 200 GB at $0.00005/GB-hr (≈ $0.0365/GB-mo) = $0.36/hr while running, and about $0.01/hr (storage only) when outbid ([TensorDock spot docs](https://docs.tensordock.com/virtual-machines/spot-instances.md)).
- **Core Compute locations** include network storage. A stopped VM can be redeployed on any server in the same location that has the GPU available ([TensorDock Core Compute VMs](https://docs.tensordock.com/virtual-machines/introduction-to-core-compute-vms.md)).
- **At a $0 balance,** "your servers are automatically deleted" ([tensordock.com](https://www.tensordock.com/)).
- **Billing granularity:** "hourly by default," with CPU, RAM and storage billed à la carte, per a third-party source ([spheron.network](https://www.spheron.network/blog/tensordock-pricing-2026/)). Not confirmed in official docs.

#### Lium
- **Storage and billing:**
  - The pod price includes local disk.
  - A persistent volume is billed separately "at cost" per GB-hour, plus charges for data read from the volume. No rates are published.
  - Billing stops when you delete the pod or at its scheduled end.

  ([lium.io/pricing](https://lium.io/pricing))
- Data is released when a pod is deleted; volumes can outlive pods ([Lium RTX PRO 6000 WS page](https://lium.io/gpu/rtx-pro-6000-blackwell-workstation-edition)).

#### Shadeform
- **Storage:** Instance types include fixed local disk, for example Massed Compute RTX PRO 6000 with 750 GB ([Shadeform API](https://api.shadeform.ai/v1/instances/types)). Persistent volumes are "recently shipped," with no pricing published in the FAQ ([Shadeform FAQ](https://docs.shadeform.ai/getting-started/faq)).
- **Billing:** "1-minute increments," per a third-party source dated March 2026 ([deploybase.ai](https://deploybase.ai/articles/shadeform-gpu-pricing)). Not confirmed officially.

#### Salad
- **Storage is ephemeral:** "Local storage is ephemeral—completely erased when containers exit or nodes are interrupted," with up to 250 GB while running. External storage is recommended, for example Cloudflare R2 ([Salad SCE architecture, updated Jul 13, 2026](https://docs.salad.com/products/sce/getting-started/architectual-overview)).
- **Billing:** per second while running ([salad.com/pricing](https://salad.com/pricing)).

### Inferences
- **For "pay only when the GPU is in use" with 500 GB of persistent data,** the cleanest pattern among these providers is a RunPod Secure Cloud network volume (~$35/month for 500 GB, ~$20 until Nov 4) plus terminate-on-idle Secure pods. You lose the cheaper Community pricing, because network volumes cannot attach to Community pods.
- **Stopping and later restarting** either a RunPod Community pod or a Vast instance risks GPU unavailability: RunPod's zero-GPU restart, or Vast's indefinite SCHEDULING state. For 20 parallel short runs, an object store plus fresh instances is more robust than stop/restart. This is an inference from the documented restart behaviour.
- **On Vast, a 500 GB disk can add $0.07–$0.68/hr** depending on the host, and egress at $40–80/TB on some hosts could matter if checkpoints or logs are pulled back. Filter on both storage and bandwidth price, not only GPU $/hr.
- **Disk sizing for parallel runs:** A 500 GB disk per parallel run is likely unnecessary. Only the debugging box needs it; per-run disks can be small. This depends on dataset size, which I did not verify.

### Gaps
- Lium volume $/GB-hr and read charges; Shadeform volume pricing; whether Shadeform instances (for example Massed Compute) can be stopped rather than only deleted; TensorDock's official billing granularity and stopped-VM charges; TensorDock egress fees.
- Vast's exact negative-balance deletion grace period: the docs conflict.

---

## Q3. Can we guarantee CUDA 13 / NVIDIA driver >= 580 hosts (filters, templates)?

### Takeaway
Yes on RunPod, Vast and Lium, which are container platforms with a host-fixed driver:
- **RunPod:** The pod-create API accepts `allowedCudaVersions: ["13.0"]`.
- **Vast:** Supports `driver_version` and `cuda_vers` filters. In the snapshot, 100% of RTX PRO 6000 WS and Max-Q offers and 13 of 14 Server offers already had driver >= 580.
- **Lium:** Exposes driver and `max_cuda_version` per executor. Both RTX PRO 6000 hosts were 580.178 or 595.91.

On VM platforms (TensorDock, Shadeform's VM clouds) you have root and can install the driver yourself. Shadeform also lists `cuda13.0` OS images on Massed Compute and Scaleway. Salad is not applicable.

### Cited Findings
- **RunPod:**
  - `allowedCudaVersions` accepts `11.8`, `12.0`–`12.9` and `13.0`; if unset, any CUDA version is acceptable.
  - `minVCPUPerGPU` (default 2) and `minRAMPerGPU` (default 8 GB) enforce CPU and RAM floors.
  - `cloudType` is `SECURE` or `COMMUNITY`.
  - RTX PRO 6000 `gpuTypeIds`: "NVIDIA RTX PRO 6000 Blackwell Server Edition", "…Workstation Edition", "…Max-Q Workstation Edition".

  ([RunPod API: POST /pods](https://docs.runpod.io/api-reference/pods/POST/pods))
- **Vast:**
  - Official SDK/CLI docs describe `driver_version` as a string filter ("machine's nvidia/amd driver version as 3 digit string ex. '535.86.05'") and `cuda_vers` as the machine's max supported CUDA version ([Vast Python SDK docs](https://docs.vast.ai/sdk/python), via search snippet).
  - The offers API also returns `driver_version` and `cuda_max_good` per offer ([Vast offers API](https://console.vast.ai/api/v0/bundles/)).
- **Vast snapshot: share of on-demand single-GPU offers with driver >= 580** ([Vast offers API](https://console.vast.ai/api/v0/bundles/)):
  - RTX PRO 6000 WS 29/29, Max-Q 20/20, S 13/14
  - L40S 5/7, RTX 6000 Ada 5/7, A6000 3/4
  - A100 SXM4 17/19, A100 PCIe 10/11, H100 SXM 8/10, H100 NVL 1/3
  - RTX 5090 77/82
  - Drivers seen on compliant RTX PRO 6000 hosts: 580.173, 580.178, 582.16, 590.48, 595.71, 595.84, 595.91, 595.99.
  - The cheapest RTX 6000 Ada (Utah, $0.535) ran driver 535.183, which shows why the filter matters.
- **Lium:** Each executor exposes `specs.gpu.driver` and `max_cuda_version` ([lium.io/api/executors](https://lium.io/api/executors)):
  - RTX PRO 6000 Server hosts: 595.91.07 (CUDA 13.1) and 580.178.04 (CUDA 13.0).
  - Of 28 executors, one H100 host was on 570.148.08 (CUDA 12.8).
- **Shadeform:** OS options per instance type include `ubuntu22.04_cuda13.0_shade_os` (all Massed Compute types) and `ubuntu24.04_cuda13.0_shade_os` (Scaleway). Other clouds list CUDA 12.x images: imwt 12.6, hyperstack 12.8, verda 12.8, latitude 12.4, lambdalabs 12.4. `deployment_type` is "vm" for almost all ([Shadeform API](https://api.shadeform.ai/v1/instances/types)).
- **TensorDock:** "Root access with self-managed drivers" ([tensordock.com](https://www.tensordock.com/)). The docs include a "Linux & NVIDIA Drivers" page on updating drivers on Ubuntu ([TensorDock docs index](https://docs.tensordock.com/llms.txt); [driver doc](https://docs.tensordock.com/virtual-machines/updating-nvidia-drivers-on-ubuntu.md)).

### Inferences
- **RunPod:** Pass `allowedCudaVersions=["13.0"]` (plus `minVCPUPerGPU=16`, `minRAMPerGPU=64`) when creating pods. Whether the UI exposes the same filter was not verified in this session.
- **Vast:** Use a query like `driver_version>=580` (string comparison, so be careful), `cuda_vers>=13.0`, `cpu_cores_effective>=16`, `cpu_ram>=65536`, `disk_space>=500`, `reliability>=0.97`. Note that `cpu_cores_effective` and `cpu_ram` in the API are already the per-rental share (the GPU fraction of host resources).
- **VM providers** (TensorDock, Shadeform clouds): even 12.x images can be upgraded to a 580+ driver with root. That costs setup time on each fresh VM unless a custom image or startup script is used.

### Gaps
- Whether the RunPod and Vast web UIs expose a CUDA 13 filter, and whether RunPod's `allowedCudaVersions` list was extended to 13.1 or later. The docs list only up to 13.0.
- Whether Shadeform's other clouds ship drivers >= 580 despite their "cuda12.x" image names. Image names reflect the toolkit, not necessarily the driver.

---

## Q4. What are the risks (interruption, host reliability, data loss) for community / spot / interruptible options?

### Takeaway
- **Vast interruptible** is the cheapest at ~40–60% of on-demand. Being outbid pauses (stops) the instance and kills its processes. It can wait indefinitely to resume, and storage keeps billing.
- **Vast unverified and RunPod Community hosts** carry host-quality variance plus the stop/restart GPU-loss problem.
- **Lium** supply is thin and volatile: several hosts were scheduled for permanent removal within 24 hours.
- **Salad** interrupts without warning and has no SSH.
- **RunPod Secure + network volume** is the lowest-risk option here, at a premium.

### Cited Findings
- **Vast interruptible:**
  - A bidding system where a higher bid gets priority. Lower-priority instances are "paused until they become the highest priority."
  - On-demand always outranks interruptible.
  - When outbid, the instance is stopped (running processes killed) and "may wait long to resume." Vast recommends checkpointing.
  - There is no 24-hour cap, unlike GCE preemptible.

  ([Vast rental types](https://docs.vast.ai/rental-types); [Vast FAQ rental types](https://docs.vast.ai/guides/reference/faq/rental-types); via search summary)
- **Vast host quality:**
  - Hosts carry a `reliability` score and a verified or unverified flag. In the snapshot, compliant RTX PRO 6000 hosts scored 0.98–0.998 ([Vast offers API](https://console.vast.ai/api/v0/bundles/)).
  - The cheapest H100 SXM ($1.335) had reliability 0.883 ([Vast offers API](https://console.vast.ai/api/v0/bundles/)).
  - Trustpilot reviewers describe stopped instances that disappear from availability and sit in SCHEDULING for long periods. This is anecdotal ([Trustpilot via search summary](https://no.trustpilot.com/review/vast.ai)).
- **RunPod interruptible:** Can "be stopped at any time to free resources" ([RunPod API](https://docs.runpod.io/api-reference/pods/POST/pods)). Third-party accounts disagree on notice: DeployBase says "typically <5 minute notice" ([deploybase.ai](https://deploybase.ai/articles/runpod-gpu-pricing)), while Hivenet says RunPod gives termination warnings ([hivenet.com](https://www.hivenet.com/post/runpod-pricing-complete-guide-to-gpu-cloud-costs)).
- **RunPod Community / volume-disk pods:** Risk restarting with zero GPUs if the GPU is rented while stopped, and terminating a pod deletes all data not on a network volume ([RunPod zero-GPU doc](https://docs.runpod.io/pods/troubleshooting/zero-gpus)).
- **TensorDock spot:**
  - Still beta: "Expect higher risk of bugs."
  - Priority goes to the highest *aggregate* revenue per VM, so a larger VM can outbid a higher per-GPU bid.
  - Hosts set minimum bids of around 50% of on-demand.
  - The docs do not describe interruption notice or data handling.

  ([TensorDock spot docs](https://docs.tensordock.com/virtual-machines/spot-instances.md))
- **TensorDock host reliability (third-party, Spheron):**
  - Hosts must schedule maintenance two weeks ahead.
  - TensorDock claims 99.99% uptime.
  - GPU Cloud List observed about 99.1% uptime on datacenter-verified hosts and about 97% on community hosts.

  ([spheron.network](https://www.spheron.network/blog/tensordock-pricing-2026/))
- **Lium:**
  - Spot executors are flagged `is_spot`. The two in the snapshot had reliability scores of 82.1 and 81.2, against 92–99.7 for "secure" tier hosts.
  - Several A100, H100 and B200 hosts carried `scheduled_notice` entries with `permanent_removal: true` dated 2026-10-18 to 2026-10-19.

  ([lium.io/api/executors](https://lium.io/api/executors))
- **Salad:**
  - "Machines can be interrupted without warning at unpredictable times," with "No advance notification events (unlike AWS spot instances)."
  - Local storage is erased on interruption ([Salad SCE architecture](https://docs.salad.com/products/sce/getting-started/architectual-overview)).
  - Medium and Low priorities can be preempted after a minimum run of roughly 30 minutes ([salad.com/pricing](https://salad.com/pricing)).
- **Shadeform:** Nearly all capacity is on-demand VMs from datacenter clouds; spot was only 3 of 761 rows ([Shadeform API](https://api.shadeform.ai/v1/instances/types)).

### Inferences
- **2-hour independent runs** are a good fit for Vast interruptible or verified on-demand, provided runs checkpoint to external storage and a preempted run can simply be resubmitted. The expected rework cost is low for 2-hour jobs compared with the ~50% price cut.
- **For the 1-day interactive debugging session,** preemption or host loss is costly in human time. On-demand is preferable: a verified Vast host or RunPod Secure or Community.
- **Unverified Vast hosts** in CN or JP were the cheapest compliant offers. Risk factors for those hosts (network throughput to the EU or Turkey, data jurisdiction, host churn) were not measured.
- **Lium:** Its two-host RTX PRO 6000 supply and the scheduled removals suggest availability may vanish between debugging and the training batch.

### Gaps
- Actual preemption frequency on Vast interruptible for RTX PRO 6000. No published statistics were found; it depends on competing bids.
- RunPod spot notice period, from an official source.
- Lium host churn rates and its interruption policy for non-spot pods.

---

## Q5. Sign-up friction (card, KYC, deposit, non-US/Turkish cards), SSH, typical vCPU/RAM, multi-GPU availability, and credits or programs

### Takeaway
- **Sign-up:** All five usable providers are prepaid, card-or-crypto platforms with low minimums: RunPod $10, Vast $5, TensorDock $5, Lium a 15-minute balance, Shadeform pay-as-you-go. None publishes a Turkey restriction. KYC is documented only for RunPod crypto payments.
- **SSH:** Works on RunPod (full SSH needs a public-IP pod), Vast, TensorDock, Lium and Shadeform. Salad has no SSH.
- **Credits:** Startup programs exist at RunPod and Vast (and Vast has an EDU program for universities). No generic new-user credit was found.

### Cited Findings
- **RunPod sign-up:**
  - Minimum deposit $10. Prepaid cards should deposit at least $100 per transaction because of Stripe minimums.
  - Payment by Visa, Mastercard, Amex and other Stripe-supported cards, or crypto. **KYC is required before the first crypto payment.**
  - Invoicing (ACH or wire) for amounts over $5,000.

  ([RunPod billing info](https://docs.runpod.io/references/billing-information); [RunPod funding blog](https://www.runpod.io/blog/manage-runpod-account-funding))
- **RunPod card declines:** The processor may block all funding attempts after declines from multiple cards on one account; these blocks generally clear after 24 hours. RunPod cannot help with bank-side blocks ([RunPod manage cards FAQ](https://docs.runpod.io/references/faq/manage-cards), via search summary).
- **Turkish cards (general, not provider-specific):** Cards issued by Turkish banks may need online use authorized by the bank ([Google Payments help](https://support.google.com/payments/answer/7501626)). No RunPod, Vast, Lium, TensorDock or Shadeform document mentions Turkey.
- **Vast sign-up:**
  - $5 minimum deposit; card, BitPay or Crypto.com.
  - Email verification is required before renting. Phone and KYC are not mentioned.
  - Autobilling is available for cards only.

  ([Vast quickstart](https://docs.vast.ai/guides/get-started/quickstart); [Vast billing](https://docs.vast.ai/documentation/reference/billing))
- **Vast refunds:** Unspent card-bought credits are refundable via chat; crypto purchases are not refunded ([Vast billing](https://docs.vast.ai/documentation/reference/billing)).
- **TensorDock sign-up:** $5 minimum deposit ([tensordock.com](https://www.tensordock.com/)). Payment methods are not listed on the homepage.
- **Lium sign-up:** Card, crypto (choice of coin and network), or TAO / Bittensor alpha; crypto top-ups get a 2.5% bonus. Starting a pod requires a balance covering 15 minutes ([lium.io/pricing](https://lium.io/pricing)).
- **Shadeform sign-up:** Pay-as-you-go by default; invoice payment via support@shadeform.ai. You pay Shadeform, which passes payment to the cloud ([Shadeform FAQ](https://docs.shadeform.ai/getting-started/faq)).
- **Salad sign-up:** Pay-as-you-go, no minimum commitment, no free trial ([salad.com/pricing](https://salad.com/pricing)).
- **SSH by provider:**
  - **RunPod:** Basic proxy SSH works on all pods (no SCP or SFTP). Full SSH with SCP/SFTP requires an instance with a public IP and TCP 22 exposed ([RunPod SSH docs](https://docs.runpod.io/pods/configuration/use-ssh)).
  - **Vast:** SSH keys are uploaded on the Keys page ([Vast quickstart](https://docs.vast.ai/guides/get-started/quickstart)).
  - **TensorDock:** Has SSH key and SSH how-to docs; each Core Compute VM gets a static IP with the full port range ([TensorDock docs index](https://docs.tensordock.com/llms.txt); [Core Compute](https://docs.tensordock.com/virtual-machines/introduction-to-core-compute-vms.md)).
  - **Lium:** Pods get SSH root access ([getdeploying.com/lium](https://getdeploying.com/lium), via search summary); the console has an SSH Keys page ([lium.io](https://lium.io)).
  - **Shadeform:** Connect as the `shadeform` user; root needs manual setup ([Shadeform FAQ](https://docs.shadeform.ai/getting-started/faq)).
  - **Salad:** Only "basic log and terminal access" ([Salad SCE architecture](https://docs.salad.com/products/sce/getting-started/architectual-overview)); search results summarize the docs as saying external SSH is not supported.
- **Typical vCPU/RAM per GPU:** See the Q1 tables. In summary:
  - **RunPod:** RTX PRO 6000 16 vCPU / 188 GB; RTX 6000 Ada 10 vCPU / 167 GB on the page (16 / 188 at the cheapest API offer); A6000 9 / 50; A100 PCIe 8 / 117 ([runpod.io/pricing](https://www.runpod.io/pricing)).
  - **Vast:** Varies per host. Compliant RTX PRO 6000 offers ranged 16–64 vCPU and 63–283 GB.
  - **Shadeform / Massed Compute:** RTX PRO 6000 at 16 vCPU / 192 GB.
  - **Lium:** ~26 vCPU / ~125 GB per GPU on its 8x RTX PRO 6000 hosts.
- **Multi-GPU (4x) availability:**
  - **Vast:** 4x RTX PRO 6000 from $1.00–1.32 per GPU-hour (24 listings of 4x or more across the variants) ([Vast offers API](https://console.vast.ai/api/v0/bundles/)).
  - **RunPod:** Secure Cloud offers RTX PRO 6000 in 1x–4x configurations ([getdeploying RTX PRO 6000](https://getdeploying.com/gpus/nvidia-rtx-pro-6000)).
  - **Shadeform:** 4x RTX PRO 6000 types at $1.25–2.19 per GPU ([Shadeform API](https://api.shadeform.ai/v1/instances/types)).
  - **Lium:** 8x hosts only for RTX PRO 6000 ([lium.io/api/executors](https://lium.io/api/executors)).
- **Credits and programs:**
  - **RunPod:** The startup-credits page advertises "up to $25K" in credits ([runpod.io/startup-credits](https://runpod.io/startup-credits)); the startup-program page says up to $10K ([runpod.io/startup-program](https://www.runpod.io/startup-program)). These are search-snippet figures; the pages were not fetched, and the amounts conflict.
  - **Vast:** The education page offers "EDU Pricing and Credits" for universities and research labs ([vast.ai/education](https://vast.ai/education)). Vast startup terms were found only on unverified aggregators ([perkstack](https://perkstack.co/catalog/vast-ai-startups)).
  - No new-user credits are documented for RunPod, Vast, Salad or Shadeform ([RunPod billing info](https://docs.runpod.io/references/billing-information); [Vast quickstart](https://docs.vast.ai/guides/get-started/quickstart); [salad.com/pricing](https://salad.com/pricing)).

### Inferences
- **Lowest-friction path from Turkey:** a Stripe card top-up of $5–$10 at Vast or RunPod after enabling online/international use with the issuing bank. Crypto is a fallback at Vast and Lium; at RunPod, crypto triggers KYC.
- **Credit programs:** The RunPod and Vast startup/EDU programs are unlikely to be approved before 2026-11-04. Treat them as optional upside, not budget.

### Gaps
- Explicit acceptance of Turkish-issued cards at any provider, and whether RunPod or Vast block certain countries or BINs. None of the fetched documents says so.
- TensorDock and Shadeform payment-method lists and KYC policies.
- RunPod Community Cloud public-IP availability for full SSH, which the SSH doc does not specify per tier.
