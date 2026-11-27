"""Rebuild, on this machine, the evaluation setup of every policy in the final Track 3 pack (14p), so the submitted
policies can be replayed on CPU and rendered (owner 2026-11-27: "render the v2d challenge final videos like this").

For each eval episode in pack14p_policies.json:
  OUT/ep<N>/policy.safetensors   the submitted checkpoint (sha256 checked against the packed rows)
  OUT/ep<N>/ref/...              the reference stored in the checkpoint's config, with object paths pointed at
  OUT/ep<N>/assets/              the object assets the evaluation used: the stored reference asset copy, or
                                 make_assets.py at the training commit (library_v3 + carve pieces, 0.3 kg)
  OUT/ep<N>/setup.json           paths for the replay (task parquet, checkpoint)
No ground truth is read: references, assets and checkpoints are our own inference-side files.
  setup_replays.py [--out /content/ev] [--eps 1,3,...] [--store aebatirel/v2d-store]
"""
import argparse, glob, hashlib, json, os, shutil, subprocess, sys, tempfile

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfApi, hf_hub_download

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
p = argparse.ArgumentParser(); p.add_argument('--out', default='/content/ev'); p.add_argument('--eps', default='')
p.add_argument('--store', default='aebatirel/v2d-store'); p.add_argument('--python', default=sys.executable)
a = p.parse_args()
TOK = os.environ.get('HF_TOKEN', 'hf_dummy0000000000000000000000000000')   # the network proxy injects the real token
M = json.load(open(f'{HERE}/pack14p_policies.json'))['episodes']
eps = [e for e in M if not a.eps or e in a.eps.split(',')]
api = HfApi(token=TOK)


def get(path, dst):
    if os.path.exists(dst):
        return dst
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = tempfile.mkdtemp(dir=a.out)
    f = hf_hub_download(a.store, path, repo_type='dataset', token=TOK, local_dir=tmp)
    shutil.move(f, dst); shutil.rmtree(tmp, ignore_errors=True)
    return dst


def tree(prefix, dst):
    for f in api.list_repo_tree(a.store, path_in_repo=prefix, repo_type='dataset', recursive=True):
        if hasattr(f, 'size') and f.size is not None and '.' in f.path.split('/')[-1]:
            get(f.path, os.path.join(dst, os.path.relpath(f.path, prefix)))


os.makedirs(a.out, exist_ok=True)
for ep in sorted(eps, key=int):
    e = M[ep]; D = os.path.join(a.out, f'ep{ep}'); os.makedirs(D, exist_ok=True)
    ck = get(e['checkpoint'], f'{D}/policy.safetensors')
    sha = hashlib.sha256(open(ck, 'rb').read()).hexdigest()
    assert sha == e['checkpoint_sha256'], f'ep{ep}: checkpoint sha256 {sha} != packed {e["checkpoint_sha256"]}'
    A = f'{D}/assets'
    if e['assets']['kind'] == 'stored':
        tree(e['assets']['path'], A)
    elif not os.path.exists(f'{A}/urdf'):
        src = subprocess.run(['git', '-C', REPO, 'show', f"{e['assets']['commit']}:pipeline/make_assets.py"], capture_output=True, text=True, check=True).stdout
        tool = f'{D}/make_assets_{e["assets"]["commit"]}.py'; open(tool, 'w').write(src)
        cmd = [a.python, tool, f"{REPO}/{e['assets']['library']}", A, '--mass', str(e['assets']['mass'])]
        if e['assets']['pieces']:
            cmd += ['--pieces', f"{REPO}/{e['assets']['pieces']}"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        open(f'{D}/make_assets.log', 'w').write(' '.join(cmd) + '\n' + r.stdout + r.stderr)
        assert r.returncode == 0, f'ep{ep}: make_assets failed, see {D}/make_assets.log'
    root = e['reference_root']; R = f'{D}/ref'
    tree(root, R)
    src_pq = os.path.join(R, os.path.relpath(e['reference'], root))
    t = pq.ParquetFile(src_pq).read(); row = t.to_pylist()[0]
    for k, sub in (('object_urdf_paths', 'urdf'), ('object_mesh_paths', 'mesh')):
        new = []
        for pth in row[k]:
            b = os.path.basename(pth)
            cand = f'{A}/urdf/{b}' if sub == 'urdf' else f'{A}/mesh/{os.path.basename(os.path.dirname(pth))}/{b}'
            assert os.path.exists(cand), f'ep{ep}: {k} {pth} -> {cand} missing'
            new.append(cand)
        row[k] = new
    task = os.path.join(os.path.dirname(src_pq), 'ref_local.parquet')
    pq.write_table(pa.Table.from_pylist([row], schema=t.schema), task)
    json.dump(dict(ep=int(ep), task=task, checkpoint=ck, checkpoint_sha256=sha, refdir=R, assets=A,
                   objects=[os.path.basename(x).replace('_rigid.urdf', '') for x in row['object_urdf_paths']]),
              open(f'{D}/setup.json', 'w'), indent=1)
    print(f'ep{ep}: ok, objects {row["object_urdf_paths"]}', flush=True)
