"""GT-free depth check of eval 10's blue-cup horizontal step: render our cups (library_v3, z-buffered point splat, half
resolution) into frames 0/30/60/150 at H1 = the tracked poses and at H0 = the tracked poses with the blue cup's horizontal
displacement since frame 0 removed (both cups shifted together: the stack stays nested); compare with our stored stereo
depth (cache/depth/eval/ep10, the 29 Oct recomputation; same camera track). Prints, per hypothesis, the median absolute
residual on the blue cup's front-most pixels (eroded 2 px) and the share of those pixels whose observed depth is > 1.5 cm
behind the rendered surface (free space where the hypothesis puts the cup)."""
import sys, numpy as np, trimesh, cv2
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/screen/scripts')
import eval_screen as E
ep = 10; frames = [0, 30, 60, 150]  # rows of the depth file
I = E.inputs(ep, False); det = np.load(I['det'], allow_pickle=True); pl = E.plane_of(det); nrm = np.asarray(pl[0], float)
P = np.load(I['poses']); W = P['world_T_cam'].astype(float); Wd = E.world(P); names = ['blue_cup', 'beige_cup']
dp = sys.argv[1]; E.assert_inference_input(dp); D = np.load(dp)[:, ::2, ::2]
K2 = np.diag([0.5, 0.5, 1.0]) @ det['K'].astype(float); Hh, Ww = D.shape[1:]
pts = {n: trimesh.sample.sample_surface(E.mesh(f'{E.REPO}/meshes/library_v3/{n}.glb'), 200000, seed=11)[0] for n in names}
cm = np.asarray(E.mesh(f'{E.REPO}/meshes/library_v3/blue_cup.glb').vertices, float).mean(0)
cb = Wd['blue_cup'][:, :3, :3] @ cm + Wd['blue_cup'][:, :3, 3]
def render(t, shift, blue_only=None):
    zb = np.full((Hh, Ww), np.inf); lab = np.full((Hh, Ww), -1)
    for s, n in enumerate(names):
        M = Wd[n][t].copy(); M[:3, 3] += shift + (blue_only if (blue_only is not None and n == 'blue_cup') else 0)
        T = np.linalg.inv(W[t]) @ M; X = pts[n] @ T[:3, :3].T + T[:3, 3]; uv = X @ K2.T
        u = np.round(uv[:, 0] / uv[:, 2]).astype(int); v = np.round(uv[:, 1] / uv[:, 2]).astype(int); z = X[:, 2]
        for du in (0, 1):
            for dv in (0, 1):
                uu, vv = u + du, v + dv; ok = (uu >= 0) & (uu < Ww) & (vv >= 0) & (vv < Hh) & (z > 0)
                uu, vv, zz = uu[ok], vv[ok], z[ok]; o = np.argsort(-zz); uu, vv, zz = uu[o], vv[o], zz[o]
                up = zz < zb[vv, uu]; zb[vv[up], uu[up]] = zz[up]; lab[vv[up], uu[up]] = s
    return zb, lab
for k, t in enumerate(frames):
    d = cb[t] - cb[0]; hshift = d - (d @ nrm) * nrm
    out = []
    vsh = -(d @ nrm) * nrm
    for name, sh, bo in (('H1 tracked', np.zeros(3), None), ('H0 no horizontal move', -hshift, None), ('H2 tracked, blue at its f0 height', np.zeros(3), vsh)):
        zb, lab = render(t, sh, bo)
        m = cv2.erode((lab == 0).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & (D[k] > 0)
        r = D[k][m] - zb[m]
        out.append(f'{name}: px {m.sum():5d} med|r| {np.median(np.abs(r))*100:5.2f} cm, behind>1.5cm {np.mean(r > 0.015)*100:5.1f} %, front<-1.5cm {np.mean(r < -0.015)*100:5.1f} %')
    print(f'f{t:3d} blue horizontal {np.linalg.norm(hshift)*100:4.1f} cm, vertical {(d @ nrm)*100:+4.1f} cm | ' + ' | '.join(out))
