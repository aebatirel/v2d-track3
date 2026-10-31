"""GT-free: frame-0 lean of the sweeper's long axis (PCA major axis of our library_v3 sweeper) from our frame-0 table
normal, on eval 30 / 19 and on the public ep31 / ep18 tracks (25 Oct refine/in and Phase-1 P_o); plus the end-rest lean."""
import sys, numpy as np, trimesh
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/screen/scripts')
import eval_screen as E
V = np.asarray(E.mesh(f'{E.REPO}/meshes/library_v3/mini_sweeper.glb').vertices, float)
P = trimesh.sample.sample_surface(E.mesh(f'{E.REPO}/meshes/library_v3/mini_sweeper.glb'), 20000, seed=2)[0]
ax = np.linalg.svd(P - P.mean(0), full_matrices=False)[2][0]
def lean(R, n):
    a = R @ ax; return float(np.degrees(np.arccos(abs(np.clip(a @ n, -1, 1)))))
for ep, public in ((31, True), (18, True), (30, False), (19, False)):
    I = E.inputs(ep, public); det = np.load(I['det'], allow_pickle=True); pl = E.plane_of(det); n = np.asarray(pl[0], float)
    Wd = E.world(np.load(I['poses'])); T = Wd['mini_sweeper']
    s = f'ep{ep} {"public refine/in" if public else "eval"}: f0 lean {lean(T[0,:3,:3], n):.1f} deg, frames 0-9 mean {np.mean([lean(T[i,:3,:3], n) for i in range(10)]):.1f}, last 10 frames {np.mean([lean(T[i,:3,:3], n) for i in range(len(T)-10, len(T))]):.1f}'
    if public:
        p = f'{E.S}/leak/p1/oracle_roots/Po/ep{ep}/poses_world_vo.npz'; E.assert_inference_input(p); Q = np.load(p)['mini_sweeper']
        s += f' | Phase-1 P_o f0 {lean(Q[0,:3,:3], n):.1f}, last 10 {np.mean([lean(Q[i,:3,:3], n) for i in range(len(Q)-10, len(Q))]):.1f}'
    print(s)
