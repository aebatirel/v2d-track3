# Stage C: rack (and boards) scan-top vs hull-top heights per 12 mm block, cm digits (A=10+), rest pose of public ep 13/23
import sys, os, numpy as np, trimesh
sys.path.insert(0,os.path.dirname(__file__)); import coacd_fill as C
for n in (sys.argv[1:2] or ['plastic_dish_rack']):
    f=f'{C.D}/mesh/{n}/{n}_collision.glb' if os.path.exists(f'{C.D}/mesh/{n}/{n}_collision.glb') else f'{C.D}/mesh/{n}/{n}.glb'
    m=trimesh.load(f,force='mesh'); R=C.rest_R(n); so=m.sample(1500000)@R.T
    z=np.load(f'{C.H}/{n}.npz'); sh=np.vstack([trimesh.Trimesh(z[f'v{i}'],z[f'f{i}']).sample(40000) for i in range(int(z['n']))])@R.T
    base=so[:,2].min(); lo=so.min(0); C.CELL=float(sys.argv[2]) if len(sys.argv)>2 else 0.012
    nx=int((so[:,0].max()-lo[0])/C.CELL)+1; ny=int((so[:,1].max()-lo[1])/C.CELL)+1
    A=C.topmap(so,lo[0],lo[1],nx,ny); B=C.topmap(sh,lo[0],lo[1],nx,ny)
    dig=lambda v: '.' if np.isnan(v) else 'A' if (v-base)>=0.1 else str(int((v-base)*100))
    print(n,'scan top (cm above base) | hull top; rows = long axis')
    for yy in range(ny-1,-1,-1): print(''.join(dig(v) for v in A[yy]),' ',''.join(dig(v) for v in B[yy]))
