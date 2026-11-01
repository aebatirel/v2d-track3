import sys, numpy as np, mujoco
m = mujoco.MjModel.from_xml_path(sys.argv[1]); d = mujoco.MjData(m)
B = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)
J = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)
mujoco.mj_forward(m, d)
P = lambda n: d.xpos[B(n)].copy()
chains = {'thumb':['firstmc_r','proximal_thumb_r','distal_thumb_r'],
          'index':['secondmc_r','2proxph_r','midph2_r','distph2_r'],
          'middle':['thirdmc_r','3proxph_r','midph3_r','distph3_r'],
          'ring':['fourthmc_r','4proxph_r','midph4_r','distph4_r'],
          'little':['fifthmc_r','5proxph_r','midph5_r','distph5_r']}
print('segment lengths between body origins (mm):')
for f,c in chains.items():
    L=[np.linalg.norm(P(c[i+1])-P(c[i]))*1000 for i in range(len(c)-1)]
    print(' ',f, [round(float(x),1) for x in L], '(first = MC body origin to MCP: not the full metacarpal)')
print('MCP spacing index->little (2proxph to 5proxph) mm', round(np.linalg.norm(P('2proxph_r')-P('5proxph_r'))*1000,1))
print('MCP spacing index->middle, middle->ring, ring->little',[round(np.linalg.norm(P(a)-P(b))*1000,1) for a,b in [('2proxph_r','3proxph_r'),('3proxph_r','4proxph_r'),('4proxph_r','5proxph_r')]])
# distal tip: farthest point of distal capsule geoms
for f,c in chains.items():
    b=B(c[-1]); gs=[g for g in range(m.ngeom) if m.geom_bodyid[g]==b and m.geom_contype[g]]
    far=0
    for g in gs:
        far=max(far, np.linalg.norm(d.geom_xpos[g]-P(c[-1]))+m.geom_size[g].max())
    print('  distal origin->approx tip',f, round(far*1000,1),'mm')
hand_bodies=[i for i in range(m.nbody) if m.body(i).name in sum(chains.values(),[])+['lunate_r','capitate_r','scaphoid_r','trapezium_r','trapezoid_r','hamate_r','pisiform_r','triquetrum_r']]
print('mass of carpals+MC+phalanges (kg)', round(sum(m.body_mass[i] for i in hand_bodies),4))
print('finger joint damping/armature', [ (m.joint(j).name, round(float(m.dof_damping[m.jnt_dofadr[j]]),3), float(m.dof_armature[m.jnt_dofadr[j]])) for j in [J('mcp2_flexion_r'),J('pm2_flexion_r'),J('md2_flexion_r'),J('cmc_flexion')]])
# per-joint muscle torque capacity: see myohand_torque.py
