# [D] Kit CD-O (metric_code/track_3/CD-O.py _object_chamfer_cm, imported directly) on budget_mesh'd candidate and scan.
import sys, json, importlib.util, numpy as np, time
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
K=f'{S}/kit/v2d_submission_kit'; sys.path.insert(0,K)
from v2dlb.mesh_budget import budget_mesh
spec=importlib.util.spec_from_file_location('cdo',f'{K}/metric_code/track_3/CD-O.py'); cdo=importlib.util.module_from_spec(spec); spec.loader.exec_module(cdo)
SCAN=f'{S}/loc/t3/mesh/mini_sweeper/mini_sweeper_visual.glb'
rv,rf=budget_mesh(SCAN,4096,4096)
label,path=sys.argv[1],sys.argv[2]
cv,cf=budget_mesh(path,4096,4096)
seeds=[19000057,30000090,11,22,33,44]
vals=[float(cdo._object_chamfer_cm((np.asarray(rv,float),np.asarray(rf,np.int64)),(np.asarray(cv,float),np.asarray(cf,np.int64)),s)) for s in seeds]
rec=dict(label=label,path=path,cdo_cm=[round(v,4) for v in vals],cdo_eval_mean=round(float(np.mean(vals[:2])),4),cdo_all_mean=round(float(np.mean(vals)),4),time=time.strftime('%H:%M:%S'))
print(json.dumps(rec)); open(f'{S}/diag/sweeper_verify/cdo.jsonl','a').write(json.dumps(rec)+'\n')
