"""Per-seed BYTE copies of a packed grasp-lock eval reference for the D arm (2026-10-31, pack 9b; ops/jobs/mass_eval.sh
ARM=dr; docs/research/work/pack9b-20261031/PREREG.md section 1.1). The counterpart of tools/mass_arm.py without any
mass change: the D arm trains on exactly the packed reference file and the packed asset copy it names.

For one episode (after mass_eval.sh pulled and checked the packed reference):
  1. SRC = refs/glockt/ep<N>/<hive>/ref_gl_ilc.parquet (exactly one), whose md5 and fingerprint must be the table's
     (packed_refs.json); every URDF it names must be a file under ONE asset root, the table's asset_root, at the 0.3 kg
     placeholder;
  2. per SEED: CONTENT/refs/drs<SEED>_glockt/ep<N>/<hive>/ref_gl_ilc.parquet = a byte copy of SRC (md5 asserted; the
     only .parquet there: FlashCHORD's resolve_parquet needs exactly one); the base link CONTENT/refs/drs<SEED><BASE>/ep<N>
     -> CONTENT/refs/perc2<BASE>/ep<N> (glock_public.sh reads its hive and support stage there); CONTENT/results/
     drs<SEED>_glock_public/ep<N>/{rest_check.json, zero_score.txt, support_fill.json} copied from the packed run's
     results, so glock_public.sh REUSE_REF=1 REQUIRE_REUSE=1 trains on the copy. PAIRS entry <N>:local:<BASE>:drs<SEED>;
  3. a manifest (JSON): source md5 / fingerprint, the URDFs (path, md5, mass) and the md5 of every file under the asset
     root (tools/dr_eval_verify.py compares them after training), per seed the copy's md5, link, results dir and pair.
Nothing here reads ground truth. Usage:
  dr_arm.py --ep N --base mck --seeds "42 43" --table packed_refs.json --out MANIFEST.json [--content /content]
"""
import argparse, glob, json, os, re, shutil, sys, time
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_arm import md5, traj_fingerprint, read_inertial, PLACEHOLDER   # noqa: E402

PREFIX = 'drs'


def tab_path(p, C):
    """a box path of the table (/content/... or /workspace/...) under this box's content root C (regex: no literal box
    root in this file, so the CPU mock's path rewrite leaves it alone)"""
    return re.sub(r'^/(?:content|workspace)/', C.rstrip('/') + '/', p)


def tree_md5(root):
    return {os.path.relpath(f, root): md5(f) for f in sorted(glob.glob(f'{root}/**/*', recursive=True)) if os.path.isfile(f)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ep', type=int, required=True); ap.add_argument('--base', required=True)
    ap.add_argument('--seeds', required=True); ap.add_argument('--table', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--content', default='/content')
    a = ap.parse_args()
    C, ep = a.content.rstrip('/'), a.ep
    T = json.load(open(a.table))['episodes'][str(ep)]
    if T['mode'] != 'glock':
        sys.exit(f'dr_arm ep{ep}: table mode {T["mode"]} (grasp lock only; the standard learner copies with hard_ab.sh SUF=dr)')
    src = glob.glob(f'{C}/refs/glockt/ep{ep}/processed/*/*/ref_gl_ilc.parquet')
    if len(src) != 1:
        sys.exit(f'dr_arm ep{ep}: {len(src)} finished references under {C}/refs/glockt/ep{ep} (one expected)')
    src = src[0]; hive = os.path.relpath(os.path.dirname(src), f'{C}/refs/glockt/ep{ep}')
    t = pq.read_table(src); fp, m5 = traj_fingerprint(t), md5(src)
    if m5 != T['md5'] or fp != T['traj_fingerprint']:
        sys.exit(f'dr_arm ep{ep}: {src} is {m5} / {fp}, the packed reference is {T["md5"]} / {T["traj_fingerprint"]}')
    R0 = f'{C}/refs/perc2{a.base}/ep{ep}'
    if not glob.glob(f'{R0}/{hive}/*.parquet'):
        sys.exit(f'dr_arm ep{ep}: no base reference under {R0}/{hive}')
    rc = f'{C}/results/glock_public/ep{ep}/rest_check.json'
    if not os.path.exists(rc):
        sys.exit(f'dr_arm ep{ep}: {rc} missing (glock_public.sh REUSE_REF needs it)')
    names = t.column('object_body_names')[0].as_py(); urdfs = t.column('object_urdf_paths')[0].as_py()
    roots = {os.path.dirname(os.path.dirname(tab_path(u, C))) for u in urdfs}
    want_root = tab_path(T['asset_root'], C)
    if roots != {want_root}:
        sys.exit(f'dr_arm ep{ep}: the reference names asset roots {sorted(roots)}, the table {want_root}')
    src_urdf = {}
    for n, u in zip(names, urdfs):
        lu = tab_path(u, C)
        if os.path.basename(lu) != f'{n}_rigid.urdf' or not os.path.isfile(lu):
            sys.exit(f'dr_arm ep{ep}: URDF {u} missing or not named after body {n}')
        m, com, _ = read_inertial(open(lu).read())
        if abs(m - PLACEHOLDER) > 1e-9:
            sys.exit(f'dr_arm ep{ep}: {lu} has mass {m}, not the {PLACEHOLDER} kg placeholder the packed policy trained with')
        src_urdf[n] = dict(path=lu, md5=md5(lu), mass=m, com=com)
    man = dict(episode=ep, base=a.base, arm='dr', source_parquet=src, source_md5=m5, traj_fingerprint=fp, hive=hive,
               asset_root=want_root, urdfs=src_urdf, asset_md5=tree_md5(want_root), seeds={},
               created=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    ts = int(time.time())
    for s in a.seeds.split():
        pre = f'{PREFIX}{s}'
        RD = f'{C}/refs/{pre}_glockt/ep{ep}'
        if os.path.lexists(RD):
            os.rename(RD, f'{RD}.prev_{ts}')
        os.makedirs(f'{RD}/{hive}'); dpq = f'{RD}/{hive}/ref_gl_ilc.parquet'; shutil.copyfile(src, dpq)
        if md5(dpq) != m5:
            sys.exit(f'dr_arm ep{ep}: copy {dpq} is not byte-identical to {src}')
        n_pq = len(glob.glob(f'{RD}/**/*.parquet', recursive=True))
        if n_pq != 1:
            sys.exit(f'dr_arm: {RD} holds {n_pq} parquet files (FlashCHORD needs exactly one)')
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
        json.dump(dict(arm='dr', seed=int(s), source_parquet=src, source_md5=m5, traj_fingerprint=fp, asset_root=want_root,
                       masses={n: v['mass'] for n, v in src_urdf.items()}), open(f'{O}/dr_arm.json', 'w'), indent=1)
        man['seeds'][s] = dict(parquet=dpq, md5=md5(dpq), base_link=lk, results=O, pair=f'{ep}:local:{a.base}:{pre}')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(man, open(a.out, 'w'), indent=1)
    print(f'dr_arm ep{ep}: source {src} (md5 {m5}, fingerprint {fp}) byte-copied for seeds {a.seeds.split()}; URDFs '
          + ', '.join(f'{n} {v["mass"]} kg' for n, v in src_urdf.items()) + f' under {want_root} (unchanged)')


if __name__ == '__main__':
    main()
