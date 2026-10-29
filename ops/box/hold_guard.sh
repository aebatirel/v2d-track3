#!/bin/bash
# Keep /content/HOLD fresh while any pipeline_ep.sh runs on this box (2026-10-20 night: several jobs started by hand
# on one box; a finishing job may remove the hold while another still runs). Stops when no pipeline is left; then the
# job that ends last releases the hold and the watchdog saves and destroys the box.
while pgrep -f '[p]ipeline_ep.sh' > /dev/null; do
  echo $(( $(date +%s) + 1800 )) > /content/HOLD
  sleep 20
done
