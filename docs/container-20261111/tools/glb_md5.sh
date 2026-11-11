#!/bin/bash
# md5 of every .glb blob reachable from any remote branch tip, with one path per blob
cd /home/user/v2d-track3
for b in $(git branch -r | grep -v HEAD); do git ls-tree -r $b | awk '$4 ~ /\.glb$/ {print $3" "$4}'; done | sort -u -k1,1 > /tmp/claude-0/-home-user-v2d-track3/40ae8bef-a6ac-5623-abee-9e3e721c7845/scratchpad/container/dl/glb_blobs.txt
while read -r sha path; do echo "$(git cat-file blob $sha | md5sum | cut -c1-32) $sha $path"; done < /tmp/claude-0/-home-user-v2d-track3/40ae8bef-a6ac-5623-abee-9e3e721c7845/scratchpad/container/dl/glb_blobs.txt
