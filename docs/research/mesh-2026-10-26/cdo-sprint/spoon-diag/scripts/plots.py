"""Plots for spoon_diag.json / plotdata.npz (matplotlib). Usage: plots.py OUT_DIR"""
import json, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = sys.argv[1]; LATHE = sys.argv[2]
R = json.load(open(f'{OUT}/spoon_diag.json')); P = np.load(f'{OUT}/plotdata.npz')
C = dict(blue='#2a78d6', orange='#eb6834', aqua='#1baf7a', yellow='#eda100', violet='#6250d6')
INK, MUTED, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
                     'axes.spines.top': False, 'axes.spines.right': False, 'legend.frameon': False})


def series(rows, k):
    return np.array([r[k] if r.get(k) is not None else np.nan for r in rows], float)


for ep in ('32', '33'):
    r = R[ep]; rows = r['per_frame']; f = np.arange(len(rows)); cf = r['cup_frame']; cav = r['cavity']
    rim = float(P[f'{ep}/rim']) * 1000; floor = float(P[f'{ep}/floor']) * 1000
    fig = plt.figure(figsize=(12, 7.6))
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.9], hspace=0.38, wspace=0.22)
    ax = fig.add_subplot(gs[:, 0])
    rb, hb = P[f'{ep}/map_vis'].shape, None
    rbe = np.arange(0, 0.06, 0.002) * 1000; hbe = np.arange(-0.005, float(P[f'{ep}/rim']) + 0.01, 0.002) * 1000
    hbe = hbe[:P[f'{ep}/map_vis'].shape[1] + 1]
    ax.pcolormesh(rbe, hbe, P[f'{ep}/map_vis'].T, cmap='Greys', vmin=0, vmax=1.4, shading='flat', rasterized=True)
    rc = 0.5 * (rbe[1:] + rbe[:-1]); hc = 0.5 * (hbe[1:] + hbe[:-1])
    ax.contour(rc, hc, P[f'{ep}/map_hull'].T, levels=[0.5], colors=C['blue'], linewidths=2)
    lj = json.load(open(LATHE)); prof = np.array(lj['profile']) * 1000; off = -cf['lathe_h_of_cup_base_and_rim_mm'][0]
    ax.plot(prof[:, 0], prof[:, 1] + off, color=C['aqua'], lw=1.5, ls='--')   # own axis (2.5 deg from ours); base mapped
    ax.plot(P[f'{ep}/Rout'] * 1000 - 3, P[f'{ep}/Rout_h'] * 1000, color=MUTED, lw=1, ls=':')
    fm = int(P[f'{ep}/spoon_f']); sr, sh = P[f'{ep}/spoon_r'] * 1000, P[f'{ep}/spoon_h'] * 1000
    k = (sr < 60) & (sh > -10) & (sh < rim + 40)
    ax.scatter(sr[k], sh[k], s=2.5, color=C['orange'], alpha=0.6, lw=0, rasterized=True, zorder=5)
    ax.axhline(rim, color=INK, lw=0.8); ax.axhline(floor, color=INK, lw=0.8, ls='--')
    ax.text(58, rim + 2, 'rim', ha='right', color=INK); ax.text(58, floor + 2, 'floor (5 mm)', ha='right', color=INK)
    ax.set_xlim(0, 60); ax.set_ylim(-10, rim + 40); ax.set_xlabel('radius from cup axis (mm)'); ax.set_ylabel('height above cup base (mm)')
    ax.set_title(f'Eval {ep}: cup section (azimuthal), spoon at f{fm}', loc='left', color=INK)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color='#8a8a86', label='visual solid (grey = solid share)'), Line2D([], [], color=C['blue'], lw=2, label='CoACD pieces (50 % contour)'),
                       Line2D([], [], color=C['aqua'], lw=1.5, ls='--', label='C0 lathe profile (open cavity)'), Line2D([], [], color=MUTED, lw=1, ls=':', label='cavity edge R_out - 3 mm'),
                       Line2D([], [], marker='o', ls='', color=C['orange'], label=f'spoon solid, f{fm} (deepest)')], loc='upper right', fontsize=7.5)
    a1 = fig.add_subplot(gs[0, 1])
    d = series(rows, 'depth_below_rim_mm')
    a1.plot(f, d, color=C['orange'], lw=2, label='spoon depth below rim (in cavity cylinder)')
    a1.axhline(rim - floor, color=C['aqua'], lw=1.2, ls='--'); a1.text(len(f) - 1, rim - floor - 2, f'open cavity, rim to floor: {rim - floor:.0f} mm', ha='right', va='top', color=INK, fontsize=8)
    for key, col, lab, dy, va in (('vis_top50_h_cm', '#8a8a86', 'visual', 2, 'bottom'), ('hull_top50_h_cm', C['blue'], 'CoACD', -2, 'top')):
        if cav.get(key) is not None:
            y = rim - cav[key] * 10; a1.axhline(y, color=col, lw=1.2); a1.text(1, y + dy, f'{lab} fill top (cavity >= 50 % solid): {y:.0f} mm below rim', color=INK, fontsize=8, va=va)
    a1.set_ylabel('mm below rim'); a1.set_title('Spoon depth below the rim, inside the cavity cylinder (our reference)', loc='left', color=INK); a1.set_xlim(0, len(f) - 1)
    a1.set_ylim(0, max(rim - floor + 15, np.nanmax(d) + 10))
    a2 = fig.add_subplot(gs[1, 1])
    for key, col, lab, lw in (('cavity_cm3', C['orange'], 'spoon in cavity cylinder', 2), ('hull_cm3', C['blue'], 'spoon in CoACD pieces', 2.5),
                              ('vis_cm3', '#5f5e5a', 'spoon in visual solid', 1.2), ('lathe_cm3', C['aqua'], 'spoon in C0 lathe solid', 1.5)):
        a2.plot(f, series(rows, key), color=col, lw=lw, label=lab)
    a2.set_xlabel('reference frame (20 fps)'); a2.set_ylabel('spoon volume (cm³)'); a2.set_xlim(0, len(f) - 1)
    a2.set_title('Spoon volume inside each cup shape', loc='left', color=INK); a2.legend(loc='upper right', fontsize=8)
    fig.savefig(f'{OUT}/ev{ep}_spoon_cup.png', dpi=130, bbox_inches='tight'); plt.close(fig)

ep = '16'; r = R[ep]; rows = r['per_frame']; f = np.arange(len(rows)); sup = json.load(open(f'{OUT}/ev16_support.json'))
fig = plt.figure(figsize=(12, 11))
gs = fig.add_gridspec(3, 2, hspace=0.45, wspace=0.22, height_ratios=[1, 1, 1.1])
a1 = fig.add_subplot(gs[0, :])
for key, col, lab, lw in (('hull_cm3', C['blue'], 'spoon in rack CoACD pieces', 2.5), ('vis_cm3', '#5f5e5a', 'spoon in rack visual solid', 1.2),
                          ('hull_only_cm3', C['orange'], 'in pieces but outside visual (added by CoACD)', 1.5)):
    a1.plot(f, series(rows, key), color=col, lw=lw, label=lab)
a1.set_ylabel('spoon volume (cm³)'); a1.set_xlim(0, len(f) - 1); a1.set_ylim(0, 2)
a1.set_title('Eval 16: spoon volume inside the rack shapes (our reference)', loc='left', color=INK); a1.legend(loc='upper left', fontsize=8)
a2 = fig.add_subplot(gs[1, :])
g_ = np.array([x['gap_mm'] if x['gap_mm'] is not None else np.nan for x in sup], float); t_ = np.array([x['lowest_above_table_mm'] for x in sup], float)
a2.plot(f, np.where(g_ > 40, np.nan, g_), color=C['violet'], lw=2, label='gap spoon to rack visual solid (mm, shown when < 40)')
a2.plot(f, np.where(t_ > 40, np.nan, t_), color=C['yellow'], lw=1.5, label='spoon lowest point above the table (mm, shown when < 40)')
a2.axhline(0, color=MUTED, lw=0.8); a2.set_xlim(0, len(f) - 1); a2.set_xlabel('reference frame (20 fps)'); a2.set_ylabel('mm')
a2.set_title('What the reference spoon rests on', loc='left', color=INK); a2.legend(loc='upper right', fontsize=8)
tag = 'last'
sp = P[f'{ep}/{tag}_spoon']; rk = P[f'{ep}/{tag}_rack']; ho = P[f'{ep}/{tag}_hull_only']; ff = int(P[f'{ep}/{tag}_f'])
c = sp.mean(0); U = np.linalg.svd(sp - c, full_matrices=False)[2]
for j, (ia, ib, inorm, nm) in enumerate(((0, 1, 2, 'top'), (0, 2, 1, 'side'))):
    ax = fig.add_subplot(gs[2, j])
    def sl(X):
        q = (X - c) @ U.T; return q[np.abs(q[:, inorm]) < 0.004][:, [ia, ib]] * 100
    for X, col, a, s_ in ((rk, '#8a8a86', 0.35, 2), (ho, C['blue'], 0.5, 3), (sp, C['orange'], 0.6, 2)):
        if len(X):
            q = sl(X); ax.scatter(q[:, 0], q[:, 1], s=s_, color=col, alpha=a, lw=0, rasterized=True)
    ax.set_aspect('equal'); ax.set_xlabel('along spoon (cm)'); ax.set_ylabel(('across' if nm == 'top' else 'normal to') + ' spoon (cm)')
    ax.set_title(f'f{ff}, {nm} section (slab ±4 mm through the spoon)', loc='left', color=INK)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker='o', ls='', color='#8a8a86', label='rack visual solid'),
                       Line2D([], [], marker='o', ls='', color=C['blue'], label='added by CoACD'),
                       Line2D([], [], marker='o', ls='', color=C['orange'], label='spoon')], loc='lower left', fontsize=7)
fig.savefig(f'{OUT}/ev16_spoon_rack.png', dpi=130, bbox_inches='tight'); plt.close(fig)
print('plots ok')
