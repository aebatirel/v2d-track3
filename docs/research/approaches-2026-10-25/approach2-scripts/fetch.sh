#!/bin/bash
# fetch URL -> lit/NAME.html and lit/NAME.txt (tags stripped)
D=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/approach2
curl -sSL -m 60 -A "Mozilla/5.0" -o "$D/lit/$1.html" "$2" -w "$1 %{http_code} %{size_download}\n"
/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/venv/bin/python -I "$D/tools/strip.py" "$D/lit/$1.html" > "$D/lit/$1.txt"
