"""Stream-check a `docker save | zstd` style tarball: every blobs/sha256/<h> hashes to <h>; manifest.json, index.json
and the OCI manifest name the config and layers that are present; the config's diff_ids equal the layer list."""
import hashlib, json, sys, tarfile
import zstandard
path = sys.argv[1]
blobs, files = {}, {}
with open(path, 'rb') as fh:
    r = zstandard.ZstdDecompressor().stream_reader(fh, read_size=1 << 22)
    t = tarfile.open(fileobj=r, mode='r|')
    for m in t:
        if not m.isfile():
            continue
        f = t.extractfile(m); h = hashlib.sha256(); small = b''
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            h.update(b)
            if m.size < 1 << 20:
                small += b
        if m.name.startswith('blobs/sha256/'):
            blobs[m.name.split('/')[-1]] = (h.hexdigest(), m.size, small)
        else:
            files[m.name] = small
bad = [k for k, (d, _, _) in blobs.items() if d != k]
man = json.loads(files['manifest.json'])[0]; idx = json.loads(files['index.json'])
cfg_h = man['Config'].split('/')[-1]; cfg = json.loads(blobs[cfg_h][2])
layers = [l.split('/')[-1] for l in man['Layers']]
oci = json.loads(blobs[idx['manifests'][0]['digest'].split(':')[1]][2])
ok = (not bad and all(l in blobs for l in layers) and [d.split(':')[1] for d in cfg['rootfs']['diff_ids']] == layers
      and oci['config']['digest'] == f'sha256:{cfg_h}' and [l['digest'].split(':')[1] for l in oci['layers']] == layers)
print(f'{len(blobs)} blobs, digest mismatches {len(bad)}, image id sha256:{cfg_h}, RepoTags {man["RepoTags"]}, '
      f'{len(layers)} layers, uncompressed {sum(s for _, s, _ in blobs.values())} B, OCI manifest {idx["manifests"][0]["digest"]}')
print('TARBALL OK' if ok else 'TARBALL BAD')
sys.exit(0 if ok else 1)
