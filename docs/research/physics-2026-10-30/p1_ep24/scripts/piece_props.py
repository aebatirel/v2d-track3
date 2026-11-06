"""Exact mass properties of the uniform solid of a set of convex pieces (sum over pieces, parallel-axis theorem),
in the format make_assets.py --pieces reads (<obj>/inertia.json: com, inertia about the COM, mass, volume_cm3).
Usage: piece_props.py PIECES_DIR OUT_DIR --mass 0.3 [--compare R0_DIR]   (copies piece_*.obj and writes inertia.json)"""
import argparse, glob, json, os, shutil
import numpy as np, trimesh
ap = argparse.ArgumentParser(); ap.add_argument('pieces'); ap.add_argument('out'); ap.add_argument('--mass', type=float, default=0.3)
ap.add_argument('--compare', default=''); a = ap.parse_args()


def props(files, mass):
    V = 0.0; M1 = np.zeros(3); J = np.zeros((3, 3))           # J = second moment sum over pieces about the origin
    for f in files:
        m = trimesh.load(f, force='mesh'); mp = m.mass_properties          # density 1
        v = mp['volume']; c = mp['center_mass']; Ic = mp['inertia']         # Ic about the piece's COM
        V += v; M1 += v * c
        J += Ic + v * (np.dot(c, c) * np.eye(3) - np.outer(c, c))           # inertia about the origin
    com = M1 / V
    I0 = J - V * (np.dot(com, com) * np.eye(3) - np.outer(com, com))       # back to the union COM
    return dict(com=com.tolist(), inertia=(I0 * mass / V).tolist(), mass=mass, volume_cm3=round(V * 1e6, 3))


res = {}
for d in sorted(glob.glob(f'{a.pieces}/*/')):
    n = os.path.basename(d.rstrip('/')); fs = sorted(glob.glob(f'{d}/piece_*.obj'))
    if not fs:
        continue
    os.makedirs(f'{a.out}/{n}', exist_ok=True)
    for f in fs:
        shutil.copy(f, f'{a.out}/{n}/')
    p = props(fs, a.mass); json.dump(p, open(f'{a.out}/{n}/inertia.json', 'w'), indent=1); res[n] = p
    s = f'{n}: {len(fs)} pieces, volume {p["volume_cm3"]} cm3, com mm {np.round(np.array(p["com"]) * 1e3, 2).tolist()}, diag I {np.round(np.diag(p["inertia"]), 7).tolist()}'
    if a.compare and os.path.exists(f'{a.compare}/{n}/inertia.json'):
        q = json.load(open(f'{a.compare}/{n}/inertia.json'))
        s += f' | compare: com mm {np.round(np.array(q["com"]) * 1e3, 2).tolist()}, diag I {np.round(np.diag(q["inertia"]), 7).tolist()}, vol {q.get("volume_cm3")}'
    print(s)
