# Split the W2 solid into box parts (recursive bisection of the longest occupied extent until <= Lmax), each part
# closed by flat caps (marching cubes on max(field, box sdf)), so every part is its own watertight mesh for CoACD.
# usage: b_split.py name h_mm delta_mm t_mm Lmax_mm outdir
import sys, os, numpy as np, trimesh
from skimage.measure import marching_cubes
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from b_field import *
n,h,dl,t,L,od=sys.argv[1],float(sys.argv[2])*1e-3,float(sys.argv[3])*1e-3,float(sys.argv[4])*1e-3,float(sys.argv[5])*1e-3,sys.argv[6]
os.makedirs(od,exist_ok=True)
f,lo=w2_field(n,h,t); solid=f<dl; N=np.array(f.shape)
X=[lo[i]+h*np.arange(N[i]) for i in range(3)]
def occ_ext(b):   # occupied extent (m) inside index box b=[(i0,i1),...] (half-open, cut planes at half-voxel positions)
    s=solid[b[0][0]:b[0][1],b[1][0]:b[1][1],b[2][0]:b[2][1]]
    if not s.any(): return None
    idx=[np.where(s.any(axis=tuple(j for j in range(3) if j!=k)))[0] for k in range(3)]
    return np.array([(ix[-1]-ix[0]+1)*h for ix in idx]), [(b[k][0]+idx[k][0],b[k][0]+idx[k][-1]+1) for k in range(3)]
boxes=[]; stack=[[(0,N[0]),(0,N[1]),(0,N[2])]]
while stack:
    b=stack.pop(); r=occ_ext(b)
    if r is None: continue
    ext,tb=r; k=int(np.argmax(ext))
    if ext[k]<=L: boxes.append(tb); continue
    mid=(tb[k][0]+tb[k][1])//2
    b1=list(tb); b2=list(tb); b1[k]=(tb[k][0],mid); b2[k]=(mid,tb[k][1]); stack+= [b1,b2]
parts=[]
for j,b in enumerate(sorted(boxes)):
    # box in world coords: cut planes half a voxel outside the first/last occupied voxel centres
    bmin=np.array([X[k][b[k][0]]-0.5*h for k in range(3)]); bmax=np.array([X[k][b[k][1]-1]+0.5*h for k in range(3)])
    sl=tuple(slice(max(b[k][0]-2,0),min(b[k][1]+2,N[k])) for k in range(3))
    sub=f[sl]; g=np.stack(np.meshgrid(*[X[k][sl[k]] for k in range(3)],indexing='ij'),-1)
    dbox=np.max(np.maximum(bmin-g,g-bmax),-1)        # box sdf (exact on faces, inside negative)
    fp=nudge(np.maximum(sub,dbox),dl,h)
    fp=np.pad(fp,1,constant_values=1.0)
    v,fc,_,_=marching_cubes(fp,level=dl,spacing=(h,h,h),allow_degenerate=False)
    v=v-h+np.array([X[k][sl[k]][0] for k in range(3)])
    w=trimesh.Trimesh(v,fc,process=True); w.merge_vertices()
    keep=[c for c in w.split(only_watertight=False) if abs(c.volume)>0.05e-6]
    if not keep: continue
    w=trimesh.util.concatenate(keep)
    if w.volume<0: w.invert()
    p=f'{od}/{n}_p{len(parts):03d}.npz'; np.savez(p,v=np.asarray(w.vertices),f=np.asarray(w.faces,np.int64))
    parts.append((p,len(w.faces),np.ptp(w.vertices,0).max()*1e3,w.is_watertight,w.volume*1e6))
print(f'{n} Lmax={L*1e3:.0f}mm parts={len(parts)} F_total={sum(x[1] for x in parts)} L_part_mm max={max(x[2] for x in parts):.1f} '
      f'median={np.median([x[2] for x in parts]):.1f} all_watertight={all(x[3] for x in parts)} vol_cm3={sum(x[4] for x in parts):.1f}',flush=True)
