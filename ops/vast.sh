#!/bin/bash
# Vast.ai control for the orchestrating session (Claude cloud session or the owner's Mac). Written 2026-10-20, not yet
# run against the authenticated API; the public offers query was tested.
# HTTP goes through curl only: Vast answered python urllib with HTTP 403.
# Auth: in a Claude Code cloud session the VAST_API_KEY network secret makes the proxy add
# "Authorization: Bearer <key>" for console.vast.ai, so nothing is needed here. Elsewhere, export VAST_API_KEY.
#
#   ops/vast.sh offers [gpu_name|any] [on-demand|bid]   cheapest compliant offers (default "RTX PRO 6000 WS",
#                                                   on-demand); "any" = cheapest GPU of any kind (for the smoke box)
#   ops/vast.sh create <offer_id> <run_id> '<job command>' [bid_price]
#        optional env: V2D_COMMIT (default: origin/main), ENV_SNAPSHOT, HF_STORE, SETUP=none, RESUME_FROM, IMAGE, DISK
#   ops/vast.sh show                                our instances: id, label, status, $/h, ssh
#   ops/vast.sh logs <instance_id> [lines]          container log tail (onstart output)
#   ops/vast.sh label <instance_id> <text>
#   ops/vast.sh destroy <instance_id>               irreversible: deletes the instance and its disk
#   ops/vast.sh ssh-key <public_key_file>           add a key to the account (applies to new instances)
#   ops/vast.sh attach-key <instance_id> <public_key_file>
#   ops/vast.sh exec <run_id> '<bash command>' [timeout_s]   run a command on the box over HTTPS (SSH replacement:
#                                                   rexec.py behind a Cloudflare tunnel; URL and token from the HF store)
#   Settings can also lead the arguments, e.g. ops/vast.sh SETUP=none DISK=40 create ..., so that one permission rule
#   "Bash(ops/vast.sh *)" in .claude/settings.json covers every call.
set -euo pipefail
API=https://console.vast.ai/api/v0
HERE=$(cd "$(dirname "$0")" && pwd)
while [[ ${1:-} =~ ^(V2D_COMMIT|ENV_SNAPSHOT|HF_STORE|SETUP|RESUME_FROM|IMAGE|DISK)=[^\ ]*$ ]]; do export "$1"; shift; done
. "$HERE/config.env"
AUTH=(); [ -n "${VAST_API_KEY:-}" ] && AUTH=(-H "Authorization: Bearer $VAST_API_KEY")
req() { curl -sS ${AUTH[@]+"${AUTH[@]}"} -H 'Content-Type: application/json' "$@"; }   # bash 3.2-safe

case ${1:-} in
offers)
  GPU=${2:-RTX PRO 6000 WS}; TYPE=${3:-on-demand}
  Q=$(python3 -c 'import json,sys; q={"rentable":{"eq":True},"rented":{"eq":False},"num_gpus":{"eq":1},"type":sys.argv[2],
      "limit":500}
if sys.argv[1] == "any": q.update(verified={"eq":True}, cuda_max_good={"gte":13.0}, order=[["dph_total","asc"]], limit=64)
else: q["gpu_name"] = {"eq": sys.argv[1]}
print(json.dumps(q))' "$GPU" "$TYPE")
  OF=$(mktemp); trap 'rm -f "$OF"' EXIT     # a file, not an env var: the market list can exceed ARG_MAX
  curl -sS -X POST $API/bundles/ -H 'Content-Type: application/json' -d "$Q" > "$OF"
  OFFERS_FILE=$OF python3 - "$TYPE" "$DISK" "$GPU" <<'EOF'
import json, os, sys
bid = sys.argv[1] == "bid"; disk = float(sys.argv[2]); small = sys.argv[3] == "any"
ok = lambda o: (o.get("cuda_max_good") or 0) >= 13.0 and o.get("verification") == "verified" \
    and (o.get("inet_down") or 0) >= 300 and (o.get("reliability2") or 0) >= (0.97 if small else 0.98) and (small or (
    (o.get("cpu_cores_effective") or 0) >= 16 and (o.get("cpu_ram") or 0) >= 64000 and (o.get("disk_space") or 0) >= disk))
rows = []
for o in json.load(open(os.environ["OFFERS_FILE"]))["offers"]:
    if not ok(o): continue
    gpu = o["min_bid"] if bid else o["dph_total"]
    store = (o.get("storage_cost") or 0) * disk / 720          # $/GB/month -> $/h
    rows.append((gpu + store, o, gpu, store))
print("offer_id  all-in$/h  gpu$/h  disk$/h  cpu  ramGB  diskGB  down/up Mbps  $/TB down  rel    cuda  gpu / location")
for tot, o, gpu, store in sorted(rows, key=lambda r: r[0])[:15]:
    print(f"{o['id']:<9} {tot:9.3f} {gpu:7.3f} {store:7.3f} {o['cpu_cores_effective']:4.0f} {o['cpu_ram']/1024:6.0f}"
          f" {o['disk_space']:7.0f} {o['inet_down']:6.0f}/{o['inet_up']:<6.0f} {o.get('internet_down_cost_per_tb') or 0:9.2f}"
          f"  {o['reliability2']:.3f} {o['cuda_max_good']:5.1f}  {o['gpu_name']} / {o.get('geolocation')}")
print(f"{len(rows)} compliant offer(s)")
EOF
  ;;
create)
  OFFER=$2; RUN_ID=$3; JOB=$4; PRICE=${5:-}
  COMMIT=${V2D_COMMIT:-$(git -C "$HERE/.." rev-parse origin/main)}
  ONSTART="$HERE/box/onstart.sh"; [ $(wc -c < "$ONSTART") -le 4048 ] || { echo "onstart.sh > 4048 chars"; exit 1; }
  BODY=$(python3 - "$IMAGE" "$DISK" "$RUN_ID" "$JOB" "$COMMIT" "${ENV_SNAPSHOT:-}" "${HF_STORE:-}" "$PRICE" "$ONSTART" \
                   "${SETUP:-}" "${RESUME_FROM:-}" <<'EOF'
import base64, json, sys
image, disk, run_id, job, commit, snap, store, price, onstart, setup, resume = sys.argv[1:]
env = {"RUN_ID": run_id, "V2D_COMMIT": commit, "JOB_B64": base64.b64encode(job.encode()).decode(), "V2D_IMAGE": image}
if snap: env["ENV_SNAPSHOT"] = snap
if store: env["HF_STORE"] = store
if setup: env["SETUP"] = setup
if resume: env["RESUME_FROM"] = resume
for k, v in env.items():
    assert all(c not in v for c in " '\"\\"), f"{k} must not contain spaces or quotes"
b = {"client_id": "me", "image": image, "disk": float(disk), "label": run_id, "runtype": "ssh",
     "env": " ".join(f"-e {k}={v}" for k, v in env.items()), "onstart": open(onstart).read(), "cancel_unavail": True}
if price: b["price"] = float(price)
print(json.dumps(b))
EOF
)
  echo "creating $RUN_ID on offer $OFFER (image $IMAGE, disk $DISK GB, commit ${COMMIT:0:7}${PRICE:+, bid \$$PRICE/h})" >&2
  req -X PUT "$API/asks/$OFFER/" -d "$BODY"; echo
  ;;
show)
  INST=$(req "https://console.vast.ai/api/v1/instances/?limit=25") python3 - <<'EOF'
import json, os
d = json.loads(os.environ["INST"])
for i in d.get("instances", []):
    p = ((i.get("ports") or {}).get("22/tcp") or [{}])[0]
    direct = f"ssh -p {p['HostPort']} root@{i.get('public_ipaddr')}" if p.get("HostPort") else "-"
    print(f"{i['id']}  {i.get('label')}  {i.get('actual_status')}/{i.get('intended_status')}  ${i.get('dph_total') or 0:.3f}/h"
          f"  {i.get('gpu_name')}  proxy: ssh -p {i.get('ssh_port')} root@{i.get('ssh_host')}  direct: {direct}")
print(f"{len(d.get('instances', []))} instance(s)")
EOF
  ;;
logs)
  URL=$(req -X PUT "$API/instances/request_logs/$2/" -d "{\"tail\": \"${3:-200}\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("result_url",""))')
  [ -n "$URL" ] || { echo "no log url"; exit 1; }
  for i in 1 2 3 4 5 6; do curl -sf "$URL" && exit 0; sleep 5; done; echo "log not ready: $URL"
  ;;
label)   req -X PUT "$API/instances/$2/" -d "$(python3 -c 'import json,sys; print(json.dumps({"label": sys.argv[1]}))' "$3")"; echo ;;
destroy) req -X DELETE "$API/instances/$2/"; echo ;;
ssh-key) req -X POST "$API/ssh/" -d "$(python3 -c 'import json,sys; print(json.dumps({"ssh_key": open(sys.argv[1]).read().strip()}))' "$2")"; echo ;;
attach-key) req -X POST "$API/instances/$2/ssh/" -d "$(python3 -c 'import json,sys; print(json.dumps({"ssh_key": open(sys.argv[1]).read().strip()}))' "$3")"; echo ;;
exec)
  # The huggingface.co network secret (or HF_TOKEN) authorises the read of the private store.
  HFA=(); [ -n "${HF_TOKEN:-}" ] && HFA=(-H "Authorization: Bearer $HF_TOKEN")
  ACC=$(curl -sSfL ${HFA[@]+"${HFA[@]}"} "https://huggingface.co/datasets/$HF_STORE/resolve/main/access/$2.json") \
    || { echo "no access record for $2 in $HF_STORE (tunnel not up yet?)"; exit 1; }
  URL=$(echo "$ACC" | python3 -c 'import json,sys; print(json.load(sys.stdin)["url"])')
  TOK=$(echo "$ACC" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
  curl -sSf -m $(( ${4:-120} + 30 )) -X POST -H "X-Token: $TOK" -H "X-Timeout: ${4:-120}" --data-binary "$3" "$URL/exec"
  ;;
*) sed -n '2,25p' "$0"; exit 1 ;;
esac
