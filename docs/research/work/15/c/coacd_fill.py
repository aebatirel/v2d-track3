# Stage C: top-down height maps of the true scan vs its CoACD hull union (object at its public frame-0 rest pose).
# Delta = hull top - scan top per 4 mm cell. Large Delta = a cavity the collision model fills (seen from above).
import os, sys, numpy as np, pandas as pd, trimesh
from scipy.spatial.transform import Rotation as Rot
D='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'; H=os.path.join(os.path.dirname(__file__),'hulls')
REST={'blue_cup':11,'beige_cup':11,'plastic_dish_rack':13,'white_pot':41,'wooden_piece_1':23,'wooden_piece_2':23,
      'mini_dust_pan':40,'white_pot_lid':0,'mini_sweeper':18,'water_pitcher':21}
CELL=0.004
def rest_R(n):
    df=pd.read_parquet(f'{D}/data/chunk-000/episode_{REST[n]:06d}.parquet',columns=['observation.objects'])
    p=[o['pose'] for o in df['observation.objects'].iloc[0] if o['name']==n][0]
    return Rot.from_quat([p[4],p[5],p[6],p[3]]).as_matrix()
def topmap(pts,x0,y0,nx,ny):
    ix=((pts[:,0]-x0)/CELL).astype(int); iy=((pts[:,1]-y0)/CELL).astype(int)
    ok=(ix>=0)&(ix<nx)&(iy>=0)&(iy<ny); M=np.full((ny,nx),np.nan)
    order=np.argsort(pts[ok,2]); 
    M[iy[ok][order],ix[ok][order]]=pts[ok,2][order]   # last write = max z
    return M
def main():
  for n in (sys.argv[1:] or REST):
    f=f'{D}/mesh/{n}/{n}_collision.glb' if os.path.exists(f'{D}/mesh/{n}/{n}_collision.glb') else f'{D}/mesh/{n}/{n}.glb'
    m=trimesh.load(f,force='mesh'); R=rest_R(n)
    so=m.sample(1500000)@R.T
    z=np.load(f'{H}/{n}.npz'); hs=[]
    for i in range(int(z['n'])):
        hm=trimesh.Trimesh(z[f'v{i}'],z[f'f{i}']); k=max(2000,int(hm.area/m.area*1500000)); hs.append(hm.sample(k))
    sh=np.vstack(hs)@R.T
    lo=np.minimum(so.min(0),sh.min(0)); hi=np.maximum(so.max(0),sh.max(0))
    nx=int((hi[0]-lo[0])/CELL)+1; ny=int((hi[1]-lo[1])/CELL)+1
    A=topmap(so,lo[0],lo[1],nx,ny); B=topmap(sh,lo[0],lo[1],nx,ny)
    d=(B-A)*1000; both=~np.isnan(A)&~np.isnan(B); hullonly=np.isnan(A)&~np.isnan(B)
    zr=(so[:,2].max()-so[:,2].min())*1000
    print(f'{n}: hulls {int(z["n"])}, height {zr:.0f} mm, cells {both.sum()}; Delta>5mm {np.mean(d[both]>5):.2f}, '
          f'>10mm {np.mean(d[both]>10):.2f}, >25mm {np.mean(d[both]>25):.2f}, max {np.nanmax(d):.0f} mm; '
          f'hull-only cells (holes closed in plan view) {hullonly.sum()} vs scan cells {(~np.isnan(A)).sum()}',flush=True)
    # ASCII plan map at 3x coarser grid: '.' none, 'o' scan only(hull missing), '-' |Delta|<=5, '1' 5-10, '2' 10-25, '#' >25, 'H' hull-only
    s=3; rows=[]
    for yy in range(ny-1,-1,-s):
        r=''
        for xx in range(0,nx,s):
            a=A[yy:yy+s,xx:xx+s]; b=B[yy:yy+s,xx:xx+s]
            if np.all(np.isnan(a)) and np.all(np.isnan(b)): r+='.'; continue
            if np.all(np.isnan(a)): r+='H'; continue
            if np.all(np.isnan(b)): r+='o'; continue
            v=np.nanmax(b)-np.nanmin(a) if False else np.nanmedian(b-a)*1000
            r+='-' if abs(v)<=5 else '1' if v<=10 else '2' if v<=25 else '#'
        rows.append(r)
    open(os.path.join(os.path.dirname(__file__),f'fill_{n}.txt'),'w').write('\n'.join(rows)+'\n')

if __name__=='__main__': main()
