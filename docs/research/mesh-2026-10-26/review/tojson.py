import sys, os, json, base64, numpy as np, trimesh
src, out = sys.argv[1], sys.argv[2]
tot = 0
for f in sorted(os.listdir(src)):
    if not f.endswith('.glb'): continue
    m = trimesh.load(os.path.join(src, f), force='mesh')
    V = np.asarray(m.vertices, dtype=np.float64); F = np.asarray(m.faces, dtype=np.int64)
    lo = V.min(0); span = np.maximum(V.max(0) - lo, 1e-9)
    q = np.round((V - lo) / span * 65535).astype('<u2')
    idx = F.astype('<u2') if len(V) < 65536 else F.astype('<u4')
    d = dict(n_v=int(len(V)), n_f=int(len(F)), min=lo.tolist(), span=span.tolist(),
             v=base64.b64encode(q.tobytes()).decode(), i=base64.b64encode(idx.tobytes()).decode(), it='u16' if idx.dtype == np.uint16 else 'u32')
    p = os.path.join(out, f[:-4] + '.json'); json.dump(d, open(p, 'w'), separators=(',', ':'))
    tot += os.path.getsize(p); print(f, len(V), len(F), os.path.getsize(p))
print('total', tot)
