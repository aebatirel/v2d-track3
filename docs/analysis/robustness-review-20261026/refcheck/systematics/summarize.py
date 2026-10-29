"""Markdown tables from systematics.py / lagdrift.py outputs (refcheck/systematics). Usage:
python -I summarize.py systematics_all.json lagdrift.json > tables.md"""
import json, sys
import numpy as np

R = json.load(open(sys.argv[1])); LD = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else None
EPS = sorted(R, key=int)


def main_src(r):
    return 'ref' if 'ref' in r['sources'] else 'perc'


def f(x, n=3):
    return '-' if x is None else (f'{x:.{n}f}' if isinstance(x, float) else str(x))


def short(n):
    return {'white_pot': 'pot', 'white_pot_lid': 'lid', 'blue_cup': 'bcup', 'beige_cup': 'gcup', 'plastic_dish_rack': 'rack',
            'mini_sweeper': 'swp', 'mini_dust_pan': 'pan', 'water_pitcher': 'pitch', 'wooden_piece_1': 'b1', 'wooden_piece_2': 'b2'}.get(n, n)


print('### Scale and time (source: ref = final reference, perc = perception)\n')
print('| ep | src | s joint (gt->ours) | s surface-centroid | mocap spread cm | rmse rigid / sim mm | per-object s | disp ratio (median) | inter-object rest ratio (diff mm) | lag xcorr (frames) | lag rmse-min |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for ep in EPS:
    for src in ('ref', 'perc'):
        r = R[ep]['sources'].get(src)
        if not r:
            continue
        sc = r['scale']; j = sc['joint']; tm = r['time']
        po = ', '.join(f"{short(n)} {f(v['s'])}" for n, v in sc['per_object'].items())
        dr = ', '.join(f"{short(n)} {f(v['disp_ratio_median'])}" for n, v in sc['per_object'].items())
        io = sc.get('inter_object_rest')
        ios = f"{io['ratio']:.3f} ({io['diff_mm']:+.0f})" if io else '-'
        lag = ', '.join(f"{short(n)} {v['xcorr_lag_frames']:+.2f}" for n, v in tm.items() if isinstance(v, dict) and 'xcorr_lag_frames' in v) or '-'
        lr = ', '.join(f"{short(n)} {v['rmse_min_shift_frames']:+.2f}" for n, v in tm.items() if isinstance(v, dict) and 'rmse_min_shift_frames' in v) or '-'
        print(f"| {ep} | {src} | {j['s']:.4f} | {j['s_surface_centroids']:.4f} | {j['mocap_spread_cm']:.1f} | {j['rmse_rigid_mm']:.1f} / {j['rmse_similarity_mm']:.1f} | {po} | {dr} | {ios} | {lag} | {lr} |")

print('\n### Up axis and rest tilt (degrees)\n')
print('| ep | src | kit frame-0 alignment: table normal vs mocap z | rigid position fit | rest orientation per object | between objects | rest tilt per object pre/post (median) | kit residual at rest pre/post |')
print('|---|---|---|---|---|---|---|---|')
for ep in EPS:
    for src in ('ref', 'perc'):
        r = R[ep]['sources'].get(src)
        if not r:
            continue
        u = r['up_axis']; rb = r['rotation_bias']
        ro = ', '.join(f"{short(n)} {v['angle']:.1f}" for n, v in u['rest_orientation_deg'].items())
        tl = ', '.join(f"{short(n)} " + '/'.join(f"{v[s]['tilt_deg']:.1f}" if s in v else '-' for s in ('pre', 'post')) for n, v in rb.items())
        kr = ', '.join(f"{short(n)} " + '/'.join(f"{v[s]['kit_residual_deg']:.1f}" if s in v else '-' for s in ('pre', 'post')) for n, v in rb.items())
        print(f"| {ep} | {src} | {u['kit_alignment_deg']:.2f} | {u['rigid_position_fit_deg']:.2f} (extent {min(u['position_fit_conditioning']['mocap_extent_cm']):.0f} cm) | {ro} | {f(u.get('rest_orientation_between_objects_deg'), 1)} | {tl} | {kr} |")

print('\n### Resting height (mm; float > 0 = our object higher than mocap; pre / post segments)\n')
print('| ep | src | mocap table z (from) | lowest point above table: ours vs mocap | float (lowest point) | centre-height error | relative centre height (obj2 - obj1) error | kit-aligned vertical error at rest |')
print('|---|---|---|---|---|---|---|---|')
for src_list in (('ref', 'pre', 'perc'),):
    for ep in EPS:
        for src in src_list:
            r = R[ep]['sources'].get(src)
            if not r:
                continue
            h = r['rest_height']; names = R[ep]['objects']
            seg = lambda n, k: '/'.join(f"{h[n][s][k]:+.0f}" if s in h[n] else '-' for s in ('pre', 'post'))
            lo = ', '.join(f"{short(n)} " + '/'.join(f"{h[n][s]['ours_lowest_above_table_mm']:.0f}:{h[n][s]['mocap_lowest_above_table_mm']:.0f}" if s in h[n] else '-' for s in ('pre', 'post')) for n in names)
            fl = ', '.join(f"{short(n)} {seg(n, 'float_mm')}" for n in names)
            ce = ', '.join(f"{short(n)} {seg(n, 'centre_height_error_mm')}" for n in names)
            rel = [v for k, v in h.items() if k.endswith('_centre_height')]
            rels = '/'.join(f"{rel[0][s]['error_mm']:+.0f}" if s in rel[0] else '-' for s in ('pre', 'post')) if rel else '-'
            ve = r['kit_aligned_vertical_error_mm']
            ves = ', '.join(f"{short(n)} " + '/'.join(f"{v[s]:+.0f}" if s in v else '-' for s in ('pre', 'post')) for n, v in ve.items())
            print(f"| {ep} | {src} | {h['mocap_table_z_m']:.4f} ({short(h['mocap_table_from'])}) | {lo} | {fl} | {ce} | {rels} | {ves} |")

print('\n### AUC cost of each systematic (oracle correction of our path, kit registered AUC with our meshes)\n')
print('| ep | src | base AUC | +scale (s) | +time (lag) | +rest height | +tilt bias | all | per-object base |')
print('|---|---|---|---|---|---|---|---|---|')
tot = {}
for ep in EPS:
    for src in ('ref', 'perc', 'pre'):
        r = R[ep]['sources'].get(src)
        if not r or 'auc_oracle_corrections' not in r:
            continue
        a = r['auc_oracle_corrections']
        if src == 'pre':
            print(f"| {ep} | pre | {a['base']['AUC']:.4f} | | | | | | {', '.join(f'{short(n)} {v:.3f}' for n, v in a['base']['per_obj'].items())} |")
            continue
        for k in ('base', 'scale', 'time', 'height', 'tilt', 'all'):
            tot.setdefault(src, {}).setdefault(k, []).append(a[k]['AUC'])
        print(f"| {ep} | {src} | {a['base']['AUC']:.4f} | {a['scale']['delta']:+.4f} ({a['scale']['s_applied']:.3f}) | {a['time']['delta']:+.4f} ({a['time']['lag_applied_frames']:+.2f}) | "
              f"{a['height']['delta']:+.4f} | {a['tilt']['delta']:+.4f} | {a['all']['delta']:+.4f} | {', '.join(f'{short(n)} {v:.3f}' for n, v in a['base']['per_obj'].items())} |")
for src, d in tot.items():
    b = np.mean(d['base'])
    print(f"| mean ({len(d['base'])} eps) | {src} | {b:.4f} | {np.mean(d['scale']) - b:+.4f} | {np.mean(d['time']) - b:+.4f} | {np.mean(d['height']) - b:+.4f} | {np.mean(d['tilt']) - b:+.4f} | {np.mean(d['all']) - b:+.4f} | |")

if LD:
    print('\n### Lag drift along the episode (windowed speed cross-correlation)\n')
    print(f"Pooled within-episode slope {LD['pooled_within_episode_slope_frames_per_100']:+.3f} +- {LD['slope_se_per_100']:.3f} frames per 100 frames "
          f"(H-drift predicts +{LD['predicted_slope_if_mocap_on_timestamp_grid_per_100']}); {LD['windows']} windows; median lag {LD['lag_median_all_windows']:+.2f} "
          f"(IQR {LD['lag_iqr'][0]:+.2f} .. {LD['lag_iqr'][1]:+.2f}) frames.\n")
    print('| ep | src | windows | median lag | first half | second half | slope per 100 frames | clock offset slope per 100 |')
    print('|---|---|---|---|---|---|---|---|')
    for ep, v in sorted(LD['per_episode'].items(), key=lambda kv: int(kv[0])):
        print(f"| {ep} | {v['source']} | {v['windows']} | {v['lag_median']:+.2f} | {f(v['lag_first_half'], 2)} | {f(v['lag_second_half'], 2)} | {f(v['slope_frames_per_100'], 2)} | {v['clock_offset_slope_per_100']:.2f} |")

# ---- one row per public episode (main source: final reference where one exists, else perception)
FS = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
print('\n### Per-episode summary (main source = final reference where one exists, else perception)\n')
print('| ep | objects | src | s (gt->ours) | lag frames | kit up deg | rest tilt deg (max obj) | worst rest centre-height error mm | AUC base | d time | d height | d tilt | d all | fixed +0.5 frame | snap (pre - perc) |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for ep in EPS:
    src = main_src(R[ep]); r = R[ep]['sources'][src]; a = r['auc_oracle_corrections']
    lags = [v['xcorr_lag_frames'] for v in r['time'].values() if isinstance(v, dict) and 'xcorr_lag_frames' in v]
    tl = max((v[s]['tilt_deg'], short(n)) for n, v in r['rotation_bias'].items() for s in v)
    ce = max(((abs(v[s]['centre_height_error_mm']), v[s]['centre_height_error_mm'], short(n), s) for n, v in r['rest_height'].items()
              if isinstance(v, dict) and n in R[ep]['objects'] for s in v), default=None)
    fs = FS.get(ep, {}).get(src)
    fss = f"{fs['0.5'] - fs['0']:+.4f}" if fs else '-'
    snap = '-'
    if 'pre' in R[ep]['sources']:
        snap = f"{R[ep]['sources']['pre']['auc_oracle_corrections']['base']['AUC'] - R[ep]['sources']['perc']['auc_oracle_corrections']['base']['AUC']:+.4f}"
        if ep == '18':                       # perception tracked/scored with library_v2, reference with v3 (flattened sweeper)
            snap += ' (mesh differs; same mesh v3: +0.0067)'
    print(f"| {ep} | {'+'.join(short(n) for n in R[ep]['objects'])} | {src} | {r['scale']['joint']['s']:.3f} | {np.median(lags):+.2f} | "
          f"{r['up_axis']['kit_alignment_deg']:.1f} | {tl[0]:.1f} ({tl[1]}) | {ce[1]:+.0f} ({ce[2]} {ce[3]}) | {a['base']['AUC']:.4f} | "
          f"{a['time']['delta']:+.4f} | {a['height']['delta']:+.4f} | {a['tilt']['delta']:+.4f} | {a['all']['delta']:+.4f} | {fss} | {snap} |")
