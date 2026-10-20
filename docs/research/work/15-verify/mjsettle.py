# Approximate (NOT the evaluator) MuJoCo CPU settle test of public-GT frame-0 contact states with pinned-CoACD hulls.
# Settings mirror flash_chord sim/rl.yaml: dt 0.01, implicitfast, Newton solver, pyramidal cone, impratio 20,
# friction 1.0, margin 0; contact softness = MuJoCo default solref (0.02, 1) [assumption: Newton ke/kd mapping unverified].
import sys, os, numpy as np
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),'pylibmj'))
import mujoco
from scipy.spatial.transform import Rotation as Rot
import penv as P
INER={'mini_sweeper':(0.00251588,0.00207442,0.00118396),'plastic_dish_rack':(0.00722555,0.00672021,0.00081938),
      'white_pot':(0.00134675,0.00073265,0.00064751),'white_pot_lid':(0.00068732,0.00052155,0.00019193),
      'blue_cup':None}
def body_xml(n,R,t,hulls):
    q=Rot.from_matrix(R).as_quat(); q=[q[3],q[0],q[1],q[2]]
    I=INER[n]; geoms=''.join(f'<geom type="mesh" mesh="{n}_{i}" density="0"/>' for i in range(len(hulls)))
    return (f'<body name="{n}" pos="{t[0]} {t[1]} {t[2]}" quat="{q[0]} {q[1]} {q[2]} {q[3]}"><freejoint/>'
            f'<inertial pos="0 0 0" mass="0.3" diaginertia="{I[0]} {I[1]} {I[2]}"/>{geoms}</body>')
def build(objs,ztop,solref):
    assets=''; bodies=''
    for n,R,t in objs:
        H=P.load_hulls(n)
        for i,(v,_) in enumerate(H): assets+=f'<mesh name="{n}_{i}" vertex="{" ".join("%.6f"%x for x in v.ravel())}"/>'
        bodies+=body_xml(n,R,t,H)
    xml=(f'<mujoco><option timestep="0.01" integrator="implicitfast" solver="Newton" cone="pyramidal" impratio="20" '
         f'iterations="100" ls_iterations="50"/><default><geom friction="1 0.005 0.0001" condim="3" margin="0" solref="{solref}"/></default>'
         f'<asset>{assets}</asset><worldbody><geom name="table" type="box" size="1 1 0.05" pos="0 0 {ztop-0.05}"/>{bodies}</worldbody></mujoco>')
    return mujoco.MjModel.from_xml_string(xml)
def run(tag,objs,ztop,solref='0.02 1',T=(0.05,0.25,1.0)):
    m=build(objs,ztop,solref); d=mujoco.MjData(m); mujoco.mj_forward(m,d)
    p0={n:(d.body(n).xpos.copy(),d.body(n).xquat.copy()) for n,_,_ in objs}
    out=[]; t=0; 
    for Tt in T:
        while d.time<Tt-1e-9: mujoco.mj_step(m,d)
        s=[]
        for n,_,_ in objs:
            x,q=d.body(n).xpos,d.body(n).xquat
            dq=Rot.from_quat([q[1],q[2],q[3],q[0]])*Rot.from_quat([p0[n][1][1],p0[n][1][2],p0[n][1][3],p0[n][1][0]]).inv()
            dx=(x-p0[n][0])*1e3
            s.append(f'{n} d={np.linalg.norm(dx):.1f}mm (dz {dx[2]:+.1f}) rot={np.degrees(dq.magnitude()):.1f}deg')
        out.append(f't={Tt:.2f}s: '+'; '.join(s))
    print(f'[{tag}] ncon0={d.ncon}'); [print('   ',o) for o in out]
def gt(ep,f,names):
    return [(n,)+P.pose(ep,f,n) for n in names]
def minz(n,R,t): return min(((v@R.T)+t)[:,2].min() for v,_ in P.load_hulls(n))
if __name__=='__main__':
    sol=os.environ.get('SOLREF','0.02 1')
    ep,f,a,b=31,0,'mini_sweeper','plastic_dish_rack'
    O=gt(ep,f,[a,b]); zt=minz(*O[1])
    print('ep31 f0 table top (rack hull min z)=%.4f, sweeper hull min z=%.4f'%(zt,minz(*O[0])))
    run('ep31 f0 sweeper+rack (GT)',O,zt,sol)
    run('ep31 f0 rack alone',[O[1]],zt,sol)
    Rs,ts=O[0][1],O[0][2].copy(); ts[2]+=zt-minz(a,Rs,ts)
    run('sweeper alone on table (same orientation)',[(a,Rs,ts)],zt,sol)
    O=gt(0,0,['white_pot_lid','white_pot']); zt=minz(*O[1])
    run('ep0 f0 lid+pot (GT)',O,zt,sol)
    run('ep0 f0 pot alone',[O[1]],zt,sol)
