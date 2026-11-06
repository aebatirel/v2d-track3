"""b4_report: summaries of a clean B4 run for git (small files only; bundles stay in the scratchpad and the HF store).

Writes OUT/summary.json (per episode and object: points, owned/shared, grid box, seed and guard, OBSERVED voxels,
sigma, sanity, census and contact per pair, timing), OUT/b3.json (PREREG B.3 counts over the dev validation records),
OUT/b15.json (PREREG B.15 / P22 table), OUT/bundle_manifest.json (path, bytes, sha256 of every file of the run's
bundle/, hands/, manifests/, identity/, validate/ folders). Reads the run's files directly (summary step after the
guarded runs; no data outside the two run folders).
Usage: python gmg/tools/b4_report.py --run <clean run> --dev-run <dev run> --out gmg/build/b4
"""
import argparse
import glob
import hashlib
import json
import os

import numpy as np


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# PREREG C.2 anchor order (fixed at the freeze; GT-free: largest view_cap60 in obs_census.jsonl)
C2_ORDER = {'white_pot': [27, 43, 26, 45, 41, 42, 44, 0, 2], 'white_pot_lid': [2, 0],
            'plastic_dish_rack': [31, 26, 12, 13, 27], 'blue_cup': [12, 13, 11, 22, 21], 'beige_cup': [11],
            'water_pitcher': [21, 22], 'mini_dust_pan': [40, 39, 18], 'mini_sweeper': [18, 31],
            'wooden_piece_1': [24, 23], 'wooden_piece_2': [23, 24]}


def anchors(rows):
    """PREREG C.2: per object, the first episode of its list that has neither TRACK_FAIL nor IDENTITY_SWAP (None if
    every listed episode is flagged), with the skipped episodes and their flags."""
    fl = {(x['ep'], x['obj']): [f for f in x['flags'] if f in ('TRACK_FAIL', 'IDENTITY_SWAP')] for x in rows}
    out = {}
    for o, order in C2_ORDER.items():
        skipped, pick = [], None
        for ep in order:
            f = fl.get((ep, o))
            if f is None:
                continue
            if f:
                skipped.append(dict(ep=ep, flags=f))
            else:
                pick = ep
                break
        out[o] = dict(anchor=pick, first_listed=order[0], skipped=skipped)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--dev-run', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--audit-glob', default=None, help='strace audit reports (<log>.audit.json) of the run')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    eps = sorted(int(os.path.basename(d)[2:]) for d in glob.glob(os.path.join(a.run, 'bundle', 'public', 'ep*')))
    summ = {}
    for ep in eps:
        bd = os.path.join(a.run, 'bundle', 'public', f'ep{ep}')
        if not os.path.exists(os.path.join(bd, 'episode.json')):
            continue
        m = json.load(open(os.path.join(bd, 'episode.json')))
        rec = dict(objects=m['objects'], T=m['T'], timing=m.get('timing'), hands=m.get('hands'), flags=m.get('flags'),
                   table_inlier=m['table'].get('inlier_frac'), n_samples_pass0=m.get('n_samples_pass0'), obj={},
                   pairs={})
        for o in m['objects']:
            z = np.load(os.path.join(bd, f'{o}.npz'))
            own = z['own']
            st = z['state']
            rec['obj'][o] = dict(points=int(len(own)), owned=int((own == 0).sum()), shared=int((own == 1).sum()),
                                 frames=int(len(np.unique(z['frame'][own == 0]))) if len(own) else 0,
                                 grid=list(st.shape), lo=np.round(z['lo'], 4).tolist(),
                                 observed=int((st == 2).sum()), free=int((st == 1).sum()),
                                 shared_vox=int((z['shared'] > 0).sum()), pocc_vox=int((z['pocc'] > 0).sum()),
                                 sigma_mm=m['sigma_mm'][o], crop=m['crop'][o], sanity=m['sanity'][o],
                                 rest=m.get('rest', {}).get(o, {}).get('share'), shell=m.get('shells', {}).get(o))
        for key, c in (m.get('contact') or {}).items():
            o, p = key.split('|')
            if m['objects'].index(o) > m['objects'].index(p):
                continue
            c1 = m['census_pass1'][key]
            rec['pairs'][key] = dict(contact=len(c['contact']), separated=len(c['separated']), sep3d=len(c['sep3d']),
                                     overlap2d=c['overlap2d'], frames=len(c['frames']),
                                     contact_pass1=len(c1['contact']), separated_pass1=len(c1['separated']),
                                     census_change=m['census_change'][key], j_mm=c.get('j_mm'),
                                     band_mm=c.get('band_mm'), co_moving=c.get('co_moving'),
                                     co_moving_unresolved=c.get('co_moving_unresolved'), tie_break=c.get('tie_break'),
                                     ownership={k: m['ownership'][k] for k in (key, f'{p}|{o}')},
                                     band_mm_rev=m['contact'][f'{p}|{o}'].get('band_mm'),
                                     j_mm_rev=m['contact'][f'{p}|{o}'].get('j_mm'),
                                     sep3d_frame_diag=(len(c['sep3d_frame']) if 'sep3d_frame' in c else None))
        summ[f'ep{ep}'] = rec
    json.dump(summ, open(os.path.join(a.out, 'summary.json'), 'w'), indent=1)
    # B.3
    recs = []
    for f in sorted(glob.glob(os.path.join(a.dev_run, 'b3', 'public-ep*.json'))):
        if f.endswith('.manifest.json'):
            continue
        recs += json.load(open(f))['records']
    hand = [r for r in recs if r['hands_in_obs_all']]
    noh = [r for r in recs if not r['hands_in_obs_all']]
    nj = sum(r['pass_jaccard'] for r in hand)
    no = sum(r['pass_outside'] for r in hand)
    b3 = dict(prereg='B.3', files_with_hands=len(hand), files_hands_null=len(noh),
              jaccard_ge_095=nj, outside_le_5pct=no,
              verdict=('PASS' if len(hand) == 25 and nj >= 23 and no >= 23 else
                       'FAIL' if len(hand) == 25 else f'INCOMPLETE ({len(hand)} of 25 files)'),
              records=recs)
    # diagnostic only (DEVIATIONS 100; not the pre-registered rule): the same counts if every in-cube sample counted
    # as a hit (the obs_points.py vote with the clean filters), and the share of the lost voxels' re-voted hits that
    # came from unowned samples
    def _ad(r, k):
        return (r.get('attribution_diag') or {}).get(k)
    lost_tot = [sum((_ad(r, 'lost_hits_revote') or {}).values()) for r in hand]
    b3['diagnostic'] = dict(
        note='not the B.3 pass rule (DEVIATIONS 100)',
        jaccard_all_samples_ge_095=sum(1 for r in hand if (_ad(r, 'jaccard_all_samples_diag') or 0) >= 0.95),
        jaccard_owned_unowned_ge_095=sum(1 for r in hand if (_ad(r, 'jaccard_owned_unowned_diag') or 0) >= 0.95),
        unowned_share_of_lost_hits={f"ep{r['ep']}:{r['obj']}": round((_ad(r, 'lost_hits_revote') or {}).get('unowned', 0)
                                                                      / t, 3) if t else None
                                    for r, t in zip(hand, lost_tot)})
    json.dump(b3, open(os.path.join(a.out, 'b3.json'), 'w'), indent=1)
    # B.15
    cross = os.path.join(a.run, 'identity', 'cross.json')
    if os.path.exists(cross):
        cj = json.load(open(cross))
        rows = []
        for ep in eps:
            r = summ.get(f'ep{ep}')
            if not r:
                continue
            for o, d in r['obj'].items():
                s = d['sanity']
                rows.append(dict(ep=ep, obj=o, flags=s['flags'], n_good=s['n_good'], n_frames=s['n_frames'],
                                 track_fail_readings=s.get('track_fail_readings'),
                                 split={p: (v.get('testable'), v.get('pass_')) for p, v in
                                        (s.get('identity_split') or {}).items()},
                                 identity_fail=s.get('identity_fail'),
                                 cross={k: v for k, v in cj['results'][f'ep{ep}:{o}'].items()
                                        if k not in ('chamfers_mm', 'chamfers_seed0_mm')}))
        flagged = [f'ep{x["ep"]}:{x["obj"]}' for x in rows if 'IDENTITY_SWAP' in x['flags']]
        # P22 is about the cross-object test; split-test failures also mark IDENTITY_SWAP (SPEC section 7) and are
        # listed apart
        cross_flagged = [f'ep{x["ep"]}:{x["obj"]}' for x in rows
                         if x['cross'].get('testable') and not x['cross'].get('pass_')]
        split_flagged = [f'ep{x["ep"]}:{x["obj"]}' for x in rows
                         if any(t and p is False for t, p in x['split'].values())]
        not_testable = [f'ep{x["ep"]}:{x["obj"]}' for x in rows if not x['cross'].get('testable')]
        # round 2: the round-1 registration (seed 0 only) verdicts, reported beside; they set no flag
        cross_flagged_seed0 = [f'ep{x["ep"]}:{x["obj"]}' for x in rows if x['cross'].get('testable')
                               and x['cross'].get('seed0') is not None and not x['cross']['seed0']['pass_']]
        split_flagged_seed0 = [f'ep{x["ep"]}:{x["obj"]}' for x in rows
                               if (x.get('identity_fail') or {}).get('seed0_split')]
        lid_cup = [k for k in not_testable if k.split(':')[1] in ('white_pot_lid', 'beige_cup')]
        p22 = dict(cross_flags_exactly_ep23_board2=(cross_flagged == ['ep23:wooden_piece_2']),
                   lid_and_beige_cup_not_testable=sorted(lid_cup) == sorted(
                       k for k in (f'ep{x["ep"]}:{x["obj"]}' for x in rows)
                       if k.split(':')[1] in ('white_pot_lid', 'beige_cup')))
        json.dump(dict(prereg='B.15', P22_prediction='flags ep23 board 2 and no other public object-episode; lid and '
                       'beige cup not testable', flagged=flagged, cross_flagged=cross_flagged,
                       split_flagged=split_flagged, P22=p22,
                       P22_supported=bool(p22['cross_flags_exactly_ep23_board2'] and
                                          p22['lid_and_beige_cup_not_testable']),
                       track_fail=[f'ep{x["ep"]}:{x["obj"]}' for x in rows if 'TRACK_FAIL' in x['flags']],
                       not_testable_cross=not_testable,
                       seed0=dict(note='round-1 registration (subsample seed 0 only); sets no flag',
                                  cross_flagged=cross_flagged_seed0, split_flagged=split_flagged_seed0),
                       anchors=anchors(rows),
                       rows=rows), open(os.path.join(a.out, 'b15.json'), 'w'), indent=1)
    # strace audits
    if a.audit_glob:
        aud = {}
        keys = ('events', 'forbidden_opens', 'forbidden_attempted_failed', 'returncode', 'opens_ok', 'system',
                'code_outside_interp', 'git', 'git_tree_reads')
        for f in sorted(glob.glob(a.audit_glob)):
            d = json.load(open(f))
            aud[os.path.basename(f)] = dict({k: d.get(k) for k in keys},
                                            **{k: len(d.get(k) or []) for k in ('forbidden', 'unlisted', 'unrecorded',
                                                                                 'writes_outside_run', 'network',
                                                                                 'data_reads', 'written')})
        json.dump(dict(audits=aud, total_forbidden_opens=int(sum(v['forbidden_opens'] or 0 for v in aud.values())),
                       all_rc0=all(v['returncode'] == 0 for v in aud.values())),
                  open(os.path.join(a.out, 'audits.json'), 'w'), indent=1)
    # bundle manifest
    files = []
    for sub in ('bundle', 'hands', 'manifests', 'identity', 'validate', 'logs'):
        for p in sorted(glob.glob(os.path.join(a.run, sub, '**'), recursive=True)):
            if os.path.isfile(p):
                files.append(dict(path=os.path.relpath(p, a.run), bytes=os.path.getsize(p), sha256=sha256(p)))
    json.dump(dict(run=os.path.basename(os.path.realpath(a.run)), files=files,
                   total_bytes=int(sum(f['bytes'] for f in files))),
              open(os.path.join(a.out, 'bundle_manifest.json'), 'w'), indent=1)
    print('episodes', len(summ), 'B.3', b3['verdict'], nj, no, 'files', len(files))


if __name__ == '__main__':
    main()
