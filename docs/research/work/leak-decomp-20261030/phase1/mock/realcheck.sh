#!/bin/bash
# Real-code checks of pipeline/perc2.py on this CPU VM (2026-10-30, Phase-1 build), with local public data only:
#  (1) template switch: perc2's own D / MESH_DIR / scan_path / mesh_path (taken from its source by tools/leak_p1.py)
#      resolve every Phase-1 object with MESH_DIR unset, MESH_DIR='' and MESH_DIR=library_v3; the meshes are loaded
#      and compared (vertices, faces, extents, md5). The only change to perc2.py is the path /content -> $W/content.
#  (2) depth cache: perc2.py itself (paths remapped, a stub `torch` module since this VM has none) runs on ep11 with a
#      full-size depth cache whose frame 0 is the store cache's frame 0 (sparse file, sha256 checked): it must log
#      'depth ready 137' without entering the FoundationStereo branch, and leave the cache untouched. Without the cache
#      it must enter that branch (it fails there on this VM: no FoundationStereo). perc2 stops later (no stereo videos
#      or GPU here); only the depth stage is under test. Reads ep11.parquet only as perc2 does (object names).
# usage: realcheck.sh W (scratch dir) > out/realcheck.txt
set -u
W=$1; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; R=/home/user/v2d-track3
PY=$S/map/scoring/venv/bin/python; IN=$S/refine/in
rm -rf "${W:?}"; mkdir -p $W/content/t3/v $W/shim/torch $W/repo/pipeline $W/repo/tools
ln -s $S/hfds/track_3/public/mesh $W/content/t3/mesh; ln -s $S/map/scoring/t3/ep11.parquet $W/content/t3/
ln -s $S/hfds/track_3/public/meta/camera_calibration.json $W/content/t3/calib.json
sed "s#/content#$W/content#g" $R/pipeline/perc2.py > $W/repo/pipeline/perc2.py; cp $R/pipeline/det_rules.py $W/repo/pipeline/
cp $R/tools/leak_p1.py $W/repo/tools/; : > $W/shim/torch/__init__.py
echo "== perc2.py copy vs repo: $(diff $R/pipeline/perc2.py $W/repo/pipeline/perc2.py | grep -c '^>') changed lines, all /content -> $W/content:" \
     "$(diff $R/pipeline/perc2.py $W/repo/pipeline/perc2.py | grep '^>' | grep -vc "$W/content") other"
echo "== MESH_DIR uses in perc2.py:"; grep -n 'MESH_DIR\|mesh_path(\|scan_path(' $R/pipeline/perc2.py
echo; echo "== (1) template switch"
$PY -I - $W/repo/pipeline/perc2.py $R/meshes/library_v3 << 'EOF'
import hashlib, sys
sys.path.insert(0, sys.argv[1].rsplit('/pipeline/', 1)[0] + '/tools')
import trimesh, numpy as np
from leak_p1 import templates
p2, lib = sys.argv[1], sys.argv[2]
objs = ['white_pot', 'white_pot_lid', 'blue_cup', 'beige_cup', 'plastic_dish_rack', 'water_pitcher', 'mini_sweeper',
        'mini_dust_pan', 'wooden_piece_1', 'wooden_piece_2']
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()[:10]
res = {k: templates(p2, v, objs) for k, v in (('unset', None), ('empty', ''), ('lib', lib))}
D = res['unset'][0]; print('perc2 D =', D)
bad = 0
for o in objs:
    row = []
    for k in ('unset', 'empty', 'lib'):
        f = res[k][1][o]; m = trimesh.load(f, force='mesh')
        row.append((k, f.replace(D, '<D>').replace(lib, '<lib>'), md5(f), len(m.vertices), len(m.faces), np.round(m.extents * 100, 1).tolist()))
    s, e, l = row
    ok = s[1].startswith('<D>/mesh/') and e[1] == s[1] and l[1] == f'<lib>/{o}.glb' and s[2] != l[2]
    bad += not ok
    print(f'{o:18s} unset -> {s[1]:42s} md5 {s[2]} V {s[3]:7d} F {s[4]:7d} ext {s[5]} cm | empty -> same: {e[1] == s[1]}'
          f' | lib -> {l[1]:28s} md5 {l[2]} V {l[3]:6d} F {l[4]:6d} ext {l[5]} cm | {"OK" if ok else "UNEXPECTED"}')
print('template switch:', 'as expected for all objects' if not bad else f'{bad} UNEXPECTED')
EOF
echo; echo "== (2) depth cache reuse (real perc2.py, ep11)"
$PY -I - $IN/ep11/depth0.npy $W/out/ep11/depths_fs0.5.npy 137 << 'EOF'
import hashlib, os, sys
import numpy as np
from numpy.lib import format as F
d0 = np.load(sys.argv[1]); T = int(sys.argv[3]); os.makedirs(os.path.dirname(sys.argv[2]), exist_ok=True)
with open(sys.argv[2], 'wb') as f:                       # header + frame 0 + sparse zeros: the store cache's size
    F.write_array_header_1_0(f, dict(descr='<f4', fortran_order=False, shape=(T,) + d0.shape)); f.write(d0.astype('<f4').tobytes())
    f.truncate(f.tell() + (T - 1) * d0.size * 4)
D = np.load(sys.argv[2], mmap_mode='r')
print('cache', D.shape, os.path.getsize(sys.argv[2]), 'bytes; frame-0 sha256', hashlib.sha256(np.array(D[0]).tobytes()).hexdigest())
EOF
echo "expected (inputs.tsv): $(awk -F'\t' '$1 == 11 {print $5, "bytes; frame-0 sha256", $6}' $R/docs/research/work/leak-decomp-20261030/phase1/inputs.tsv)"
C=$W/out/ep11/depths_fs0.5.npy; s0=$(stat -c '%i %s %Y' $C); m0=$(md5sum < $C | cut -c1-12)
(cd $W && PYTHONPATH=$W/shim EP=11 OUT=$W/out/ep11 KF_MIN=120 SPLIT=public timeout 600 $PY $W/repo/pipeline/perc2.py) > $W/out/ep11.log 2>&1
echo "rc=$? (perc2 stops after the depth stage here: no stereo videos / GPU)"; grep -a '^\[' $W/out/ep11.log | head -4
echo "last error: $(grep -aE 'Error|error' $W/out/ep11.log | tail -1)"
echo "FoundationStereo branch entered: $(grep -ac FoundationStereo $W/out/ep11.log) traceback lines"
echo "cache stat before [$s0] after [$(stat -c '%i %s %Y' $C)]; md5 before $m0 after $(md5sum < $C | cut -c1-12)"
mkdir -p $W/out/ep11nc
(cd $W && PYTHONPATH=$W/shim EP=11 OUT=$W/out/ep11nc KF_MIN=120 SPLIT=public timeout 600 $PY $W/repo/pipeline/perc2.py) > $W/out/ep11nc.log 2>&1
echo "control without a cache: rc=$?; 'depth ready' lines $(grep -ac 'depth ready' $W/out/ep11nc.log);" \
     "$(grep -aE 'Error' $W/out/ep11nc.log | tail -1); traceback through the FoundationStereo branch:" \
     "$(grep -a 'perc2.py", line' $W/out/ep11nc.log | tail -1 | sed "s#$W#<W>#")"
