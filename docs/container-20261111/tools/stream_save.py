"""Stream a local image as an OCI image layout + docker manifest.json tar (the layout `docker save` writes) to stdout,
without the daemon's on-disk staging copy (docker save first writes every uncompressed layer to
/var/lib/docker/tmp; this host has no room for that).

Each layer tar is reassembled exactly the way the daemon's own export does it (layer.TarStream: tar-split metadata in
layerdb + the files of the overlay2 diff directory). Its sha256 is checked against the image config's diff_id while it
streams; any mismatch aborts with a non-zero exit (the partial output must then be discarded).

    python3 stream_save.py IMAGE_ID REPO:TAG | zstd -T0 > image.tar.zst
"""
import base64, gzip, hashlib, io, json, os, sys, tarfile

DOCKER = '/var/lib/docker'
IMG, TAG = sys.argv[1].split(':')[-1], sys.argv[2]
cfg_bytes = open(f'{DOCKER}/image/overlay2/imagedb/content/sha256/{IMG}', 'rb').read()
assert hashlib.sha256(cfg_bytes).hexdigest() == IMG
cfg = json.loads(cfg_bytes)
diff_ids = cfg['rootfs']['diff_ids']

chain, layers = None, []
for d in diff_ids:
    chain = d if chain is None else 'sha256:' + hashlib.sha256(f'{chain} {d}'.encode()).hexdigest()
    ldb = f'{DOCKER}/image/overlay2/layerdb/sha256/{chain.split(":")[1]}'
    cache = open(f'{ldb}/cache-id').read().strip()
    assert open(f'{ldb}/diff').read().strip() == d
    entries = [json.loads(line) for line in gzip.open(f'{ldb}/tar-split.json.gz', 'rt')]
    size = sum(len(base64.b64decode(e['payload'])) if e['type'] == 2 else e.get('size', 0) for e in entries)
    layers.append(dict(diff_id=d, root=f'{DOCKER}/overlay2/{cache}/diff', entries=entries, size=size))


class LayerReader(io.RawIOBase):
    """The layer's tar stream, assembled from tar-split segments and diff-directory file contents."""

    def __init__(self, layer):
        self.layer, self.digest, self.buf, self.gen = layer, hashlib.sha256(), b'', self._chunks()

    def _chunks(self):
        for e in self.layer['entries']:
            if e['type'] == 2:
                yield base64.b64decode(e['payload'])
            elif e.get('size', 0) > 0:
                name = base64.b64decode(e['name_raw']).decode('utf-8', 'surrogateescape') if e.get('name_raw') else e['name']
                left = e['size']
                with open(os.path.join(self.layer['root'], name), 'rb') as f:
                    while left:
                        b = f.read(min(left, 1 << 22))
                        if not b:
                            raise SystemExit(f'short file {name} in {self.layer["diff_id"]}')
                        left -= len(b)
                        yield b

    def readable(self):
        return True

    def readinto(self, out):
        while not self.buf:
            try:
                self.buf = next(self.gen)
            except StopIteration:
                return 0
        n = min(len(out), len(self.buf))
        out[:n], self.buf = self.buf[:n], self.buf[n:]
        self.digest.update(out[:n])
        return n


def add_bytes(tar, name, data):
    info = tarfile.TarInfo(name); info.size = len(data); info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))


def add_dir(tar, name):
    info = tarfile.TarInfo(name); info.type = tarfile.DIRTYPE; info.mode = 0o755
    tar.addfile(info)


out = tarfile.open(fileobj=sys.stdout.buffer, mode='w|', format=tarfile.PAX_FORMAT)
add_dir(out, 'blobs'); add_dir(out, 'blobs/sha256')
written = set()
for layer in layers:
    h = layer['diff_id'].split(':')[1]
    if h in written:
        continue
    info = tarfile.TarInfo(f'blobs/sha256/{h}'); info.size = layer['size']; info.mode = 0o644
    reader = LayerReader(layer)
    out.addfile(info, io.BufferedReader(reader, 1 << 22))
    if reader.digest.hexdigest() != h:
        raise SystemExit(f'layer digest mismatch: {reader.digest.hexdigest()} != {h}')
    written.add(h)
    print(f'layer {h[:12]} {layer["size"]} bytes ok', file=sys.stderr, flush=True)
add_bytes(out, f'blobs/sha256/{IMG}', cfg_bytes)
manifest = json.dumps({
    'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.manifest.v1+json',
    'config': {'mediaType': 'application/vnd.oci.image.config.v1+json', 'digest': f'sha256:{IMG}', 'size': len(cfg_bytes)},
    'layers': [{'mediaType': 'application/vnd.oci.image.layer.v1.tar', 'digest': l['diff_id'], 'size': l['size']}
               for l in layers]}, separators=(',', ':')).encode()
mh = hashlib.sha256(manifest).hexdigest()
add_bytes(out, f'blobs/sha256/{mh}', manifest)
repo, tag = TAG.rsplit(':', 1)
index = {'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.index.v1+json',
         'manifests': [{'mediaType': 'application/vnd.oci.image.manifest.v1+json', 'digest': f'sha256:{mh}',
                        'size': len(manifest),
                        'annotations': {'io.containerd.image.name': f'docker.io/library/{TAG}',
                                        'org.opencontainers.image.ref.name': tag}}]}
add_bytes(out, 'index.json', json.dumps(index, separators=(',', ':')).encode() + b'\n')
add_bytes(out, 'manifest.json', json.dumps([{'Config': f'blobs/sha256/{IMG}', 'RepoTags': [TAG],
                                             'Layers': [f'blobs/sha256/{l["diff_id"].split(":")[1]}' for l in layers]}],
                                           separators=(',', ':')).encode() + b'\n')
add_bytes(out, 'oci-layout', b'{"imageLayoutVersion":"1.0.0"}')
out.close()
print(f'image sha256:{IMG}; OCI manifest sha256:{mh}; {len(written)} distinct layers', file=sys.stderr)
