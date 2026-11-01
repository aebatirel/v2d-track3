import sys, numpy as np, mujoco
m = mujoco.MjModel.from_xml_path(sys.argv[1])
J = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)
def capacity(post, joints):
    d=mujoco.MjData(m)
    for jn,v in post.items(): d.qpos[m.jnt_qposadr[J(jn)]]=v
    mujoco.mj_forward(m,d)
    mom=np.zeros((m.nu,m.nv)); mujoco.mju_sparse2dense(mom, d.actuator_moment, d.moment_rownnz, d.moment_rowadr, d.moment_colind)
    base=d.qfrc_actuator.copy()
    out={}
    for jn in joints:
        dof=m.jnt_dofadr[J(jn)]; r=[]
        for sgn in (+1,-1):
            sel=[i for i in range(m.nu) if sgn*mom[i,dof]>1e-5]
            dd=mujoco.MjData(m); dd.qpos[:]=d.qpos
            for i in sel: dd.ctrl[i]=1.0; dd.act[m.actuator_actadr[i]]=1.0
            mujoco.mj_forward(m,dd); r.append(float(dd.qfrc_actuator[dof]-base[dof]))
        out[jn]=(round(max(r),2), round(min(r),2))
    return out
fingers=['mcp2_flexion_r','pm2_flexion_r','md2_flexion_r','mcp3_flexion_r','pm3_flexion_r','md3_flexion','mcp4_flexion_r','pm4_flexion','md4_flexion_r','mcp5_flexion_r','pm5_flexion_r','md5_flexion_r','mcp2_abduction_r','mcp5_abduction_r']
thumb=['cmc_flexion','cmc_abduction','mp_flexion_r','ip_flexion_r']
for name,post in [('neutral (all 0)',{}),('MCP45/PIP45/DIP10',{j:v for j,v in zip(fingers[:12],[0.785,0.785,0.175]*4)})]:
    print('posture',name)
    for k,v in capacity(post, fingers+thumb).items(): print(f'   {k:18s} max+ {v[0]:6.2f}  max- {v[1]:6.2f} N m')
