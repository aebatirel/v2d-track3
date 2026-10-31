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
    """The 6.2 table for one pair at P_sel (moved to simphys.pair_physics, shared with interlock.default_physics)."""
    return PH.pair_physics(b, o, p, hulls_o, hulls_p, run, carve_cm3, default_o, default_p, copies, label,
                           do_proxy=do_proxy, log=log)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--ep', type=int, required=True)
    ap.add_argument('--bundle', required=True); ap.add_argument('--cands', required=True)
    ap.add_argument('--pick', required=True); ap.add_argument('--video'); ap.add_argument('--calib')
    ap.add_argument('--hands'); ap.add_argument('--gen', default='')
    ap.add_argument('--diag', action='store_true'); ap.add_argument('--proxy-copies', type=int, default=16)
    ap.add_argument('--no-physics', action='store_true'); ap.add_argument('--tag', default='')
    ap.add_argument('--identity', default='public', choices=('public', 'eval'),
                    help='public: IDENTITY_SWAP makes (c) absent (F-I1.2); eval: the identity test only flags (SPEC '
                         'section 7), i.e. what the same rule does on an eval episode')
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
                  identity_semantics=a.identity, sanity_flags={o: (b.meta.get('sanity') or {}).get(o, {}).get('flags')
                                                               for o in objs},
                  sim_pose='P_sel (flag sim_pose_fallback: no provenance-checked replay reference for public dev)',
                  pairs={}, silhouette={o: ({k: v for k, v in (sil[o] or {}).items() if not k.startswith('_') and
                                             k not in ('nmv', 'nmf', 'nmv_sub', 'nmf_sub', 'notches')} | dict(
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
            pc = geom.volume_samples(cands[q][picks[q]], 20000, seed=0)[0]
            # the same constructor as the export path (F-I3.1); sources (a) / (b) are filled below
            sides[t] = IL.make_side(b, t, q, ev[t], intr, cf, sources=dict(sil=sil[t]), identity=a.identity,
                                    partner_collider=pc, fh=fh[t])
            runs, comps, okfr, track_ok = sides[t].runs, sides[t].comps, sides[t].gate['good_share'], \
                sides[t].track_ok
            prep[f'{t}<-{q}'] = dict(contact_frames=len(cf), runs=[r.summary() for r in runs],
                                     components=[dict(voxels=int(len(c.lin)), swept=int(c.swept.sum()),
                                                      cm3=round(len(c.lin) * ev[t].grid.vox ** 3 * 1e6, 2))
                                                 for c in comps], good_share=okfr, track_ok=track_ok,
                                     gate=sides[t].gate)
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
                    # closing radius max(6 mm, partner thickness at the crossing): the partner pick's thinnest
                    # 1-99 % extent (F-I1.2)
                    Xq = geom.volume_samples(cands[p if t == o else o][picks[p if t == o else o]], 20000, seed=0)[0]
                    Aq = (Xq - Xq.mean(0)) @ np.linalg.svd(Xq - Xq.mean(0), full_matrices=False)[2].T
                    th = float(np.percentile(Aq[:, 2], 99) - np.percentile(Aq[:, 2], 1))
                    # capped at t_max (20 mm): the thinnest extent of a pot or cup is its diameter, not a wall
                    r_notch = min(max(GS.k_('notch_r_min'), th), IL.K('offset_tmax_m'))
                    sa = GS.source_a(ev[t], pl['mesh'], pl['side_resolved'], r_notch, near_lin=near,
                                     kind=s.comps[0].run.kind)
                    row = dict(path=gp, residual_mm=pl['residual_mm'], margin_sigma=pl['margin_sigma'],
                               scale=round(pl['s'], 5), closing_r_mm=round(r_notch * 1e3, 1), placed_extents_mm=np.round(pl['mesh'].extents * 1e3, 1).tolist(),
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
        if sides[o].runs:
            np.save(os.path.join(out_dir, 'T_asm.npy'), IL._asm_pose(sides[o].intr, sides[o].runs[0]))
        for t in (o, p):                                   # voxel sets for the figures (build/I/i_png.py)
            arr = {}
            for i, r in enumerate([r for r in recs if r['target'] == t]):
                arr[f'comp{i}_lin'] = r['_comp'].lin
                arr[f'comp{i}_region'] = r['_comp'].region()
                arr[f'comp{i}_nv'] = r['_comp'].n_v
                if '_sim_solid' in r:
                    arr[f'comp{i}_sim_sub'] = r['_sim_solid']['sub_lin']
                if '_sub_solid' in r:
                    arr[f'comp{i}_sub_sub'] = r['_sub_solid']['sub_lin']
            if sides[t].gen is not None:
                arr['gen_C_a'] = sides[t].gen['C_a']
            if sil[t] and 'nmv' in sil[t]:
                from gmg import silhouette as SI
                arr['sil'] = SI.sil_mask(sil[t]['nmv'], sil[t]['nmf']) & ev[t].occ
            arr['occ'] = ev[t].occ
            np.savez_compressed(os.path.join(out_dir, f'voxels_{t}.npz'), lo=ev[t].grid.lo, vox=ev[t].grid.vox,
                                shape=np.asarray(ev[t].grid.shape), **arr)
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
                # F-I3.8: the default pieces must hold <= 0.3 cm3 keep-out per hull; else CoACD's pieces checked
                # against the same keep-out; else the delivery is marked do-not-use
                gate = SP.pieces_gate({'gmg': built[x]['default'], 'coacd': built[x]['coacd']}, *built[x]['keep'])
                log('pieces gate', x, gate['choice'], json.dumps(gate['report']), gate['do_not_use'] or '')
                hl = gate['hulls']
                if phys is not None and phys['deliver_carved']:
                    deliver, hl = 'carved', built[x]['carved']
                    gate = SP.pieces_gate({'carved': built[x]['carved']}, *built[x]['keep'])
                prep.setdefault('pieces_gate', {})[x] = {k: v for k, v in gate.items() if k != 'hulls'}
                sim_objects[x] = dict(visual=cands[x][picks[x]], hulls=hl, gate=gate,
                                      sources=dict(sil=sil[x], gen=sides[x].gen, notches=sides[x].notches,
                                                   notches_sil=sides[x].notches_sil, grid=ev[x].grid),
                                      carve=dict(delivered=deliver, decisions=[d for d in all_dec if d['target'] == x],
                                                 pieces_report=built[x]['report'],
                                                 pieces_choice=gate['choice'], pieces_gate=gate['report'],
                                                 do_not_use=gate['do_not_use'],
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
        for x, so in sim_objects.items():                # sources (a), (b), notches travel with the round (F-I3.1)
            sx = so.pop('sources')
            IL.write_sources(os.path.join(sim_dir, 'sources'), x, sx['sil'], sx['gen'], sx['notches'],
                             sx['notches_sil'], sx['grid'])
        state = dict(round=0, holdout={}, carved_cm3={x: 0.0 for x in sim_objects},
                     solid_ref_cm3={x: round(ev[x].solid_cm3(), 3) for x in sim_objects},
                     default_collider_cm3={x: round(SP.hull_volume(so['hulls']) * 1e6, 3)
                                           for x, so in sim_objects.items()}, delivered='default')
        man = SP.write_round(sim_dir, a.ep, split, 0, sim_objects, dict(source='P_sel', flag='sim_pose_fallback',
                                                                       tracks=b.meta['tracks']), interlock=state)
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
