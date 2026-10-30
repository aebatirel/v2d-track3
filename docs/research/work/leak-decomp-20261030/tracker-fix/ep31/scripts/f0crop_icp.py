"""DISPLAY (public ep31 f0, rectified half res): sweeper silhouettes, rack as occluder, from f0icp.py's functions:
truth (green, ORACLE mapping via the P_s rack fit), P_o tracker (red), F1 ICP on our mask (cyan). Usage: python -I f0crop_icp.py SCRIPTS OUT_PNG"""
import sys, numpy as np, cv2
OUTPNG = sys.argv[2]; sys.argv = [sys.argv[0], sys.argv[1], "/dev/null"]
src = open(sys.argv[1] + '/f0icp.py').read().split('# ---------------- GT-free: predicted visible')[0]
exec(compile(src, 'f0icp_head', 'exec'))
T_icp = icp(Plib[names[sw]][0], backproject(msw), SL[names[sw]])
pts = H[rk]['points'][::10] + H[rk]['anchor']
P = np.concatenate([pts @ tr['Ps'][names[rk]][i][:3, :3].T + tr['Ps'][names[rk]][i][:3, 3] for i in range(N)])
Q = np.concatenate([pts @ gt[names[rk]][i][:3, :3].T + gt[names[rk]][i][:3, 3] for i in range(N)])
mp, mq = P.mean(0), Q.mean(0); U, _, Vt = np.linalg.svd((P - mp).T @ (Q - mq))
Rm = Vt.T @ np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]) @ U.T; tm = mq - Rm @ mp
G = np.eye(4); G[:3, :3] = Rm.T; G[:3, 3] = -Rm.T @ tm
Xs = np.linalg.inv(Xg[names[sw]])
rack = (rk, Plib[names[rk]][0], SL[names[rk]])
labs = {'truth': render([rack, (sw, G @ gt[names[sw]][0] @ Xg[names[sw]], SL[names[sw]])])[1],
        'Po': render([rack, (sw, Plib[names[sw]][0], SL[names[sw]])])[1],
        'icp': render([rack, (sw, T_icp, SL[names[sw]])])[1]}
img = cv2.cvtColor(det['image'], cv2.COLOR_GRAY2BGR)
ys, xs = np.where(labs['truth'] == sw); cy, cx = int(ys.mean()), int(xs.mean())
crop = lambda im: cv2.resize(im[max(0, cy - 70):cy + 70, max(0, cx - 90):cx + 90], None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
def outl(m, col, im):
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(im, cs, -1, col, 1)
tiles = []
for title, ks in (('tracker P_o (red) vs truth (green)', [('truth', (0, 220, 0)), ('Po', (0, 0, 255))]),
                  ('F1 ICP on our mask (cyan) vs truth (green)', [('truth', (0, 220, 0)), ('icp', (255, 255, 0))])):
    im = img.copy()
    for k, col in ks:
        outl(labs[k] == sw, col, im)
    outl(msw, (0, 255, 255), im) if False else None
    c = crop(im); cv2.rectangle(c, (0, 0), (c.shape[1], 22), (0, 0, 0), -1)
    cv2.putText(c, title, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA); tiles.append(c)
out = np.hstack(tiles)
cv2.putText(out, 'ep31 f0, our library_v3 meshes; ORACLE display (truth = mocap via the P_s rack fit, at X*_geom)', (5, out.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
cv2.imwrite(OUTPNG, out); print("wrote", OUTPNG)
