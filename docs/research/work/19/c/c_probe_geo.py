import numpy as np
B='/Users/aebatirel/Documents/Code/v2d-research/work/19/b/FG'
d=np.load(f'{B}/white_pot.npz'); f,lo,h=d['f'],d['lo'],float(d['h']); print('pot grid',f.shape,lo)
S=f<0
# occupancy profile along x at the body centre column (find body centre in y,z from the x-projection)
proj=S.any(0); ys,zs=np.where(proj); 
jc=int(np.median(ys)); 
# body = circular part: use z-range where y-extent is large
wid=np.array([proj[:,k].sum() for k in range(S.shape[2])]); body=np.where(wid>150)[0]; kc=int(np.median(body))
print('body centre idx y',jc,'z',kc,'-> mm',lo[1]*1e3+jc,lo[2]*1e3+kc,' body z idx range',body.min(),body.max())
col=S[:,jc,kc]; xs=np.where(col)[0]; print('centre column solid x mm:',[round(lo[0]*1e3+i,1) for i in xs[:3]],'...',[round(lo[0]*1e3+i,1) for i in xs[-3:]], 'n',len(xs))
d=np.load(f'{B}/plastic_dish_rack.npz'); f,lo=d['f'],d['lo']; S=f<0; print('rack grid',f.shape,lo)
# height (along +x, up) top map in y,z at 12 mm blocks
xi=np.arange(S.shape[0]); top=np.where(S.any(0),(S*xi[:,None,None]).max(0),-1)
base=np.where(S.any((1,2)))[0].min()
for j in range(0,S.shape[1],12):
    print(''.join('.' if top[j:j+12,k:k+12].max()<0 else 'A' if top[j:j+12,k:k+12].max()-base>=100 else str((top[j:j+12,k:k+12].max()-base)//10) for k in range(0,S.shape[2],12)))
