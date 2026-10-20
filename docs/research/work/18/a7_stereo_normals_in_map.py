"""DIG 18 A7: bring each frame's stereo table normal (a5, cam_c frame) into the map frame with that frame's map pose and
compare the mean with the map's table and floor planes (a3)."""
import json, sys, numpy as np, pycolmap
rec = pycolmap.Reconstruction(sys.argv[1]); A3 = json.load(open(sys.argv[2])); A5 = json.load(open(sys.argv[3]))
nT = np.array(A3["floor"]["table_n"]); nF = np.array(A3["floor"]["up_map"])
byname = {im.name: im for im in rec.images.values()}
N = []; names = []
for r in A5:
    if not r.get("ok") or r["ninl"] < 3000 or r["sig_deg"] > 1.0: continue
    Rcw = byname["c/" + r["name"]].cam_from_world().rotation.matrix()
    N.append(Rcw.T @ np.array(r["n"])); names.append(r["name"])
N = np.array(N); m = N.mean(0); m /= np.linalg.norm(m)
ang = lambda a, b: np.degrees(np.arccos(np.clip(a @ b, -1, 1)))
spread = np.array([ang(n, m) for n in N])
print(f"n={len(N)} stereo table normals in the map frame: spread about their mean median {np.median(spread):.2f} p90 {np.percentile(spread,90):.2f} deg")
print(f"mean stereo normal vs map TABLE plane {ang(m,nT):.2f} deg; vs map FLOOR plane {ang(m,nF):.2f} deg; map table vs floor {ang(nT,nF):.2f}")
for s in "pe":
    k = [i for i, n in enumerate(names) if n[0] == s]; ms = N[k].mean(0); ms /= np.linalg.norm(ms)
    print(f"  {s}: n={len(k)} vs table {ang(ms,nT):.2f} vs floor {ang(ms,nF):.2f}")
# per-session consistency: group by episode
eps = sorted(set(n[:3] for n in names)); E = []
for e in eps:
    k = [i for i, n in enumerate(names) if n[:3] == e]; ms = N[k].mean(0); ms /= np.linalg.norm(ms); E.append(ms)
E = np.array(E); print("per-session mean normals: spread about the overall mean median", round(float(np.median([ang(x, m) for x in E])), 2),
                      "max", round(float(max(ang(x, m) for x in E)), 2))
json.dump(dict(mean_stereo_table_normal_map=m.tolist(), vs_table=float(ang(m, nT)), vs_floor=float(ang(m, nF))),
          open("a7_stereo_normals_in_map.json", "w"), indent=1)
