"""Config of the eval precheck: per eval episode the packed reference, its support, and per object the packed visual
mesh and packed collision source (carve pieces or the coacd 1.0.11 hulls, matched by geometry sha1).
Usage: python -I make_config.py PACKED_REFS.json DL_DIR PACKED_DIR EV01_DIR OUT.json eps"""
import sys, os, json, glob, hashlib
import numpy as np, trimesh
refs, dl, packed, ev01, out, eps = sys.argv[1:7]
R = json.load(open(refs))['episodes']
REPO = '/home/user/v2d-track3'
rep = json.load(open(os.path.join(packed, 'report.json')))
by_sha = {v['geom_sha1_12']: (k, v) for k, v in rep.items()}
dlr = json.load(open(os.path.join(dl, 'dl_report.json')))
cfg = dict(_note='built by make_config.py', episodes={})
for ep in eps.split(','):
    e = R[ep]
    ref = f"runs/{e['source_run']}/{e['reference']}"
    if not os.path.exists(os.path.join(dl, ref)):          # eval 1: the perc2mcks byte copy is not in the store
        ref = ref.replace('/refs/perc2mcks/', '/refs/perc2mck/')
    refp = os.path.join(dl, ref)
    import hashlib as H
    md5 = H.md5(open(refp, 'rb').read()).hexdigest()
    sup = glob.glob(os.path.join(os.path.dirname(refp.split('/processed/')[0] + '/x'), 'reconstructed_stage', '*.usda'))
    if not sup:                                             # std refs/perc2mcks copy: the stage stays in perc2mck
        sup = glob.glob(os.path.join(os.path.dirname(refp.split('/processed/')[0].replace('/refs/perc2mcks/', '/refs/perc2mck/') + '/x'), 'reconstructed_stage', '*.usda'))
    assert len(sup) == 1, (ep, sup)
    import pyarrow.parquet as pq
    row = pq.read_table(refp, columns=['object_body_names', 'object_mesh_paths', 'object_urdf_paths']).to_pylist()[0]
    objs = {}
    for n, mp, up in zip(row['object_body_names'], row['object_mesh_paths'], row['object_urdf_paths']):
        # the simulator loads object_urdf_paths; its <collision> mesh is the packed collision source
        if up.startswith('/content/assets/'):
            mesh = f'{REPO}/meshes/library_v3/{n}.glb'       # make_assets: visual = collision = the library glb
            assert up == f'/content/assets/urdf/{n}_rigid.urdf', up
            col = f'/content/assets/mesh/{n}/{n}.glb'
        else:
            ul = os.path.join(dl, f"runs/{e['source_run']}/" + up.replace('/content/', ''))
            import re as _re
            cols = _re.findall(r'<collision>.*?filename="([^"]+)"', open(ul).read(), _re.S)
            assert len(cols) == 1, (ul, cols)
            mesh = os.path.normpath(os.path.join(os.path.dirname(ul), cols[0]))
            col = os.path.normpath(os.path.join(os.path.dirname(up), cols[0]))
        m = trimesh.load(mesh, force='mesh')
        sha = hashlib.sha1(np.ascontiguousarray(m.vertices, np.float64).tobytes()
                           + np.ascontiguousarray(m.faces, np.int64).tobytes()).hexdigest()[:12]
        o = dict(mesh=mesh, mesh_ref_path=mp, urdf_ref_path=up, collision_ref_path=col, geom_sha1_12=sha)
        pdir = None
        if e.get('pieces'):
            base = ev01 if e['pieces'].endswith('ev01') else f"{REPO}/{e['pieces']}"
            pdir = os.path.join(base, n)
        pcs = sorted(glob.glob(os.path.join(pdir, 'piece_*.obj'))) if pdir else []
        if pcs:
            o.update(pieces=pcs, pieces_src=f"{e['pieces']}/{n} ({len(pcs)} pieces, one hull each)")
        else:
            k, v = by_sha[sha]
            o.update(packed_npz=os.path.join(packed, f'{k}.npz'),
                     pieces_src=f"coacd {v['coacd']} threshold 0.05 on the visual mesh ({k}, {v['n']} hulls)")
        objs[n] = o
    cfg['episodes'][ep] = dict(ref=refp, ref_store_path=ref, ref_md5=md5, ref_md5_listed=e['md5'],
                               ref_md5_match=md5 == e['md5'], support=sup[0], mode=e['mode'],
                               packed_run=e['packed_run'], pieces=e.get('pieces'), lib=e.get('lib'),
                               objects=objs)
json.dump(cfg, open(out, 'w'), indent=1)
print(json.dumps({ep: {n: o['pieces_src'] for n, o in v['objects'].items()} for ep, v in cfg['episodes'].items()}, indent=1))
