"""Replace git-lfs pointer files under ROOT/SUB with their content from media.githubusercontent.com, sha256-checked."""
import hashlib, os, sys, urllib.request, concurrent.futures as cf
root, sub, pin = sys.argv[1], sys.argv[2], sys.argv[3]
todo = []
for d, _, fs in os.walk(os.path.join(root, sub)):
    for f in fs:
        p = os.path.join(d, f)
        with open(p, 'rb') as fh: head = fh.read(200)
        if head.startswith(b'version https://git-lfs'):
            lines = dict(l.split(' ', 1) for l in open(p).read().strip().splitlines())
            todo.append((p, lines['oid'].split(':')[1], int(lines['size'])))
def get(t):
    p, oid, size = t; rel = os.path.relpath(p, root)
    url = f'https://media.githubusercontent.com/media/nvidia-isaac/video_to_data/{pin}/{urllib.parse.quote(rel)}'
    for k in range(4):
        try:
            data = urllib.request.urlopen(url, timeout=120).read()
            if hashlib.sha256(data).hexdigest() == oid and len(data) == size:
                open(p, 'wb').write(data); return 0
        except Exception as e: err = e
    print('FAIL', rel); return 1
import urllib.parse
with cf.ThreadPoolExecutor(16) as ex: bad = sum(ex.map(get, todo))
print(len(todo), 'pointers,', bad, 'failed')
