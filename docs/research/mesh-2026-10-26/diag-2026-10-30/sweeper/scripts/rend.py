"""Tiny numpy z-buffer splat renderer (orthographic). Layers: dict(p=(N,3), n=(N,3) or None, c=(N,3) uint8 or rgb tuple)."""
import numpy as np, cv2, trimesh

def look(view):
    """rotation whose rows are screen x (right), screen y (down), view dir (into screen) for named views."""
    az, el = view
    a, e = np.radians(az), np.radians(el)
    d = -np.array([np.cos(e)*np.cos(a), np.cos(e)*np.sin(a), np.sin(e)])   # camera looks along d (from direction -d)
    up = np.array([0,0,1.0]) if abs(np.sin(e))<0.99 else np.array([0,1.0,0])
    r = np.cross(d, up); r/=np.linalg.norm(r); u = np.cross(r, d)
    return np.stack([r, -u, d])

def sample_mesh(m, n=300000, tex=True, seed=0):
    rng = np.random.default_rng(seed)
    p, fi = trimesh.sample.sample_surface(m, n, seed=seed)
    nrm = m.face_normals[fi]
    col = None
    if tex and getattr(m.visual,'kind',None)=='texture' and m.visual.uv is not None:
        try:
            img = np.asarray(m.visual.material.baseColorTexture.convert('RGB'))
            tri = m.triangles[fi]; uvt = m.visual.uv[m.faces[fi]]
            bc = trimesh.triangles.points_to_barycentric(tri, p)
            uv = (uvt*bc[:,:,None]).sum(1)
            H,W = img.shape[:2]
            x = np.clip((uv[:,0]%1)*(W-1),0,W-1).astype(int); y = np.clip((1-uv[:,1]%1)*(H-1),0,H-1).astype(int)
            col = img[y,x]
        except Exception as e:
            print('tex fail', e)
    return p, nrm, col

def render(layers, R, size=420, scale=None, center=None, bg=255, light=None, rad=1):
    allp = np.concatenate([L['p'] for L in layers])
    if center is None: center = 0.5*(allp.min(0)+allp.max(0))
    q = (allp-center)@R.T
    if scale is None: scale = 0.86*size/max(np.ptp(q[:,0]), np.ptp(q[:,1]))
    img = np.full((size,size,3), bg, np.uint8); zb = np.full((size,size), np.inf)
    if light is None: light = R.T@np.array([-0.3,-0.5,-1.0]); light/=np.linalg.norm(light)
    out=[]
    for L in layers:
        q = (L['p']-center)@R.T
        x = (q[:,0]*scale+size/2).astype(int); y=(q[:,1]*scale+size/2).astype(int); z=q[:,2]
        ok = (x>=rad)&(x<size-rad)&(y>=rad)&(y<size-rad)
        c = L.get('c')
        if c is None or (isinstance(c,tuple)):
            base = np.array(c if c is not None else (200,200,200),float)[None].repeat(len(q),0)
        else: base = np.asarray(c,float)
        if L.get('n') is not None and L.get('shade',True):
            nn = L['n']; s = np.abs(nn@light)  # two-sided
            base = base*(0.35+0.65*s[:,None])
        base = np.clip(base,0,255).astype(np.uint8)
        idx = np.where(ok)[0]
        order = idx[np.argsort(-z[idx])]   # far first; later (near) overwrite
        for dx in range(-rad+1, rad) if rad>1 else [0]:
            for dy in range(-rad+1, rad) if rad>1 else [0]:
                xx=x[order]+dx; yy=y[order]+dy; zz=z[order]
                closer = zz < zb[yy,xx] + L.get('ztol',0)
                o2 = order[closer]; xx=xx[closer]; yy=yy[closer]
                img[yy,xx]=base[o2]; zb[yy,xx]=np.minimum(zb[yy,xx], z[o2])
    return img, dict(center=center, scale=scale)

def label(img, txt, pos=(6,18), col=(0,0,0), s=0.5):
    cv2.putText(img, txt, pos, cv2.FONT_HERSHEY_SIMPLEX, s, (255,255,255), 3, cv2.LINE_AA)
    cv2.putText(img, txt, pos, cv2.FONT_HERSHEY_SIMPLEX, s, col, 1, cv2.LINE_AA)
    return img

def scalebar(img, scale, mm=50, y=None):
    size=img.shape[0]; y = y or size-12; L=int(mm/1000*scale)
    cv2.line(img,(10,y),(10+L,y),(0,0,0),2); label(img, f'{mm} mm', (12+L, y+4), s=0.4)
    return img

def render_layer(p, n, c, R, center, scale, size=360, light=None):
    q=(p-center)@R.T
    x=(q[:,0]*scale+size/2).astype(int); y=(q[:,1]*scale+size/2).astype(int); z=q[:,2]
    ok=(x>=0)&(x<size)&(y>=0)&(y<size)
    if light is None: light=R.T@np.array([-0.3,-0.5,-1.0]); light/=np.linalg.norm(light)
    if isinstance(c,tuple) or c is None: base=np.array(c or (200,200,200),float)[None].repeat(len(p),0)
    else: base=np.asarray(c,float)
    if n is not None: base=base*(0.35+0.65*np.abs(n@light))[:,None]
    img=np.zeros((size,size,3),np.uint8); zb=np.full((size,size),np.inf); m=np.zeros((size,size),bool)
    idx=np.where(ok)[0]; idx=idx[np.argsort(-z[idx])]
    img[y[idx],x[idx]]=np.clip(base[idx],0,255).astype(np.uint8); zb[y[idx],x[idx]]=z[idx]; m[y[idx],x[idx]]=True
    # 1-px dilation fill of holes
    k=np.ones((3,3),np.uint8)
    m2=cv2.morphologyEx(m.astype(np.uint8),cv2.MORPH_CLOSE,k).astype(bool)
    fill=m2&~m
    if fill.any():
        bl=cv2.dilate(img,k); img[fill]=bl[fill]
    return img, m2

def overlay(imA, mA, imB, mB, bg=255, alpha=0.5):
    out=np.full_like(imA,bg)
    out[mA]=imA[mA]; out[mB&~mA]=imB[mB&~mA]
    both=mA&mB; out[both]=(alpha*imA[both]+(1-alpha)*imB[both]).astype(np.uint8)
    return out
