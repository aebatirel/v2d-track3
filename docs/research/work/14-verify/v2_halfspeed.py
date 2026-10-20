"""Pass-2: re-derive 'motion_speed 0.5 export packed as-is' score with perfect tracking: row f = source frame 0.508 f (slerp/lerp), kit-scored."""
import sys
src=open("c2_kit.py").read().split("\nrows=[]")[0]
sys.argv=["x","surf"]; exec(src)
def half(P,ratio):
    T=len(P); o=P.copy()
    for f in range(T):
        x=min(ratio*f,T-1); i=int(np.floor(x)); k=min(i+1,T-1); w=x-i
        o[f,:,:3]=(1-w)*P[i,:,:3]+w*P[k,:,:3]; o[f,:,3:]=nlerp_slerp(P[i,:,3:],P[k,:,3:],w)
    return o
for ratio in (0.508,0.5):
    rs=[score(ep,names,P,half(P,ratio)) for ep,names,P in EPS]
    d=pd.DataFrame(rs).mean(); print(ratio, d.round(3).to_dict())
