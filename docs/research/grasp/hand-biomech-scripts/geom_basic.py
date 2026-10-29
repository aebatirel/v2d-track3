import sys, json, numpy as np, trimesh
lib = sys.argv[1]; out = sys.argv[2]
names = ['mini_sweeper','mini_dust_pan','wooden_piece_1','wooden_piece_2','water_pitcher','white_pot','white_pot_lid','blue_cup']
res = {}
for n in names:
    m = trimesh.load(f'{lib}/{n}.glb', force='mesh')
    v = m.vertices
    c = v.mean(0)
    U,S,Vt = np.linalg.svd(v-c, full_matrices=False)
    ext_obj = (v.max(0)-v.min(0))*100
    p = (v-c)@Vt.T
    ext_pca = (p.max(0)-p.min(0))*100
    vol = float(m.volume)*1e6 if m.is_watertight else None
    res[n] = dict(ext_obj_cm=ext_obj.round(1).tolist(), ext_pca_cm=ext_pca.round(1).tolist(),
                  bbox_min=v.min(0).round(3).tolist(), bbox_max=v.max(0).round(3).tolist(),
                  watertight=bool(m.is_watertight), volume_cm3=vol, area_cm2=float(m.area)*1e4,
                  pca_axes=Vt.round(3).tolist())
    print(n, res[n])
json.dump(res, open(out,'w'), indent=1)
