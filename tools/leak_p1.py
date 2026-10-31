"""Phase-1 bundles of the leak decomposition (2026-10-30), the helper of ops/jobs/perc_leak.sh.

Plan: docs/research/work/leak-decomp-20261030/PLAN.md §3 Phase 1, §7 B4; build notes: .../phase1/BUILD.md.
The box commands (inputs, bundle, summary, templates) read no ground truth: no parquet, no mocap ('score', a CPU
oracle scoring run after inference, does; see below). perc2's result.json and the last lines of its log.txt DO hold mocap
scores (perc2.py's final scoring block): `bundle` only cuts them off (perc_log_inference.txt) and `summary`, which runs
after all inference, quotes the scan-template arm's own vo score for the record.
  inputs EP TSV DEPTH HANDS_DIR OUT   check the depth cache (size, shape, frame-0 sha256) and the hands (md5, frames)
                                      against the refine-input manifest TSV (phase1/inputs.tsv); write OUT/depth0.npy,
                                      OUT/hands/{hands,hands_refined}.npz and OUT/inputs.json. Exit 2 when the depth
                                      cache is unusable (perception would not run on it); mismatches are flagged.
  bundle EP OUT PERC2_PY              per arm folder in OUT (perc2 = P_o, perc2scan = P_s, perc2rep = P_o repeat):
                                      perc_log_inference.txt, poses_world_vo.npz when perc2 stopped before writing it,
                                      the template files perc2 resolves for the arm's MESH_DIR (perc2.py's own D /
                                      MESH_DIR / scan_path / mesh_path, taken from its source), camera agreement, depth
                                      reuse, Grounding DINO loaded (gdino: no 'grounding unavailable' line; an arm
                                      without it is not ok, NO-GDINO in the summary); -> OUT/bundle.json
  summary ROOT EP...                  ROOT/summary.json; one line per episode on stdout; exit 3 unless every arm
                                      ran (rc 0, tracks written), so run_job.sh holds a failed box for debugging
  templates PERC2_PY MESH_DIR|- OBJ... the template file perc2 would track for each object ('-' = MESH_DIR unset)
Opt-in per-episode templates (2026-10-31, re-track test, docs/research/work/retrack-20261031/): when an arm's run.json
carries lib_ep_dir (perc_leak.sh LIB_EP_DIR), `bundle` also records per object the template's real path and source
('episode' = LIB_EP_DIR/ep<N>/<obj>.glb, 'library' = LIB/<obj>.glb) and requires every delivered mesh to have been used
(templates_as_delivered, part of ok); the summary line adds "ep-mesh k/n". Without lib_ep_dir nothing changes.
  score --perc ROOT --t3 T3 --kit KIT [--lib LIB] [--lib-ep-dir DIR] [--episodes 0,2,...] [--out JSON] [--jobs N]
      ORACLE SCORING, after inference only (reads public mocap; never on a box, never for eval): R = registered ADD-AUC
      vs mocap in the lib convention (the kit's registration of the mesh the arm tracked with onto the public scan,
      seed 1_000_003 ep + 101 slot; tools/xstar_fit.py kit_X / score_track, as Phase 1's "lib" scores) plus the kit's
      registered RPE and MPPE (cm) on the same aligned poses, for ROOT/ep<N>/poses_world_vo.npz. The registered mesh is
      DIR/ep<N>/<obj>.glb where it exists (--lib-ep-dir, or env LIB_EP_DIR), else LIB/<obj>.glb (perc_leak.sh's rule);
      unset = library_v3 for every object, i.e. Phase 1's lib numbers.
"""
import ast, hashlib, json, os, re, shutil, sys, types

import numpy as np

ARMS = {'perc2': 'o', 'perc2scan': 's', 'perc2rep': 'o2'}               # folder -> arm
COLS = ['ep', 'T', 'objects', 'depth_store', 'depth_bytes', 'depth0_sha256', 'hands_store_dir', 'hands_md5', 'hands_refined_md5']
SCORE = re.compile(r' AUC |anchor:|\] DONE')                             # perc2's mocap-scoring lines (refine cut rule)
STAMP = re.compile(r'^\[\s*([\d.]+)s\] ')


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def js(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def row(tsv, ep):
    for line in open(tsv).read().splitlines()[1:]:
        r = dict(zip(COLS, line.split('\t')))
        if int(r['ep']) == ep:
            return r
    sys.exit(f'ep{ep} not in {tsv}')


def templates(perc2_py, mesh_dir, names):
    """perc2's own template choice: its module-level D and MESH_DIR and its scan_path / mesh_path, run with the
    environment the arm got (mesh_dir None = MESH_DIR unset)."""
    keep, got = [], set()
    for node in ast.parse(open(perc2_py).read()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('D', 'MESH_DIR') for t in node.targets):
            keep.append(node); got |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        elif isinstance(node, ast.FunctionDef) and node.name in ('scan_path', 'mesh_path'):
            keep.append(node); got.add(node.name)
    if got != {'D', 'MESH_DIR', 'scan_path', 'mesh_path'}:
        sys.exit(f'{perc2_py}: template code not found (have {sorted(got)}); update tools/leak_p1.py')
    env = {k: v for k, v in os.environ.items() if k != 'MESH_DIR'}
    if mesh_dir is not None:
        env['MESH_DIR'] = mesh_dir
    ns = {'os': types.SimpleNamespace(environ=env, path=os.path)}
    exec(compile(ast.Module(body=keep, type_ignores=[]), perc2_py, 'exec'), ns)
    return ns['D'], {n: ns['mesh_path'](n) for n in names}


def inputs(ep, tsv, depth, hands_dir, out):
    r = row(tsv, ep); T = int(r['T']); names = r['objects'].split(','); os.makedirs(f'{out}/hands', exist_ok=True)
    res = dict(episode=ep, objects=names, T=T, depth=dict(store=r['depth_store'], path=os.path.realpath(depth)),
               hands=dict(store_dir=r['hands_store_dir']), ok=True, problems=[])
    d = res['depth']
    try:
        st = os.stat(depth); D = np.load(depth, mmap_mode='r')
        d.update(bytes=st.st_size, bytes_expected=int(r['depth_bytes']), shape=list(D.shape), dtype=str(D.dtype),
                 stat=f'{st.st_ino} {st.st_size} {int(st.st_mtime)}')
        usable = st.st_size == int(r['depth_bytes']) and D.dtype == np.float32 and D.shape == (T, 1000, 1600)
    except Exception as x:
        usable = False; d['error'] = repr(x)
    d['usable'] = usable
    if not usable:
        res.update(ok=False); res['problems'].append('depth cache size/shape differs from the refine inputs: not used')
    else:
        d0 = np.array(D[0]); np.save(f'{out}/depth0.npy', d0)
        d.update(frame0_sha256=hashlib.sha256(d0.tobytes()).hexdigest(), frame0_sha256_expected=r['depth0_sha256'],
                 frame0_valid_frac=round(float((d0 > 0).mean()), 4), depth0_npy_md5=md5(f'{out}/depth0.npy'))
        d['matches_refine_inputs'] = d['frame0_sha256'] == r['depth0_sha256']
        if not d['matches_refine_inputs']:
            res.update(ok=False); res['problems'].append('depth frame 0 differs from the refine inputs (store cache changed?)')
    h = res['hands']
    for f, k in (('hands.npz', 'hands_md5'), ('hands_refined.npz', 'hands_refined_md5')):
        src = f'{hands_dir}/{f}'; e = h[f] = dict(store=f"{r['hands_store_dir']}/{f}", md5_expected=r[k])
        if not os.path.isfile(src):
            res.update(ok=False); res['problems'].append(f'{f} missing'); continue
        shutil.copyfile(src, f'{out}/hands/{f}'); e['md5'] = md5(f'{out}/hands/{f}'); e['md5_ok'] = e['md5'] == r[k]
        try:
            z = np.load(f'{out}/hands/{f}'); e['frames'] = [int(z[f'joints_{s}'].shape[0]) for s in ('left', 'right')]
        except Exception as x:
            e['frames'] = repr(x)
        if not e['md5_ok']:
            res.update(ok=False); res['problems'].append(f'{f} md5 differs from the refine inputs')
        if e['frames'] != [T, T]:
            res.update(ok=False); res['problems'].append(f'{f} frames {e["frames"]} != {T}')
    json.dump(res, open(f'{out}/inputs.json', 'w'), indent=1)
    print(f'[leak_p1] ep{ep} inputs: depth {"usable" if usable else "UNUSABLE"} frame-0 '
          f'{"= refine" if d.get("matches_refine_inputs") else "!= refine" if usable else "not read"}; hands md5 '
          f'{[h[f].get("md5_ok") for f in ("hands.npz", "hands_refined.npz")]}' + (f'; PROBLEMS {res["problems"]}' if res['problems'] else ''))
    return 0 if usable else 2


def template_sources(ep, tp, lep, lib):
    """LIB_EP_DIR mode: where each template perc2 resolved really is ('episode' / 'library' / 'other') and whether it
    is the one perc_leak.sh's rule asks for (the delivered mesh when LIB_EP_DIR/ep<N>/<obj>.glb exists, else LIB's)."""
    out = {}
    for n, v in tp.items():
        real, want_ep = os.path.realpath(v['path']), f'{lep}/ep{ep}/{n}.glb'
        has = os.path.isfile(want_ep)
        src = 'episode' if real == os.path.realpath(want_ep) else \
            'library' if lib and real == os.path.realpath(f'{lib}/{n}.glb') else 'other'
        out[n] = dict(real=real, source=src, expected='episode' if has else 'library')
    return out


def arm_check(ep, out, folder, names, T, perc2_py, depth_stat):
    A = f'{out}/{folder}'; run = js(f'{A}/run.json') or {}; c = dict(arm=ARMS[folder], folder=folder, rc=run.get('rc'),
                                                                   seconds=(run.get('t1') or 0) - (run.get('t0') or 0))
    md = run.get('mesh_dir'); md = None if md in (None, '<unset>') else md
    D, tp = templates(perc2_py, md, names)
    c['mesh_dir'] = run.get('mesh_dir'); c['templates'] = {n: dict(path=p, md5=md5(p) if os.path.isfile(p) else None,
                                                                    scan=p.startswith(f'{D}/mesh/')) for n, p in tp.items()}
    c['template_kind'] = 'scan' if all(v['scan'] for v in c['templates'].values()) else \
        'library' if not any(v['scan'] for v in c['templates'].values()) else 'mixed'
    if run.get('lib_ep_dir'):                                            # opt-in: per-episode templates (re-track)
        for n, v in template_sources(ep, c['templates'], run['lib_ep_dir'], run.get('lib')).items():
            c['templates'][n].update(v)
        c['lib_ep_dir'], c['lib'] = run['lib_ep_dir'], run.get('lib')
        c['template_sources'] = {n: v['source'] for n, v in c['templates'].items()}
        c['templates_as_delivered'] = all(v['source'] == v['expected'] for v in c['templates'].values())
    lines = open(f'{A}/log.txt', errors='replace').read().splitlines() if os.path.isfile(f'{A}/log.txt') else []
    keep = []
    for ln in lines:
        if SCORE.search(ln):
            break
        if STAMP.match(ln):
            keep.append(ln)
    open(f'{A}/perc_log_inference.txt', 'w').write('\n'.join(keep) + '\n')
    dr = [float(STAMP.match(ln).group(1)) for ln in keep if ' depth ready ' in ln]
    c['gdino'] = not any('grounding unavailable' in ln for ln in lines)  # Grounding DINO loaded (eval-pipeline parity)
    c['depth_ready_s'] = dr[0] if dr else None
    c['depth_stat_unchanged'] = run.get('depth_stat_before') == run.get('depth_stat_after') == depth_stat
    c['depth_reused'] = bool(c['depth_stat_unchanged'] and dr and dr[0] < 60)   # computing it takes minutes on the GPU
    W = None
    try:
        z = np.load(f'{A}/poses.npz'); W = z['world_T_cam'].astype(float)
        keys = [k[6:] for k in z.files if k.startswith('cam_T_')]
        c['objects_ok'] = keys == names
        c['poses_ok'] = bool(c['objects_ok'] and W.shape == (T, 4, 4) and np.isfinite(W).all()
                             and all(z[f'cam_T_{n}'].shape == (T, 4, 4) and np.isfinite(z[f'cam_T_{n}']).all() for n in names))
        vo = {n: np.stack([W[i] @ z[f'cam_T_{n}'][i].astype(float) for i in range(T)]) for n in names}
        if not os.path.isfile(f'{A}/poses_world_vo.npz'):                  # perc2 writes it in its scoring block
            np.savez(f'{A}/poses_world_vo.npz', **vo); c['poses_world_vo_written_here'] = True
        w = np.load(f'{A}/poses_world_vo.npz')
        c['world_vo_maxdiff'] = float(max(np.abs(w[n] - vo[n]).max() for n in names))
    except Exception as x:
        c['poses_ok'] = False; c['error'] = repr(x)
    c['ok'] = bool(c['rc'] == 0 and c['poses_ok'] and c['depth_reused'] and c['gdino'] and c.get('world_vo_maxdiff', 1) <= 1e-6
                   and c['template_kind'] == ('scan' if folder == 'perc2scan' else 'library')
                   and c.get('templates_as_delivered', True))
    return c, W


def epm(a):  # " ep-mesh k/n" for an arm with per-episode templates (LIB_EP_DIR), else ''
    s = a.get('template_sources')
    return f' ep-mesh {sum(v == "episode" for v in s.values())}/{len(s)}' if s else ''


def bundle(ep, out, perc2_py):
    inp = js(f'{out}/inputs.json') or {}; names, T = inp['objects'], inp['T']
    arms, cams = {}, {}
    for folder in ARMS:
        if os.path.isdir(f'{out}/{folder}'):
            arms[folder], cams[folder] = arm_check(ep, out, folder, names, T, perc2_py, inp['depth'].get('stat'))
    if cams.get('perc2') is not None:                                     # same depth and images: VO should agree
        for f, W in cams.items():
            if W is not None and f != 'perc2':
                arms[f]['camera_maxdiff_vs_perc2'] = float(np.abs(W - cams['perc2']).max())
    b = dict(episode=ep, objects=names, T=T, run_id=os.environ.get('RUN_ID'), commit=os.environ.get('COMMIT'),
             oracle=['perc2scan (scan templates = ground-truth geometry)'], inputs=inp, arms=arms,
             gt_files='result.json and log.txt of every arm hold mocap scores (perc2 scoring block); poses.npz, '
                      'poses_world_vo.npz, vo.json, perc_log_inference.txt do not; bundle_ep<N>_oracle.tar leaves '
                      'both out (they stay in the folder push for diagnostics)',
             ok=bool(inp.get('ok') and arms and all(a['ok'] for a in arms.values())))
    lep = sorted({a['lib_ep_dir'] for a in arms.values() if a.get('lib_ep_dir')})
    if lep:                                                              # opt-in per-episode templates only
        b['lib_ep_dir'] = lep[0] if len(lep) == 1 else lep
        b['template_sources'] = {f: a['template_sources'] for f, a in arms.items() if 'template_sources' in a}
    json.dump(b, open(f'{out}/bundle.json', 'w'), indent=1)
    print(f'[leak_p1] ep{ep} bundle {"OK" if b["ok"] else "NOT OK"}: ' + '; '.join(
        f'{a["arm"]} rc {a["rc"]} {a["seconds"]} s {a["template_kind"]}{epm(a)}{"" if a["gdino"] else " NO-GDINO"} depth reused '
        f'{a["depth_reused"]} poses {a["poses_ok"]}'
        + (f' cam {a["camera_maxdiff_vs_perc2"]:.1e}' if 'camera_maxdiff_vs_perc2' in a else '') for a in arms.values()))


def summary(root, eps):
    out = dict(rule='docs/research/work/leak-decomp-20261030/PLAN.md §3 Phase 1', episodes={})
    for e in eps:
        b = js(f'{root}/ep{e}/bundle.json'); r = js(f'{root}/ep{e}/perc2scan/result.json') or {}
        if not b:                                                        # skipped: inputs not downloaded / unusable
            p = (js(f'{root}/ep{e}/inputs.json') or {}).get('problems') or ['inputs not downloaded']
            out['episodes'][f'ep{e}'] = dict(ok=False, problems=p); print(f'ep{e}: NO BUNDLE (perception not run): {p}'); continue
        s = dict(ok=b['ok'], problems=b['inputs'].get('problems'), arms={a['arm']: {k: a.get(k) for k in (
            'ok', 'rc', 'seconds', 'template_kind', 'gdino', 'depth_reused', 'depth_ready_s', 'poses_ok', 'camera_maxdiff_vs_perc2')}
            for a in b['arms'].values()}, s_vo_auc_scan_frame=(r.get('vo') or {}).get('AUC'))
        for a in b['arms'].values():                                     # opt-in per-episode templates only
            if 'template_sources' in a:
                s['arms'][a['arm']]['template_sources'] = a['template_sources']
        out['episodes'][f'ep{e}'] = s
        print(f'ep{e}: {"OK" if s["ok"] else "NOT OK"} ' + ' | '.join(
            f'{k} {"ok" if v["ok"] else "FAIL"} rc {v["rc"]} {v["seconds"]} s {v["template_kind"]}{epm(v)}{"" if v["gdino"] else " NO-GDINO"}'
            for k, v in s['arms'].items())
            + f' | P_s vo AUC (scan frame, unregistered) {s["s_vo_auc_scan_frame"]}' + (f' | {s["problems"]}' if s['problems'] else ''))
    out['all_ok'] = all(v['ok'] for v in out['episodes'].values())
    out['all_ran'] = all(v.get('arms') and all(x['rc'] == 0 and x['poses_ok'] for x in v['arms'].values()) for v in out['episodes'].values())
    json.dump(out, open(f'{root}/summary.json', 'w'), indent=1)
    print(f'all bundles ok: {out["all_ok"]} ({sum(v["ok"] for v in out["episodes"].values())}/{len(eps)}); every arm ran '
          f'(rc 0, tracks written): {out["all_ran"]}')
    return 0 if out['all_ran'] else 3


# ---------------- score: R (lib convention) + RPE, ORACLE scoring after inference (re-track test, 2026-10-31)
PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]


def mesh_for(ep, n, lib, lep):
    """The mesh the arm tracked with, i.e. the one it submits (lib convention): LEP/ep<N>/<obj>.glb if delivered."""
    q = f'{lep}/ep{ep}/{n}.glb' if lep else None
    p = q if q and os.path.isfile(q) else f'{lib}/{n}.glb'
    return dict(path=os.path.abspath(p), md5=md5(p), source='episode' if p == q else 'library')


def score_episode(ep, root, t3, kit, lib, lep):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import xstar_fit as X                                                # Phase 1's scoring chain (kit functions)
    X.kit(kit); T3 = X.K['T3']
    f = f'{root}/ep{ep}/poses_world_vo.npz'
    V = np.load(f); names, gt = X.mocap(t3, ep, len(V[V.files[0]]))     # GROUND TRUTH: scoring only
    if sorted(names) != sorted(V.files):
        sys.exit(f'ep{ep}: track names {V.files} != episode slots {names}')
    Tp = {n: V[n].astype(np.float64) for n in names}
    H = [X.host_geometry(t3, n, s) for s, n in enumerate(names)]
    ms = {n: mesh_for(ep, n, lib, lep) for n in names}
    REG = [X.kit_X(ms[n]['path'], H[s], ep, s)[1] for s, n in enumerate(names)]
    sc = X.score_track(names, Tp, gt, H, REG)                            # R: exactly Phase 1's lib AUC when lep unset
    N, B = len(Tp[names[0]]), len(names)                                 # RPE / MPPE on the same chain (score_track's)
    ach = np.stack([X.to7(Tp[n]) for n in names], 1)[:, None].copy()
    ref = np.stack([X.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes, orders, pts = [h['axis'] for h in H], [h['order'] for h in H], [h['points'] for h in H]
    ach = T3._align_registered_scene(ach, ref, axes)
    m = {k: round(float(T3._registered_pose_metric(k, ach, ref, pts, axes, orders)), 4) for k in ('add_auc', 'rpe_cm', 'mppe_cm')}
    if m['add_auc'] != sc['AUC']:
        sys.exit(f'ep{ep}: AUC {m["add_auc"]} != score_track {sc["AUC"]} (chain mismatch)')
    r = dict(track=os.path.abspath(f), track_md5=md5(f), frames=N, objects=names, AUC=sc['AUC'], per_obj_AUC=sc['per_obj_AUC'],
             RPE_cm=m['rpe_cm'], MPPE_cm=m['mppe_cm'], meshes=ms)
    print(f'ep{ep}: R {r["AUC"]:.4f}  RPE {r["RPE_cm"]:.3f} cm  MPPE {r["MPPE_cm"]:.3f} cm  '
          + ', '.join(f'{n} {ms[n]["source"]} {sc["per_obj_AUC"][n]:.4f}' for n in names), flush=True)
    return ep, r


def score(argv):
    import argparse
    from concurrent.futures import ProcessPoolExecutor
    p = argparse.ArgumentParser(prog='leak_p1.py score')
    p.add_argument('--perc', required=True, help='ROOT with ep<N>/poses_world_vo.npz')
    p.add_argument('--t3', required=True); p.add_argument('--kit', required=True)
    p.add_argument('--lib', default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'meshes', 'library_v3'))
    p.add_argument('--lib-ep-dir', default=None)   # explicit only (review 31 Oct: an exported LIB_EP_DIR must not change P_o's score)
    p.add_argument('--episodes', default=','.join(map(str, PUBLIC))); p.add_argument('--out')
    p.add_argument('--jobs', type=int, default=2)
    a = p.parse_args(argv)
    eps = [int(e) for e in a.episodes.split(',') if e]
    if [e for e in eps if e not in PUBLIC] or os.environ.get('SPLIT', 'public') != 'public':
        sys.exit(f'episodes {eps} / SPLIT={os.environ.get("SPLIT")}: oracle scoring of PUBLIC episodes only')
    lep = os.path.abspath(a.lib_ep_dir) if a.lib_ep_dir else None
    if lep and not os.path.isdir(lep):
        sys.exit(f'--lib-ep-dir {lep} is not a directory')
    res = dict(kind='score', rule='R = registered ADD-AUC vs mocap, lib convention (kit registration of the mesh the arm '
               'tracked with onto the public scan); RPE / MPPE (cm) on the same chain. ORACLE scoring (reads mocap), '
               'public episodes, after inference.', perc=os.path.abspath(a.perc), lib=os.path.abspath(a.lib),
               lib_ep_dir=lep, episodes={})
    with ProcessPoolExecutor(a.jobs) as ex:
        for ep, r in ex.map(score_episode, eps, *[[x] * len(eps) for x in (a.perc, a.t3, a.kit, a.lib, lep)]):
            res['episodes'][str(ep)] = r
    v = list(res['episodes'].values())
    res['mean'] = dict(AUC=round(float(np.mean([x['AUC'] for x in v])), 5), RPE_cm=round(float(np.mean([x['RPE_cm'] for x in v])), 5),
                       MPPE_cm=round(float(np.mean([x['MPPE_cm'] for x in v])), 5), n=len(v))
    print(f'mean over {len(v)}: R {res["mean"]["AUC"]:.5f}  RPE {res["mean"]["RPE_cm"]:.4f} cm  MPPE {res["mean"]["MPPE_cm"]:.4f} cm')
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1); print(f'wrote {a.out}')
    return 0


if __name__ == '__main__':
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == 'inputs':
        sys.exit(inputs(int(a[0]), a[1], a[2], a[3], a[4]))
    elif cmd == 'bundle':
        bundle(int(a[0]), a[1], a[2])
    elif cmd == 'summary':                                               # exit 3 unless every arm ran
        sys.exit(summary(a[0], [int(x) for x in a[1:]]))
    elif cmd == 'score':                                                 # oracle scoring, after inference only
        sys.exit(score(a))
    elif cmd == 'templates':
        D, tp = templates(a[0], None if a[1] == '-' else a[1], a[2:])
        print(json.dumps(dict(D=D, templates=tp), indent=1))
    else:
        sys.exit(__doc__)
