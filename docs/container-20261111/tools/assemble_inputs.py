"""Per-episode evaluator inputs for the container: eval_inputs/track3_13h/episode_XXXXXX/assets/
   refs/...            the reference parquet the checkpoint names (task.parquet, /workspace/ stripped) and its
                       reconstructed_stage/ support USDA, from the run whose box produced the packed rollout
   urdf/, mesh/        the URDF closure the reference names: /content/refs/<sf>/epN/assets/** of that run, or the
                       regenerated shared /content/assets of that box (only the episode's objects)
Writes a record with the source and md5 of every file."""
import hashlib, json, os, shutil, sys, re
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
S, B = sys.argv[1], sys.argv[2]
listing = [x['path'] for x in json.load(open(f'{S}/container/dl/runs_listing.json'))]
src = json.load(open(f'{S}/container/stage/rollout_sources.json'))
regen = {'20261030-e1conf2-d41382e': 'e1conf2', '20261025-pack3-3758189': 'pack3', '20261026-pack4-f7a49a9': 'pack4',
         '20261101-e10nj-451b82d': 'e10nj'}
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()
def dl(path):
    return hf_hub_download('aebatirel/v2d-store', path, repo_type='dataset', local_dir=f'{S}/container/dl/inputs')
record = {}
for ep in sorted(src):
    run = src[ep][ep + '.json']['source'].split('/')[1]
    rj = json.load(open(f'{S}/container/stage/rollouts/{ep}.json'))
    ref = rj['parquet']; rel = ref[len('/workspace/'):]
    E = f'{B}/eval_inputs/track3_13h/{ep}/assets'
    if os.path.exists(E): shutil.rmtree(E)
    files = []
    def put(local, dst, source):
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(local, dst)
        files.append(dict(file=os.path.relpath(dst, E), source=source, md5=md5(dst)))
    put(dl(f'runs/{run}/{rel}'), f'{E}/{rel}', f'runs/{run}/{rel}')
    epdir = rel.split('/processed/')[0]
    for p in listing:
        if p.startswith(f'runs/{run}/{epdir}/reconstructed_stage/'):
            put(dl(p), f'{E}/{p[len(f"runs/{run}/"):]}', p)
    row = pq.read_table(f'{E}/{rel}', columns=['object_urdf_paths', 'object_body_names']).to_pylist()[0]
    for u, obj in zip(row['object_urdf_paths'], row['object_body_names']):
        if u.startswith('/content/refs/'):
            root = u[len('/content/'):].split('/assets/')[0] + '/assets/'
            for p in listing:
                if p.startswith(f'runs/{run}/{root}'):
                    put(dl(p), f'{E}/{p[len(f"runs/{run}/{root}"):]}', p)
        elif u.startswith('/content/assets/'):
            R = f'{S}/container/regen/assets_{regen[run]}'
            assert u == f'/content/assets/urdf/{obj}_rigid.urdf', u
            put(f'{R}/urdf/{obj}_rigid.urdf', f'{E}/urdf/{obj}_rigid.urdf', f'regen:{regen[run]}/urdf/{obj}_rigid.urdf')
            for f in sorted(os.listdir(f'{R}/mesh/{obj}')):
                put(f'{R}/mesh/{obj}/{f}', f'{E}/mesh/{obj}/{f}', f'regen:{regen[run]}/mesh/{obj}/{f}')
        else:
            raise SystemExit(f'{ep}: unexpected URDF path {u}')
    # every mesh a URDF names must exist in the tree
    for u in row['object_urdf_paths']:
        local = f'{E}/urdf/' + os.path.basename(u)
        for m in re.findall(r'filename="([^"]+)"', open(local).read()):
            assert os.path.isfile(os.path.normpath(os.path.join(os.path.dirname(local), m))), (ep, local, m)
    record[ep] = dict(run=run, reference=ref, urdfs=row['object_urdf_paths'], files=files)
    print(ep, run, len(files), 'files', 'ref md5', md5(f'{E}/{rel}'))
json.dump(record, open(f'{S}/container/stage/eval_inputs_record.json', 'w'), indent=1)
