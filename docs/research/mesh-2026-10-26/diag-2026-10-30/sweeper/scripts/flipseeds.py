# [D] flip rate over 24 extra random seeds (registration only, kit _register_object_body); same meshes as S01/S02
import sys, json, numpy as np
sys.path.insert(0,'/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts')
import mesh_metric as MM
ref=MM.reference('mini_sweeper')
out={}
for label,path in [('library_v3','/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb'),('M2_libsym_balls','meshes/M2_libsym_balls.glb')]:
    v,f,_=MM.load_candidate(path); rows=[]
    for s in range(1000,1024):
        ca,R=MM.auc._register_object_body((v,f),(ref['v'],ref['f']),ref['anchor'],s)
        rows.append(MM.angle_deg(R))
    out[label]=rows
    print(label,'flips %d/24'%sum(r>90 for r in rows), 'median rot %.1f'%np.median(rows), flush=True)
json.dump(out,open('flipseeds.json','w'))
