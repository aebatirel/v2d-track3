"""INTERLOCK stage, dev driver for one episode (build step BI2: T-I2 .. T-I6 in dev mode; INTERLOCK.md 12-13).

  GMG_MODE=dev python -m gmg.tools.interlock_dev --run RUN --ep N --bundle BUNDLE_DIR --cands CAND_DIR
      --pick obj=cid[,obj=cid] [--video MP4 --calib JSON --hands NPZ] [--gen obj=path[;path],...] [--diag]
      [--proxy-copies 16] [--no-physics]

Per pair (o, p) of the episode, GT-free:
  1. P_sel = the bundle's tracks; P_sim = P_sel with flag sim_pose_fallback (no provenance-checked replay reference for
     public dev episodes);
  2. sources: (c) intrusions_from_tracks, engaged runs, regions; (b) silhouette.run per object when a video is given;
     (a) gen_slot (generator meshes placed by our depth, dev role x0_pool) when --gen is given;
  3. interlock.decide_pair -> decisions, tiers, push list;
  4. simulator copy r0: default pieces (simpieces.decompose of the pick), carved pieces for CARVE / OFFSET decisions,
     the physical tests of simphys (P1 pre-check, P2-P7) and the delivery decision; CoACD pieces of the pick as the
     FlashCHORD baseline for overlap;
  5. physcheck features for every candidate (placement along the whole movement, partner overlap per phase, table,
     rest), VI relative to the best candidate;
  6. ICARVE candidates at T2 / T3 / T2o (packed, 4000 faces, watertight);
  7. --diag: DIAGNOSTIC slotted counterfactuals (never submitted, never delivered): the pick carved at the motion
     region (split at the pair's shared plane, width w_sub) and at the placed generator notch, with the same physical
     tests, so the owner can see what a slot would do. Labelled DIAG in every output.
Outputs: RUN/interlock/public/ep<N>/ (decisions.json, push_list.json, physcheck.json, report.json, diag/...),
RUN/sim/public/ep<N>/r0/ (delivered layout), RUN/cand/public/ep<N>/<obj>/icarve_*.glb.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

from gmg import interlock as IL, simpieces as SP, simphys as PH, physcheck as PC, geom  # noqa: E402

LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(f'{time.strftime("%H:%M:%S")} {s}')
    print(LOG[-1], flush=True)


def jdump(obj, path):
    with open(path, 'w') as f:
        json.dump(obj, f, indent=1, default=IL._jdefault)


def load_mesh(path):
    m = trimesh.load(path, force='mesh')
    return trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)


def coacd_pieces(mesh, threshold=0.05):
    import coacd
    parts = coacd.run_coacd(coacd.Mesh(np.asarray(mesh.vertices), np.asarray(mesh.faces)), threshold=threshold)
    return [np.asarray(v) for v, f in parts]


def partner_occ_lin(b, o, p, ev_o, frames, nmin, poses=None):
    """Voxels of o's grid (inside or outside the candidate) that p's evidence samples occupy in >= nmin frames."""
    poses = b.poses if poses is None else poses
    Xp = IL.partner_points(b, p)
    cnt = np.zeros(ev_o.grid.size, np.int32)
    for f in frames:
        T = IL.rel_pose(poses, o, p, f)
        l, ok = ev_o.grid.lin(Xp @ T[:3, :3].T + T[:3, 3])
        cnt[np.unique(l[ok])] += 1
    return np.nonzero(cnt >= nmin)[0]


def world_pose(b, obj, f):
    return b.poses['world_T_cam'][f].astype(np.float64) @ b.poses[f'cam_T_{obj}'][f].astype(np.float64)


def physics(b, o, p, hulls_o, hulls_p, run, carve_cm3, default_o, default_p, copies, label, do_proxy=True):
    """The 6.2 table for one pair (o host, p guest) at poses P_sim (= P_sel here)."""
    out = dict(label=label)
    rels = {f: IL.rel_pose(b.poses, o, p, f) for f in range(int(b.meta['T']))}
    asm = run.assembled or run.build[-5:]
    f_asm = asm[len(asm) // 2]
    # P2 free travel: gravity (table normal in the host frame), +d, +n, -n
    pl = b.table_in_obj(o, f_asm) if b.meta.get('table') else None
    dirs = {}
    if pl is not None:
        dirs['gravity'] = -np.asarray(pl[0])
    A = IL.axes_of(np.vstack(hulls_p) @ rels[f_asm][:3, :3].T + rels[f_asm][:3, 3], run.d)[1]
    dirs.update({'+d': A[0], '+n': A[1], '-n': -A[1]})
    Xg, cell = PH.guest_samples(hulls_p)
    tr_c, base_c = PH.free_travel(hulls_o, hulls_p, rels[f_asm], dirs, Xg, cell)
    Xd, celld = PH.guest_samples(default_p)
    tr_d, base_d = PH.free_travel(default_o, default_p, rels[f_asm], dirs, Xd, celld)
    p2 = all(tr_c[k] <= max(PH.k_('travel_max_m'), tr_d[k] + PH.k_('travel_default_plus_m')) for k in tr_c)
    out['P2'] = dict(frame=int(f_asm), carved_mm={k: round(v * 1e3, 1) for k, v in tr_c.items()},
                     default_mm={k: round(v * 1e3, 1) for k, v in tr_d.items()}, overlap_at_pose_cm3=[round(base_d, 3),
                                                                                                     round(base_c, 3)],
                     pass_=bool(p2))
    # P4 over-removal (both objects)
    out['P4'] = {o: PH.over_removal(default_o, hulls_o, carve_cm3.get(o, 0.0)),
                 p: PH.over_removal(default_p, hulls_p, carve_cm3.get(p, 0.0))}
    # P6 / P7 overlap series (default vs carved) on stride-4 frames and the run's check frames
    fr6 = sorted(set(list(range(0, int(b.meta['T']), 4)) + list(run.assembled)))
    ov_d = PH.overlap_series(default_o, default_p, rels, fr6, Xd, celld)
    ov_c = PH.overlap_series(hulls_o, hulls_p, rels, fr6, Xg, cell)
    worse = [f for f in fr6 if ov_c[f] > ov_d[f] + PH.k_('p6_tol_cm3')]
    out['P6'] = dict(frames=len(fr6), worse_frames=worse[:20], n_worse=len(worse), pass_=not worse,
                     default_asm_median=round(float(np.median([ov_d[f] for f in run.assembled])) if run.assembled else 0, 3),
                     carved_asm_median=round(float(np.median([ov_c[f] for f in run.assembled])) if run.assembled else 0, 3))
    if run.check:
        chk = [f for f in run.check]
        od = PH.overlap_series(default_o, default_p, rels, chk, Xd, celld)
        oc = PH.overlap_series(hulls_o, hulls_p, rels, chk, Xg, cell)
        sd, sc = float(np.sum(list(od.values()))), float(np.sum(list(oc.values())))
        out['P7'] = dict(check_frames=len(chk), default_sum_cm3=round(sd, 2), carved_sum_cm3=round(sc, 2),
                         default_median=round(float(np.median(list(od.values()))), 3),
                         carved_median=round(float(np.median(list(oc.values()))), 3),
                         pass_=bool(sc <= PH.k_('p7_share') * sd) if sd > 0 else True)
    else:
        out['P7'] = dict(applies=False, flag='no_holdout')
    out['overlap_series'] = dict(default={int(k): round(v, 3) for k, v in ov_d.items()},
                                 carved={int(k): round(v, 3) for k, v in ov_c.items()})
    # P1 settle pre-check (plain MuJoCo) at the assembled frame
    if b.meta.get('table'):
        tb = b.meta['table']
        W0 = world_pose(b, o, f_asm); Wg = world_pose(b, p, f_asm)
        hp = SP.props(hulls_o, 0.3); gp = SP.props(hulls_p, 0.3)
        try:
            out['P1_precheck'] = PH.settle(hulls_o, hulls_p, W0, Wg, (np.asarray(tb['n']), float(tb['d'])), hp, gp,
                                           copies=copies)
            hpd = SP.props(default_o, 0.3); gpd = SP.props(default_p, 0.3)
            out['P1_precheck_default'] = PH.settle(default_o, default_p, W0, Wg, (np.asarray(tb['n']), float(tb['d'])),
                                                   hpd, gpd, copies=copies)
        except Exception as e:
            out['P1_precheck'] = dict(error=f'{type(e).__name__}: {e}')
    else:
        out['P1_precheck'] = dict(applies=False, reason='no table plane in the bundle')
    out['P1'] = dict(run=False, reason='FlashCHORD scene not in this container (INTERLOCK 6.2: the pre-check does not '
                                       'decide)')
    # P3 replay proxy (INSERTION)
    if do_proxy and run.kind == 'INSERTION':
        t0 = max(0, run.frames[0] - PH.k_('pre'))
        frames = list(range(t0, int(b.meta['T'])))
        gpp = SP.props(hulls_p, 0.3)
        t = time.time()
        res = PH.replay_proxy(hulls_o, hulls_p, rels, frames, asm,
                              dict(default=(default_o, default_p, True), carved=(hulls_o, hulls_p, True),
                                   nocollide=(default_o, default_p, False)), copies=copies, guest_props=gpp, log=log)
        res['sec'] = round(time.time() - t, 1)
        res['frames'] = [frames[0], frames[-1]]
        res['judge'] = PH.p3_pass(res)
        out['P3'] = res
    tests = [out['P2']['pass_'], out['P4'][o]['pass_'], out['P4'][p]['pass_'], out['P6']['pass_'],
             out['P7'].get('pass_', True)]
    if 'P3' in out:
        tests.append(out['P3']['judge']['pass_'])
    out['P2_P7_pass'] = bool(all(tests))
    out['deliver_carved'] = False
    out['deliver_reason'] = ('P2-P7 pass but P1 (FlashCHORD settle) not run: default pieces delivered, carved pieces '
                             'kept for the FlashCHORD check') if out['P2_P7_pass'] else 'a physical test failed: default pieces'
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--ep', type=int, required=True)
    ap.add_argument('--bundle', required=True); ap.add_argument('--cands', required=True)
    ap.add_argument('--pick', required=True); ap.add_argument('--video'); ap.add_argument('--calib')
    ap.add_argument('--hands'); ap.add_argument('--gen', default='')
    ap.add_argument('--diag', action='store_true'); ap.add_argument('--proxy-copies', type=int, default=16)
    ap.add_argument('--no-physics', action='store_true'); ap.add_argument('--tag', default='')
    a = ap.parse_args()
    guard.set_run(a.run)
    t_start = time.time()
    split = 'public'
    out_dir = os.path.join(a.run, 'interlock', split, f'ep{a.ep}' + (f'-{a.tag}' if a.tag else ''))
    os.makedirs(out_dir, exist_ok=True)
    b = IL.load_bundle_any(a.bundle)
    picks = dict(kv.split('=') for kv in a.pick.split(','))
    objs = b.objects
    cands = {o: {f[:-4]: load_mesh(os.path.join(a.cands, o, f)) for f in sorted(os.listdir(os.path.join(a.cands, o)))
                 if f.endswith('.glb') and not f.startswith('icarve')} for o in objs}
    log('ep', a.ep, 'objects', objs, 'picks', picks, 'cands', {o: list(c) for o, c in cands.items()})
    ev = {o: IL.Evidence(b, o, cands[o][picks[o]]) for o in objs}
    fh = {o: IL.FrameHits(b, o, ev[o].grid) for o in objs}
    hands = dict(guard.load_npz(a.hands, 'own' if a.hands.startswith(a.run) else 'dev_hands')) if a.hands else None
    # (b) silhouette
    sil = {o: None for o in objs}
    if a.video:
        from gmg import silhouette as SI
        for o in objs:
            t = time.time()
            r = SI.run(b, o, ev[o], a.video, a.calib, hands=hands)
            sil[o] = r
            log('silhouette', o, json.dumps({k: v for k, v in r.items() if k in ('gate_ok', 'gate', 'qualifying',
                                                                                   'sil_voxels')}, default=str),
                f'{time.time() - t:.0f}s')
            if 'nmv' in r:
                np.savez_compressed(os.path.join(out_dir, f'sil_{o}.npz'), nmv=r['nmv'], nmf=r['nmf'], occ=ev[o].occ)
    report = dict(ep=a.ep, bundle=a.bundle, tier=b.meta.get('tier'), picks=picks, constants=IL.constants_report(),
                  sim_pose='P_sel (flag sim_pose_fallback: no provenance-checked replay reference for public dev)',
                  pairs={}, silhouette={o: ({k: v for k, v in (sil[o] or {}).items() if not k.startswith('_') and
                                             k not in ('nmv', 'nmf', 'notches')} | dict(
                                                 notch_voxels=[int(len(n)) for n in (sil[o] or {}).get('notches', [])]))
                                            if sil[o] else None for o in objs})
    pairs = [(objs[i], objs[j]) for i in range(len(objs)) for j in range(i + 1, len(objs))]
    all_dec, push = [], []
    sim_objects = {}
    diag = {}
    for o, p in pairs:
        prep = dict()
        sides = {}
        for t, q in ((o, p), (p, o)):
            cf = b.contact(t, q)['contact']
            intr = IL.intrusions_from_tracks(b, t, q, ev[t], cf)
            runs = IL.engaged_runs(intr, cf, int(b.meta['stride']))
            comps = []
            for r in runs:
                cs, nmin = IL.regions(intr, r, ev[t], float(b.contact(t, q).get('j_mm') or 0) * 1e-3)
                comps += cs
            good = set(b.good_frames(t)) & set(b.good_frames(q))
            okfr = [len([f for f in r.frames if f in good]) / max(len(r.frames), 1) for r in runs]
            sflags = (b.meta.get('sanity') or {}).get(t, {}).get('flags', [])
            track_ok = all(x >= 0.8 for x in okfr) and not any(f in ('TRACK_FAIL', 'IDENTITY_SWAP') for f in sflags)
            pc = geom.volume_samples(cands[q][picks[q]], 20000, seed=0)[0]
            sides[t] = IL.Side(t, ev[t], intr, comps, runs, sil=sil[t], track_ok=track_ok,
                               track_reason=f'good share {np.round(okfr, 2).tolist()} flags {sflags}',
                               partner_collider=pc, fh=fh[t])
            prep[f'{t}<-{q}'] = dict(contact_frames=len(cf), runs=[r.summary() for r in runs],
                                     components=[dict(voxels=int(len(c.lin)), swept=int(c.swept.sum()),
                                                      cm3=round(len(c.lin) * ev[t].grid.vox ** 3 * 1e6, 2))
                                                 for c in comps], good_share=okfr, track_ok=track_ok)
            log(t, '<-', q, json.dumps(prep[f'{t}<-{q}'], default=IL._jdefault)[:600])
        # (a) generator
        gen_paths = {}
        for kv in [x for x in a.gen.split(',') if x]:
            k, v = kv.split('=')
            gen_paths[k] = v.split(';')
        for t in (o, p):
            s = sides[t]
            s.notches = list((sil[t] or {}).get('notches', []) or [])
            s.notches_sil = list(s.notches)
            if t in gen_paths and s.comps:
                from gmg import gen_slot as GS
                near = np.concatenate([c.lin for c in s.comps])
                best = None
                rows = []
                for gp in gen_paths[t]:
                    gm = GS.decimate(GS.load_gen(gp), GS.k_('dec_faces'))
                    pl = GS.place_by_depth(gm, b, t, ref_mesh=cands[t][picks[t]])
                    other = sides[p if t == o else o]
                    r_notch = max(GS.k_('notch_r_min'), float(np.median([c.info.get('s_min_mm', 8) for c in
                                                                        s.comps])) * 1e-3)
                    sa = GS.source_a(ev[t], pl['mesh'], pl['side_resolved'], r_notch, near_lin=near,
                                     kind=s.comps[0].run.kind)
                    row = dict(path=gp, residual_mm=pl['residual_mm'], margin_sigma=pl['margin_sigma'],
                               side_resolved=pl['side_resolved'], scale=round(pl['s'], 5),
                               **{k: v for k, v in sa.items() if k not in ('C_a', 'C_a_sub')})
                    rows.append(row)
                    pl['mesh'].export(os.path.join(out_dir, f'gen_placed_{t}_{os.path.basename(gp)[:-4]}.glb'))
                    if best is None or pl['residual_mm'][0] < best[0]['residual_mm'][0]:
                        best = (pl, sa, row)
                    log('gen', t, os.path.basename(gp), json.dumps(row, default=IL._jdefault)[:500])
                pl, sa, row = best
                s.gen = sa
                if sa.get('survived'):
                    from scipy import ndimage
                    lab, n = ndimage.label(sa['C_a'].reshape(ev[t].grid.shape), structure=np.ones((3, 3, 3)))
                    for i in range(1, n + 1):
                        l = np.nonzero(lab.ravel() == i)[0]
                        if len(l) >= 3:
                            s.notches.append(l)
                prep[f'gen_{t}'] = dict(runs=rows, used=row['path'])
        recs = IL.decide_pair(b, sides[o], sides[p])
        for r in recs:
            all_dec.append(IL.public(r))
            if 'push_list' in r:
                push.append(dict(target=r['target'], partner=r['partner'], **r['push_list']))
            log('decision', r['target'], '<-', r['partner'], r['decision'], r['tier'], r['flags'],
                dict(mix=r.get('class_mix'), iw=r.get('image_width_px'), push=r.get('push_mm'),
                     split=(r.get('split') or {}).get('through_column'), sources={k: (v or {}).get('agree') if
                                                                                  isinstance(v, dict) else v for k, v in
                                                                                  r['sources'].items()}))
        report['pairs'][f'{o}|{p}'] = prep
        # ---- simulator copy r0
        if not a.no_physics:
            t = time.time()
            occ = {}
            for x, y in ((o, p), (p, o)):
                fr = [f for r in sides[x].runs for f in r.build]
                nm = max([c.nmin for c in sides[x].comps] or [5])
                occ[x] = partner_occ_lin(b, x, y, ev[x], fr, nm) if fr else np.zeros(0, np.int64)
            built = {}
            for x in (o, p):
                carves = [r['_sim_solid'] for r in recs if r['target'] == x and r.get('sim_carve')]
                sil_lin = None
                if sil[x] and sil[x].get('gate_ok'):
                    from gmg import silhouette as SI
                    sil_lin = np.nonzero(SI.sil_mask(sil[x]['nmv'], sil[x]['nmf']))[0]
                built[x] = SP.build(cands[x][picks[x]], ev[x], carves, occ[x], sil_lin)
                built[x]['coacd'] = coacd_pieces(cands[x][picks[x]])
                log('pieces', x, 'default', len(built[x]['default']), 'carved',
                    None if built[x]['carved'] is None else len(built[x]['carved']), 'coacd', len(built[x]['coacd']),
                    f'{time.time() - t:.0f}s')
            # overlap along the track: CoACD (FlashCHORD default) vs our default pieces
            rels = {f: IL.rel_pose(b.poses, o, p, f) for f in range(int(b.meta['T']))}
            fr6 = list(range(0, int(b.meta['T']), 4))
            ovl = {}
            for name in ('coacd', 'default'):
                ser = PH.overlap_series(built[o][name], built[p][name], rels, fr6)
                ovl[name] = dict(median=round(float(np.median(list(ser.values()))), 3),
                                 max=round(float(max(ser.values())), 3), series=ser)
            prep['collider_overlap_track'] = {k: {kk: vv for kk, vv in v.items() if kk != 'series'} for k, v in
                                              ovl.items()}
            jdump(ovl, os.path.join(out_dir, f'overlap_{o}_{p}.json'))
            carved_pairs = [r for r in recs if r.get('sim_carve')]
            phys = None
            if carved_pairs and all(built[x]['carved'] is not None for x in (o, p)):
                run = sides[o].runs[0] if sides[o].runs else sides[p].runs[0]
                phys = physics(b, o, p, built[o]['carved'], built[p]['carved'], run,
                               {r['target']: r['_sim_solid']['cm3'] for r in carved_pairs}, built[o]['default'],
                               built[p]['default'], a.proxy_copies, 'decided')
                prep['physics'] = {k: v for k, v in phys.items() if k != 'overlap_series'}
                jdump(phys, os.path.join(out_dir, f'physics_{o}_{p}.json'))
            for x in (o, p):
                deliver = 'default'
                hl = built[x]['default']
                if phys is not None and phys['deliver_carved']:
                    deliver, hl = 'carved', built[x]['carved']
                sim_objects[x] = dict(visual=cands[x][picks[x]], hulls=hl,
                                      carve=dict(delivered=deliver, decisions=[d for d in all_dec if d['target'] == x],
                                                 pieces_report=built[x]['report'],
                                                 flags=['sim_pose_fallback'] + ([] if phys is None else
                                                                               ['p1_not_run_flashchord']),
                                                 physics=None if phys is None else
                                                 {k: v for k, v in phys.items() if k != 'overlap_series'}))
                if built[x]['carved'] is not None:
                    dd = os.path.join(out_dir, '_carved_pending_p1', x)
                    os.makedirs(dd, exist_ok=True)
                    for kk, V in enumerate(built[x]['carved']):
                        trimesh.convex.convex_hull(V).export(os.path.join(dd, f'piece_{kk:02d}.obj'))
            # ---- DIAG counterfactuals
            if a.diag:
                diag[f'{o}|{p}'] = run_diag(b, o, p, sides, recs, cands, picks, ev, built, out_dir, a.proxy_copies)
                jdump(diag[f'{o}|{p}'], os.path.join(out_dir, f'diag_{o}_{p}.json'))
        # ---- ICARVE (submitted path)
        for r in recs:
            if r.get('submitted') and '_sub_solid' in r:
                x = r['target']
                sm = IL.solid_mesh(ev[x], r['_sub_solid'])
                for cid, m in cands[x].items():
                    if cid.startswith('hull'):
                        continue
                    mc, info = IL.icarve(m, [sm])
                    from gmg import pack as PK
                    pm, pinfo = PK.pack(mc, os.path.join(a.cands, x, f'icarve_{cid}.glb'))
                    log('ICARVE', x, cid, info, pinfo['faces'], pinfo['watertight_packed'])
    # ---- physcheck for every candidate
    pcs = {}
    for o in objs:
        pcs[o] = {}
        ph_by_p = {}
        for p in b.partners(o):
            cf = b.contact(o, p)['contact']
            intr = IL.intrusions_from_tracks(b, o, p, ev[o], cf)
            runs = IL.engaged_runs(intr, cf, int(b.meta['stride']))
            ph_by_p[p] = PC.phases(b, o, p, runs)
        for cid, m in cands[o].items():
            t = time.time()
            cls = 'HULL' if cid.startswith('hull') else 'SHELL'
            pcs[o][cid] = PC.features(m, b, o, ph_by_p, cls, hands)
            log('physcheck', o, cid, json.dumps(dict(pl={k: v for k, v in pcs[o][cid]['placement'].items()
                                                         if k != 'per_frame_t_mm'},
                                                     inter=pcs[o][cid]['interpenetration'],
                                                     table=pcs[o][cid]['table'].get('frames_over_share')),
                                                default=IL._jdefault)[:700], f'{time.time() - t:.0f}s')
        I = {cid: (pcs[o][cid]['interpenetration'].get(p, {}).get('assembled', {}).get('median', 0.0) or 0.0)
             for cid in pcs[o] for p in b.partners(o)[:1]}
        report.setdefault('VI', {})[o] = dict(I_assembled_cm3=I, veto=PC.vi_veto(I))
    jdump(pcs, os.path.join(out_dir, 'physcheck.json'))
    jdump(all_dec, os.path.join(out_dir, 'decisions.json'))
    jdump(push, os.path.join(out_dir, 'push_list.json'))
    if sim_objects and not a.no_physics:
        sim_dir = os.path.join(a.run, 'sim', split, f'ep{a.ep}' + (f'-{a.tag}' if a.tag else ''), 'r0')
        man = SP.write_round(sim_dir, a.ep, split, 0, sim_objects, dict(source='P_sel', flag='sim_pose_fallback',
                                                                       tracks=b.meta['tracks']), guard._git('rev-parse', 'HEAD'))
        report['sim_dir'] = sim_dir
    report['sec'] = round(time.time() - t_start, 1)
    report['log'] = LOG
    jdump(report, os.path.join(out_dir, 'report.json'))
    guard.write_manifest(os.path.join(out_dir, 'manifest.json'))
    log('done', report['sec'], 's')


def run_diag(b, o, p, sides, recs, cands, picks, ev, built, out_dir, copies):
    """DIAGNOSTIC (not pre-registered for delivery or submission): slotted counterfactuals of the picks.
    (m) motion: each component's region split at the pair's shared plane (forced, even when the through-column test
        fails), width w_sub for the visual mesh and w_sim for the pieces;
    The physical tests run on the (m) pieces. Never delivered, never submitted."""
    out = {}
    solids = {}
    for r in recs:
        x = r['target']
        comp = r['_comp']
        if r['decision'] == 'IGNORE' or r['voxels'] < 10:
            continue
        # forced split at the pair plane (through the centroid of both components in x's frame), entry side
        C = ev[x].grid.centres(comp.lin)
        d = comp.run.d
        c = C.mean(0)
        if r.get('linked'):
            other = sides[p if x == o else o]
            T = IL._asm_pose(sides[x].intr, comp.run)
            oc = [cc for cc in other.comps if len(cc.lin) >= 10]
            if oc:
                Ti = np.linalg.inv(IL._asm_pose(other.intr, oc[0].run))
                Cp = ev[other.name].grid.centres(oc[0].lin) @ Ti[:3, :3].T + Ti[:3, 3]
                c = np.vstack([C, Cp]).mean(0)
        s = (C - c) @ d
        lin = comp.lin[s < 0]
        if len(lin) < 3:
            continue
        A = np.asarray(r['widths']['axes_dnm']); cen = r['widths']['centre_n_mm'] * 1e-3
        w_sim = r['widths']['w_sim_mm'] * 1e-3; w_sub = r['widths']['w_sub_mm'] * 1e-3
        ssim = IL.carve_solid(ev[x], lin, A, cen, w_sim, plate=True)
        ssub = IL.carve_solid(ev[x], lin, A, cen, w_sub, plate=True)
        solids[x] = (ssim, ssub)
        out[x] = dict(region_voxels=int(len(lin)), plane_point_mm=np.round(c * 1e3, 1).tolist(),
                      sim_solid={k: v for k, v in ssim.items() if k != 'sub_lin'},
                      sub_solid={k: v for k, v in ssub.items() if k != 'sub_lin'})
    if len(solids) < 2:
        out['note'] = 'fewer than two solids: no diagnostic pair'
        return out
    pieces = {}
    for x in (o, p):
        hl, _ = SP.remove_box(built[x]['default'], solids[x][0]) if solids[x][0]['kind'] == 'box' else (None, 0)
        if hl is None:
            continue
        pieces[x] = [SP.reduce_hull(V, 64) for V in hl]
        mc, info = IL.icarve(cands[x][picks[x]], [IL.solid_mesh(ev[x], solids[x][1])])
        from gmg import pack as PK
        dd = os.path.join(out_dir, 'diag', x)
        os.makedirs(dd, exist_ok=True)
        pm, pinfo = PK.pack(mc, os.path.join(dd, f'DIAG_slot_{picks[x]}.glb'))
        out[x]['slotted_mesh'] = dict(info, packed_faces=pinfo['faces'], packed_watertight=pinfo['watertight_packed'],
                                      path=pinfo['path'])
        for kk, V in enumerate(pieces[x]):
            trimesh.convex.convex_hull(V).export(os.path.join(dd, f'piece_{kk:02d}.obj'))
        log('DIAG', x, out[x]['slotted_mesh'], 'pieces', len(pieces[x]))
    if len(pieces) == 2:
        run = sides[o].runs[0]
        out['physics'] = physics(b, o, p, pieces[o], pieces[p], run, {x: solids[x][0]['cm3'] for x in solids},
                                 built[o]['default'], built[p]['default'], copies, 'DIAG motion slot')
    return out


if __name__ == '__main__':
    main()
