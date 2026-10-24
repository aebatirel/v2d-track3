"""Build ops/provenance/denylist.json for pipeline/provenance.py (mesh pipeline v5 spec section 3.2).

Globs (spec 3.2) plus the sha256 of: every file under track_3/public/mesh and track_3/public/urdf of the challenge
dataset (from the Hugging Face LFS metadata, nothing downloaded), every meshes/library_v1-v4 file in this repo, and any
extra files given (e.g. the scan-templated loc/perc/ep*/poses.npz), so renamed copies are caught.
Usage: python tools/build_denylist.py [EXTRA_FILE ...]
"""
import glob, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from provenance import sha256  # noqa: E402

GLOBS = [
    '*/t3/mesh/*', '*/loc/t3/mesh/*', '*/t3/urdf/*',              # public scans, organisers' meshes and URDFs
    'meshes/library_v1/*', 'meshes/library_v2/*', 'meshes/library_v3/*', 'meshes/library_v4/*',
    '*/meshes/library_v1/*', '*/meshes/library_v2/*', '*/meshes/library_v3/*', '*/meshes/library_v4/*',
    '*/loc/perc/*', '*/loc/refs/*',                               # scan-templated tracks and what was built on them
    '*/oracle/*',                                                 # the mocap oracle
    '*/scratchpad/interact/*',                                    # prototype grids, meshes, pieces (library_v2 ROI)
    '*/runs/20261022-r5ks*',                                      # ASSET_SRC=public runs
]


def main():
    sha = {}
    from huggingface_hub import HfApi
    for x in HfApi().list_repo_tree('nvidia/video_to_data_challenge', path_in_repo='track_3/public', repo_type='dataset',
                                    recursive=True):
        p = getattr(x, 'path', '')
        if ('/mesh/' in p or '/urdf/' in p) and getattr(x, 'lfs', None) is not None:
            sha[x.lfs.sha256] = f'dataset {p}'
        elif ('/mesh/' in p or '/urdf/' in p) and getattr(x, 'size', None) is not None and not getattr(x, 'lfs', None):
            sha.setdefault(f'git-blob:{x.blob_id}', f'dataset {p} (non-LFS; matched by glob only)')
    for f in sorted(glob.glob(os.path.join(REPO, 'meshes', 'library_v[1-4]', '*'))):
        if os.path.isfile(f):
            sha[sha256(f)] = os.path.relpath(f, REPO)
    for f in sys.argv[1:]:
        sha[sha256(f)] = f'extra {f}'
    out = os.path.join(REPO, 'ops', 'provenance', 'denylist.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(dict(note='mesh pipeline v5 spec 3.2; built by tools/build_denylist.py', globs=GLOBS,
                   sha256={k: v for k, v in sorted(sha.items()) if not k.startswith('git-blob:')}), open(out, 'w'), indent=1)
    n_ds = sum(1 for v in sha.values() if v.startswith('dataset') and 'non-LFS' not in v)
    print(f'wrote {out}: {len(GLOBS)} globs, {n_ds} dataset scan/URDF hashes, '
          f'{sum(1 for v in sha.values() if v.startswith("meshes/"))} library_v1-v4 hashes, {len(sys.argv) - 1} extra')


if __name__ == '__main__':
    main()
