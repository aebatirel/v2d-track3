"""Inventory every mesh our experiments produced, dedupe by sha1[:16], attach [D] CD-O scores where a score record
exists, reduce to ~2000 faces, write one JSON bundle per object and one thumbnail sprite sheet per object.
Read-only on all inputs. Scores are the stored public-scan diagnostics; nothing is re-scored."""
import os, re, sys, json, glob, base64, hashlib, math
import numpy as np, trimesh
from PIL import Image, ImageDraw

R = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
OUT = S + '/meshreview/lib'
os.makedirs(OUT + '/b', exist_ok=True); os.makedirs(OUT + '/s', exist_ok=True)
MAXF = 2000; TILE = 112; SS = 2; COLS = 16

OBJS = ['white_pot_lid', 'white_pot', 'blue_cup', 'beige_cup', 'plastic_dish_rack', 'water_pitcher', 'mini_dust_pan',
        'mini_sweeper', 'wooden_piece_1', 'wooden_piece_2', 'wooden_spoon']
UP = {'blue_cup': 'z', 'beige_cup': 'z'}

def sha16(p):
    h = hashlib.sha1()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()[:16]

def resolve(p, base):
    p = p.replace('<scratchpad>', S).replace('SCR/', S + '/')
    if os.path.isabs(p): return p if os.path.exists(p) else None
    for b in (base, R, S, R + '/docs/research/mesh-2026-10-26'):
        q = os.path.join(b, p)
        if os.path.exists(q): return q
    return None

def guess_obj(path):
    name = os.path.basename(path).lower(); parts = path.lower().split('/')
    for txt in [name] + parts[::-1][1:4]:
        t = txt.replace('-', '_')
        if 'lid' in t: return 'white_pot_lid'
        if 'white_pot' in t or re.search(r'(^|_)pot(_|\.|$)', t): return 'white_pot'
        if 'blue' in t or re.search(r'(^|_)cup(_|\.|$)', t): return 'blue_cup'
        if 'beige' in t: return 'beige_cup'
        if 'rack' in t: return 'plastic_dish_rack'
        if 'pitcher' in t: return 'water_pitcher'
        if 'dust' in t or re.search(r'(^|_)pan(_|\.|$)', t): return 'mini_dust_pan'
        if 'sweeper' in t: return 'mini_sweeper'
        if 'wooden_piece_1' in t or 'board1' in t or 'board_1' in t: return 'wooden_piece_1'
        if 'wooden_piece_2' in t or 'board2' in t or 'board_2' in t: return 'wooden_piece_2'
        if 'spoon' in t: return 'wooden_spoon'
    return None

GEN = {'sam3d': 'Generated · SAM 3D', 'pixal_mv': 'Generated · Pixal3D-MV', 'pixal_v1': 'Generated · Pixal3D-MV',
       'trellis2': 'Generated · TRELLIS.2', 'hy21': 'Generated · Hunyuan3D-2.1', 'triposg': 'Generated · TripoSG'}
def family(path, group=None):
    if group in GEN: return GEN[group]
    p = path.lower()
    for k, v in GEN.items():
        if '/gen/' in p and k in p: return v
    if '/library_v' in p: return 'Library (v1–v4, v3x)'
    if '/library_e0b' in p or '/e0b/' in p or 'cdo-sprint/e0b' in p: return 'Eval-built, scan-free (E0b)'
    if '/library_e0' in p or '/cdo_e0/' in p or 'cdo-sprint/e0/' in p: return 'Eval-built (E0)'
    if 'pubown' in p: return 'Own video, per episode'
    if 'c0b' in p: return 'Scan-free public (C0b)'
    if '/library_c0' in p or 'cdo-sprint/c0/' in p or '/cdo_c0/' in p: return 'C0 fits (pack 9a)'
    if 'c2r' in p or 'r-rack' in p: return 'C2 rack parts'
    if 'cdo_c2' in p or 'p-pitcher' in p: return 'C2 pitcher lathe'
    if '/t3' in p or 't3-gen-fit' in p: return 'Generate-then-fit (C1 T3)'
    if '/t2' in p or 't2-probe' in p: return 'Generated pick, placed (C1 T2)'
    if '/t1' in p or 't1-beige' in p: return 'Lathe from video (C1 T1)'
    if '/prim/' in p: return 'Primitive fits'
    if 'lathe' in p: return 'Lathe from video'
    if 'gmg' in p: return 'gmg shells and hulls'
    if 'diag' in p or 'bench' in p: return 'Diagnostics and benchmark'
    return 'Other'

# ---- 1. score records
scores = {}
recs = []
for f in glob.glob(R + '/docs/research/**/*.jsonl', recursive=True) + glob.glob(S + '/**/*.jsonl', recursive=True):
    if '/lib/' in f: continue
    try:
        for l in open(f):
            try: d = json.loads(l)
            except Exception: continue
            if isinstance(d, dict) and 'cdo_eval' in d and d.get('sha'):
                recs.append((f, d))
    except Exception: pass
for f, d in recs:
    sh = d['sha']
    if sh in scores: continue
    scores[sh] = dict(cdo=d.get('cdo_eval'), add=d.get('add_med'), flips=d.get('flips_eval'), label=d.get('label'),
                      obj=d.get('object'), group=d.get('group'), path=d.get('path'), src_file=f)

# ---- 2. candidate files
cands = []
def add(p, hint=None):
    if not p or not os.path.exists(p): return
    cands.append((p, hint))
for f, d in recs:
    add(resolve(d.get('path', ''), os.path.dirname(f)), d)
pats = [R + '/meshes/*/*.glb', R + '/docs/research/mesh-2026-10-26/**/meshes/**/*.glb', R + '/docs/research/mesh-2026-10-26/**/meshes/**/*.ply',
        S + '/cdo_c1/**/*.glb', S + '/cdo_c1/**/*.ply', S + '/cdo_c2/**/*.glb', S + '/cdo_c2/**/*.ply', S + '/cdo_c2r/**/*.glb',
        S + '/c0b/**/*.glb', S + '/cdo_e0/**/*.glb', S + '/e0b/**/*.glb', S + '/pubown/box/dl/**/*.glb',
        R + '/docs/research/mesh-2026-10-26/gmg/build/b1/**/*.glb']
for pat in pats:
    for p in glob.glob(pat, recursive=True): add(p)

skip = re.compile(r'(/piece_\d+|/_default/|/r0/|/sim_r0/|/_fit/|/dry/|/pixal_test/)')
seen = {}
for p, hint in cands:
    if skip.search(p): continue
    try: sh = sha16(p)
    except Exception: continue
    if sh in seen: seen[sh]['also'].add(p); continue
    sc = scores.get(sh)
    obj = (sc or {}).get('obj') or (hint or {}).get('object') or guess_obj(p)
    if obj not in OBJS: continue
    fam = family(p, (sc or {}).get('group') or (hint or {}).get('group'))
    rel = p.replace(R + '/', '').replace(S + '/', 'scratch/')
    label = (sc or {}).get('label') or rel.split('/')[-1].rsplit('.', 1)[0]
    seen[sh] = dict(sha=sh, path=p, rel=rel, obj=obj, fam=fam, label=label, also=set(),
                    cdo=(sc or {}).get('cdo'), add=(sc or {}).get('add'), flips=(sc or {}).get('flips'))
print('unique meshes', len(seen), 'scored', sum(1 for v in seen.values() if v['cdo'] is not None), file=sys.stderr)

# pack 9a+ membership
pack_files = [R + '/meshes/library_c0/white_pot.glb', R + '/meshes/library_c0/white_pot_lid.glb', R + '/meshes/library_c0/plastic_dish_rack.glb',
              R + '/docs/research/mesh-2026-10-26/cdo-sprint/C1/T1-beige-lathe/meshes/ep11_beige_cup_sep_g1.glb',
              R + '/docs/research/mesh-2026-10-26/cdo-sprint/C1/T2-probe-picks/meshes/mini_dust_pan_k297_s42_lib.glb'] + \
             [R + f'/meshes/library_v3/{o}.glb' for o in ('blue_cup', 'water_pitcher', 'mini_sweeper', 'wooden_piece_1', 'wooden_piece_2', 'wooden_spoon')]
PACK = {sha16(p) for p in pack_files if os.path.exists(p)}
CAND = {sha16(R + '/meshes/library_c0/blue_cup.glb'), sha16(R + '/meshes/library_e0b/white_pot.glb'), sha16(R + '/meshes/library_e0b/beige_cup.glb')}

# ---- 3. process per object
def to_up(V, obj):
    if UP.get(obj) == 'z': return np.c_[V[:, 0], V[:, 2], -V[:, 1]]
    return np.c_[-V[:, 1], V[:, 0], V[:, 2]]

D = np.array([0.9, 0.55, 1.1]); D /= np.linalg.norm(D)
Rt = np.cross(-D, [0, 1, 0]); Rt /= np.linalg.norm(Rt); Uv = np.cross(Rt, -D)
Lt = D + np.array([0.3, 0.8, 0.2]); Lt /= np.linalg.norm(Lt)
def thumb(V, F, obj):
    P = to_up(V, obj); P = P - (P.max(0) + P.min(0)) / 2
    x = P @ Rt; y = P @ Uv; z = P @ D
    s = (TILE * SS * 0.86) / max(x.max() - x.min(), y.max() - y.min(), 1e-9)
    cx = (x.max() + x.min()) / 2; cy = (y.max() + y.min()) / 2
    X = (x - cx) * s + TILE * SS / 2; Y = TILE * SS / 2 - (y - cy) * s
    tri = P[F]; n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); nl = np.linalg.norm(n, axis=1); nl[nl == 0] = 1
    shade = 0.28 + 0.72 * np.abs((n / nl[:, None]) @ Lt)
    order = np.argsort(z[F].mean(1))
    im = Image.new('RGBA', (TILE * SS, TILE * SS), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    for k in order:
        a, b, c = F[k]; g = int(40 + 185 * shade[k])
        dr.polygon([(X[a], Y[a]), (X[b], Y[b]), (X[c], Y[c])], fill=(g, g, min(255, g + 8), 255))
    return im.resize((TILE, TILE), Image.LANCZOS)

FAM_ORDER = ['Library (v1–v4, v3x)', 'C0 fits (pack 9a)', 'Lathe from video (C1 T1)', 'Generated pick, placed (C1 T2)', 'Generate-then-fit (C1 T3)',
             'Generated · SAM 3D', 'Generated · Pixal3D-MV', 'Generated · TRELLIS.2', 'Generated · Hunyuan3D-2.1', 'Generated · TripoSG',
             'Primitive fits', 'Lathe from video', 'Scan-free public (C0b)', 'Own video, per episode', 'C2 pitcher lathe', 'C2 rack parts',
             'Eval-built (E0)', 'Eval-built, scan-free (E0b)', 'gmg shells and hulls', 'Diagnostics and benchmark', 'Other']
index = {}
for obj in OBJS:
    items = [v for v in seen.values() if v['obj'] == obj]
    if not items: continue
    items.sort(key=lambda v: (v['cdo'] is None, v['cdo'] if v['cdo'] is not None else 0, FAM_ORDER.index(v['fam']) if v['fam'] in FAM_ORDER else 99, v['label']))
    rows = (len(items) + COLS - 1) // COLS
    sheet = Image.new('RGBA', (COLS * TILE, rows * TILE), (0, 0, 0, 0))
    bundle = []; idx = []
    for i, v in enumerate(items):
        try:
            m = trimesh.load(v['path'], force='mesh')
            if not isinstance(m, trimesh.Trimesh) or len(m.faces) == 0: raise ValueError('empty')
            f0 = len(m.faces)
            if f0 > MAXF:
                try: m = m.simplify_quadric_decimation(face_count=MAXF)
                except Exception: pass
            V = np.asarray(m.vertices, float); F = np.asarray(m.faces, np.int64)
        except Exception as e:
            print('skip', v['rel'], e, file=sys.stderr); continue
        sheet.paste(thumb(V, F, obj), ((i % COLS) * TILE, (i // COLS) * TILE))
        lo = V.min(0); span = np.maximum(V.max(0) - lo, 1e-9)
        q = np.round((V - lo) / span * 65535).astype('<u2'); ix = F.astype('<u2') if len(V) < 65536 else F.astype('<u4')
        mid = f'{obj}:{v["sha"]}'
        bundle.append(dict(id=mid, min=lo.round(6).tolist(), span=span.round(6).tolist(), v=base64.b64encode(q.tobytes()).decode(),
                           i=base64.b64encode(ix.tobytes()).decode(), it='u16' if ix.dtype == np.uint16 else 'u32'))
        idx.append(dict(id=mid, sha=v['sha'], label=v['label'], fam=v['fam'], src=v['rel'], n_src=f0,
                        ext=(np.round((V.max(0) - V.min(0)) * 1000)).astype(int).tolist(),
                        cdo=None if v['cdo'] is None else round(float(v['cdo']), 4), add=v['add'], flips=v['flips'],
                        pack=v['sha'] in PACK, cand=v['sha'] in CAND, tile=i, copies=len(v['also'])))
    sheet.save(f'{OUT}/s/{obj}.png', optimize=True)
    json.dump(dict(obj=obj, meshes=bundle), open(f'{OUT}/b/{obj}.json', 'w'), separators=(',', ':'))
    index[obj] = dict(cols=COLS, tile=TILE, rows=(len(idx) + COLS - 1) // COLS, items=idx)
    print(obj, len(idx), os.path.getsize(f'{OUT}/b/{obj}.json'), os.path.getsize(f'{OUT}/s/{obj}.png'), file=sys.stderr)
json.dump(index, open(f'{OUT}/index.json', 'w'), separators=(',', ':'))
print('done', sum(len(v['items']) for v in index.values()), file=sys.stderr)
