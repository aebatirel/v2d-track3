"""Package a built candidate in the pack's layout for pipeline/make_assets.py --pieces DIR:
DIR/plastic_dish_rack/piece_XX.obj (one <collision> per convex piece; the visual stays the mesh) plus DIR/carve.json
(provenance, inputs with md5, piece md5s). No inertia.json is written, so make_assets.py keeps the rack's mass, COM
and inertia exactly as now (uniform triangle-surface estimate over the mesh).

Usage: package.py BUILD_DIR OUT_DIR CANDIDATE_NAME
"""
import glob, hashlib, json, os, shutil, sys
import rs_lib as L


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def main():
    bd, out, name = sys.argv[1], sys.argv[2], sys.argv[3]
    b = json.load(open(f'{bd}/build.json'))
    os.makedirs(f'{out}/plastic_dish_rack', exist_ok=True)
    for f in glob.glob(f'{out}/plastic_dish_rack/piece_*.obj'):
        os.remove(f)
    pieces = []
    for f in sorted(glob.glob(f'{bd}/plastic_dish_rack/piece_*.obj')):
        shutil.copy(f, f'{out}/plastic_dish_rack/')
        pieces.append(dict(file=os.path.basename(f), md5=md5(f)))
    eps = list(b['episodes'])
    refs = {'30': dict(reference='runs/20261025-std30-ee7ba8e/refs/perc2mcks/ep30/processed/sequence_id=t3_ep030/'
                                 'robot_name=sharpa_wave/a2eb7d276dd84fe6bed9251b46e93770-0.parquet',
                       md5='dd464c96184e84400e62ffcfa17a6ac4', packed_run='20261025-std30-ee7ba8e',
                       asset_root='/content/assets (shared, library_v3)'),
            '14': dict(reference='runs/20261025-evb1420-ee7ba8e/refs/glockt/ep14/processed/sequence_id=t3_ep014/'
                                 'robot_name=sharpa_wave/ref_gl_ilc.parquet',
                       md5='10d5f3ba6b7368ed30dad9d0c9c30df1', packed_run='20261025-evb1420-ee7ba8e',
                       asset_root='/content/refs/sf/ep14/assets (sf rack = library_v3 rack vertex for vertex)')}
    inputs = {
        'rack_mesh_library_v3': dict(path='meshes/library_v3/plastic_dish_rack.glb', md5=md5(L.RACK_MESH),
                                     geom_sha1_12='c9ee8c559c02'),
        'rack_packed_hulls': dict(path='<scratch>/evck/out/packed/rack_lib.npz', md5=md5(L.RACK_PACKED),
                                  what='FlashCHORD CoACD of the rack at load: coacd 1.0.11, threshold 0.05, 43 hulls'),
        'packed_refs_json': dict(path='docs/research/work/masses-eval-20261031/packed_refs.json (focused-pascal)',
                                 md5='a7ed39d65e522c22aa9d04bb22d15a6e'),
    }
    for ep in eps:
        g = L.GUEST[ep]
        inputs[f'ep{ep}_guest_mesh'] = dict(path=g['mesh'].replace(L.SCR, '<scratch>').replace(L.REPO + '/', ''),
                                            md5=md5(g['mesh']))
        inputs[f'ep{ep}_guest_packed_hulls'] = dict(path=g['packed'].replace(L.SCR, '<scratch>'), md5=md5(g['packed']))
        pf = f'{L.PRECHECK}/per_frame/ep{ep}_frames.json'
        inputs[f'ep{ep}_precheck_frames'] = dict(path=pf.replace(L.REPO + '/', ''), md5=md5(pf))
        pn = f'{L.EVCK}/out/geo2/ep{ep}_poses.npz'
        inputs[f'ep{ep}_poses'] = dict(path=pn.replace(L.SCR, '<scratch>'), md5=md5(pn),
                                       what='object poses read from the packed reference by the precheck')
    meta = dict(
        tool='rackslot build.py (docs/research/mesh-2026-10-26/gmg/build/I/results/rackslot/scripts)',
        candidate=name, status='CANDIDATE: simulator collision copy of the rack only; the submitted mesh is unchanged',
        note=('Packed rack hulls (FlashCHORD CoACD 1.0.11 of library_v3, 43) with the hulls that reach into the '
              "guest's swept rest volume beyond the rack mesh split / clipped into convex cells that keep every "
              'rack-mesh point, then merged back where a merge adds no rest-volume cell. Use: make_assets.py LIBRARY '
              'OUT --pieces <this folder>; only plastic_dish_rack gets pieces, the guest keeps its default collision. '
              'No inertia.json: the rack mass, COM and inertia stay as make_assets.py computes them today.'),
        episodes={ep: dict(refs[ep], rest_frames_R=b['episodes'][ep]['runs'], gate_frames=L.gate_frames(ep))
                  for ep in eps},
        scope=b['scope'], n_pieces=len(pieces), packed_pieces=43, build=dict(constants=b['constants'],
                                                                            merges=len(b['merges']), secs=b['secs']),
        inputs=inputs, pieces=pieces)
    json.dump(meta, open(f'{out}/carve.json', 'w'), indent=1)
    print(name, len(pieces), 'pieces ->', out)


if __name__ == '__main__':
    main()
