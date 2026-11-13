import numpy as np, sys
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
EP = int(sys.argv[1]) if len(sys.argv) > 1 else 0
step = int(sys.argv[2]) if len(sys.argv) > 2 else 10
d = np.load(f'{S}/leak/diag_ep{EP}/out/perframe.npz')
names = sorted({k.split('mocap_speed_')[1] for k in d.files if k.startswith('mocap_speed_')})
N = len(d[f'mocap_speed_{names[0]}'])
arms = sorted({k.split('_')[0] for k in d.files if k.split('_')[0] in ('Ps', 'Po', 'Pr', 'Po2')})
for n in names:
    print('==', n)
    hdr = 'f    v_cms  w_dps  hand  ' + ('reld  ' if 'lid_rel_d' in d.files else '') + '  '.join(f'{a}:kADD  kT   kR | gADD   gT   gR  ' + ('tilt' if f'{a}_ind_axis_tilt_deg_{n}' in d.files else '') for a in arms)
    print(hdr)
    for i in list(range(0, N, step)) + [N - 1]:
        row = f'{i:3d} {d[f"mocap_speed_{n}"][i]:6.1f} {d[f"mocap_angvel_{n}"][i]:6.1f} {d[f"hand_{n}"][i] if f"hand_{n}" in d.files else np.nan:5.1f} '
        if 'lid_rel_d' in d.files: row += f'{d["lid_rel_d"][i]:5.1f} '
        for a in arms:
            row += f' {d[f"{a}_add_{n}"][i]:6.1f} {d[f"{a}_t_{n}"][i]:5.1f} {d[f"{a}_r_{n}"][i]:5.1f} | {d[f"{a}_ind_add_cm_{n}"][i]:5.1f} {d[f"{a}_ind_t_cm_{n}"][i]:5.1f} {d[f"{a}_ind_rot_deg_{n}"][i]:5.1f} '
            if f'{a}_ind_axis_tilt_deg_{n}' in d.files: row += f'{d[f"{a}_ind_axis_tilt_deg_{n}"][i]:5.1f} '
        print(row)
