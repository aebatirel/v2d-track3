"""Per-axis sign statistics of each public scan in its published frame (visual + collision meshes)."""
import os, json, numpy as np, trimesh
MESH = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh"
NAMES = ["beige_cup","blue_cup","mini_dust_pan","mini_sweeper","plastic_dish_rack","water_pitcher","white_pot","white_pot_lid","wooden_piece_1","wooden_piece_2"]

def h3(a,b,c): return a**3+b**3+c**3+a*a*b+a*a*c+b*b*a+b*b*c+c*c*a+c*c*b+a*b*c
def h2(a,b,c): return a*a+b*b+c*c+a*b+a*c+b*c
def h4(a,b,c):
    # complete homogeneous symmetric polynomial degree 4 (integral of f^4 over triangle = 2A*h4/30 ... /15 normalisation below)
    s=0
    for i in range(5):
        for j in range(5-i):
            k=4-i-j; s=s+a**i*b**j*c**k
    return s
def exact_moments(V,F):
    T=V[F]; area=0.5*np.linalg.norm(np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]),axis=1); A=area.sum()
    c=(area[:,None]*T.mean(1)).sum(0)/A
    f=T-c
    out={}
    m2=np.array([(area*h2(*f[:,:,i].T)/6).sum()/A for i in range(3)])
    m3=np.array([(area*h3(*f[:,:,i].T)/10).sum()/A for i in range(3)])
    m4=np.array([(area*h4(*f[:,:,i].T)/15).sum()/A for i in range(3)])
    out["c"]=c; out["std"]=np.sqrt(m2); out["skew"]=m3/m2**1.5; out["kurt"]=m4/m2**2
    return out, area, T
def stats(V,F):
    ex, area, T = exact_moments(V,F)
    c=ex["c"]; A=area.sum(); tc=T.mean(1)-c; Vc=V-c
    S={}
    S["skew"]=ex["skew"]; S["kurt_minus3"]=ex["kurt"]-3
    S["signed_sq"]=np.array([(area*np.sign(tc[:,i])*tc[:,i]**2).sum()/A for i in range(3)])/ex["std"]**2
    S["vert_skew"]=(Vc**3).mean(0)/Vc.var(0)**1.5
    S["vert_mean"]=Vc.mean(0)/ex["std"]
    S["bbox_ctr"]=(0.5*(V.max(0)+V.min(0))-c)/ex["std"]
    S["extreme"]=(V.max(0)-c + (V.min(0)-c))/ex["std"]   # >0 if farther extreme on + side
    S["area_frac"]=np.array([(area*(tc[:,i]>0)).sum()/A-0.5 for i in range(3)])
    # area-weighted median offset (neg of what skew suggests typically)
    med=[]
    for i in range(3):
        o=np.argsort(tc[:,i]); cw=np.cumsum(area[o]); med.append(tc[o[np.searchsorted(cw,A/2)],i])
    S["median"]=np.array(med)/ex["std"]
    S["net_normal"]=(np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0])*0.5).sum(0)/A
    # 5th moment (odd) standardized, area-sampled approximation via centroid+vertices
    w=np.concatenate([area/6]*3+[area/2]); P=np.concatenate([T[:,0]-c,T[:,1]-c,T[:,2]-c,tc])
    S["m5"]=(w[:,None]*P**5).sum(0)/w.sum()/ex["std"]**5
    S["abs_m1_pos_minus_neg"]=np.array([((w*P[:,i]**3*(P[:,i]>0)).sum()+(w*P[:,i]**3*(P[:,i]<0)).sum())/w.sum() for i in range(3)])/ex["std"]**3
    return S, ex
def load(p): 
    m=trimesh.load(p,force="mesh",process=False); return np.asarray(m.vertices,float),np.asarray(m.faces)
res={}
for n in NAMES:
    d=f"{MESH}/{n}"; vis=f"{d}/{n}_visual.glb" if os.path.exists(f"{d}/{n}_visual.glb") else f"{d}/{n}.glb"
    V,F=load(vis); S,ex=stats(V,F)
    res[n]={k:v.tolist() for k,v in S.items()}; res[n]["std_mm"]=(ex["std"]*1000).tolist(); res[n]["c_mm"]=(ex["c"]*1000).tolist()
    col=f"{d}/{n}_collision.glb"
    if os.path.exists(col):
        V2,F2=load(col); S2,ex2=stats(V2,F2)
        res[n+"__collision"]={k:v.tolist() for k,v in S2.items()}; res[n+"__collision"]["c_mm"]=(ex2["c"]*1000).tolist()
json.dump(res,open("out/stats.json","w"),indent=1)
keys=[k for k in res[NAMES[0]] if k not in ("std_mm","c_mm")]
for k in keys:
    print(f"== {k}")
    for n in res:
        print(f"  {n:30s}"+"  ".join(f"{v:+9.4f}" for v in res[n][k]))
