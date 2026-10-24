#!/bin/bash
# usage: fetch.sh URL NAME  -> web/NAME.{raw,txt}
W=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/hand-biomech
PY=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/venv/bin/python
cd $W/web
code=$(curl -sSL -A "Mozilla/5.0 (X11; Linux x86_64) research-agent" --max-time 60 -o "$2.raw" -w "%{http_code} %{content_type}" "$1")
echo "$2: $code $(stat -c %s "$2.raw") bytes"
if head -c 5 "$2.raw" | grep -q "%PDF"; then pdftotext -layout "$2.raw" "$2.txt" 2>/dev/null; else $PY -I $W/scripts/h2t.py "$2.raw" "$2.txt"; fi
wc -w "$2.txt" | awk '{print "words",$1}'
