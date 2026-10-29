#!/bin/bash
# Start rexec.py behind a Cloudflare quick tunnel and publish {url, token} to the private HF store at
# access/<RUN_ID>.json, so the agent can run commands over HTTPS (`ops/vast.sh exec`). Written 2026-10-20.
# Started in the background by run_job.sh; set REXEC=0 to skip. Log: /content/tunnel.log.
. /content/v2d-track3/ops/box/lib.sh
set -u
[ -s /root/.rexec_token ] || { umask 077; openssl rand -hex 24 > /root/.rexec_token; }
setsid nohup python3 $OPS/rexec.py 8765 >> /content/rexec.log 2>&1 < /dev/null &
CF=/usr/local/bin/cloudflared
[ -x $CF ] || curl -sfL -o $CF https://github.com/cloudflare/cloudflared/releases/download/2026.9.1/cloudflared-linux-amd64 \
  || curl -sfL -o $CF https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x $CF || { log "tunnel: cloudflared download FAILED"; exit 1; }
setsid nohup $CF tunnel --no-autoupdate --url http://127.0.0.1:8765 > /content/cloudflared.log 2>&1 < /dev/null &
for i in $(seq 60); do
  URL=$(grep -aoE 'https://[a-z0-9-]+\.trycloudflare\.com' /content/cloudflared.log | head -1)
  [ -n "$URL" ] && break; sleep 2
done
[ -n "$URL" ] || { log "tunnel: no quick-tunnel URL after 120 s (see cloudflared.log)"; exit 1; }
umask 077; J=/root/rexec_access.json
python3 -c 'import json,sys; print(json.dumps({"url": sys.argv[1], "token": open("/root/.rexec_token").read().strip(),
            "instance": sys.argv[2]}))' "$URL" "${CONTAINER_ID:-?}" > $J
hf upload "$HF_STORE" $J access/${RUN_ID}.json --repo-type dataset --commit-message "access $RUN_ID" > /dev/null \
  && log "tunnel: TUNNEL-OK $URL (token in store access/${RUN_ID}.json)" || log "tunnel: access upload FAILED"
