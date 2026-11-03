import numpy as np, json, sys
from scipy.ndimage import median_filter
S='/tmp/claude-0/-home-user-v2d-track3/179e384c-3df3-5902-b468-f503474d35e9/scratchpad'
NAMES=['wooden_piece_1','wooden_piece_2']
def spans(flag):
    idx=np.nonzero(flag)[0]; out=[]
    if not len(idx): return out
    s0=p0=idx[0]
    for j in idx[1:]:
        if j-p0<=3: p0=j; continue
        if p0-s0+1>=5: out.append([int(s0),int(p0)])
        s0=p0=j
    if p0-s0+1>=5: out.append([int(s0),int(p0)])
    return out
def spanflag(d,tau,alt='ROLL'):
    fl=d< -tau; m=np.zeros(len(d),bool)
    for a,b in spans(fl): m[a:b+1]=True
    return m
def dser(z,n,alt='ROLL'):
    d=z[f'{n}_{alt}']-z[f'{n}_REF']; return median_filter(np.nan_to_num(d),5,mode='nearest')
if __name__=='__main__':
    data=[]
    for e in (23,24):
        z=np.load(f'{S}/bface/pub{e}.npz'); pf=np.load(f'{S}/srpub/ep{e}_pf.npz'); ori=np.degrees(pf['ori']); names=list(pf['names'])
        for n in NAMES:
            T=min(len(z[f'{n}_REF']),len(ori)); truth=ori[:T,names.index(n)]>135
            data.append((e,n,dser(z,n)[:T],truth))
    for tau in (3,5,8,12,16,20):
        fp=sum(int((spanflag(d,tau)&~t).sum()) for *_,d,t in data); neg=sum(int((~t).sum()) for *_,d,t in data)
        tp=sum(int((spanflag(d,tau)&t).sum()) for *_,d,t in data); pos=sum(int(t.sum()) for *_,d,t in data)
        print(f'tau {tau}: false-flag {fp}/{neg} = {fp/neg:.3f}  recall {tp}/{pos} = {tp/max(pos,1):.3f}', {f'{e}/{n[-1]}':spans(spanflag(d,tau)) for e,n,d,t in data})
    for e,n,d,t in data:
        print(e,n,'d median nonflip %.1f flip %.1f'%(np.median(d[~t]), np.median(d[t]) if t.any() else np.nan), 'frac d==0 %.2f'%np.mean(d==0))
