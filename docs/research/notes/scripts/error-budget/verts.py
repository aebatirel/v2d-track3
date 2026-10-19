"""AUC point-set approximations: 500 points on a box surface whose surface second
moments match the URDF inertia (uniform-surface estimate, m=0.3 kg). Real mesh samples
for the two locally available GLBs (white_pot, white_pot_lid) are used only to validate."""
import json, re, struct, glob, os
import numpy as np
from scipy.optimize import least_squares
from common import PUB

M = 0.3


def urdf_inertia(name):
    txt = open(f"{PUB}/urdf/{name}_rigid.urdf").read()
    inert = re.search(r"<inertial>(.*?)</inertial>", txt, re.S).group(1)
    com = np.array([float(x) for x in re.search(r'origin xyz="([^"]+)"', inert).group(1).split()])
    g = {k: float(v) for k, v in re.findall(r'(i[xyz]{2})="([^"]+)"', inert)}
    I = np.array([[g["ixx"], g["ixy"], g["ixz"]], [g["ixy"], g["iyy"], g["iyz"]], [g["ixz"], g["iyz"], g["izz"]]])
    return com, I


def second_moments(I):
    # surface covariance C = E[v v^T] about COM: I = m (tr(C) Id - C)
    tr = np.trace(I) / (2 * M)
    return tr * np.eye(3) - I / M


def box_surface_m2(h):
    a, b, c = h
    A = np.array([b*c, a*c, a*b])  # face areas (per 4) for faces normal to x,y,z
    tot = A.sum()
    out = []
    for k in range(3):
        on = A[k] * h[k]**2  # faces normal to axis k: coordinate == +-h_k
        off = (tot - A[k]) * h[k]**2 / 3
        out.append((on + off) / tot)
    return np.array(out)


def box_points(name, n=500, seed=0):
    com, I = urdf_inertia(name)
    C = second_moments(I)
    w, V = np.linalg.eigh(C)
    w = np.maximum(w, 1e-8)
    sol = least_squares(lambda h: box_surface_m2(np.abs(h)) / w - 1, np.sqrt(3 * w)).x
    h = np.abs(sol)
    rng = np.random.default_rng(seed)
    A = np.array([h[1]*h[2], h[0]*h[2], h[0]*h[1]])
    face = rng.choice(3, size=n, p=A / A.sum())
    u = rng.uniform(-1, 1, (n, 3)) * h
    sign = rng.choice([-1, 1], n)
    u[np.arange(n), face] = sign * h[face]
    return u @ V.T + com, h, V


def glb_points(name, n=500, seed=0):
    path = f"{PUB}/mesh/{name}/{name}.glb"
    b = open(path, "rb").read()
    L = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + L]); off = 20 + L
    bl = struct.unpack("<I", b[off:off + 4])[0]; binb = b[off + 8: off + 8 + bl]
    prim = j["meshes"][0]["primitives"][0]

    def acc(i, dt, k):
        a = j["accessors"][i]; bv = j["bufferViews"][a["bufferView"]]
        s = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        return np.frombuffer(binb, dtype=dt, count=a["count"] * k, offset=s).reshape(-1, k)
    v = acc(prim["attributes"]["POSITION"], np.float32, 3).astype(np.float64)
    f = acc(prim["indices"], np.uint32, 1).reshape(-1, 3)
    a_, b_, c_ = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b_ - a_, c_ - a_), axis=1)
    rng = np.random.default_rng(seed)
    ch = rng.choice(len(f), size=n, p=area / area.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)[:, None]
    return (1 - s) * a_[ch] + s * (1 - r2[:, None]) * b_[ch] + s * r2[:, None] * c_[ch]


def vertex_table(names, mode="box"):
    out = {}
    for nm in names:
        if mode == "mesh" and os.path.exists(f"{PUB}/mesh/{nm}/{nm}.glb"):
            out[nm] = glb_points(nm)
        else:
            out[nm] = box_points(nm)[0]
    return out


if __name__ == "__main__":
    names = sorted(os.path.basename(p)[:-11] for p in glob.glob(f"{PUB}/urdf/*_rigid.urdf"))
    for nm in names:
        P, h, V = box_points(nm)
        r = np.linalg.norm(P, axis=1)
        print(f"{nm:20s} box full dims cm {np.round(2*h*100,1)}  mean|v| {r.mean()*100:.1f} cm  rms {np.sqrt((r**2).mean())*100:.1f} cm")
    for nm in ["white_pot", "white_pot_lid"]:
        G = glb_points(nm, 20000)
        r = np.linalg.norm(G, axis=1)
        print(f"MESH {nm}: centroid cm {np.round(G.mean(0)*100,2)} m2 diag cm2 {np.round(np.diag(np.cov(G.T, bias=True))*1e4,1)} "
              f"vs urdf {np.round(np.diag(second_moments(urdf_inertia(nm)[1]))*1e4,1)}; E|v| {r.mean()*100:.1f} rms {np.sqrt((r**2).mean())*100:.1f}")
