# GT-free part program P1 for the mini sweeper, fitted to OUR ep31 observed points (hand-masked, cleaned) in our frame.
# Parts: elliptic-section torus ring + trapezoid head slab + trapezoid bristle-fan slab + 2 observed marker balls (+posts).
# Priors (generic, not from the scan): parts share one mid-plane and one left/right mirror plane (unseen -x/-y sides
# completed by symmetry); flat ring perpendicular to the slab. No scan, mocap, align or parquet pose is read.
import numpy as np, trimesh, json, manifold3d as m3
p=np.load('ep31_clean.npy').astype(float)
lib=json.load(open('meshes/M2_libsym_balls.json'))
R=np.array(lib['R']); t=np.array(lib['c2_t'])
# mid-plane x_m: point on the library's own C2 axis (solve (I-R)c=t, least squares) -> x of axis
ax=np.array(lib['c2_axis']); c_ax=0.5*(t-(t@ax)*ax); x_lib=float(c_ax[0])
def sl0(z0,z1): return p[(p[:,2]>z0)&(p[:,2]<z1)]
xm=[]
for zc in list(np.arange(-0.055,-0.024,0.005))+[0.0775,0.0815]:
    s_=sl0(zc-0.0025,zc+0.0025)
    if len(s_)>4000: xm.append(0.5*(np.percentile(s_[:,0],2)+np.percentile(s_[:,0],98)))
x_m=float(np.median(xm)); print('x_m from see-through bristles + ring top: %.2f cm (library C2 axis would give %.2f)'%(x_m*100,x_lib*100))
def sl(z0,z1): return p[(p[:,2]>z0)&(p[:,2]<z1)]
# mirror plane y_m: median of slice mid-points over well-covered bristle and ring-top slices
mids=[]
for zc in list(np.arange(-0.055,-0.025,0.005))+[0.075,0.08]:
    s=sl(zc-0.0025,zc+0.0025)
    if len(s)>4000: mids.append(0.5*(np.percentile(s[:,1],1)+np.percentile(s[:,1],99)))
y_m=float(np.median(mids))
print('x_m %.2f cm, y_m %.2f cm (median of %d slice mids)'%(x_m*100,y_m*100,len(mids)))
# ---- ring: points above the head (z > 3 cm)
r=sl(0.03,0.09); yz=r[:,1:]
# outer radius from the better-seen +y side of the ring flanks (z 4-6 cm); top from the highest points;
# inner radius from the hole edge; round tube section (generic prior) because the x-extent of the ring is smeared
fl=sl(0.04,0.06); R_out=float(np.percentile(fl[:,1],99)-y_m)
z_top=float(np.percentile(r[:,2],99.5)); zc=z_top-R_out
rho=np.hypot(yz[:,0]-y_m, yz[:,1]-zc); R_in=float(np.percentile(rho,2)); Rm=0.5*(R_in+R_out)
b_r=0.5*(R_out-R_in)
h=r[:,0]-x_m
print('  (ring x half-extent seen in obs p97: %.2f cm; not used)'%(np.percentile(h,97)*100))
print('ring: centre z %.2f cm, radius mean %.2f, R_in %.2f R_out %.2f cm, half-thickness(x) %.2f cm'%(zc*100,Rm*100,R_in*100,R_out*100,b_r*100))
# ---- head band (z -1.5..2 cm) excluding balls: half-thickness from 90th pct of x where not protruding
hb=sl(-0.015,0.02); face=np.percentile(hb[:,0],60); b_h=float(face-x_m)
def halfw(z0,z1):
    s=sl(z0,z1); return float(np.percentile(s[:,1],99)-y_m)   # +y side is the better-seen side
z_ht=0.020; z_hb=-0.015
w_ht=halfw(0.015,0.02); w_hb=halfw(-0.015,-0.01)
print('head: z %.1f..%.1f cm, half-widths top %.2f bottom %.2f cm, half-thickness %.2f cm'%(z_hb*100,z_ht*100,w_ht*100,w_hb*100,b_h*100))
# ---- bristle fan
bz=sl(-0.07,z_hb); z_bb=float(np.percentile(bz[:,2],0.5))
w_bb=halfw(z_bb,z_bb+0.005); w_bt=halfw(z_hb-0.005,z_hb)
b_b=float(np.percentile(bz[:,0],95)-x_m)
print('bristles: z %.2f..%.1f cm, half-widths bottom %.2f top %.2f cm, half-thickness %.2f cm'%(z_bb*100,z_hb*100,w_bb*100,w_bt*100,b_b*100))
# ---- build
def man(m): return m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices,np.float32), tri_verts=np.asarray(m.faces,np.uint32)))
def prism(z0,z1,w0,w1,b):
    pts=[]
    for z,w in [(z0,w0),(z1,w1)]:
        for yy in (-w,w):
            for xx in (-b,b): pts.append([x_m+xx,y_m+yy,z])
    return trimesh.convex.convex_hull(np.array(pts))
def torus(zc,R0,a,b,n=96,m=32):
    u=np.linspace(0,2*np.pi,n,endpoint=False); v=np.linspace(0,2*np.pi,m,endpoint=False)
    U,V=np.meshgrid(u,v,indexing='ij')
    rr=R0+a*np.cos(V); X=x_m+b*np.sin(V); Y=y_m+rr*np.cos(U); Z=zc+rr*np.sin(U)
    verts=np.c_[X.ravel(),Y.ravel(),Z.ravel()]
    F=[]
    for i in range(n):
        for j in range(m):
            a0=i*m+j; a1=((i+1)%n)*m+j; a2=((i+1)%n)*m+(j+1)%m; a3=i*m+(j+1)%m
            F+= [[a0,a1,a2],[a0,a2,a3]]
    T=trimesh.Trimesh(verts,np.array(F),process=True)
    if T.volume<0: T.invert()
    return T
ring=torus(zc,0.5*(R_in+R_out),0.5*(R_out-R_in),b_r)
head=prism(z_hb,z_ht,w_hb,w_ht,b_h)
br=prism(z_bb,z_hb+0.002,w_bb,w_bt,b_b)
M=man(ring)+man(head)+man(br)
balls=json.load(open('balls_obs.json'))
for b in balls['balls']:
    _,yc,zc_=np.array(b['centre_r7_cm'])/100; cen=[b['apex_x_cm']/100-0.007,yc,zc_]
    M=M+m3.Manifold.sphere(0.007,48).translate(cen)+m3.Manifold.cylinder(cen[0]-x_m,0.0035,0.0035,24).rotate([0,90,0]).translate([x_m,yc,zc_])
mm=M.to_mesh(); T=trimesh.Trimesh(np.asarray(mm.vert_properties)[:,:3],np.asarray(mm.tri_verts),process=False); T.merge_vertices()
print('P1: watertight',T.is_watertight,'bodies',T.body_count,'vol %.1f cm3 area %.1f cm2 faces %d extents %s cm'%(T.volume*1e6,T.area*1e4,len(T.faces),np.round(T.extents*100,2)))
T.export('meshes/P1_partprog.glb')
json.dump(dict(x_m=x_m,y_m=y_m,ring=dict(zc=zc,R_in=R_in,R_out=R_out,b=b_r),head=dict(z=[z_hb,z_ht],w=[w_hb,w_ht],b=b_h),bristle=dict(z=[z_bb,z_hb],w=[w_bb,w_bt],b=b_b)),open('meshes/P1_partprog.json','w'),indent=1)
