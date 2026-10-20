"""Read only the JSON chunk of each Track 2 GLB (HTTP range) to get POSITION accessor min/max = bbox."""
import json, os, struct, subprocess, sys
D = os.path.dirname(os.path.abspath(__file__)); B = "https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_2/tier_1_multiview_caption/mesh"
names = [x["path"].split("/")[-2] for x in json.load(open(f"{D}/meshtree.json")) if x["type"] == "file"]
out = {}
for n in names:
    p = f"{D}/glbhead/{n}.head"
    if not os.path.exists(p) or os.path.getsize(p) < 20:
        subprocess.run(["curl", "-sSL", "-m", "120", "-r", "0-262143", f"{B}/{n}/{n}.glb", "-o", p + ".part"], check=True); os.replace(p + ".part", p)
    b = open(p, "rb").read(); L, T = struct.unpack("<II", b[12:20]); assert T == 0x4E4F534A, n
    if len(b) < 20 + L: print("short", n, L); continue
    g = json.loads(b[20:20 + L])
    mins, maxs = [], []
    for m in g.get("meshes", []):
        for pr in m["primitives"]:
            a = g["accessors"][pr["attributes"]["POSITION"]]; mins.append(a["min"]); maxs.append(a["max"])
    nodes = [(nd.get("scale"), nd.get("rotation"), nd.get("translation"), nd.get("matrix") is not None) for nd in g.get("nodes", [])]
    import numpy as np
    lo, hi = np.min(mins, 0), np.max(maxs, 0)
    out[n] = dict(min=lo.tolist(), max=hi.tolist(), ext=(hi - lo).tolist(), nodes=nodes[:3])
    print(n, np.round(hi - lo, 3), "centre", np.round((hi + lo) / 2, 3), nodes[:2])
json.dump(out, open(f"{D}/glb_bbox.json", "w"), indent=1)
