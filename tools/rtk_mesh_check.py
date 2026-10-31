"""Delivery validator for per-episode tracking templates (re-track test, 2026-10-31;
docs/research/work/retrack-20261031/{PREREG,BUILD,JOBS}).

The mesh session delivers DIR/ep<N>/<object>.glb, built by its C0b/E0b method from public episode N's own video, plus
DIR/MANIFEST.json (method, commit, provenance). ops/jobs/perc_leak.sh LIB_EP_DIR=DIR tracks episode N with those meshes
(library_v3 for objects not delivered) and tools/leak_p1.py score registers the same meshes (lib convention).

  check DIR --kit KIT [--tsv TSV] [--lib LIB] [--write] [--dense N] [--query N]      (CPU, this VM)
    HARD checks, exit 1 on any failure:
      layout    only ep<N>/ folders of the 20 public episodes (TSV, phase1/inputs.tsv) and only <obj>.glb meshes named
                after that episode's objects; any other mesh suffix (.obj .ply .stl .off .gltf) fails, because perc2 only
                reads <obj>.glb and would silently use library_v3; sidecar .json / .md / .txt files are allowed;
      glTF      GLB version 2, no extensionsRequired (e.g. Draco: trimesh may not decode it), every node's matrix /
                translation / rotation / scale the identity (perc2, the kit and the simulator must all see the same
                body frame; a node transform is a frame trap);
      geometry  trimesh.load(force='mesh') as perc2 and the kit load it: non-empty, finite; the kit's budget_mesh(4096,
                4096) (what the scorer registers) succeeds;
      metres    largest extent in [2 cm, 1 m] and each sorted extent within x0.5-x2 of library_v3's same object (a mm or
                cm export is a 10-1000x error);
      manifest  DIR/MANIFEST.json parses and has an entry per delivered mesh (a key, or a 'path' / 'file' value, ending
                in 'ep<N>/<obj>.glb'); when the entry gives md5 / sha256 they equal the file's; a provenance tier
                ('provenance_tier' of the entry, else of the manifest) is present. It is recorded verbatim: the
                validator CANNOT prove that a mesh is GT-free; the tier is the mesh session's statement;
      guard     tools/no_oracle.py on DIR refuses nothing (public scans and scan-templated tracks by sha256, oracle /
                scan names).
    FLAGS, exit 2 (a human reads them; they do not invalidate the public test, which registers the tracked mesh itself,
    but they matter for any later use of the meshes as simulator / reference bodies built from library_v3):
      frame     tools/pack_swap_meshes.py's frame_report vs library_v3 (centroid, AABB, surface distance, ICP from
                identity, kit-registration proxy, extent ratios; same limits: 5 mm, 5 deg, +-15 %);
      size      more than 300k faces (FoundationPose time; the Phase-1 scans had ~98k);
      tier      a provenance tier that mentions scan / mocap / oracle / ground truth / GT (read it: it may be a
                legitimate disclaimer such as "library_v3 itself was fused along scan-templated tracks").
    --write  DIR/VALIDATION.json: status pass | flagged | fail, every file's md5 / sha256 / bytes, the manifest's md5,
             coverage per episode (objects delivered vs library_v3 fallback), failures, flags, frame reports.
  verify DIR [TSV]                                                                    (box, stdlib only)
    perc_leak.sh's gate in LIB_EP_DIR mode: DIR/VALIDATION.json exists with status pass or flagged, every mesh file
    under DIR/ep*/ is listed in it, every listed file and MANIFEST.json still has its recorded md5, and (TSV given)
    every listed mesh is an object of its episode. Exit 0, else 1.
Reads no ground truth: no parquet, no mocap, no scan geometry (the frame report compares with library_v3 only).
"""
import argparse, glob, hashlib, json, os, re, struct, subprocess, sys, time, types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSV = os.path.join(REPO, 'docs', 'research', 'work', 'leak-decomp-20261030', 'phase1', 'inputs.tsv')
MESH_SUFFIX = ('.glb', '.gltf', '.obj', '.ply', '.stl', '.off')
SIDECAR = ('.json', '.md', '.txt')
TOP_OK = {'MANIFEST.json', 'VALIDATION.json'}
TIER_WORDS = re.compile(r'\b(?:scan\w*|mocap|oracle|ground[ -]?truth|GT)\b(?![ -]?free)', re.I)   # review 31 Oct: 'GT-free' is not a hit
MAX_FACES = 300_000


def digest(path, algo='md5'):
    h = hashlib.new(algo)
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def roster(tsv):  # episode -> [objects in slot order] (inputs.tsv: names only, no poses)
    out = {}
    for line in open(tsv).read().splitlines()[1:]:
        c = line.split('\t')
        out[int(c[0])] = c[2].split(',')
    return out


def glb_json(path):
    with open(path, 'rb') as f:
        head = f.read(20)
        if len(head) < 20:
            raise ValueError('shorter than a GLB header')
        magic, ver, _ = struct.unpack('<4sII', head[:12]); clen, ctype = struct.unpack('<I4s', head[12:20])
        if magic != b'glTF' or ver != 2 or ctype != b'JSON':
            raise ValueError(f'not a GLB v2 with a JSON chunk (magic {magic!r}, version {ver}, chunk {ctype!r})')
        return json.loads(f.read(clen))


def node_problems(j):
    bad = []
    for i, n in enumerate(j.get('nodes', [])):
        M = n.get('matrix')
        if M is not None and any(abs(a - b) > 1e-9 for a, b in zip(M, [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])):
            bad.append(f'node {i} matrix {M}')
        if any(abs(a) > 1e-12 for a in n.get('translation', [0, 0, 0])):
            bad.append(f'node {i} translation {n["translation"]}')
        if any(abs(a - b) > 1e-12 for a, b in zip(n.get('rotation', [0, 0, 0, 1]), [0, 0, 0, 1])):
            bad.append(f'node {i} rotation {n["rotation"]}')
        if any(abs(a - 1) > 1e-12 for a in n.get('scale', [1, 1, 1])):
            bad.append(f'node {i} scale {n["scale"]}')
    return bad


def find_entry(man, rel):
    """The manifest entry of DIR-relative path rel ('ep<N>/<obj>.glb'): a dict under a key ending in rel, or a dict
    whose 'path' / 'file' ends in rel (depth-first, first match)."""
    if isinstance(man, dict):
        for k, v in man.items():
            if isinstance(v, dict) and (k == rel or k.endswith('/' + rel)):
                return v
        for key in ('path', 'file'):
            if isinstance(man.get(key), str) and (man[key] == rel or man[key].endswith('/' + rel)):
                return man
        vals = man.values()
    elif isinstance(man, list):
        vals = man
    else:
        return None
    for v in vals:
        e = find_entry(v, rel)
        if e is not None:
            return e
    return None


def check(a):
    d = os.path.abspath(a.dir); fails, flags, files, frames = [], [], {}, []
    R = roster(a.tsv); sys.path.insert(0, a.kit); sys.path.insert(0, os.path.join(REPO, 'tools'))
    import numpy as np, trimesh
    from v2dlb.mesh_budget import budget_mesh
    import pack_swap_meshes as PS
    if not os.path.isdir(d):
        sys.exit(f'{d} is not a directory')
    man, man_md5 = None, None
    if os.path.isfile(f'{d}/MANIFEST.json'):
        man_md5 = digest(f'{d}/MANIFEST.json')
        try:
            man = json.load(open(f'{d}/MANIFEST.json'))
        except Exception as x:
            fails.append(f'MANIFEST.json does not parse: {x!r}')
    else:
        fails.append('MANIFEST.json missing (the provenance tier must be recorded)')
    top_tier = man.get('provenance_tier') if isinstance(man, dict) else None
    for name in sorted(os.listdir(d)):                                   # layout
        p = f'{d}/{name}'
        if os.path.isdir(p):
            m = re.fullmatch(r'ep(\d+)', name)
            if not m or int(m.group(1)) not in R:
                fails.append(f'{name}/: not ep<N> of a public episode in {os.path.basename(a.tsv)}'); continue
            ep = int(m.group(1))
            for f in sorted(os.listdir(p)):
                stem, suf = os.path.splitext(f); rel = f'{name}/{f}'
                if os.path.isdir(f'{p}/{f}'):
                    fails.append(f'{rel}/: sub-folder (perc2 reads ep<N>/<obj>.glb only)')
                elif suf.lower() == '.glb' and suf == '.glb':
                    if stem not in R[ep]:
                        fails.append(f'{rel}: {stem} is not an object of ep{ep} ({",".join(R[ep])})')
                    else:
                        files[rel] = dict(episode=ep, object=stem, slot=R[ep].index(stem))
                elif suf.lower() in MESH_SUFFIX:
                    fails.append(f'{rel}: mesh suffix {suf} (perc2 only reads <obj>.glb; it would track library_v3)')
                elif suf.lower() not in SIDECAR:
                    fails.append(f'{rel}: unexpected file')
        elif name not in TOP_OK and not name.lower().endswith(('.md', '.txt')):
            fails.append(f'{name}: unexpected top-level file')
    if not files:
        fails.append('no ep<N>/<obj>.glb mesh delivered')
    for rel, r in files.items():
        p = f'{d}/{rel}'; ep, obj = r['episode'], r['object']; lib = f'{a.lib}/{obj}.glb'
        r.update(md5=digest(p), sha256=digest(p, 'sha256'), bytes=os.path.getsize(p))
        try:
            j = glb_json(p)
            if j.get('extensionsRequired'):
                fails.append(f'{rel}: extensionsRequired {j["extensionsRequired"]}')
            nb = node_problems(j)
            if nb:
                fails.append(f'{rel}: node transforms ({"; ".join(nb[:3])})')
            r['gltf'] = dict(nodes=len(j.get('nodes', [])), meshes=len(j.get('meshes', [])), extensionsUsed=j.get('extensionsUsed', []))
        except Exception as x:
            fails.append(f'{rel}: GLB unreadable ({x!r})'); continue
        try:
            m = trimesh.load(p, force='mesh'); v, f = np.asarray(m.vertices, float), np.asarray(m.faces)
            ok = len(v) > 0 and len(f) > 0 and np.isfinite(v).all()
            r.update(vertices=int(len(v)), faces=int(len(f)))
            if not ok:
                fails.append(f'{rel}: empty or non-finite geometry'); continue
            budget_mesh(p, 4096, 4096)
        except Exception as x:
            fails.append(f'{rel}: trimesh / kit budget_mesh failed ({x!r})'); continue
        ext = v.max(0) - v.min(0); r['extent_mm'] = [round(float(e) * 1000, 2) for e in ext]
        if not 0.02 <= ext.max() <= 1.0:
            fails.append(f'{rel}: largest extent {ext.max():.4g} (units: metres expected, 2 cm-1 m)')
        if os.path.isfile(lib):
            lv = np.asarray(trimesh.load(lib, force='mesh').vertices, float); le = lv.max(0) - lv.min(0)
            ratio = np.sort(ext) / np.maximum(np.sort(le), 1e-9); r['sorted_extent_ratio_vs_library_v3'] = ratio.round(4).tolist()
            if ratio.min() < 0.5 or ratio.max() > 2.0:
                fails.append(f'{rel}: sorted extents {ratio.round(3).tolist()} x library_v3 (scale or units)')
        else:
            fails.append(f'{rel}: no library_v3 mesh {lib} to compare (the fallback template is missing too)')
        if r['faces'] > MAX_FACES:
            flags.append(f'{rel}: {r["faces"]} faces > {MAX_FACES} (FoundationPose time)')
        e = find_entry(man, rel) if man is not None else None
        if man is not None and e is None:
            fails.append(f'{rel}: no MANIFEST.json entry')
        if e is not None:
            for k in ('md5', 'sha256'):
                if isinstance(e.get(k), str) and e[k] != r[k]:
                    fails.append(f'{rel}: MANIFEST {k} {e[k][:12]}... != file {r[k][:12]}...')
            r['manifest_hashes_checked'] = [k for k in ('md5', 'sha256') if isinstance(e.get(k), str)]
        tier = (e or {}).get('provenance_tier') or top_tier
        r['provenance_tier'] = tier
        if man is not None and not tier:
            fails.append(f'{rel}: no provenance tier (entry or manifest provenance_tier)')
        elif tier and TIER_WORDS.search(str(tier)):
            flags.append(f'{rel}: provenance tier mentions {TIER_WORDS.search(str(tier)).group(0)!r}: "{str(tier)[:160]}"')
        if os.path.isfile(lib):                                          # frame report vs library_v3 (flags only)
            args = types.SimpleNamespace(dense=a.dense, query=a.query, max_centre_mm=5.0, max_icp_mm=5.0, max_icp_deg=5.0,
                                         max_median_mm=5.0, extent_tol=0.15)
            sym = PS.SYMMETRY.get(obj, 'none')
            fr = PS.frame_report(lib, p, 7, 1_000_003 * ep + 101 * r['slot'], sym, args)
            fr.update(file=rel, symmetry=sym, library_v3_md5=digest(lib)); frames.append(fr)
            r['frame_flags'] = fr['flags']
            flags += [f'{rel}: frame: {x}' for x in fr['flags']]
    g = subprocess.run([sys.executable, '-I', os.path.join(REPO, 'tools', 'no_oracle.py'), d], capture_output=True, text=True)
    guard = (g.stdout.strip() or g.stderr.strip())[-400:]
    if g.returncode:
        fails.append(f'tools/no_oracle.py refuses the delivery: {guard}')
    cov = {}
    for ep in sorted(R):
        dl = [o for o in R[ep] if f'ep{ep}/{o}.glb' in files]
        cov[str(ep)] = dict(objects=R[ep], delivered=dl, library_v3=[o for o in R[ep] if o not in dl])
    status = 'fail' if fails else 'flagged' if flags else 'pass'
    try:
        commit = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = None
    out = dict(tool='tools/rtk_mesh_check.py check', time=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), commit=commit,
               dir=d, tsv=os.path.relpath(a.tsv, REPO) if a.tsv.startswith(REPO) else a.tsv, library=a.lib, status=status,
               hard_failures=fails, flags=flags, manifest=dict(md5=man_md5, provenance_tier=top_tier),
               guard=dict(rc=g.returncode, out=guard), files=files,
               coverage=dict(episodes_with_a_mesh=sum(bool(v['delivered']) for v in cov.values()),
                             meshes=len(files), per_episode=cov), frame_reports=frames)
    print(f'rtk_mesh_check {d}: {status.upper()}  {len(files)} meshes in {out["coverage"]["episodes_with_a_mesh"]}/{len(R)} '
          f'episodes; {len(fails)} failures, {len(flags)} flags; guard rc {g.returncode}')
    for x in fails:
        print('  FAIL', x)
    for x in flags:
        print('  FLAG', x)
    for ep, v in cov.items():
        print(f'  ep{ep}: delivered {",".join(v["delivered"]) or "-"}; library_v3 {",".join(v["library_v3"]) or "-"}')
    if a.write:
        json.dump(out, open(f'{d}/VALIDATION.json', 'w'), indent=1); print(f'wrote {d}/VALIDATION.json')
    return 1 if fails else 2 if flags else 0


def verify(d, tsv=None):
    d = os.path.abspath(d); p = f'{d}/VALIDATION.json'
    try:
        v = json.load(open(p))
    except Exception as x:
        print(f'rtk_mesh_check verify: {p} unreadable ({x!r})'); return 1
    bad = []
    if v.get('status') not in ('pass', 'flagged'):
        bad.append(f'status {v.get("status")!r} (pass or flagged needed)')
    listed = v.get('files') or {}
    if not listed:
        bad.append('no files listed')
    for rel, f in listed.items():
        q = f'{d}/{rel}'
        if not os.path.isfile(q) or digest(q) != f.get('md5'):
            bad.append(f'{rel}: missing or md5 changed since validation')
    have = {os.path.relpath(q, d) for s in MESH_SUFFIX for q in glob.glob(f'{d}/ep*/*{s}')}
    bad += [f'{x}: not in VALIDATION.json' for x in sorted(have - set(listed))]
    mm = (v.get('manifest') or {}).get('md5')
    if not mm or not os.path.isfile(f'{d}/MANIFEST.json') or digest(f'{d}/MANIFEST.json') != mm:
        bad.append('MANIFEST.json missing or changed since validation')
    if tsv:
        R = roster(tsv)
        for rel, f in listed.items():
            m = re.fullmatch(r'ep(\d+)/(\w+)\.glb', rel)
            if not m or int(m.group(1)) not in R or m.group(2) not in R[int(m.group(1))]:
                bad.append(f'{rel}: not an object of its episode in {tsv}')
    print(f'rtk_mesh_check verify {d}: ' + ('OK' if not bad else 'FAILED') + f' ({len(listed)} meshes, status '
          f'{v.get("status")}, validated {v.get("time")} at {str(v.get("commit"))[:7]})' + ''.join(f'\n  {x}' for x in bad))
    return 1 if bad else 0


def main():
    if sys.argv[1:2] == ['verify']:
        if len(sys.argv) not in (3, 4):
            sys.exit('usage: rtk_mesh_check.py verify DIR [TSV]')
        sys.exit(verify(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None))
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('cmd', choices=['check']); p.add_argument('dir')
    p.add_argument('--kit', required=True, help='v2d_submission_kit root (v2dlb: budget_mesh, registration proxy)')
    p.add_argument('--tsv', default=TSV); p.add_argument('--lib', default=os.path.join(REPO, 'meshes', 'library_v3'))
    p.add_argument('--write', action='store_true', help='write DIR/VALIDATION.json')
    p.add_argument('--dense', type=int, default=200_000); p.add_argument('--query', type=int, default=20_000)
    a = p.parse_args(); a.tsv, a.lib = os.path.abspath(a.tsv), os.path.abspath(a.lib)
    sys.exit(check(a))


if __name__ == '__main__':
    main()
