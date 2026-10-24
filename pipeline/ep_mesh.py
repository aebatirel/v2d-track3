"""Mesh v5 build orchestration (docs/mesh-v5-spec-draft.md sections 10.1 and 10.2): one object from one or more
episodes of our own tracks, depth and hands, through the ported stages. Inputs are ours only; no scan, no mocap.

  pass 0   recon_mesh classic 4 mm, --others none                      -> M0 (ROI, others, X reference)
  fuse     recon_mesh obs, ROI = M0 + 40 mm, --others = the other objects' M0 posed by their tracks   -> grid
  post     mesh_post 4c12_adj_g2_f0_cont@lc25 on 'nobc' grids           -> O (full) + G1, G2, G5
  F4       recon_mesh classic 4 mm, --others = the other objects' M0    -> fallback
  select   O if G1, G2, T, X (and C per episode) pass; else F4 if T, X (and C) pass; else the seed (owner O2) or F4
           with a QA flag
  support  rest_support on the chosen full mesh (planes from the grid)
  final    mesh_decimate -> <obj>.glb (submitted style), <obj>_full.glb; collision_decomp -> pieces/<obj>/
Parameters come from pipeline/mesh_v5.json (frozen). The spoon is never built here (template, spec section 9).

Library mode (spec 10.2): every public episode of the object, C does not apply, X uses M0, fallback F4 only.
Episode mode (spec 10.1, stage 2m): one episode, every roster object; C against the seed library mesh (owner O3).

  python ep_mesh.py m0      OBJ M0_DIR  --ep POSES DEPTH HANDS - [--ep ...]   (library step 1: pass 0 only)
  python ep_mesh.py library OBJ OUT_DIR --ep POSES DEPTH HANDS OTHERS [--ep ...] [--m0_dir M0_DIR] [--calib C] [--g0]
  python ep_mesh.py object  OBJ OUT_DIR --ep ... --seed SEED.glb            (episode mode for one object)
  OTHERS: '-', NAME=M0.glb,... or bare names resolved to M0_DIR/<name>_M0.glb (the other objects of that episode,
  posed by their own tracks in POSES).
Writes OUT_DIR/<obj>.glb, <obj>_full.glb, <obj>.json (branch, gates, timings), work/ (M0, grid, O, F4) and
pieces/<obj>/ (collision_decomp).
"""
import argparse, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
P5 = json.load(open(os.path.join(HERE, 'mesh_v5.json')))


def run(cmd, log):
    t = time.time()
    with open(log, 'a') as fh:
        fh.write('$ ' + ' '.join(cmd) + '\n'); fh.flush()
        r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f'{os.path.basename(cmd[1])} failed (rc {r.returncode}); see {log}')
    return round(time.time() - t, 1)


def classic(obj, eps, out, calib, log, others=False):
    """recon_mesh classic at 4 mm over the episodes (pass 0, or F4 with the other objects' M0). Returns the full mesh."""
    f = P5['pass0_M0'] if not others else P5['fallback_F4']; fu = P5['fusion']
    cmd = [sys.executable, f'{HERE}/recon_mesh.py', '--obj', obj, '--out', out, '--calib', calib,
           '--poses', ','.join(e[0] for e in eps), '--depth', ','.join(e[1] for e in eps),
           '--voxel', str(f['voxel']), '--trunc', str(f['trunc']), '--close', f['close'], '--below_carve', str(f['below_carve']),
           '--edge_thr', str(fu['edge_thr']), '--stride', str(fu['stride'])]
    if all(e[2] != '-' for e in eps):
        cmd += ['--hands', ','.join(e[2] for e in eps)]
    if others and any(e[3] != '-' for e in eps):
        cmd += ['--others', ';'.join('' if e[3] == '-' else e[3] for e in eps)]
    run(cmd, log)
    return out.replace('.glb', '_full.glb') if os.path.exists(out.replace('.glb', '_full.glb')) else out


def fuse(obj, eps, roi, out, calib, log, g0=False):
    fu = P5['fusion']
    cmd = [sys.executable, f'{HERE}/recon_mesh.py', 'obs', '--obj', obj, '--out', out, '--roi', roi, '--calib', calib,
           '--voxel', str(fu['voxel']), '--margin', str(fu['margin']), '--free_m', str(fu['free_m']), '--free_s', str(fu['free_s']),
           '--edge_thr', str(fu['edge_thr']), '--zmax', str(fu['zmax']), '--table_band', str(fu['table_band']),
           '--below_carve', str(fu['below_carve']), '--hand_r', str(fu['hand_r']), '--arm_r', str(fu['arm_r']),
           '--arm_len', str(fu['arm_len']), '--other_r', str(fu['other_r'])] + (['--g0'] if g0 else [])
    for p, d, h, o in eps:
        cmd += ['--ep', p, d, h, str(fu['stride']), o]
    run(cmd, log)
    return out


def candidate(name, full_path, tag, work, ref_m0, seed=None):
    """Decimate a full mesh and apply T, X (vs M0) and C (vs the seed, episode mode). Returns (path or None, gates)."""
    import trimesh
    import mesh_decimate, mesh_gates
    g = dict(tag=tag)
    m = trimesh.load(full_path, force='mesh', process=True)
    try:
        md, info = mesh_decimate.decimate(m); g['T'] = True; g['decimate'] = info.get('method')
    except mesh_decimate.GateFail as e:
        g['T'] = False; g['T_fail'] = str(e)[:200]; return None, g
    p = f'{work}/{tag}_dec.glb'; md.export(p)
    x = mesh_gates.flip_check(p, ref_m0, name); g.update(X=x['pass'], xflips=x['xflips'], xadd_med_mm=x['xadd_med'])
    if seed:
        c = mesh_gates.consistency(p, seed); g.update(C=c['pass'], C_cm=c['cd_cm'])
    return p, g


def resolve_others(eps, m0_dir):
    """OTHERS entries may name objects only ('a,b'): their M0 from M0_DIR (pass 0 of the same build)."""
    out = []
    for p, d, h, o in eps:
        if o != '-' and m0_dir:
            o = ','.join(x if '=' in x else f'{x}={m0_dir}/{x}_M0.glb' for x in o.split(','))
        out.append((p, d, h, o))
    return out


def m0_only(obj, eps, out, calib):
    """Pass 0 for one object (library build step 1): OUT/<obj>_M0.glb and _M0_full.glb."""
    os.makedirs(out, exist_ok=True); t = time.time()
    m0 = classic(obj, [(p, d, h, '-') for p, d, h, _ in eps], f'{out}/{obj}_M0.glb', calib, f'{out}/{obj}_M0.log')
    return dict(obj=obj, M0=m0, sec=round(time.time() - t, 1))


def build(obj, eps, out, calib, mode='library', seed=None, g0=False, pieces=True, m0_dir=None):
    t0 = time.time(); work = f'{out}/work/{obj}'; os.makedirs(work, exist_ok=True); log = f'{work}/log.txt'
    eps = resolve_others(eps, m0_dir)
    rep = dict(obj=obj, mode=mode, episodes=[list(e) for e in eps], params='pipeline/mesh_v5.json', timings={})
    if obj == 'wooden_spoon':
        rep['skipped'] = 'spoon: template T0 (spec section 9; spoon_mesh not ported yet)'; return rep
    # pass 0 (or the build's step-1 M0)
    t = time.time()
    if m0_dir and os.path.exists(f'{m0_dir}/{obj}_M0.glb'):
        shutil.copy(f'{m0_dir}/{obj}_M0.glb', f'{work}/M0.glb')
        full0 = f'{m0_dir}/{obj}_M0_full.glb'
        m0 = full0 if os.path.exists(full0) else f'{work}/M0.glb'
    else:
        m0 = classic(obj, [(p, d, h, '-') for p, d, h, _ in eps], f'{work}/M0.glb', calib, log)
    rep['timings']['pass0'] = round(time.time() - t, 1); rep['M0'] = m0
    m0_dec = f'{work}/M0.glb'                                          # the X reference (scorer-decoded inside the gate)
    # fusion + post
    t = time.time(); grid = fuse(obj, eps, m0, f'{work}/grid.npz', calib, log, g0); rep['timings']['fuse'] = round(time.time() - t, 1)
    import mesh_post
    t = time.time(); _, orec = mesh_post.run([grid], f'{work}/O', P5['post']['below_mode'], P5['post']['variant'], decimate=False)
    rep['timings']['post'] = round(time.time() - t, 1)
    rep['O'] = {k: orec.get(k) for k in ('solid_cm3', 'g1_seen_free_violation_cm3', 'g2_unexplained8', 'g5_coarse_only_share',
                                          'g1_pass', 'g2_pass', 'full_topo', 'closing', 'unknown_share')}
    # F4
    t = time.time(); f4 = classic(obj, eps, f'{work}/F4.glb', calib, log, others=True); rep['timings']['F4'] = round(time.time() - t, 1)
    # selection (spec 4.5)
    seed_c = seed if mode != 'library' else None
    po, go = candidate(obj, orec['full'], 'O', work, m0_dec, seed_c)
    go.update(G1=orec['g1_pass'], G2=orec['g2_pass'])
    pf, gf = candidate(obj, f4, 'F4', work, m0_dec, seed_c)
    ok = lambda g, need: all(g.get(k) is True for k in need)  # noqa: E731
    need_o = ['G1', 'G2', 'T', 'X'] + (['C'] if seed_c else []); need_f = ['T', 'X'] + (['C'] if seed_c else [])
    if ok(go, need_o):
        branch, chosen = 'O', orec['full']
    elif ok(gf, need_f):
        branch, chosen = 'F4', f4
    elif seed:
        branch, chosen = 'seed (owner O2)', seed
    else:
        branch, chosen = 'F4 (QA flag: gates failed)', f4
    rep.update(gates_O=go, gates_F4=gf, branch=branch)
    # support rule on the chosen full mesh; planes from the grid, per --ep order
    import trimesh, rest_support, mesh_decimate
    full = trimesh.load(chosen, force='mesh'); full.merge_vertices()
    t = time.time()
    sup_eps = [(p, h, f'{grid}:{k}') for k, (p, d, h, o) in enumerate(eps)]
    full2, srep = rest_support.support_rule(full, obj, sup_eps, grid=grid)
    rep['support'] = srep; rep['timings']['support'] = round(time.time() - t, 1)
    if srep.get('changed'):
        _, gx = candidate(obj, _export(full2, f'{work}/support_full.glb'), 'support', work, m0_dec, seed_c)
        if not (gx.get('T') and gx.get('X')):                             # T / X re-checked after the edit (spec 4.5)
            rep['support']['reverted'] = gx; full2 = full
    full2.export(f'{out}/{obj}_full.glb')
    md, dinfo = mesh_decimate.decimate(full2); md.export(f'{out}/{obj}.glb'); rep['final'] = dinfo
    if pieces:
        import collision_decomp
        t = time.time(); hulls, crep = collision_decomp.decompose(full2, log=lambda *a: None)
        collision_decomp.write(hulls, crep, f'{out}/pieces/{obj}')
        rep['pieces'] = {k: crep[k] for k in ('n_pieces', 'solid_cm3', 'union_over_solid', 'max_piece_excess_cm3')}
        rep['timings']['pieces'] = round(time.time() - t, 1)
    rep['timings']['total'] = round(time.time() - t0, 1)
    json.dump(rep, open(f'{out}/{obj}.json', 'w'), indent=1, default=str)
    return rep


def _export(m, p):
    m.export(p); return p


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('mode', choices=['m0', 'library', 'object']); ap.add_argument('obj'); ap.add_argument('out')
    ap.add_argument('--ep', nargs=4, action='append', metavar=('POSES', 'DEPTH', 'HANDS', 'OTHERS'), required=True)
    ap.add_argument('--calib', default='/content/t3/calib.json'); ap.add_argument('--seed')
    ap.add_argument('--g0', action='store_true', default=os.environ.get('COMPLIANT') == '1')
    ap.add_argument('--no_pieces', action='store_true'); ap.add_argument('--m0_dir', help='M0 meshes of this build (step 1)')
    a = ap.parse_args()
    if a.mode == 'm0':
        print(json.dumps(m0_only(a.obj, [tuple(e) for e in a.ep], a.out, a.calib))); return
    if a.mode == 'object' and not a.seed:
        sys.exit('object (episode) mode needs --seed (the tracking seed mesh, for gate C)')
    rep = build(a.obj, [tuple(e) for e in a.ep], a.out, a.calib, a.mode, a.seed, a.g0, not a.no_pieces, a.m0_dir)
    print(json.dumps({k: rep.get(k) for k in ('obj', 'branch', 'O', 'gates_O', 'gates_F4', 'final', 'pieces', 'timings')}, default=str))


if __name__ == '__main__':
    main()
