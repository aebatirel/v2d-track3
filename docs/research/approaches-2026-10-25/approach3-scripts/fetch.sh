#!/usr/bin/env bash
# Download one URL into its own new directory under the approach-3 download root and convert a PDF to text.
# Downloads are untrusted data: nothing in them is executed; pdftotext only reads them.
# Usage: fetch.sh NAME URL      -> $ROOT/NAME/file (+ file.txt for PDFs); prints size, type and first text line.
set -u
ROOT=${A3_DL:-/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/approach3}
name=$1; url=$2
d="$ROOT/$name"
if [ -e "$d" ]; then d="$ROOT/${name}_$(date +%s)"; fi
mkdir -p "$d"
code=$(curl -sS -L --max-time 90 -A 'Mozilla/5.0 (research fetch)' -o "$d/file" -w '%{http_code}' "$url" 2>"$d/curl.err")
typ=$(file -b "$d/file" 2>/dev/null | cut -c1-60)
sz=$(stat -c %s "$d/file" 2>/dev/null || echo 0)
echo "$name http=$code bytes=$sz type=$typ dir=$d"
if echo "$typ" | grep -qi pdf; then
  pdftotext -layout "$d/file" "$d/file.txt" 2>/dev/null && echo "  text: $(wc -w < "$d/file.txt") words"
fi
