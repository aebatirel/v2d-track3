"""Collision-piece sets of the eval-10 cavity-safe retrain (2026-11-01; ops/jobs/ev10_cs.sh; pre-registered in
docs/research/work/eval10-cs4-20261101/PREREG.md). A piece set is a folder meshes/carve/<set>/ in make_assets.py's --pieces
layout (<obj>/piece_NN.obj, <obj>/inertia.json, <obj>/lathe_collision.json, carve.json), plus three records that
make_assets.py never reads: MD5SUMS (this tool's manifest of the input files), FROZEN.md (the mesh lane's own md5 freeze,
byte copy) and PROVENANCE.md (where it came from). GT-free: nothing here reads a scan, mocap or a dataset pose.

  import    byte copy of a frozen piece set from a commit of the mesh lane (git show <rev>:<path>, file by file), the
            MD5SUMS manifest, a PROVENANCE.md header; refuses if the source FROZEN.md does not list exactly the copied
            input files with the same md5 (no freeze, no import), or if the destination exists.
  check     the folder against its MD5SUMS (and FROZEN.md): the same file set (an extra piece_*.obj would be read by
            make_assets.py's glob) and the same md5 per file. Reports per cup the piece count, the md5 of the sorted
            per-piece md5 list, the inertia.json values and, from lathe_collision.json, the floor plate. Exit 1 on failure.
  compare   the piece-choice rule clause (a) of the PREREG (section 2.2): CAND differs from BASE only in the blue cup's
            floor plate piece (blue_cup/piece_<segments x bands>.obj per BASE's lathe_collision.json) and in the four records
            that follow it (blue_cup/inertia.json, blue_cup/lathe_collision.json, carve.json, FROZEN.md); every other file,
            every beige_cup file included, byte-identical; the same file names. Exit 1 if the clause fails.
  assets    after make_assets.py LIB OUT --pieces DIR: each cup's URDF names exactly its pieces as col_NN.obj, each col_NN.obj
            is a byte copy of piece_NN.obj, and the URDF inertial equals inertia.json scaled to the URDF mass; reports every
            URDF's md5, mass, COM and inertia (the inertials the training actually used). Exit 1 on failure.
Usage:
  e10cs_pieces.py import --rev <commit> --src <path in the repo> --dst meshes/carve/<set> [--repo R]
  e10cs_pieces.py check --dir meshes/carve/<set> [--out J]
  e10cs_pieces.py compare --base meshes/carve/ev10cs4 --cand meshes/carve/ev10cs5 [--out J]
  e10cs_pieces.py assets --assets /content/assets --pieces meshes/carve/<set> [--out J]
"""
import argparse, datetime, glob, hashlib, json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS = ('MD5SUMS', 'FROZEN.md', 'PROVENANCE.md')          # never read by make_assets.py
CUPS = ('blue_cup', 'beige_cup')
FOLLOW_PLATE = ('blue_cup/inertia.json', 'blue_cup/lathe_collision.json', 'carve.json', 'FROZEN.md')


def md5b(b):
    return hashlib.md5(b).hexdigest()


def md5f(p):
    return md5b(open(p, 'rb').read())


def inputs_of(d):
    """relative paths of the input files of folder d (everything but the three records), sorted"""
    out = []
    for root, _, fs in os.walk(d):
        for f in fs:
            r = os.path.relpath(os.path.join(root, f), d)
            if r not in RECORDS:
                out.append(r)
    return sorted(out)


def parse_md5_list(text):
    """lines '<md5>  ./<rel>' (md5sum's format, FROZEN.md's code block) -> {rel: md5}"""
    out = {}
    for line in text.splitlines():
        m = re.match(r'^([0-9a-f]{32})\s+\*?(?:\./)?(\S.*)$', line.strip())
        if m:
            out[m.group(2)] = m.group(1)
    return out


def manifest_text(d, rels):
    return ''.join(f'{md5f(os.path.join(d, r))}  ./{r}\n' for r in rels)


def cmd_import(a):
    repo = a.repo; src = a.src.rstrip('/'); dst = a.dst.rstrip('/')
    if os.path.exists(dst):
        sys.exit(f'import: {dst} exists (a piece set is never overwritten; a change is a new folder)')
    full = subprocess.run(['git', '-C', repo, 'rev-parse', a.rev], capture_output=True, text=True, check=True).stdout.strip()
    ls = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', full, src + '/'], capture_output=True, text=True,
                        check=True).stdout.split()
    rels = sorted(os.path.relpath(p, src) for p in ls)
    if 'FROZEN.md' not in rels:
        sys.exit(f'import: {src} at {full[:7]} has no FROZEN.md (only a frozen set is imported)')
    blobs = {r: subprocess.run(['git', '-C', repo, 'show', f'{full}:{src}/{r}'], capture_output=True, check=True).stdout for r in rels}
    frozen = parse_md5_list(blobs['FROZEN.md'].decode())
    ins = [r for r in rels if r not in RECORDS]
    got = {r: md5b(blobs[r]) for r in ins}
    if frozen != got:
        miss = sorted(set(got) ^ set(frozen)); diff = sorted(r for r in set(got) & set(frozen) if got[r] != frozen[r])
        sys.exit(f'import: FROZEN.md does not match the copied files (only in one: {miss[:6]}; md5 differs: {diff[:6]})')
    for r in rels:
        if r in ('MD5SUMS', 'PROVENANCE.md'):
            continue
        p = os.path.join(dst, r); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'wb').write(blobs[r])
    open(f'{dst}/MD5SUMS', 'w').write(manifest_text(dst, ins))
    tree = subprocess.run(['git', '-C', repo, 'rev-parse', f'{full}:{src}'], capture_output=True, text=True, check=True).stdout.strip()
    open(f'{dst}/PROVENANCE.md', 'w').write(
        f'# {os.path.basename(dst)}: provenance\n\n'
        f'- Byte copy of `{src}/` at commit `{full}` (git tree `{tree}`), imported '
        f'{datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} by `tools/e10cs_pieces.py import`.\n'
        f'- {len(ins)} input files; `MD5SUMS` lists them (md5 of MD5SUMS `{md5b(manifest_text(dst, ins).encode())}`); '
        f'`FROZEN.md` is the source\'s own freeze, byte copy, and lists the same md5s (checked at import).\n'
        f'- Check: `python3 tools/e10cs_pieces.py check --dir {dst}`.\n')
    r = check(dst)
    print(f'IMPORTED {len(ins)} files from {full[:7]}:{src} -> {dst}; ' + summary_line(r))
    sys.exit(0 if r['ok'] else 1)


def mesh_volume_cm3(p):
    """volume of a closed triangle (or polygon fan) OBJ by the divergence theorem, cm3"""
    V, vol = [], 0.0
    for line in open(p):
        s = line.split()
        if not s:
            continue
        if s[0] == 'v':
            V.append(tuple(float(x) for x in s[1:4]))
        elif s[0] == 'f':
            ix = [int(x.split('/')[0]) for x in s[1:]]
            ix = [i - 1 if i > 0 else len(V) + i for i in ix]
            a = V[ix[0]]
            for j in range(1, len(ix) - 1):
                b, c = V[ix[j]], V[ix[j + 1]]
                vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return abs(vol) * 1e6


def plate_of(d):
    """the blue cup's floor plate piece per its lathe_collision.json: index segments x bands (walls come first)"""
    try:
        lc = json.load(open(f'{d}/blue_cup/lathe_collision.json'))
        if not lc.get('floor_plate'):
            return None
        k = int(lc['segments']) * len(lc['bands']); p = f'blue_cup/piece_{k:02d}.obj'
        return dict(piece=p, plate_t_mm=lc.get('plate_t_mm'), plate_h_mm=lc['floor_plate'].get('plate_h_mm'),
                    plate_cm3_record=lc['floor_plate'].get('plate_cm3'),
                    piece_cm3=round(mesh_volume_cm3(f'{d}/{p}'), 3) if os.path.isfile(f'{d}/{p}') else None)
    except Exception as e:
        return dict(error=f'{type(e).__name__}: {str(e)[:160]}')


def check(d):
    d = d.rstrip('/'); fails = []; r = dict(dir=os.path.abspath(d), name=os.path.basename(d))
    if not os.path.isfile(f'{d}/MD5SUMS'):
        return dict(r, ok=False, failures=['MD5SUMS missing'])
    man = parse_md5_list(open(f'{d}/MD5SUMS').read()); ins = inputs_of(d); got = {x: md5f(f'{d}/{x}') for x in ins}
    r['md5sums_md5'] = md5f(f'{d}/MD5SUMS')
    if set(man) != set(got):
        fails.append(f'file set differs from MD5SUMS: extra {sorted(set(got) - set(man))[:5]}, missing {sorted(set(man) - set(got))[:5]}')
    bad = sorted(x for x in set(man) & set(got) if man[x] != got[x])
    if bad:
        fails.append(f'md5 differs from MD5SUMS: {bad[:6]}')
    if os.path.isfile(f'{d}/FROZEN.md'):
        fr = parse_md5_list(open(f'{d}/FROZEN.md').read()); r['frozen_md5'] = md5f(f'{d}/FROZEN.md')
        if fr != man:
            fails.append('FROZEN.md lists other files or md5s than MD5SUMS')
    else:
        fails.append('FROZEN.md missing')
    cups = {}
    for c in CUPS:
        ps = sorted(x for x in got if re.fullmatch(rf'{c}/piece_\d+\.obj', x))
        if not ps:
            fails.append(f'{c}: no pieces')
        ij = {}
        try:
            ij = json.load(open(f'{d}/{c}/inertia.json'))
        except Exception as e:
            fails.append(f'{c}/inertia.json unreadable: {type(e).__name__}')
        cups[c] = dict(pieces=len(ps), pieces_md5_of_md5_list=md5b(''.join(f'{got[x]}  {os.path.basename(x)}\n' for x in ps).encode()),
                       inertia=dict(mass=ij.get('mass'), com_mm=[round(v * 1000, 3) for v in ij.get('com', [])],
                                    diag=[ij['inertia'][i][i] for i in range(3)] if ij.get('inertia') else None))
    r.update(files=len(ins), cups=cups, floor_plate=plate_of(d), ok=not fails, failures=fails)
    return r


def summary_line(r):
    pl = r.get('floor_plate') or {}
    return ((('CHECK OK' if r['ok'] else 'CHECK FAILED: ' + ' | '.join(r['failures'][:4])) + f" :: {r.get('name')} {r.get('files')} input files, "
             f"MD5SUMS {str(r.get('md5sums_md5'))[:12]}; ") + ', '.join(
        f"{c} {v['pieces']} pieces (md5 list {v['pieces_md5_of_md5_list'][:8]}, COM mm {v['inertia']['com_mm']})" for c, v in (r.get('cups') or {}).items())
        + (f"; floor plate {pl.get('piece')} {pl.get('plate_t_mm')} mm, {pl.get('piece_cm3')} cm3" if pl.get('piece') else ''))


def cmd_check(a):
    r = check(a.dir)
    if a.out:
        json.dump(r, open(a.out, 'w'), indent=1)
    print(summary_line(r)); sys.exit(0 if r['ok'] else 1)


def cmd_compare(a):
    b, c = a.base.rstrip('/'), a.cand.rstrip('/'); fails = []
    rb, rc = check(b), check(c)
    if not rb['ok'] or not rc['ok']:
        fails.append(f'check failed: base {rb["failures"][:2]}, cand {rc["failures"][:2]}')
    pb = plate_of(b) or {}; pc = plate_of(c) or {}; plate = pb.get('piece')
    if not plate:
        fails.append('base has no floor plate in blue_cup/lathe_collision.json')
    elif pc.get('piece') != plate:
        fails.append(f'candidate floor plate {pc.get("piece")} != base {plate}')
    fb, fc = sorted(inputs_of(b) + ['FROZEN.md']), sorted(inputs_of(c) + ['FROZEN.md'])
    if fb != fc:
        fails.append(f'file names differ: only in base {sorted(set(fb) - set(fc))[:5]}, only in cand {sorted(set(fc) - set(fb))[:5]}')
    same = [x for x in fb if x in fc and md5f(f'{b}/{x}') == md5f(f'{c}/{x}')]
    differ = sorted(x for x in fb if x in fc and x not in same)
    pieces_differ = [x for x in differ if re.search(r'/piece_\d+\.obj$', x)]
    other = [x for x in differ if x not in pieces_differ]
    if [x for x in pieces_differ if x != plate]:
        fails.append(f'pieces other than the floor plate differ: {[x for x in pieces_differ if x != plate][:6]}')
    if [x for x in other if x not in FOLLOW_PLATE]:
        fails.append(f'records other than those following the plate differ: {[x for x in other if x not in FOLLOW_PLATE]}')
    r = dict(rule='PREREG section 2.2 clause (a): every piece other than the blue floor plate byte-identical; the records that '
                  'follow the plate (blue inertia.json, blue lathe_collision.json, carve.json, FROZEN.md) may differ',
             base=rb, cand=rc, plate=plate, plate_base=pb, plate_cand=pc, files_compared=len(fb), identical=len(same),
             differ=differ, pieces_differ=pieces_differ, records_differ=other, clause_a=not fails, failures=fails)
    if a.out:
        json.dump(r, open(a.out, 'w'), indent=1)
    print(('CLAUSE (a) HOLDS' if not fails else 'CLAUSE (a) FAILS: ' + ' | '.join(fails)) + f" :: {os.path.basename(c)} vs {os.path.basename(b)}: "
          f"{len(same)}/{len(fb)} files identical; differ {differ}; plate {plate} {pb.get('plate_t_mm')} -> {pc.get('plate_t_mm')} mm, "
          f"{pb.get('piece_cm3')} -> {pc.get('piece_cm3')} cm3")
    sys.exit(0 if not fails else 1)


def inertial(urdf_text):
    m = float(re.search(r'<mass value="([^"]+)"', urdf_text).group(1))
    com = [float(x) for x in re.search(r'<origin xyz="([^"]+)"', urdf_text.split('<inertial>')[1]).group(1).split()]
    I = {k: float(v) for k, v in re.findall(r'(i[xyz]{2})="([^"]+)"', urdf_text)}
    return m, com, I


def cmd_assets(a):
    A, d = a.assets.rstrip('/'), a.pieces.rstrip('/'); fails, out = [], {}
    for c in CUPS:
        u = f'{A}/urdf/{c}_rigid.urdf'; ps = sorted(glob.glob(f'{d}/{c}/piece_*.obj'))
        try:
            t = open(u).read()
        except Exception as e:
            fails.append(f'{c}: URDF unreadable ({type(e).__name__})'); continue
        cols = re.findall(r'<collision>.*?filename="([^"]+)".*?</collision>', t, re.S)
        want = [f'{c}/col_{k:02d}.obj' for k in range(len(ps))]
        rel = [x.split('mesh/', 1)[-1] for x in cols]                       # '../mesh/<obj>/col_NN.obj'
        row = dict(urdf=u, urdf_md5=md5f(u), collisions=len(cols), pieces=len(ps))
        if rel != want:
            fails.append(f'{c}: URDF collisions {rel[:3]}... != {len(ps)} col_NN.obj')
        cm = []
        for k, p in enumerate(ps):
            q = f'{A}/mesh/{c}/col_{k:02d}.obj'
            ok = os.path.isfile(q) and md5f(q) == md5f(p); cm.append(ok)
            if not ok:
                fails.append(f'{c}: {q} is not a byte copy of {os.path.basename(p)}')
        m, com, I = inertial(t); ij = json.load(open(f'{d}/{c}/inertia.json'))
        s = m / ij['mass']; Ij = ij['inertia']
        want_I = dict(ixx=Ij[0][0] * s, ixy=Ij[0][1] * s, ixz=Ij[0][2] * s, iyy=Ij[1][1] * s, iyz=Ij[1][2] * s, izz=Ij[2][2] * s)
        # make_assets.py writes the COM with 6 decimals (m) and the inertia with 9 significant digits
        if any(abs(com[i] - ij['com'][i]) > 6e-7 for i in range(3)) or any(abs(I[k] - want_I[k]) > 1e-8 * abs(want_I[k]) + 1e-15 for k in want_I):
            fails.append(f'{c}: URDF inertial differs from inertia.json (COM {com} vs {ij["com"]})')
        row.update(mass=m, com_m=com, com_mm=[round(x * 1000, 3) for x in com], inertia=I, col_byte_copies=all(cm))
        out[c] = row
    r = dict(assets=A, pieces=os.path.abspath(d), urdfs=out, ok=not fails, failures=fails)
    if a.out:
        json.dump(r, open(a.out, 'w'), indent=1)
    print(('ASSETS OK' if not fails else 'ASSETS FAILED: ' + ' | '.join(fails[:4])) + ' :: ' + '; '.join(
        f"{c} URDF {v['urdf_md5'][:8]} {v['collisions']} collisions, {v['mass']} kg, COM mm {v['com_mm']}, ixx/iyy/izz "
        f"{v['inertia']['ixx']:.4e}/{v['inertia']['iyy']:.4e}/{v['inertia']['izz']:.4e}" for c, v in out.items()))
    sys.exit(0 if not fails else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    i = sp.add_parser('import'); i.add_argument('--rev', required=True); i.add_argument('--src', required=True)
    i.add_argument('--dst', required=True); i.add_argument('--repo', default=REPO)
    c = sp.add_parser('check'); c.add_argument('--dir', required=True); c.add_argument('--out', default=None)
    k = sp.add_parser('compare'); k.add_argument('--base', required=True); k.add_argument('--cand', required=True); k.add_argument('--out', default=None)
    s = sp.add_parser('assets'); s.add_argument('--assets', required=True); s.add_argument('--pieces', required=True); s.add_argument('--out', default=None)
    a = ap.parse_args()
    dict(check=cmd_check, compare=cmd_compare, assets=cmd_assets)[a.cmd](a) if a.cmd != 'import' else cmd_import(a)


if __name__ == '__main__':
    main()
