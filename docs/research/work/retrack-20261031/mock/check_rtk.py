"""Checks of one re-track (LIB_EP_DIR) perc_leak mock run (2026-10-31). usage:
  check_rtk.py MR RUN_ID 'EPS' DELIVERY REF [ARMS] [REPEAT]
    DELIVERY  the delivery folder as the job got it (absolute, inside the mock repo)
    REF       folder with ep<N>/perc2/{poses.npz,poses_world_vo.npz} of the LIB_EP_DIR-unset reference run (P_o)
Exit 1 if any expectation fails:
  - job rc 0; every bundle ok; arms = perc2 (+ perc2rep on REPEAT); bundle lib_ep_dir = DELIVERY;
  - per object: source 'episode' iff DELIVERY/ep<N>/<obj>.glb exists, else 'library'; the template md5 in the bundle and
    in the perc2 audit (what the stub perc2 actually read) = that file's md5; templates_as_delivered true; run.json
    records lib_ep_dir and lib; perc2 saw MESH_DIR = MR/content/rtk_templates/ep<N>, KF_MIN 120, SPLIT public,
    HF_HUB_OFFLINE 1, the depth cache existed;
  - tracks vs P_o (REF): world_T_cam identical; cam_T_<obj> and the world track identical iff the template is
    byte-identical to library_v3, different otherwise (stub_rtk.py makes the track depend on the template bytes);
  - perc_log_inference.txt without scoring lines; store traffic 3 single-file downloads per episode, 0 listings,
    1 upload; tars = folder minus result.json / log.txt; tools/no_oracle.py refuses every pushed results/leak_p1 file
    by its store path runs/RUN_ID/... (the other pushed files are listed)."""
import hashlib, io, json, os, runpy, sys, contextlib, tarfile
import numpy as np

MR, RID, EPS, DLV, REF = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split()], sys.argv[4], sys.argv[5]
ARMS = (sys.argv[6] if len(sys.argv) > 6 else 'o').split(','); REP = {int(x) for x in (sys.argv[7] if len(sys.argv) > 7 else '').split()}
C = f'{MR}/content'; B = f'{C}/results/leak_p1'; LIB = f'{C}/v2d-track3/meshes/library_v3'; fails = []
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()


def need(cond, what):
    if not cond:
        fails.append(what)
    return cond


rc = open(f'{MR}/rc.txt').read().strip(); need(rc == '0', f'job rc {rc}')
aud = [json.loads(l) for l in open(f'{MR}/perc2_audit.log')] if os.path.exists(f'{MR}/perc2_audit.log') else []
hf = [json.loads(l) for l in open(f'{MR}/hf.log')] if os.path.exists(f'{MR}/hf.log') else []
tsv = f'{C}/v2d-track3/docs/research/work/leak-decomp-20261030/phase1/inputs.tsv'
R = {int(l.split('\t')[0]): l.split('\t')[2].split(',') for l in open(tsv).read().splitlines()[1:]}
n_same = n_diff = 0
for e in EPS:
    folders = ['perc2'] + (['perc2rep'] if 'o2' in ARMS and e in REP else [])
    b = json.load(open(f'{B}/ep{e}/bundle.json'))
    need(b['ok'], f'ep{e} bundle not ok'); need(sorted(b['arms']) == sorted(folders), f'ep{e} arms {sorted(b["arms"])}')
    need(b.get('lib_ep_dir') == DLV, f'ep{e} bundle lib_ep_dir {b.get("lib_ep_dir")} != {DLV}')
    srcs = []
    for f in folders:
        a = b['arms'][f]; au = [x for x in aud if x['ep'] == e and x['folder'] == f]
        need(len(au) == 1, f'ep{e} {f}: {len(au)} perc2 runs'); au = au[-1] if au else {}
        run = json.load(open(f'{B}/ep{e}/{f}/run.json'))
        need(run.get('lib_ep_dir') == DLV and run.get('lib') == LIB, f'ep{e} {f} run.json lib_ep_dir/lib {run.get("lib_ep_dir")}/{run.get("lib")}')
        need(au.get('mesh_dir') == f'{C}/rtk_templates/ep{e}', f'ep{e} {f} MESH_DIR seen by perc2 {au.get("mesh_dir")}')
        need(au.get('kf_min') == '120' and au.get('split') == 'public' and au.get('hf_hub_offline') == '1'
             and au.get('depth_cache_existed') is True, f'ep{e} {f} perc2 env {au}')
        need(a.get('templates_as_delivered') is True, f'ep{e} {f} templates_as_delivered {a.get("templates_as_delivered")}')
        for n in R[e]:
            dl = f'{DLV}/ep{e}/{n}.glb'; want = 'episode' if os.path.isfile(dl) else 'library'
            wmd5 = md5(dl if want == 'episode' else f'{LIB}/{n}.glb')
            t = a['templates'][n]
            need(t.get('source') == want, f'ep{e} {f} {n} source {t.get("source")} != {want}')
            need(t['md5'] == wmd5 and au.get('template_md5', {}).get(n) == wmd5, f'ep{e} {f} {n} template md5 bundle/audit != {wmd5}')
            srcs.append(f'{n}={t.get("source")}')
        need(os.path.isfile(f'{B}/ep{e}/{f}/perc_log_inference.txt') and not any(
            k in open(f'{B}/ep{e}/{f}/perc_log_inference.txt').read() for k in (' AUC ', 'anchor:', 'DONE')), f'ep{e} {f} scoring lines')
    z, r = np.load(f'{B}/ep{e}/perc2/poses.npz'), np.load(f'{REF}/ep{e}/perc2/poses.npz')
    w, rw = np.load(f'{B}/ep{e}/perc2/poses_world_vo.npz'), np.load(f'{REF}/ep{e}/perc2/poses_world_vo.npz')
    need(np.array_equal(z['world_T_cam'], r['world_T_cam']), f'ep{e} camera differs from P_o')
    rep = []
    for n in R[e]:
        same_bytes = md5(b['arms']['perc2']['templates'][n]['path']) == md5(f'{LIB}/{n}.glb')
        eq = np.array_equal(z[f'cam_T_{n}'], r[f'cam_T_{n}']) and np.array_equal(w[n], rw[n])
        need(eq == same_bytes, f'ep{e} {n}: track {"identical" if eq else "different"} to P_o, template '
             f'{"=" if same_bytes else "!="} library_v3 bytes')
        n_same += eq; n_diff += not eq
        rep.append(f'{n} {"= P_o" if eq else "!= P_o (template differs)"}')
    print(f'ep{e}: bundle ok {b["ok"]}; {", ".join(srcs)}; tracks: {"; ".join(rep)}')
dl = [x for x in hf if x['kind'] == 'file']
need('LISTING' not in [x['kind'] for x in hf], 'a download listed the repo')
need(len([x for x in dl if x['result'] == 'ok']) == 3 * len(EPS), f'{len(dl)} downloads for {len(EPS)} episodes')
need([x['kind'] for x in hf].count('upload') == 1, 'uploads != 1')
S = f'{C}/push/{RID}'; files = []
for r_, ds, fs in os.walk(S):
    files += [os.path.relpath(f'{r_}/{f}', S) for f in fs]
p1 = [f for f in files if f.startswith('results/leak_p1/')]
for e in EPS:
    tf = f'results/leak_p1/bundle_ep{e}_oracle.tar'
    if need(tf in p1, f'push lacks {tf}'):
        with tarfile.open(f'{S}/{tf}') as t:
            n = sorted(m.name for m in t.getmembers() if m.isfile())
        need(n == sorted(f[len('results/leak_p1/'):] for f in p1 if f.startswith(f'results/leak_p1/ep{e}/')
                         and os.path.basename(f) not in ('result.json', 'log.txt')), f'{tf} != ep{e}/ minus result.json, log.txt')
need(not [f for f in files if os.path.basename(f).startswith('depths_') or os.path.islink(f'{S}/{f}')], 'depth cache or link pushed')
G = f'{C}/v2d-track3/tools/no_oracle.py'


def refused(word):
    sys.argv = [G, word]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            runpy.run_path(G, run_name='__main__')
        except SystemExit as x:
            return x.code == 1
    return False


acc = [f for f in p1 if not refused(f'runs/{RID}/{f}')]
need(not acc, f'guard accepts {len(acc)} results/leak_p1 files: {acc[:3]}')
other = sorted(f for f in files if not f.startswith('results/leak_p1/'))
other_acc = [f for f in other if not refused(f'runs/{RID}/{f}')]
jl = open(f'{C}/job.log').read()
need('rtk_mesh_check verify' in jl and 'OK' in jl.split('rtk_mesh_check verify')[1][:400], 'no verify OK line in job.log')
print(f'store: {len(dl)} single-file downloads, {[x["kind"] for x in hf].count("LISTING")} listings, '
      f'{[x["kind"] for x in hf].count("upload")} upload; push {len(files)} files ({len(p1)} under results/leak_p1, all refused by '
      f'the guard by store path: {not acc}); other pushed files not refused (no tracks in them): {other_acc}')
print(f'tracks vs P_o: {n_same} objects identical, {n_diff} different')
print('RESULT:', 'ALL CHECKS PASS' if not fails else f'{len(fails)} FAILED: {fails[:12]}')
sys.exit(1 if fails else 0)
