"""Stage C: which covariance reproduces the stored Track 2 axes? Compare stored axes with eigenvectors of (a) area-weighted
surface covariance, (b) raw vertex (face-corner) covariance, (c) welded unique-vertex covariance. Usage: c_t2axes.py names..."""
import sys, numpy as np
D = "/Users/aebatirel/Documents/Code/v2d-research/work/13/t2"
def dev(C):
    w, E = np.linalg.eigh(C); return [round(float(np.degrees(np.arccos(min(1, np.max(np.abs(E[:, i])))))), 3) for i in range(3)]
for n in sys.argv[1:]:
    z = np.load(f"{D}/{n}.npz"); V, F = z["V"], z["F"]
    T = V[F]; a = 0.5*np.linalg.norm(np.cross(T[:,1]-T[:,0], T[:,2]-T[:,0]), axis=1); A = a.sum(); s = T.sum(1)
    c = (a[:,None]*s/3).sum(0)/A
    M2 = (sum(np.einsum("n,ni,nj->ij", a, T[:,k], T[:,k]) for k in range(3)) + np.einsum("n,ni,nj->ij", a, s, s))/12/A
    Ca = M2 - np.outer(c, c)
    Cv = np.cov(V.T, bias=True)
    U = np.unique(np.round(V, 7), axis=0); Cw = np.cov(U.T, bias=True)
    print(n, "area", dev(Ca), "vert", dev(Cv), "weld", dev(Cw), "vmean_mm", np.round(1000*V.mean(0), 2).tolist(), "weldmean_mm", np.round(1000*U.mean(0), 2).tolist(), "nV/nU", len(V), len(U))
