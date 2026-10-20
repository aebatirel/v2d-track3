import trimesh, numpy as np
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh'
for n,f in [('white_pot_lid','white_pot_lid/white_pot_lid.glb'),('plastic_dish_rack','plastic_dish_rack/plastic_dish_rack.glb')]:
    import os
    if not os.path.exists(f'{R}/{f}'): print('missing',f, os.listdir(f'{R}/{n}')); continue
    m=trimesh.load(f'{R}/{f}',force='mesh'); m.merge_vertices(merge_tex=True,merge_norm=True)
    _,c=np.unique(m.edges_sorted,axis=0,return_counts=True)
    print(n,'welded V',len(m.vertices),'watertight',m.is_watertight,'edges !=2',int((c!=2).sum()),'boundary(1)',int((c==1).sum()),'>2',int((c>2).sum()))
