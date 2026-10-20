import trimesh, numpy as np, re
P='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
m=trimesh.load(P+'/mesh/white_pot/white_pot.glb',force='mesh'); v=m.vertices
u=open(P+'/urdf/white_pot_rigid.urdf').read(); print(re.findall(r'<origin[^>]*>|<mass[^>]*>',u)[:3])
c=v.mean(0); w,V=np.linalg.eigh(np.cov((v-c).T)); ax=V[:,2]; s=(v-c)@ax
if np.median(s)>0: ax=-ax; s=-s   # body near s<0? choose handle side as +s
s=s-s.min(); L=s.max(); print('long axis length %.1f mm'%(L*1e3))
o1=V[:,1]; o0=V[:,0]
for a in np.arange(0,L,0.01):
    k=(s>=a)&(s<a+0.01)
    if k.sum()<30: continue
    p=v[k]-c; w1=np.percentile(p@o1,99)-np.percentile(p@o1,1); w0=np.percentile(p@o0,99)-np.percentile(p@o0,1)
    print('%3.0f-%3.0f mm: %5.1f x %5.1f mm (n=%d)'%(a*1e3,(a+.01)*1e3,w0*1e3,w1*1e3,k.sum()))
