"""refcheck/timing: compile timing.json (+ cost.json) into tables.md and summary.json.
Usage: python -I summarize.py TIMING.json COST.json OUTDIR [CREEP.json]
"""
import json, os, sys
import numpy as np

MS = 1000 * 0.049373
EXCL = {'23'}                                     # frame-0 identity swap of the two boards (perception AUC 0.04)


def fmt(x, nd=1):
    if x is None:
        return '-'
    if isinstance(x, float):
        return f'{x:+.{nd}f}' if nd else f'{x:+.0f}'
    return f'{x:+d}' if isinstance(x, int) else str(x)


def stats(v):
    v = np.asarray(v, float)
    if not len(v):
        return None
    return dict(n=int(len(v)), median=round(float(np.median(v)), 2), mean=round(float(v.mean()), 2),
                iqr=[round(float(x), 2) for x in np.percentile(v, [25, 75])],
                within_1=int((np.abs(v) <= 1).sum()), median_ms=round(float(np.median(v) * MS), 1))


def main():
    TJ = json.load(open(sys.argv[1])); CJ = json.load(open(sys.argv[2])) if os.path.exists(sys.argv[2]) else None
    od = sys.argv[3]; L = []; S = {}
    p = L.append
    # ---------------------------------------------------------------- 1 object events
    p('## 1. Object motion events: ours - mocap (frames; > 0 = ours LATE; 1 frame = 49.4 ms)\n')
    p('Mocap: physical onset / offset (speed >= 1 cm/s or rotation >= 10 deg/s, walked back / forward from the 1 cm / '
      '10 deg crossing) and the number of moving bouts. Ours: sub-frame 1 cm crossing lags (on1 / off1), 10 deg '
      'rotation-crossing lag (onR), for the canonical perception (perc) and the final reference (ref; stale 20 Oct '
      'reference where no canonical one exists). Static = the object never moves 1 cm / 10 deg in mocap.\n')
    p('| ep | object | mocap on-off (bouts) | perc on1 | perc onR | perc off1 | ref on1 | ref onR | ref off1 | note |')
    p('|---|---|---|---|---|---|---|---|---|---|')
    pooled = {}
    for ep, R in TJ.items():
        for n, o in R['obj'].items():
            m = o['mocap']
            if o['static']:
                mx = {k: v.get('max_disp_cm') for k, v in o['src'].items() if 'max_disp_cm' in v and not k.startswith('sim')}
                p(f"| {ep} | {n} | static (max {m['max_disp_cm']} cm) | | | | | | | ours max disp cm {mx} |"); continue
            lp = o['lags'].get('perc', {}); rk = 'ref' if 'ref' in o['lags'] else ('stale' if 'stale' in o['lags'] else None)
            lr = o['lags'].get(rk, {}) if rk else {}
            note = []
            if ep in EXCL:
                note.append('identity swap: excluded from pooled')
            for k, v in list(lp.items()) + list(lr.items()):
                if k.endswith('_f') and abs(v) > 3:
                    note.append(f'{k}={v:+.0f}')
            p(f"| {ep} | {n} | {m['on_phys']}-{m['off_phys']} ({len(m['bouts'])}) | {fmt(lp.get('on_p1_f'))} | {fmt(lp.get('on_r_f'))} | "
              f"{fmt(lp.get('off_p1_f'))} | {fmt(lr.get('on_p1_f'))} | {fmt(lr.get('on_r_f'))} | {fmt(lr.get('off_p1_f'))} | "
              f"{(rk + ': ' if rk == 'stale' else '') + '; '.join(sorted(set(note)))} |")
            if ep in EXCL:
                continue
            for k, lg in o['lags'].items():
                kk = 'sim' if k.startswith('sim_') else k
                for key, v in lg.items():
                    pooled.setdefault(kk, {}).setdefault(key, []).append(v)
    p('')
    p('### Pooled lags (excluding ep23; all moving objects)\n')
    p('| source | key | n | median (frames) | median (ms) | IQR | within +-1 frame | n with abs(lag) > 3 |')
    p('|---|---|---|---|---|---|---|---|')
    S['pooled_lags'] = {}
    for src in ('perc', 'pre', 'ref', 'stale', 'sim'):
        for key in ('on_p1_f', 'on_p2_f', 'on_r_f', 'off_p1_f', 'off_p2_f', 'off_r_f'):
            v = pooled.get(src, {}).get(key)
            if not v:
                continue
            st = stats(v); st['n_abs_gt3'] = int((np.abs(v) > 3).sum())
            vv = np.asarray(v); st['median_abs_le3'] = round(float(np.median(vv[np.abs(vv) <= 3])), 2) if (np.abs(vv) <= 3).any() else None
            S['pooled_lags'].setdefault(src, {})[key] = st
            p(f"| {src} | {key} | {st['n']} | {st['median']:+.2f} | {st['median_ms']:+.0f} | [{st['iqr'][0]:+.2f}, {st['iqr'][1]:+.2f}] | "
              f"{st['within_1']} | {st['n_abs_gt3']} |")
    p('')
    # speed-edge lags
    p('### Speed-edge lags (every bout: rising / falling edges of speed >= 5 cm/s, matched within 10 frames; integer frames)\n')
    p('| source | starts n | starts median | starts IQR | ends n | ends median | ends IQR |')
    p('|---|---|---|---|---|---|---|')
    S['edge_lags'] = {}
    for src in ('perc', 'pre', 'ref', 'stale', 'sim'):
        st_, en_ = [], []
        for ep, R in TJ.items():
            if ep in EXCL:
                continue
            for n, o in R['obj'].items():
                for k, el in o['edge_lags'].items():
                    if (k.startswith('sim_') and src == 'sim') or k == src:
                        st_ += el['starts']; en_ += el['ends']
        if st_:
            a, b = stats(st_), stats(en_)
            S['edge_lags'][src] = dict(starts=a, ends=b)
            p(f"| {src} | {a['n']} | {a['median']:+.1f} | {a['iqr']} | {b['n'] if b else 0} | {b['median'] if b else '-'} | {b['iqr'] if b else '-'} |")
    p('')
    # ---------------------------------------------------------------- 2 hands
    p('## 2. Hand contact vs the TRUE (mocap) motion window\n')
    p('lead = true physical onset - arrival of the contact run active at it (> 0: the hand is there BEFORE the object '
      'moves; < 0: it arrives late, the reference moves the object with no hand on it). rel = release - true physical '
      'offset (> 0: the hand stays after the object settles). unheld = true moving frames (mocap bouts inside the window) '
      'with no contact. Robot = 15 probe sites + palm of either robot hand within 2 cm of the object surface (our mesh, '
      'posed by that reference); pre = mkref/E2S output, ref = after contact retarget, glockt = grasp-lock training '
      'reference; human = perceived MANO joints within 2 cm; labels = the reference contact labels; plan = grasp-lock '
      'hold_from - true onset / end - true offset.\n')
    p('| ep | object | true on-off | pre robot lead / rel / unheld | ref robot | glockt robot | human | labels | plan hold_from / end |')
    p('|---|---|---|---|---|---|---|---|---|')
    hl = {}
    for ep, R in TJ.items():
        plan = {(x['object']): x for x in (R.get('grasp_lock_plan') or {}).get('phases', [])}
        for n, o in R['obj'].items():
            if o['static']:
                continue
            m = o['mocap']; cells = []
            for hk, mk in (('pre', 'robot<2cm'), ('ref', 'robot<2cm'), ('glockt', 'robot<2cm'), ('ref', 'human<2cm'), ('ref', 'labels')):
                hk2 = hk if hk in R['hands'] else ('stale' if 'stale' in R['hands'] and hk in ('ref',) else None)
                if hk2 is None or n not in R['hands'][hk2]:
                    cells.append('-'); continue
                c = R['hands'][hk2][n][mk]
                cells.append(f"{fmt(c.get('lead_vs_true'))} / {fmt(c.get('release_lag_vs_true'))} / {c.get('unheld_frames_true')}"
                             + (' (stale)' if hk2 == 'stale' else ''))
                if ep not in EXCL:
                    tag = f"{hk2}:{mk}"
                    hl.setdefault(tag, dict(lead=[], rel=[], unheld=0, frames=0, late=[], early_release=[], own_lead=[], own_late=[], own_unheld=0, own_frames=0))
                    if c.get('lead_vs_own') is not None:
                        hl[tag]['own_lead'].append(c['lead_vs_own'])
                        if c['lead_vs_own'] < 0:
                            hl[tag]['own_late'].append(f"{ep}/{n}:{c['lead_vs_own']}")
                    hl[tag]['own_unheld'] += c.get('unheld_frames_own') or 0; hl[tag]['own_frames'] += c.get('window_frames_own') or 0
                    if c.get('lead_vs_true') is not None:
                        hl[tag]['lead'].append(c['lead_vs_true'])
                        if c['lead_vs_true'] < 0:
                            hl[tag]['late'].append(f"{ep}/{n}:{c['lead_vs_true']}")
                    if c.get('release_lag_vs_true') is not None:
                        hl[tag]['rel'].append(c['release_lag_vs_true'])
                        if c['release_lag_vs_true'] < 0:
                            hl[tag]['early_release'].append(f"{ep}/{n}:{c['release_lag_vs_true']}")
                    hl[tag]['unheld'] += c.get('unheld_frames_true') or 0; hl[tag]['frames'] += c.get('window_frames_true') or 0
            x = plan.get(n)
            pc = f"{fmt(x.get('hold_from_minus_true_onset'), 0)} / {fmt(x.get('end_minus_true_offset'), 0)}" + (' replan' if x.get('replan') else '') + \
                 (f" (onset anchor f{x['onset_anchor']})" if x.get('onset_anchor') is not None else '') if x else '-'
            p(f"| {ep} | {n} | {m['on_phys']}-{m['off_phys']} | " + ' | '.join(cells) + f' | {pc} |')
    p('')
    p('### Pooled (excluding ep23)\n')
    p('| hand source | n | lead median | lead IQR | late arrivals (lead < 0) | release median | early releases | unheld / true moving frames | lead vs OWN onset: median, late | unheld / own moving frames |')
    p('|---|---|---|---|---|---|---|---|---|---|')
    S['hands'] = {}
    for tag, h in sorted(hl.items()):
        a, b, c = stats(h['lead']), stats(h['rel']), stats(h['own_lead'])
        S['hands'][tag] = dict(lead=a, release=b, late=h['late'], early_release=h['early_release'], unheld=h['unheld'], frames=h['frames'],
                               own_lead=c, own_late=h['own_late'], own_unheld=h['own_unheld'], own_frames=h['own_frames'])
        p(f"| {tag} | {a['n'] if a else 0} | {a['median'] if a else '-'} | {a['iqr'] if a else '-'} | {', '.join(h['late']) or 'none'} | "
          f"{b['median'] if b else '-'} | {', '.join(h['early_release']) or 'none'} | {h['unheld']} / {h['frames']} | "
          f"{c['median'] if c else '-'}, {', '.join(h['own_late']) or 'none'} | {h['own_unheld']} / {h['own_frames']} |")
    p('')
    # plan
    pl = [(ep, x) for ep, R in TJ.items() for x in (R.get('grasp_lock_plan') or {}).get('phases', []) if 'hold_from_minus_true_onset' in x]
    if pl:
        v = [x['hold_from_minus_true_onset'] for _, x in pl]; w = [x['end_minus_true_offset'] for _, x in pl]
        S['plan'] = dict(hold_from_minus_true_onset=stats(v), end_minus_true_offset=stats(w),
                         phases=[dict(ep=ep, **{k: x[k] for k in ('hand', 'object', 'hold_from', 'end', 'onset_anchor', 'replan', 'hold_from_minus_true_onset', 'end_minus_true_offset')}) for ep, x in pl])
        p(f"Grasp-lock plan over {len(pl)} hold phases: hold_from - true onset median {np.median(v):+.0f} frames "
          f"(range {min(v):+d} to {max(v):+d}); end - true offset median {np.median(w):+.0f} (range {min(w):+d} to {max(w):+d}).\n")
    # ---------------------------------------------------------------- mkref bookkeeping
    p('## 3. mkref hand bookkeeping: lead-in, held / attached invalid runs, tracker-filled frames\n')
    p('| ep | side | first valid (lead-in cm) | invalid runs filled by mkref (start-end, attach) overlapping true motion | hand-track frames in true motion: measured / tracker-filled / invalid |')
    p('|---|---|---|---|---|')
    S['mkref'] = {}
    for ep, R in TJ.items():
        mh = R.get('mkref_hands')
        if not mh:
            continue
        for sd, b in mh['sides'].items():
            fl = [f"{f['start']}-{f['end_excl'] - 1} ({','.join(f['attach_bodies']) or 'hold'}; {f['overlap_true_motion_frames']})"
                  for f in b['fills'] if any(v > 0 for v in f['overlap_true_motion_frames'].values())]
            ht = b.get('hand_track', {}); po = ht.get('per_object', {})
            hts = '; '.join(f"{n}: {v['of_which_measured']}/{v['tracker_filled']}/{v['invalid']} of {v['true_moving_frames']}" for n, v in po.items())
            p(f"| {ep} | {sd} | {b['first_valid']} ({b['lead_in_cm']}) | {'; '.join(fl) or 'none'} | {hts} |")
            S['mkref'].setdefault(ep, {})[sd] = dict(first_valid=b['first_valid'], lead_in_cm=b['lead_in_cm'], fills_in_motion=fl, hand_track=po,
                                                     source=mh['summary'])
    p('')
    # ---------------------------------------------------------------- creep
    cp = sys.argv[4] if len(sys.argv) > 4 else None
    if cp and os.path.exists(cp):
        CR = json.load(open(cp)); S['creep'] = {}
        p('## 3b. Our object moving while the true object rests (creep.py; > 1 cm from its own rest pose)\n')
        p('| ep / object | true window | source | before true onset: max cm / deg, frames > 1 cm (first) | after true offset: max cm / deg, frames > 1 cm | mocap same |')
        p('|---|---|---|---|---|---|')
        for key, r in CR.items():
            for k in ('perc', 'ref', 'stale'):
                x = r.get(k)
                if not x:
                    continue
                if r['static']:
                    if x['frames_over_1cm'] > 0:
                        p(f"| {key} | static | {k} | whole episode: {x['whole_max_cm']} / {x['whole_max_deg']}, {x['frames_over_1cm']} ({x['first_over_1cm']}) | | {r['mocap']['whole_max_cm']} / {r['mocap']['whole_max_deg']} |")
                        S['creep'][f'{key}:{k}'] = x
                elif x['pre_onset_frames_over_1cm'] > 0 or (x['post_offset_frames_over_1cm'] or 0) > 0:
                    m = r['mocap']
                    p(f"| {key} | {r['true_on']}-{r['true_off']} | {k} | {x['pre_onset_max_cm']} / {x['pre_onset_max_deg']}, {x['pre_onset_frames_over_1cm']} ({x['pre_onset_first_over_1cm']}) | "
                      f"{x['post_offset_max_cm']} / {x['post_offset_max_deg']}, {x['post_offset_frames_over_1cm']} | pre {m['pre_onset_max_cm']} / {m['pre_onset_max_deg']}, post {m['post_offset_max_cm']} / {m['post_offset_max_deg']} |")
                    S['creep'][f'{key}:{k}'] = x
        p('')
    # ---------------------------------------------------------------- guard
    p('## 4. Track-guard interventions (perception guard arm, 8 episodes)\n')
    p('| ep | object | counts | re-acquired frames | held frames (true object moving?) |')
    p('|---|---|---|---|---|')
    S['guard'] = {}
    for ep, R in TJ.items():
        for n, g in (R.get('guard') or {}).items():
            c = g['counts'] or {}
            if any(v for v in c.values()) or g['held_frames']:
                p(f"| {ep} | {n} | {c} | {g['reacquired_frames']} | {list(zip(g['held_frames'], g['true_moving_at_held']))} |")
            S['guard'].setdefault(ep, {})[n] = g
    p('')
    # ---------------------------------------------------------------- sim
    p('## 5. Simulated object (rollouts r1-r5 of the canonical results dir): 1 cm onset crossing vs mocap\n')
    p('| ep | object | ref on1 lag | sim on1 lag per rollout | sim off1 lag per rollout |')
    p('|---|---|---|---|---|')
    for ep, R in TJ.items():
        for n, o in R['obj'].items():
            if o['static'] or not any(k.startswith('sim_') for k in o['lags']):
                continue
            sims = sorted(k for k in o['lags'] if k.startswith('sim_'))
            p(f"| {ep} | {n} | {fmt(o['lags'].get('ref', {}).get('on_p1_f'))} | "
              f"{', '.join(fmt(o['lags'][k].get('on_p1_f'), 0) for k in sims)} | {', '.join(fmt(o['lags'][k].get('off_p1_f'), 0) for k in sims)} |")
    p('')
    # ---------------------------------------------------------------- cost
    if CJ:
        p(f"## 6. Cost in the kit's registered AUC (in-process kit scoring; pooled onset lag L = {CJ['pooled_onset_lag_frames']:+.3f} frames from {CJ['pooled_from_crossings']} perception crossings)\n")
        p('| ep | src | base | shift_pool (legal constant) | shift_ep (oracle, L) | shift_obj (oracle) | rest_hold (oracle) |')
        p('|---|---|---|---|---|---|---|')
        for ep, er in CJ['episodes'].items():
            for k, r in er.items():
                p(f"| {ep} | {k} | {r['base']:.4f} | {r['shift_pool']:.4f} ({r['shift_pool'] - r['base']:+.4f}) | "
                  f"{(format(r['shift_ep'], '.4f') + ' (' + format(r['shift_ep'] - r['base'], '+.4f') + ', L ' + str(r['shift_ep_L']) + ')') if 'shift_ep' in r else '-'} | "
                  f"{r['shift_obj']:.4f} ({r['shift_obj'] - r['base']:+.4f}) | {r['rest_hold']:.4f} ({r['rest_hold'] - r['base']:+.4f}) |")
        p('')
        if 'summary' in CJ:
            p('Means over episodes (excluding ep23): ' + json.dumps(CJ['summary']) + '\n')
        p('### Per-frame error by phase (base; pooled over objects and episodes, excluding ep23 and ep0)\n')
        p('| src | phase | frames | ADD median cm | ADD p90 cm | mean AUC share |')
        p('|---|---|---|---|---|---|')
        agg = {}
        for ep, er in CJ['episodes'].items():
            if str(ep) in EXCL or str(ep) == '0':          # ep0: hand proximity from the stale reference, whose pot path is wrong
                continue
            for k, r in er.items():
                for n, gg in (r.get('per_obj_groups') or {}).items():
                    for gk, g in gg.items():
                        a = agg.setdefault((k, gk), dict(frames=0, w_add=[], w_share=0.0))
                        a['frames'] += g['frames']; a['w_add'].append((g['add_cm_median'], g['frames'])); a['w_share'] += g['share_mean'] * g['frames']
        S['phase_errors'] = {}
        for (k, gk), a in sorted(agg.items()):
            med = float(np.average([x for x, _ in a['w_add']], weights=[w for _, w in a['w_add']]))
            S['phase_errors'][f'{k}:{gk}'] = dict(frames=a['frames'], add_cm_median_weighted=round(med, 2), share_mean=round(a['w_share'] / a['frames'], 3))
            p(f"| {k} | {gk} | {a['frames']} | {med:.2f} (frame-weighted mean of per-object medians) | - | {a['w_share'] / a['frames']:.3f} |")
        p('')
        S['cost_summary'] = CJ.get('summary')
        S['pooled_onset_lag_frames'] = CJ['pooled_onset_lag_frames']
    open(os.path.join(od, 'tables.md'), 'w').write('\n'.join(L) + '\n')
    json.dump(S, open(os.path.join(od, 'summary.json'), 'w'), indent=1)
    print('\n'.join(L[:400]))


if __name__ == '__main__':
    main()
