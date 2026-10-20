# Natural axes of an object's W2 mesh: area-weighted face-normal clustering -> rotation that makes the dominant
# planar directions axis-aligned. Compare with the minimum-volume OBB and with the GT up direction.
import sys, numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot
from scipy.optimize import minimize
n=sys.argv[1]; d=np.load(f'/Users/aebatirel/Documents/Code/v2d-research/work/19/b/W2/{n}.npz'); m=trimesh.Trimesh(d['v'],d['f'],process=False)
N=m.face_normals; A=m.area_faces; A=A/A.sum()
def cost(rv):
    R=Rot.from_rotvec(rv).as_matrix(); M=np.abs(N@R.T)          # normals in the rotated frame
    return float((A*(1-M.max(1))).sum())                        # 0 if every face normal is axis-aligned
best=min((minimize(cost,x0,method='Nelder-Mead',options=dict(xatol=1e-5,fatol=1e-9,maxiter=4000)) for x0 in [np.zeros(3)]+[np.random.default_rng(i).normal(0,0.05,3) for i in range(6)]),key=lambda r:r.fun)
R=Rot.from_rotvec(best.x)
print(f'{n}: axis-alignment cost identity {cost(np.zeros(3)):.4f} -> best {best.fun:.4f}; rotation {np.degrees(np.linalg.norm(best.x)):.2f} deg about {np.round(best.x/max(np.linalg.norm(best.x),1e-12),3)}')
To,ext=trimesh.bounds.oriented_bounds(m); print('  min-volume OBB extents mm',np.round(ext*1e3,1),' OBB rotation deg',round(np.degrees(Rot.from_matrix(To[:3,:3]).magnitude()),2))
np.save(f'/Users/aebatirel/Documents/Code/v2d-research/work/19/c/align_{n}.npy',R.as_matrix())
