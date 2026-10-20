# Field of b_remesh2.py (W2) as a reusable function: returns f (grid, + outside), grid origin lo, spacing h.
import numpy as np, igl
from scipy import ndimage
from common import *
def w2_field(n,h,t):
    m=scan_welded(n); V=np.ascontiguousarray(m.vertices,float); F=np.ascontiguousarray(m.faces,np.int64)
    lo=m.bounds[0]-4*h; hi=m.bounds[1]+4*h; N=np.ceil((hi-lo)/h).astype(int)+1
    G=np.stack(np.meshgrid(*[lo[i]+h*np.arange(N[i]) for i in range(3)],indexing='ij'),-1).reshape(-1,3)
    S=np.empty(len(G)); B=1_000_000
    for i in range(0,len(G),B): S[i:i+B]=igl.signed_distance(G[i:i+B],V,F,igl.SIGNED_DISTANCE_TYPE_PSEUDONORMAL)[0]
    S=S.reshape(N); U=np.abs(S); r=0.6*h
    lab,_=ndimage.label(U>r)
    bl=np.unique(np.concatenate([lab[0].ravel(),lab[-1].ravel(),lab[:,0].ravel(),lab[:,-1].ravel(),lab[:,:,0].ravel(),lab[:,:,-1].ravel()]))
    core=np.isin(lab,bl[bl>0])
    return np.where(U<=r,S,np.where(core,np.where(S>=0,U,U-t),-U)), lo
def nudge(f,dl,h):
    eps=0.05*h; return np.where(np.abs(f-dl)<eps, dl+np.where(f>=dl,eps,-eps), f)
