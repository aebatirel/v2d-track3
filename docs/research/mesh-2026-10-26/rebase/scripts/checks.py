"""G5 and the convexity / CoACD check of GATES.md for one delivered set folder.

  python -I checks.py SET_DIR SRC_ASSETS LIB_DIR FP_PIPELINE COACD1011 OUT.json

SET_DIR       the delivered folder (<obj>/piece_XX.obj)
SRC_ASSETS    the packed asset folder (urdf/ + mesh/) the reference names (e.g. refs/sf/ep20/assets)
LIB_DIR       library glbs (meshes/library_v3) for the make_assets route
FP_PIPELINE   focused-pascal's pipeline/ (make_assets.py, placement_carve.py)
Checks:
 1. route A, placement_carve.py assets SRC_ASSETS SET_DIR OUT: every mesh/ file other than the new col_XX.obj is
    byte-identical to SRC_ASSETS; each carved URDF equals the packed one with its <collision> blocks replaced (visual,
    inertial and the comment unchanged); other URDFs byte-identical;
 2. route B, make_assets.py LIB OUT --pieces SET_DIR: mesh/<o>/<o>.glb md5 equals the packed visual glb; the URDF
    <inertial> and <visual> blocks equal the packed URDF's;
 3. each piece: convex (vertex set = its hull's vertices) and coacd 1.0.11 at FlashCHORD's call (threshold 0.05,
    max_convex_hull -1, preprocess auto) returns one part whose hull volume is within 1 % of the piece's;
 4. md5 of the library / submission glbs (unchanged by this work).
"""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import trimesh

set_dir, src, lib, fp, coacd_t, out = sys.argv[1:7]
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()
objs = sorted(os.path.basename(d.rstrip('/')) for d in glob.glob(f'{set_dir}/*/') if glob.glob(f'{d}/piece_*.obj'))
rep = dict(set_dir=set_dir, src_assets=src, objects=objs, route_A={}, route_B={}, pieces={})
strip = lambda s: re.sub(r'\s*<collision>.*?</collision>', '', s, flags=re.S)
block = lambda s, t: re.search(rf'<{t}>.*?</{t}>', s, re.S).group(0)
td = tempfile.mkdtemp()
# route A
oa = f'{td}/A'
r = subprocess.run([sys.executable, '-I', f'{fp}/placement_carve.py', 'assets', src, set_dir, oa], capture_output=True, text=True)
rep['route_A']['stdout'] = r.stdout.strip()[-400:]; rep['route_A']['rc'] = r.returncode
same, diff = 0, []
for p in sorted(glob.glob(f'{src}/**/*', recursive=True)):
    if os.path.isfile(p):
        q = p.replace(src, oa, 1)
        if p.endswith('.urdf') and os.path.basename(p)[:-11] in objs:
            continue
        (same := same + 1) if os.path.exists(q) and md5(p) == md5(q) else diff.append(p)
rep['route_A']['files_identical'] = same; rep['route_A']['files_differ'] = diff
for o in objs:
    a, b = open(f'{src}/urdf/{o}_rigid.urdf').read(), open(f'{oa}/urdf/{o}_rigid.urdf').read()
    n = len(sorted(glob.glob(f'{set_dir}/{o}/piece_*.obj')))
    cols = re.findall(r'<mesh filename="([^"]*)"', b)
    rep['route_A'][o] = dict(collisions=b.count('<collision>'), pieces=n, non_collision_equal=strip(a).strip() == strip(b).strip(),
                             inertial_equal=block(a, 'inertial') == block(b, 'inertial'), visual_equal=block(a, 'visual') == block(b, 'visual'),
                             col_files_equal_pieces=all(md5(f'{oa}/mesh/{o}/col_{k:02d}.obj') == md5(p) for k, p in
                                                        enumerate(sorted(glob.glob(f'{set_dir}/{o}/piece_*.obj')))),
                             urdf_md5=md5(f'{oa}/urdf/{o}_rigid.urdf'), packed_urdf_md5=md5(f'{src}/urdf/{o}_rigid.urdf'),
                             visual_glb_md5=md5(f'{oa}/mesh/{o}/{o}.glb'), packed_visual_glb_md5=md5(f'{src}/mesh/{o}/{o}.glb'))
    shutil.copy(f'{oa}/urdf/{o}_rigid.urdf', f'{os.path.dirname(out)}/{o}_rigid.route_A.urdf')
# route B
lb, ob = f'{td}/lib', f'{td}/B'
os.makedirs(lb)
for o in objs:
    shutil.copy(f'{lib}/{o}.glb', lb)
r = subprocess.run([sys.executable, '-I', f'{fp}/make_assets.py', lb, ob, '--pieces', set_dir], capture_output=True, text=True)
rep['route_B']['stdout'] = r.stdout.strip()[-400:]; rep['route_B']['rc'] = r.returncode
for o in objs:
    a, b = open(f'{src}/urdf/{o}_rigid.urdf').read(), open(f'{ob}/urdf/{o}_rigid.urdf').read()
    rep['route_B'][o] = dict(visual_glb_md5=md5(f'{ob}/mesh/{o}/{o}.glb'), packed_visual_glb_md5=md5(f'{src}/mesh/{o}/{o}.glb'),
                             inertial_equal=block(a, 'inertial') == block(b, 'inertial'), visual_equal=block(a, 'visual') == block(b, 'visual'),
                             collisions=b.count('<collision>'))
# pieces
child = r'''
import sys, json, numpy as np, trimesh
sys.path.insert(0, sys.argv[1]); import coacd, importlib.metadata as md
coacd.set_log_level("error"); res = []
for p in sys.argv[2:]:
    m = trimesh.load(p, force="mesh")
    parts = coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(m.vertices, np.float64), np.ascontiguousarray(m.faces, np.int64)),
                            threshold=0.05, max_convex_hull=-1, preprocess_mode="auto")
    v = sum(trimesh.convex.convex_hull(np.asarray(a)).volume for a, b in parts)
    res.append(dict(piece=p, parts=len(parts), vol_ratio=v / trimesh.convex.convex_hull(m.vertices).volume))
print(json.dumps(dict(version=md.version("coacd"), res=res)))
'''
for o in objs:
    P = sorted(glob.glob(f'{set_dir}/{o}/piece_*.obj'))
    conv = []
    for p in P:
        V = np.asarray(trimesh.load(p, force='mesh').vertices)
        h = trimesh.convex.convex_hull(V)
        conv.append(bool(len(h.vertices) == len(np.unique(np.round(V, 12), axis=0))))
    r = subprocess.run([sys.executable, '-I', '-c', child, coacd_t] + P, capture_output=True, text=True)
    cj = json.loads(r.stdout.strip().splitlines()[-1])
    rep['pieces'][o] = dict(n=len(P), convex_all=all(conv), coacd=cj['version'],
                            coacd_one_part_all=all(x['parts'] == 1 for x in cj['res']),
                            coacd_vol_ratio_min=round(min(x['vol_ratio'] for x in cj['res']), 4),
                            coacd_vol_ratio_max=round(max(x['vol_ratio'] for x in cj['res']), 4),
                            not_one_part=[os.path.basename(x['piece']) for x in cj['res'] if x['parts'] != 1])
rep['library_md5'] = {p: md5(p) for p in sorted(glob.glob('/home/user/v2d-track3/meshes/library_*/white_pot.glb') +
                                                glob.glob('/home/user/v2d-track3/meshes/library_*/water_pitcher.glb'))}
A = rep['route_A']; B = rep['route_B']; Pc = rep['pieces']
rep['G5_pass'] = bool(A['rc'] == 0 and not A['files_differ'] and B['rc'] == 0 and
                      all(A[o]['non_collision_equal'] and A[o]['inertial_equal'] and A[o]['visual_equal'] and A[o]['col_files_equal_pieces']
                          and A[o]['collisions'] == A[o]['pieces'] and A[o]['visual_glb_md5'] == A[o]['packed_visual_glb_md5']
                          and B[o]['visual_glb_md5'] == B[o]['packed_visual_glb_md5'] and B[o]['visual_equal'] for o in objs))
rep['route_B_inertial_equal_all'] = bool(all(B[o]['inertial_equal'] for o in objs))
rep['convex_coacd_pass'] = bool(all(Pc[o]['convex_all'] and Pc[o]['coacd_one_part_all'] for o in objs))
json.dump(rep, open(out, 'w'), indent=1)
print(json.dumps(dict(G5_pass=rep['G5_pass'], route_B_inertial_equal=rep['route_B_inertial_equal_all'],
                      convex_coacd_pass=rep['convex_coacd_pass'], pieces=Pc, A={o: A[o] for o in objs}, B={o: B[o] for o in objs},
                      A_files=(A['files_identical'], A['files_differ']))))
shutil.rmtree(td)
