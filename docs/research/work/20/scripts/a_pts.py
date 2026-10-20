# Stage A0: container timestamps per camera; frame counts vs parquet rows.
import subprocess, numpy as np, os, json, sys
import pyarrow.parquet as pq
D='/Users/aebatirel/Documents/Code/v2d-research/data/track_3'
def pts(f):
    o=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','packet=pts_time,flags','-of','csv=p=0',f],capture_output=True,text=True,timeout=120).stdout.split()
    t=np.array(sorted(float(x.split(',')[0]) for x in o))
    return t
res={}
for split in ['public','evaluation']:
    for e in range(46):
        fs={c:f'{D}/{split}/videos/chunk-000/observation.images.ego_cam_{c}/episode_{e:06d}.mp4' for c in 'abc'}
        if not all(os.path.exists(f) for f in fs.values()): continue
        r={}
        for c,f in fs.items():
            t=pts(f); d=np.diff(t)
            r[c]=dict(n=len(t),t0=float(t[0]),dmin=float(d.min()),dmax=float(d.max()))
        pqf=f'{D}/public/data/chunk-000/episode_{e:06d}.parquet'
        if split=='public' and os.path.exists(pqf):
            df=pq.read_table(pqf,columns=['capture_time','frame_index']).to_pandas()
            ct=df.capture_time.values.astype(float); dd=np.diff(ct)
            r['pq']=dict(n=len(df),ct0=float(ct[0]),dmean=float(dd.mean()),dmin=float(dd.min()),dmax=float(dd.max()))
        res[f'{split[0]}{e}']=r
        print(split,e,{c:(r[c]['n'],round(r[c]['t0'],4),round(r[c]['dmin'],4),round(r[c]['dmax'],4)) for c in 'abc'},r.get('pq'),flush=True)
json.dump(res,open('/Users/aebatirel/Documents/Code/v2d-research/work/20/out/a_pts.json','w'),indent=1)
