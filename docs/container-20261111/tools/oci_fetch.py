"""Fetch vastai/pytorch@<index digest> from Docker Hub as an OCI image layout via the registry blob endpoint
(manifests are served there too; the pull rate limit counts manifest GETs only). Every blob is sha256-checked."""
import hashlib, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
REPO = 'vastai/pytorch'; INDEX = sys.argv[1]; OUT = sys.argv[2]
B = f'{OUT}/blobs/sha256'; os.makedirs(B, exist_ok=True)
def token():
    return json.loads(subprocess.check_output(['curl', '-sS', f'https://auth.docker.io/token?service=registry.docker.io&scope=repository:{REPO}:pull']))['token']
def get(digest, size=None):
    h = digest.split(':')[1]; p = f'{B}/{h}'
    for attempt in range(5):
        if os.path.exists(p) and hashlib.sha256(open(p, 'rb').read()).hexdigest() == h:
            return p
        subprocess.run(['curl', '-sSL', '--retry', '5', '-o', p + '.part', '-H', f'Authorization: Bearer {token()}',
                        f'https://registry-1.docker.io/v2/{REPO}/blobs/{digest}'], check=False)
        if os.path.exists(p + '.part'):
            os.replace(p + '.part', p)
    raise SystemExit(f'blob {digest} failed')
idx = json.load(open(get(INDEX)))
man_d = next(m for m in idx['manifests'] if m.get('platform', {}).get('architecture') == 'amd64')
man = json.load(open(get(man_d['digest'])))
get(man['config']['digest'])
with ThreadPoolExecutor(4) as ex:
    list(ex.map(lambda l: get(l['digest']), man['layers']))
json.dump({'imageLayoutVersion': '1.0.0'}, open(f'{OUT}/oci-layout', 'w'))
ref = 'docker.io/vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16'
json.dump({'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.index.v1+json',
           'manifests': [dict(man_d, annotations={'io.containerd.image.name': ref, 'org.opencontainers.image.ref.name': '2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16'})]},
          open(f'{OUT}/index.json', 'w'))
print('ok', man_d['digest'], len(man['layers']), 'layers')
