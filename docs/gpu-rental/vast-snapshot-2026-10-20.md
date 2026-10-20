# Vast.ai market snapshot, 2026-10-20 (public offers API, no key needed)

Query: `POST https://console.vast.ai/api/v0/bundles/` with JSON
`{"rentable":{"eq":true},"rented":{"eq":false},"num_gpus":{"eq":1},"gpu_name":{"eq":"<name>"},"type":"on-demand"|"bid","limit":500}`.
Python urllib gets HTTP 403; curl works. A combined query is capped at ~64 results, so query each GPU name.
Compliant = CUDA >= 13.0, >= 16 effective vCPU, >= 64 GB RAM, >= 200 GB disk, reliability >= 0.98.
Cost per policy is an ESTIMATE: (price + 200 GB storage) x 2.0 h / relative speed. Speed relative to the measured
RTX PRO 6000 Server Edition: WS 1.08, Max-Q 0.75 (unmeasured guess), PRO 5000 0.65, 6000 Ada 0.67, L40S 0.63,
A6000 0.39, A100 0.5. All except the Server Edition figure are estimates.

On-demand, verified, compliant (cheapest per policy):
| GPU | offer id | location | $/h | +200 GB storage | est. $/policy | CPU / RAM / disk | reliability | CUDA |
|---|---|---|---|---|---|---|---|---|
| RTX PRO 6000 WS | 44111199 | Spain | 1.136 | 1.19 | 2.20 | 64 / 251 GB / 2 TB | 0.982 | 13.0 |
| RTX PRO 5000 (48 GB) | 56821109 | Nebraska | 0.669 | 0.72 | 2.23 | 37 / 72 GB / 1.7 TB | 0.987 | 13.2 |
| RTX 6000 Ada (48 GB) | 55576648 | California | 0.619 | 0.77 | 2.28 | 48 / 118 GB / 540 GB | 0.995 | 13.0 |
Cheaper on-demand listings were unverified or "deverified" hosts (e.g. a $1.00 PRO 6000 WS in China), which we skip.

Interruptible (bid), compliant, verified:
| GPU | offer id | location | min bid $/h | +200 GB storage | est. $/policy | CPU / RAM | reliability |
|---|---|---|---|---|---|---|---|
| RTX PRO 6000 Max-Q | 54924110 | Georgia, US | 0.188 | 0.23 | 0.60 | 48 / 125 GB | 0.986 |
| RTX PRO 6000 WS | 44111199 | Spain | 0.282 | 0.34 | 0.62 | 64 / 251 GB | 0.982 |
| RTX PRO 6000 Max-Q | 56659799 | Japan | 0.258 | 0.31 | 0.83 | 32 / 92 GB | 0.997 |
| RTX PRO 6000 WS | 54250816 | Texas | 0.470 | 0.56 | 1.04 | 32 / 94 GB | 0.993 |
Bids at the minimum can be outbid at any time; an on-demand renter of the same machine also preempts the bid.
Some hosts charge $16-40/TB bandwidth (Estonia, Texas, Czechia, Maryland); most charge ~$2.67/TB.

Recommendation: day 1 (debugging) on demand, verified, e.g. 44111199 at ~$1.19/h all-in. On that box, measure
throughput and whether FlashCHORD resumes from a checkpoint. If it resumes, run the 20 trainings on interruptible
PRO 6000s (bid ~$0.25-0.45/h), about $10-25 for all 20 instead of ~$45 on demand. Benchmark Max-Q speed first.
