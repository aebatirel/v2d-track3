"""GT-free check of eval 10's blue-cup horizontal step (f35-50): does the left fist move with the track, and does the
29 Oct evdepth re-run of eval perception (same video, library_v3, guard on) show the same step?"""
import sys, numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/screen/scripts')
import eval_screen as E
S = E.S; ep = 10
I = E.inputs(ep, False); det = np.load(I['det'], allow_pickle=True); pl = E.plane_of(det); nrm = np.asarray(pl[0], float)
cm = np.asarray(E.mesh(f'{E.REPO}/meshes/library_v3/blue_cup.glb').vertices, float).mean(0)
def hv(Wd, n='blue_cup'):
    c = Wd[n][:, :3, :3] @ cm + Wd[n][:, :3, 3]; dc = c - c[0]; v = dc @ nrm; h = dc - v[:, None] * nrm; return c, h, v
A = E.world(np.load(I['poses'])); cA, hA, vA = hv(A)
p2 = f'{S}/daudit/dl_evposes/runs/mesh-20261029-evdepth-92f3d86/results/evalperc/ep10/poses.npz'; E.assert_inference_input(p2)
B = E.world(np.load(p2)); cB, hB, vB = hv(B)
hz = np.load(I['hands'], allow_pickle=True)
for side in ('left', 'right'):
    J = hz[f'joints_{side}'].astype(float); ok = hz[f'valid_{side}'].astype(bool) & np.isfinite(J).all((1, 2))
    W = J.mean(1)                                   # hand centroid (21 joints), world
    d = np.linalg.norm(J - cA[:, None], axis=-1).min(1) * 100
    print(side, 'hand: frame, valid, centroid horizontal shift from f35 (cm, along the cup step direction / total), min joint-to-cup-centre cm')
    u = hA[50] - hA[35]; u = u / np.linalg.norm(u)
    for i in (30, 35, 38, 40, 42, 44, 46, 48, 50, 55, 60, 80, 100, 120):
        if ok[i] and ok[35]:
            dw = W[i] - W[35]; dw = dw - (dw @ nrm) * nrm
            print(f'  f{i:3d} {int(ok[i])} {dw @ u * 100:6.2f} / {np.linalg.norm(dw) * 100:5.2f}   {d[i]:5.1f}')
        else:
            print(f'  f{i:3d} {int(ok[i])}')
print('cup track step along u:', ' '.join(f'f{i}:{(hA[i]-hA[35]) @ u * 100:.2f}' for i in (38, 40, 42, 44, 46, 48, 50, 60, 100, 160)))
print('pack6 track    h_end %.2f v_end %.2f hmax %.2f | evdepth re-run h_end %.2f v_end %.2f hmax %.2f vmax %.2f' % (
    np.linalg.norm(hA[-1]) * 100, vA[-1] * 100, np.linalg.norm(hA, axis=1).max() * 100,
    np.linalg.norm(hB[-1]) * 100, vB[-1] * 100, np.linalg.norm(hB, axis=1).max() * 100, np.abs(vB).max() * 100))
print('evdepth re-run blue cup h/v by frame:', ' '.join(f'f{i}:{np.linalg.norm(hB[i])*100:.1f}/{vB[i]*100:.1f}' for i in range(0, 161, 10)))
print('camera identical?', float(np.abs(np.load(I['poses'])['world_T_cam'] - np.load(p2)['world_T_cam']).max()))
