# Stage C: do public-GT contact states interpenetrate the CoACD collision hulls? (hull-of-A surface points inside hulls of B)
import sys, os, numpy as np, pandas as pd, trimesh
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as Rot
D='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'; H=os.path.join(os.path.dirname(__file__),'hulls')
def hulls(n):
    z=np.load(f'{H}/{n}.npz'); return [z[f'v{i}'] for i in range(int(z['n']))]
def eqs(n): return [ConvexHull(v).equations for v in hulls(n)]
def samp(n,k=30000):
    z=np.load(f'{H}/{n}.npz'); ms=[trimesh.Trimesh(z[f'v{i}'],z[f'f{i}']) for i in range(int(z['n']))]
    return trimesh.util.concatenate(ms).sample(k)
def T(p): return Rot.from_quat([p[4],p[5],p[6],p[3]]).as_matrix(), np.array(p[:3])
def depth(P,E):  # max inside-depth of points P (in B frame) over convex hulls E; 0 if outside all
    best=np.zeros(len(P))
    for e in E:
        d=-(P@e[:,:3].T+e[:,3]).max(1); best=np.maximum(best,d)
    return best
PAIRS=[(0,'white_pot_lid','white_pot'),(2,'white_pot_lid','white_pot'),(11,'beige_cup','blue_cup'),
       (12,'blue_cup','plastic_dish_rack'),(13,'blue_cup','plastic_dish_rack'),(26,'white_pot','plastic_dish_rack'),
       (27,'white_pot','plastic_dish_rack'),(31,'mini_sweeper','plastic_dish_rack'),(23,'wooden_piece_1','wooden_piece_2'),
       (24,'wooden_piece_1','wooden_piece_2'),(18,'mini_sweeper','mini_dust_pan')]
def main():
 for e,a,b in PAIRS:
    df=pd.read_parquet(f'{D}/data/chunk-000/episode_{e:06d}.parquet',columns=['observation.objects'])
    fr=df['observation.objects'].tolist(); N=len(fr); Pa=samp(a); Eb=eqs(b)
    res=[]
    for f in list(range(0,N,4))+[N-1]:
        pa=[o['pose'] for o in fr[f] if o['name']==a][0]; pb=[o['pose'] for o in fr[f] if o['name']==b][0]
        Ra,ta=T(pa); Rb,tb=T(pb); W=Pa@Ra.T+ta; Pb=(W-tb)@Rb
        d=depth(Pb,Eb); res.append((f,d.max()*1000,np.mean(d>0.002)))
    r=np.array(res); end=r[-1]; worst=r[np.argmax(r[:,1])]
    first=r[0]
    print(f'ep {e} {a} vs {b} hulls: f0 max {first[1]:.1f} mm; END f{int(end[0])} max {end[1]:.1f} mm, >2mm frac {end[2]:.3f}; '
          f'worst f{int(worst[0])} {worst[1]:.1f} mm; frames(>5mm) {np.mean(r[:,1]>5):.2f}',flush=True)

if __name__=='__main__': main()
