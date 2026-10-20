# Stage C: thin-feature sizes relevant to grasp synthesis (public scans; analysis only)
import numpy as np, trimesh
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh'
def L(n,f=None): 
    m=trimesh.load(f'{R}/{n}/{f or n}.glb',force='mesh'); m.merge_vertices(); return m
for n,f in [('wooden_piece_1','wooden_piece_1_visual'),('wooden_piece_2','wooden_piece_2_visual'),('mini_dust_pan',None),('white_pot_lid',None)]:
    m=L(n,f); v=m.vertices; e=v.max(0)-v.min(0); a=np.argmin(e)
    s=m.sample(40000); z=s[:,a]
    h,b=np.histogram(z,bins=60); top=np.argsort(h)[-4:]
    print(n,'min-axis',a,'range mm',np.round((z.min()*1000,z.max()*1000),1),'top bins mm',np.round(b[top]*1000,1),'counts',h[top],
          'watertight',m.is_watertight,'vol',round(abs(m.volume)*1e6,1) if m.is_watertight else '-')
for n,f in [('white_pot',None),('water_pitcher',None),('mini_sweeper','mini_sweeper_visual')]:
    m=L(n,f); s=m.sample(60000); c=s.mean(0); e=s.max(0)-s.min(0); a=np.argmax(e)
    d=s[:,a]-c[a]
    for side in (1,-1):
        sel=s[(side*d)>0.6*np.abs(d).max()]
        if len(sel)<50: continue
        o=[i for i in range(3) if i!=a]; ex=sel[:,o].max(0)-sel[:,o].min(0)
        print(n,'long-axis',a,'side',side,'reach mm',round(np.abs(d).max()*1000),'outer-40% cross-section mm',np.round(ex*1000),'n',len(sel))
