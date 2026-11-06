"""Stub deliveries for the re-track CPU mock (2026-10-31). usage: make_fixtures.py OUT SCANS
Writes OUT/<name>/ep<N>/<obj>.glb + MANIFEST.json in the delivery format BUILD.md asks of the mesh session:
  v3copy      every object of every public episode = a byte copy of library_v3 (tracking must reproduce P_o exactly)
  partial     E0-like scope (pot, lid, rack, blue cup) as library_v3 copies, except ep2/white_pot = library_v3 moved by
              2 deg about z and 3 mm in x (re-exported: a different template that stays under the frame flags) and
              ep13/plastic_dish_rack moved by 10 mm (frame flags expected); other objects not delivered
  bad_*       one fault each, for the validator: bad_units (white_pot in mm), bad_node (a node transform), bad_name
              (ep2/blue_cup.glb: not an ep2 object), bad_suffix (ep2/white_pot.obj), bad_md5 (MANIFEST md5 wrong),
              no_manifest, no_tier (no provenance tier), scan_copy (ep2/white_pot.glb = the public scan: the guard
              must refuse it by sha256), bad_dir (ep5/: not a public episode)
Every MANIFEST says "STUB" in its method; nothing here is a real delivery. Stdlib + numpy + trimesh."""
import hashlib, json, os, shutil, sys
import numpy as np, trimesh

OUT, SCANS = sys.argv[1], sys.argv[2]
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
LIB = f'{REPO}/meshes/library_v3'
TSV = f'{REPO}/docs/research/work/leak-decomp-20261030/phase1/inputs.tsv'
R = {int(l.split('\t')[0]): l.split('\t')[2].split(',') for l in open(TSV).read().splitlines()[1:]}
TIER = 'STUB tier (mock): byte copy of library_v3, tier P1 like library_v3'
E0 = {'white_pot', 'white_pot_lid', 'plastic_dish_rack', 'blue_cup'}


def h(p, a='md5'):
    return hashlib.new(a, open(p, 'rb').read()).hexdigest()


def moved(src, dst, deg, shift_m):
    m = trimesh.load(src, force='mesh', process=False)
    T = trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1]); T[0, 3] = shift_m
    m.apply_transform(T); m.export(dst)


def manifest(d, tier=TIER, md5=True, drop_tier=False):
    files = {}
    for ep in sorted(os.listdir(d)):
        if os.path.isdir(f'{d}/{ep}'):
            for f in sorted(os.listdir(f'{d}/{ep}')):
                p = f'{d}/{ep}/{f}'; e = dict(sha256=h(p, 'sha256'), method='STUB (mock fixture)')
                if md5:
                    e['md5'] = h(p)
                files[f'{ep}/{f}'] = e
    m = dict(method='STUB fixtures of docs/research/work/retrack-20261031/mock (not a delivery)', files=files)
    if not drop_tier:
        m['provenance_tier'] = tier
    json.dump(m, open(f'{d}/MANIFEST.json', 'w'), indent=1)
    return m


def fresh(name):
    d = f'{OUT}/{name}'; shutil.rmtree(d, ignore_errors=True); os.makedirs(d); return d


d = fresh('v3copy')
for ep, objs in R.items():
    os.makedirs(f'{d}/ep{ep}')
    for o in objs:
        shutil.copyfile(f'{LIB}/{o}.glb', f'{d}/ep{ep}/{o}.glb')
manifest(d)
d = fresh('partial')
for ep, objs in R.items():
    for o in objs:
        if o in E0:
            os.makedirs(f'{d}/ep{ep}', exist_ok=True)
            if (ep, o) == (2, 'white_pot'):
                moved(f'{LIB}/{o}.glb', f'{d}/ep{ep}/{o}.glb', 2.0, 0.003)
            elif (ep, o) == (13, 'plastic_dish_rack'):
                moved(f'{LIB}/{o}.glb', f'{d}/ep{ep}/{o}.glb', 0.0, 0.010)
            else:
                shutil.copyfile(f'{LIB}/{o}.glb', f'{d}/ep{ep}/{o}.glb')
manifest(d)


def one(name, ep=2, obj='white_pot', fname=None, how='copy'):
    d = fresh(name); os.makedirs(f'{d}/ep{ep}'); p = f'{d}/ep{ep}/{fname or obj + ".glb"}'
    if how == 'copy':
        shutil.copyfile(f'{LIB}/{obj}.glb', p)
    elif how == 'mm':
        m = trimesh.load(f'{LIB}/{obj}.glb', force='mesh', process=False); m.apply_scale(1000.0); m.export(p)
    elif how == 'node':
        m = trimesh.load(f'{LIB}/{obj}.glb', force='mesh', process=False)
        T = trimesh.transformations.translation_matrix([0.01, 0, 0])
        s = trimesh.Scene(); s.add_geometry(m, node_name='body', transform=T); s.export(p)
    elif how == 'obj':
        trimesh.load(f'{LIB}/{obj}.glb', force='mesh', process=False).export(p)
    elif how == 'scan':
        shutil.copyfile(f'{SCANS}/{obj}/{obj}.glb', p)
    return d


manifest(one('bad_units', how='mm'))
manifest(one('bad_node', how='node'))
manifest(one('bad_name', obj='blue_cup'))
manifest(one('bad_suffix', fname='white_pot.obj', how='obj'))
d = one('bad_md5'); m = manifest(d); m['files']['ep2/white_pot.glb']['md5'] = '0' * 32
json.dump(m, open(f'{d}/MANIFEST.json', 'w'), indent=1)
one('no_manifest')
manifest(one('no_tier'), drop_tier=True)
manifest(one('scan_copy', how='scan'))
manifest(one('bad_dir', ep=5))
print('fixtures:', ', '.join(sorted(os.listdir(OUT))))
