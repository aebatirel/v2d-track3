#!/bin/bash
# Vast on-start script. ops/vast.sh create sends this file inline (Vast's limit is 4048 characters).
# Account-level Vast env vars (set once by the owner): HF_TOKEN (write, our store repo only), GH_TOKEN (read, this repo).
# Per-instance env from ops/vast.sh: RUN_ID, V2D_COMMIT, JOB_B64, V2D_IMAGE [, ENV_SNAPSHOT, HF_STORE, SETUP, RESUME_FROM].
# Vast adds CONTAINER_ID and CONTAINER_API_KEY (instance-scoped key, used to self-destroy).
for v in HF_TOKEN GH_TOKEN HF_STORE RUN_ID V2D_COMMIT JOB_B64 ENV_SNAPSHOT SETUP RESUME_FROM V2D_IMAGE V2D_REPO \
         CONTAINER_ID CONTAINER_API_KEY; do
  [ -n "${!v:-}" ] && declare -p $v | sed 's/^declare -x/export/'
done > /etc/v2d_env
chmod 600 /etc/v2d_env
grep -q v2d_env /root/.bashrc 2> /dev/null || echo '. /etc/v2d_env' >> /root/.bashrc   # SSH shells see the env too
. /etc/v2d_env
mkdir -p /workspace && { [ -e /content ] || ln -s /workspace /content; }
cd /workspace
V=https://console.vast.ai/api/v0/instances/$CONTAINER_ID/; A="Authorization: Bearer $CONTAINER_API_KEY"
die() {  # label the instance, then self-destroy in 20 min unless /workspace/HOLD exists (lets the agent debug)
  echo "onstart: $1"
  curl -s -X PUT -H "$A" -H 'Content-Type: application/json' -d "{\"label\":\"${RUN_ID:-?} $1\"}" $V > /dev/null
  setsid nohup bash -c "sleep 1200; [ -e /workspace/HOLD ] || curl -s -X DELETE -H '$A' $V" > /dev/null 2>&1 < /dev/null &
  exit 1
}
R=https://github.com/${V2D_REPO:-aebatirel/v2d-track3}.git
H="http.extraheader=Authorization: Basic $(printf 'x-access-token:%s' "$GH_TOKEN" | base64 -w0)"
[ -d v2d-track3/.git ] || git -c "$H" clone -q $R v2d-track3 || die CLONE-FAIL
git -C v2d-track3 -c "$H" fetch -q origin "$V2D_COMMIT" && git -C v2d-track3 checkout -q "$V2D_COMMIT" || die CHECKOUT-FAIL
setsid nohup bash v2d-track3/ops/box/run_job.sh >> /workspace/run_job.log 2>&1 < /dev/null &
echo "onstart: started run_job.sh for ${RUN_ID:-?} at $(date -u +%FT%TZ)"
