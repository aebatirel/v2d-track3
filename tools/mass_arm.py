"""Per-arm copies of a finished grasp-lock reference that differ ONLY in the objects' masses (2026-10-31, masses
transfer check, ops/jobs/mass_check.sh; pre-registration docs/research/work/masses-transfer-20261031/PREREG.md).

Why: a grasp-lock reference names its own asset copy (refs/sf/ep<N>/assets/urdf/<obj>_rigid.urdf, written by
pipeline/support_fill.py), not /content/assets, so `make_assets.py --physics` (MA_ARGS) never reaches it. FlashCHORD
loads the URDFs named by the reference parquet's object_urdf_paths (data/motion_v1.py -> assets/registry.py
resolve_asset_path: the stored path verbatim when the file exists), with the URDF inertials (scene/objects.py add_urdf
ignore_inertial_definitions=False); the official evaluator rebuilds the scene from the checkpoint's saved task.parquet
(evaluation/harness.py). So each arm gets its own copy of the asset folder and its own copy of the reference parquet
whose object_urdf_paths point at that copy; every other column stays as it is.

For one episode:
  1. SRC = the finished reference (refs/glockt/ep<N>/<hive>/ref_gl_ilc.parquet); all its URDFs must sit under ONE asset
     root (normally refs/sf/ep<N>/assets) and carry the 0.3 kg placeholder.
  2. per ARM (name:props; props "none" = keep the placeholder): copy the asset root to
     CONTENT/refs/<ARM>_sf/ep<N>/assets; for a props arm rewrite each URDF's <mass> to the props' mass_kg and scale its
     inertia by the mass ratio (COM kept): what make_assets.py --physics does for a mass-only entry (com_m/inertia_kgm2
     null: I * mass / 0.3).
  3. per ARM and SEED: the parquet copy CONTENT/refs/<ARM>s<SEED>_glockt/ep<N>/<hive>/ref_gl_ilc.parquet (the only
     .parquet under that folder: FlashCHORD's resolve_parquet needs exactly one); the base reference link
     CONTENT/refs/<ARM>s<SEED><BASE>/ep<N> -> CONTENT/refs/perc2<BASE>/ep<N> (glock_public.sh reads its hive and support
     stage there); CONTENT/results/<ARM>s<SEED>_glock_public/ep<N>/rest_check.json (+ zero_score.txt) copied from the
     finished reference, so glock_public.sh REUSE_REF=1 trains on the copy. PAIRS entry: <N>:local:<BASE>:<ARM>s<SEED>.
  4. a manifest (JSON) with md5s, masses and the column check.
Nothing here reads ground truth. Usage:
  mass_arm.py --ep N --base mck --arms "mass0:none mass1:PROPS.json" --seeds "42 43" --out MANIFEST.json [--content /content]
"""
import argparse, glob, hashlib, json, os, re, shutil, sys, time
import pyarrow as pa, pyarrow.parquet as pq

PLACEHOLDER = 0.3
PATH_COLS = ('object_urdf_paths',)                 # the only column an arm copy changes


def md5(f):
    h = hashlib.md5()
    with open(f, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def traj_fingerprint(t):
    """md5 over every column except the asset-path columns (object_urdf_paths, object_mesh_paths): the same reference
    motion, hands and contact targets give the same value wherever the file lives or which assets it names."""
    h = hashlib.md5()
    for n in sorted(t.column_names):
        if n in ('object_urdf_paths', 'object_mesh_paths'):
            continue
        h.update(n.encode()); h.update(json.dumps(t.column(n).to_pylist(), sort_keys=True, default=str).encode())
    return h.hexdigest()


INERT = re.compile(r'<inertial>.*?</inertial>', re.S)
MASS = re.compile(r'<mass\s+value="([^"]+)"\s*/>')
INERTIA = re.compile(r'<inertia\s+([^/]*)/>')
ORIGIN = re.compile(r'<origin\s+xyz="([^"]+)"')


def read_inertial(txt):
    """(mass, com xyz string, {ixx..izz}) of the single <inertial> block of a URDF text."""
    blocks = INERT.findall(txt)
    if len(blocks) != 1:
        raise ValueError(f'{len(blocks)} <inertial> blocks (one expected)')
    b = blocks[0]
    m = MASS.findall(b); I = INERTIA.findall(b); o = ORIGIN.findall(b)
    if len(m) != 1 or len(I) != 1:
        raise ValueError('inertial block without exactly one <mass> and one <inertia>')
    comps = dict(re.findall(r'(i[xyz]{2})="([^"]+)"', I[0]))
    return float(m[0]), (o[0] if o else None), {k: float(v) for k, v in comps.items()}


def set_mass(txt, new_mass, note):
    """URDF text with the mass set to new_mass and the inertia scaled by new_mass / old mass (COM unchanged)."""
    old, _, comps = read_inertial(txt)
    k = new_mass / old
    b = INERT.findall(txt)[0]
    nb = MASS.sub(f'<mass value="{new_mass}"/>', b, count=1)
    nb = INERTIA.sub('<inertia ' + ' '.join(f'{c}="{comps[c] * k:.9g}"' for c in ('ixx', 'ixy', 'ixz', 'iyy', 'iyz', 'izz'))
                     + '/>', nb, count=1)
    out = txt.replace(b, nb, 1)
    return re.sub(r'(<robot[^>]*>)', r'\1\n  <!-- ' + note.replace('--', '-') + ' -->', out, count=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ep', type=int, required=True); ap.add_argument('--base', required=True)
    ap.add_argument('--arms', required=True); ap.add_argument('--seeds', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--content', default='/content')
    a = ap.parse_args()
    C, ep = a.content.rstrip('/'), a.ep
    src = glob.glob(f'{C}/refs/glockt/ep{ep}/processed/*/*/ref_gl_ilc.parquet')
    if len(src) != 1:
        sys.exit(f'mass_arm ep{ep}: {len(src)} finished references under {C}/refs/glockt/ep{ep} (one expected)')
    src = src[0]; R0 = f'{C}/refs/perc2{a.base}/ep{ep}'
    hive = os.path.relpath(os.path.dirname(src), f'{C}/refs/glockt/ep{ep}')
    if not glob.glob(f'{R0}/{hive}/*.parquet'):
        sys.exit(f'mass_arm ep{ep}: no base reference under {R0}/{hive}')
    rc = f'{C}/results/glock_public/ep{ep}/rest_check.json'
    if not os.path.exists(rc):
        sys.exit(f'mass_arm ep{ep}: {rc} missing (glock_public.sh REUSE_REF needs it)')
    t = pq.read_table(src); names = t.column('object_body_names')[0].as_py(); urdfs = t.column('object_urdf_paths')[0].as_py()
    roots = {os.path.dirname(os.path.dirname(u)) for u in urdfs}
    if len(roots) != 1:
        sys.exit(f'mass_arm ep{ep}: the reference names {len(roots)} asset roots {sorted(roots)} (one expected)')
    root = roots.pop()
    src_urdf = {}
    for n, u in zip(names, urdfs):
        if os.path.basename(u) != f'{n}_rigid.urdf' or not os.path.isfile(u):
            sys.exit(f'mass_arm ep{ep}: URDF {u} missing or not named after body {n}')
        m, com, _ = read_inertial(open(u).read())
        if abs(m - PLACEHOLDER) > 1e-9:
            sys.exit(f'mass_arm ep{ep}: {u} has mass {m}, not the {PLACEHOLDER} kg placeholder this check assumes')
        src_urdf[n] = dict(path=u, md5=md5(u), mass=m, com=com)
    fp = traj_fingerprint(t)
    man = dict(episode=ep, base=a.base, source_parquet=src, source_md5=md5(src), traj_fingerprint=fp, hive=hive,
               source_asset_root=root, source_urdfs=src_urdf, arms={}, created=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    ts = int(time.time())
    for spec in a.arms.split():
        arm, props = spec.split(':', 1)
        if '=' in arm or '/' in arm:
            sys.exit(f'mass_arm: bad arm name {arm}')
        props = None if props == 'none' else props
        P = json.load(open(props)) if props else {}
        A = f'{C}/refs/{arm}_sf/ep{ep}/assets'
        if os.path.lexists(A):                                   # an earlier attempt on this box: keep it aside
            os.rename(A, f'{A}.prev_{ts}')
        shutil.copytree(root, A, symlinks=False)
        new_urdfs, objs = [], {}
        for n, u in zip(names, urdfs):
            dst = os.path.join(A, os.path.relpath(u, root)); txt = open(dst).read()
            if props:
                if 'physics' not in P.get(n, {}):
                    sys.exit(f'mass_arm ep{ep} {arm}: {props} has no physics entry for {n}')
                ph = P[n]['physics']
                if ph.get('com_m') is not None or ph.get('inertia_kgm2') is not None:
                    sys.exit(f'mass_arm ep{ep} {arm}: {n} is not a mass-only entry (this check changes masses only)')
                txt = set_mass(txt, float(ph['mass_kg']), f'mass_arm.py (masses transfer check, 2026-10-31): mass {PLACEHOLDER} -> '
                               f"{ph['mass_kg']} kg from {os.path.basename(props)} ({ph.get('material')}); COM kept, inertia "
                               'scaled by the mass ratio as make_assets.py --physics does for a mass-only entry')
                open(dst, 'w').write(txt)
            m, com, I = read_inertial(open(dst).read())
            want = float(P[n]['physics']['mass_kg']) if props else PLACEHOLDER
            if abs(m - want) > 1e-9 or com != src_urdf[n]['com']:
                sys.exit(f'mass_arm ep{ep} {arm}: {dst} mass {m} (want {want}), COM {com} (source {src_urdf[n]["com"]})')
            new_urdfs.append(os.path.abspath(dst))
            objs[n] = dict(urdf=os.path.abspath(dst), md5=md5(dst), mass=m, com=com, inertia=I,
                           identical_to_source=md5(dst) == src_urdf[n]['md5'])
        meshes = {os.path.relpath(f, A): md5(f) for f in sorted(glob.glob(f'{A}/**/*', recursive=True))
                  if os.path.isfile(f) and not f.endswith('.urdf')}
        src_meshes = {os.path.relpath(f, root): md5(f) for f in sorted(glob.glob(f'{root}/**/*', recursive=True))
                      if os.path.isfile(f) and not f.endswith('.urdf')}
        if meshes != src_meshes:
            sys.exit(f'mass_arm ep{ep} {arm}: the copied mesh files differ from the source asset folder')
        ti = t.column_names.index('object_urdf_paths')
        ta = t.set_column(ti, 'object_urdf_paths', pa.array([new_urdfs], type=t.schema.field('object_urdf_paths').type))
        same = ta.drop_columns(list(PATH_COLS)).equals(t.drop_columns(list(PATH_COLS)))
        if not same or traj_fingerprint(ta) != fp:
            sys.exit(f'mass_arm ep{ep} {arm}: the copy differs from the source in a column other than {PATH_COLS}')
        man['arms'][arm] = dict(props=props, asset_root=A, objects=objs, mesh_md5=meshes, seeds={})
        for s in a.seeds.split():
            pre = f'{arm}s{s}'
            RD = f'{C}/refs/{pre}_glockt/ep{ep}'
            if os.path.lexists(RD):
                os.rename(RD, f'{RD}.prev_{ts}')
            os.makedirs(f'{RD}/{hive}'); dpq = f'{RD}/{hive}/ref_gl_ilc.parquet'; pq.write_table(ta, dpq)
            n_pq = len(glob.glob(f'{RD}/**/*.parquet', recursive=True))
            if n_pq != 1:
                sys.exit(f'mass_arm: {RD} holds {n_pq} parquet files (FlashCHORD needs exactly one)')
            lk = f'{C}/refs/{pre}{a.base}/ep{ep}'; os.makedirs(os.path.dirname(lk), exist_ok=True)
            if os.path.lexists(lk):
                os.remove(lk) if os.path.islink(lk) else os.rename(lk, f'{lk}.prev_{ts}')
            os.symlink(R0, lk)
            O = f'{C}/results/{pre}_glock_public/ep{ep}'
            if os.path.lexists(O):
                os.rename(O, f'{O}.prev_{ts}')
            os.makedirs(O)
            for f in ('rest_check.json', 'zero_score.txt', 'support_fill.json'):
                if os.path.exists(f'{C}/results/glock_public/ep{ep}/{f}'):
                    shutil.copy(f'{C}/results/glock_public/ep{ep}/{f}', f'{O}/{f}')
            json.dump(dict(arm=arm, seed=int(s), source_parquet=src, source_md5=man['source_md5'], traj_fingerprint=fp,
                           asset_root=A, masses={n: objs[n]['mass'] for n in names}), open(f'{O}/mass_arm.json', 'w'), indent=1)
            man['arms'][arm]['seeds'][s] = dict(parquet=dpq, md5=md5(dpq), traj_fingerprint=traj_fingerprint(pq.read_table(dpq)),
                                                base_link=lk, results=O, pair=f'{ep}:local:{a.base}:{pre}')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(man, open(a.out, 'w'), indent=1)
    print(f'mass_arm ep{ep}: source {src} (md5 {man["source_md5"]}, fingerprint {fp}); ' + '; '.join(
        f'{arm}: ' + ', '.join(f'{n} {o["mass"]} kg' for n, o in v['objects'].items()) for arm, v in man['arms'].items()))


if __name__ == '__main__':
    main()
