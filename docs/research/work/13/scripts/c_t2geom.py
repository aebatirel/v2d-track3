"""Stage C: fetch ONLY the geometry (POSITION + indices) of public Track 2 scans by HTTP range requests, using the GLB
JSON headers cached by note 14 (work/14/t2/glbhead/<name>.head), and test whether the stored frame is a (permuted) R1
frame: area-weighted surface centroid at the origin and surface covariance diagonal. Saves work/13/t2/<name>.npz and
appends one JSON line per object to out/c_t2geom.jsonl.  Usage: c_t2geom.py name [name ...]"""
import sys, os, json, struct, subprocess, numpy as np
HEAD = "/Users/aebatirel/Documents/Code/v2d-research/work/14/t2/glbhead"
URL = "https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_2/tier_1_multiview_caption/mesh"
D = "/Users/aebatirel/Documents/Code/v2d-research/work/13/t2"; os.makedirs(D, exist_ok=True)
OUT = "/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c_t2geom.jsonl"
CT = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC3": 3}


def fetch(name, a0, a1):
    p = f"{D}/{name}_{a0}_{a1}.bin"
    if not os.path.exists(p) or os.path.getsize(p) != a1 - a0 + 1:
        subprocess.run(["curl", "-sSL", "-m", "300", "-r", f"{a0}-{a1}", f"{URL}/{name}/{name}.glb", "-o", p + ".part"], check=True)
        os.replace(p + ".part", p)
    return open(p, "rb").read()


def load(name):
    npz = f"{D}/{name}.npz"
    if os.path.exists(npz):
        z = np.load(npz); return z["V"], z["F"]
    b = open(f"{HEAD}/{name}.head", "rb").read(); L = struct.unpack("<I", b[12:16])[0]; g = json.loads(b[20:20 + L])
    bin0 = 20 + L + 8
    Vs, Fs, off = [], [], 0
    for m in g["meshes"]:
        for pr in m["primitives"]:
            arrs = []
            for acc in (pr["attributes"]["POSITION"], pr["indices"]):
                a = g["accessors"][acc]; bv = g["bufferViews"][a["bufferView"]]
                start = bin0 + bv.get("byteOffset", 0) + a.get("byteOffset", 0)
                n = a["count"] * NC[a["type"]] * np.dtype(CT[a["componentType"]]).itemsize
                arrs.append(np.frombuffer(fetch(name, start, start + n - 1), dtype=CT[a["componentType"]]).reshape(-1, NC[a["type"]]))
            V = arrs[0].astype(np.float64); F = arrs[1].reshape(-1, 3).astype(np.int64)
            Vs.append(V); Fs.append(F + off); off += len(V)
    V, F = np.concatenate(Vs), np.concatenate(Fs)
    np.savez_compressed(npz, V=V, F=F)
    for f in os.listdir(D):
        if f.startswith(name + "_") and f.endswith(".bin"):
            os.remove(os.path.join(D, f))
    return V, F


def h2(a, b, c): return a * a + b * b + c * c + a * b + a * c + b * c
def h3(a, b, c): return a ** 3 + b ** 3 + c ** 3 + a * a * b + a * a * c + b * b * a + b * b * c + c * c * a + c * c * b + a * b * c


def stats(V, F):
    T = V[F]; area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); A = area.sum()
    s = T.sum(1); c = (area[:, None] * s / 3).sum(0) / A
    M2 = (sum(np.einsum("n,ni,nj->ij", area, T[:, k], T[:, k]) for k in range(3)) + np.einsum("n,ni,nj->ij", area, s, s)) / 12 / A
    C = M2 - np.outer(c, c)
    sd = np.sqrt(np.diag(C)); corr = C / np.outer(sd, sd)
    w, E = np.linalg.eigh(C)
    dev = [float(np.degrees(np.arccos(min(1, abs(E[:, i] @ np.eye(3)[:, int(np.argmax(np.abs(E[:, i])))]))))) for i in range(3)]
    sk = []
    for i in range(3):
        f = T[:, :, i] - c[i]
        sk.append(float((area * h3(*f.T) / 10).sum() / A / C[i, i] ** 1.5))
    return dict(centroid_mm=(1000 * c).round(2).tolist(), sd_mm=(1000 * sd).round(1).tolist(),
                max_offdiag_corr=float(np.max(np.abs(corr - np.diag(np.diag(corr))))), eig_axis_dev_deg=np.round(dev, 3).tolist(),
                order_sd=[int(i) for i in np.argsort(sd)], skew_stored=np.round(sk, 4).tolist(), nV=int(len(V)), nF=int(len(F)), area_m2=float(A))


if __name__ == "__main__":
    for name in sys.argv[1:]:
        V, F = load(name)
        S = stats(V, F); S["name"] = name
        with open(OUT, "a") as f:
            f.write(json.dumps(S) + "\n")
        print(json.dumps(S), flush=True)
