import trimesh, numpy as np, sys
from PIL import Image
M='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh/%s/%s'
def load(n):
    import os
    for f in [f'{n}.glb', f'{n}_visual.glb']:
        p=M%(n,f)
        if os.path.exists(p): return trimesh.load(p).to_geometry()
def splat(m, R, S=300):
    v=(m.vertices-m.vertices.mean(0))@R.T
    try: col=m.visual.to_color().vertex_colors[:,:3]
    except Exception: col=np.full((len(v),3),200)
    ext=np.abs(v[:,:2]).max()*1.05; px=((v[:,:2]/ext+1)/2*(S-1)).astype(int)
    img=np.zeros((S,S,3),np.uint8); zb=np.full((S,S),-1e9)
    o=np.argsort(v[:,2])
    for i in o: x,y=px[i]; img[S-1-y,x]=col[i]
    return img
names=sys.argv[2].split(',')
rows=[]
for n in names:
    m=load(n); tiles=[]
    for a in [0,90,180,270]:
        t=np.radians(a); Rz=np.array([[np.cos(t),-np.sin(t),0],[np.sin(t),np.cos(t),0],[0,0,1]])
        Rx=np.array([[1,0,0],[0,0,1],[0,-1,0]])  # look along -y: x right, z up
        tiles.append(splat(m,Rx@Rz))
    tiles.append(splat(m,np.eye(3)))  # top view
    rows.append(np.concatenate(tiles,1))
Image.fromarray(np.concatenate(rows,0)).save(sys.argv[1])
