"""verify_scorer test 4: can the hidden host geometry be the full-resolution public scans within the kit's 16 MB limit?
The kit decodes the host payload with _decode_archive(text, 16_000_000): the sum of the npz members' uncompressed sizes
must be <= 16e6 bytes and the base64 text <= 32e6 chars. One payload holds all objects (names, v{i}, f{i}, anchor{i},
points{i}, axis{i}, order{i}). Here: the size of the 10 public scans as stored (triangle soup) and welded, in float64/int64
and float32/int32, plus an estimate for the 11th object (wooden_spoon, no public scan) and for points (1000 x 3 float64).
Usage: python -I t4_budget.py OUT.json"""
import json, sys, os, io, base64
import numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_scorer')
from vs_core import T3D, scan_path, load_vf

objs = sorted(os.listdir(f'{T3D}/mesh'))
rows, tot = {}, dict(soup64=0, weld64=0, weld32=0, weld32_u16=0)
welded = {}
for n in objs:
    v, f = load_vf(scan_path(n))
    m = trimesh.Trimesh(v, f, process=False); m.merge_vertices(); m.remove_unreferenced_vertices()
    wv, wf = np.asarray(m.vertices), np.asarray(m.faces)
    welded[n] = (wv.astype(np.float32), wf.astype(np.int32))
    r = dict(soup_vertices=len(v), faces=len(f), welded_vertices=len(wv),
             soup64=v.size * 8 + f.size * 8, weld64=wv.size * 8 + wf.size * 8, weld32=wv.size * 4 + wf.size * 4)
    rows[n] = r
    for k in ('soup64', 'weld64', 'weld32'):
        tot[k] += r[k]
extra = 11 * (1000 * 3 * 8 + 3 * 8 + 3 * 8 + 8)          # points, anchor, axis, order for 11 objects
spoon = int(np.mean([rows[n]['weld32'] for n in rows]))   # 11th object (no public scan): mean welded float32 size
res = dict(per_object=rows, totals_10_public=tot, extra_points_etc=extra, spoon_estimate_weld32=spoon,
           total_11_weld32=tot['weld32'] + extra + spoon, total_11_weld64=tot['weld64'] + extra + int(spoon * 2),
           limit=16_000_000)
# actual npz with float32/int32 welded meshes of the 10 public scans: uncompressed member sizes and base64 length
buf = io.BytesIO()
np.savez_compressed(buf, **{f'v{i}': welded[n][0] for i, n in enumerate(objs)}, **{f'f{i}': welded[n][1] for i, n in enumerate(objs)})
import zipfile
zs = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
res['npz_weld32_10_public'] = dict(uncompressed=sum(i.file_size for i in zs.infolist()), b64_len=len(base64.b64encode(buf.getvalue())))
json.dump(res, open(sys.argv[1], 'w'), indent=1)
print(json.dumps(res, indent=1))
