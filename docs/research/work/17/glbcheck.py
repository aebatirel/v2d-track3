import trimesh, numpy as np, os
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh'
for n in sorted(os.listdir(R)):
    p=f'{R}/{n}/{n}.glb'
    if not os.path.exists(p): p=f'{R}/{n}/{n}_visual.glb'
    s=trimesh.load(p)
    gs=list(s.geometry.values())
    d=s.dump(concatenate=True)
    g=gs[0]
    print(n, len(gs), 'nverts',len(g.vertices),'graph T identity?', np.allclose(d.vertices[:5],g.vertices[:5]) if len(gs)==1 else 'multi', 'ext mm',np.round(np.ptp(d.vertices,0)*1000,1), 'winding_ok',g.is_winding_consistent, 'watertight', g.is_watertight, 'vol sign', np.sign(g.volume) if g.is_watertight else None)
