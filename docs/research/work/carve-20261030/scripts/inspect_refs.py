import sys, glob, os, json, hashlib
import numpy as np, pyarrow.parquet as pq
for p in sys.argv[1:]:
    t = pq.read_table(p); row = {c: t.column(c)[0].as_py() for c in ('object_body_names', 'object_urdf_paths')}
    pos = np.array(t.column('object_body_position')[0].as_py(), float)
    print(os.path.relpath(p, os.environ.get('BASE', '/')), '| md5', hashlib.md5(open(p, 'rb').read()).hexdigest()[:8], '| frames', len(pos), '| objs', row['object_body_names'])
    for u in row['object_urdf_paths']:
        print('    urdf', u)
