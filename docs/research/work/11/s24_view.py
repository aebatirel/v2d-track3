"""Stage C: overlay of the s24 fitted camera: rendered GT silhouette (red tint) + fg mask outline (green)."""
import sys, json, numpy as np, cv2, trimesh
sys.argv = [sys.argv[0], sys.argv[1]] + sys.argv[2:]
import s24_campose as S, c11
from s23_mask import masks
VAR = sys.argv[1]; res = json.load(open(f"s24_campose_{VAR}.json")); tiles = []
for ep in sys.argv[2:]:
    r = res[ep]; e = c11.load_episode(int(ep)); img0 = cv2.imread(f"cfr/pub{ep}_f0.png")
    P = np.vstack([trimesh.sample.sample_surface(c11.glb_mesh(n), 30000, seed=0)[0] @ c11.R_of(e["pose"][0, j, 3:]).T + e["pose"][0, j, :3] for j, n in enumerate(e["names"])])
    x = np.array([r["psi"], r["th"], r["ph"]] + r["C"]); img, fg, dc = masks(img0, 0.5)
    m = S.render(P, x, 0.5, fg.shape) > 0; vis = img.copy(); vis[m] = (0.5 * vis[m] + [0, 0, 127]).astype(np.uint8)
    cn, _ = cv2.findContours(fg.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(vis, cn, -1, (0, 255, 0), 1)
    cv2.putText(vis, f"{ep} psi {r['psi']:.1f} iou {r['iou']:.2f}", (10, 40), 0, 1.2, (0, 255, 255), 3); tiles.append(vis)
while len(tiles) % 2: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(f"cfr/view_{VAR}_{'_'.join(sys.argv[2:])}.png", np.vstack([np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]))
