import sys, numpy as np, pyarrow.parquet as pq
t = pq.read_table(sys.argv[1])
print(t.num_rows, t.column_names)
names = t.column('object_body_names')[0].as_py(); print('names', names)
P = np.array(t.column('object_body_position')[0].as_py(), float); B = len(names); T = P.size // (3*B); P = P.reshape(T, B, 3)
print('T', T, 'fps', t.column('fps')[0].as_py() if 'fps' in t.column_names else None)
for b, n in enumerate(names):
    print(n, 'f0', P[0, b].round(4), 'z range', P[:, b, 2].min().round(4), P[:, b, 2].max().round(4))
for f in (0, 37, 38, 46, 60, 100, 110, 117, 120, 140, 160, T-1):
    print(f, ' '.join(f'{n}:{P[f,b].round(4)}' for b, n in enumerate(names)))
