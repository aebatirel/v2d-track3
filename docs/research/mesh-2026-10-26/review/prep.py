import json, sys, os, glob, numpy as np, trimesh
R='/home/user/v2d-track3'; OUT=sys.argv[1]
G='docs/research/mesh-2026-10-26'
items = {
 'pot_lib':   'meshes/library_v3/white_pot.glb',
 'pot_c0':    'meshes/library_c0/white_pot.glb',
 'pot_e0b':   'meshes/library_e0b/white_pot.glb',
 'lid_lib':   'meshes/library_v3/white_pot_lid.glb',
 'lid_c0':    'meshes/library_c0/white_pot_lid.glb',
 'rack_lib':  'meshes/library_v3/plastic_dish_rack.glb',
 'rack_c0':   'meshes/library_c0/plastic_dish_rack.glb',
 'rack_c2r':  G+'/cdo-sprint/C2/R-rack/meshes/plastic_dish_rack_c2r_K_ep12_nomk.glb',
 'cup_lib':   'meshes/library_v3/blue_cup.glb',
 'cup_c0':    'meshes/library_c0/blue_cup.glb',
 'beige_lib': 'meshes/library_v3/beige_cup.glb',
 'beige_t1':  G+'/cdo-sprint/C1/T1-beige-lathe/meshes/ep11_beige_cup_sep_g1.glb',
 'beige_e0b': 'meshes/library_e0b/beige_cup.glb',
 'pan_lib':   'meshes/library_v3/mini_dust_pan.glb',
 'pan_t2':    G+'/cdo-sprint/C1/T2-probe-picks/meshes/mini_dust_pan_k297_s42_lib.glb',
 'pitcher_lib': 'meshes/library_v3/water_pitcher.glb',
 'pitcher_c2p': G+'/cdo-sprint/C2/P-pitcher/meshes/ep22_water_pitcher_g1_a2.glb',
 'board1_lib': 'meshes/library_v3/wooden_piece_1.glb',
}
info={}
MAXF=24000
for k,p in items.items():
    m = trimesh.load(os.path.join(R,p), force='mesh')
    f0 = len(m.faces)
    if f0 > MAXF:
        m = m.simplify_quadric_decimation(face_count=MAXF)
    m.visual = trimesh.visual.ColorVisuals(m)  # strip colour/texture; the page colours by role
    m.export(f'{OUT}/{k}.glb')
    info[k] = dict(src=p, faces_src=f0, faces=len(m.faces), ext_mm=(m.extents*1000).round(0).tolist(), bytes=os.path.getsize(f'{OUT}/{k}.glb'))
# board-slot round 3 low-piece boxes (ep24 record, DO_NOT_USE) : merge pieces per board into one GLB
B = G+'/gmg/build/I/results/slot3-ep24/fi4q/r0'
for b in ('wooden_piece_1','wooden_piece_2'):
    ps = sorted(glob.glob(os.path.join(R,B,b,'piece_*.obj')))
    parts = [trimesh.load(q, force='mesh') for q in ps]
    sc = trimesh.Scene()
    for i,q in enumerate(parts): sc.add_geometry(q, node_name=f'piece_{i:02d}')
    sc.export(f'{OUT}/slot3_{b}.glb')
    info['slot3_'+b] = dict(src=B+'/'+b, pieces=len(parts), bytes=os.path.getsize(f'{OUT}/slot3_{b}.glb'))
json.dump(info, open(f'{OUT}/../mesh_info.json','w'), indent=1)
for k,v in info.items(): print(k, v)
