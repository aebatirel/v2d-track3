import sys, numpy as np, pyarrow.parquet as pq
npz, ref = sys.argv[1], sys.argv[2]
d = np.load(npz, allow_pickle=True); L = [str(x) for x in d['labels']]; q = d['q']
t = pq.read_table(ref).to_pylist()[0]; RP = np.array(t['object_body_position'], float); RW = np.array(t['robot_right_wrist_position'], float).reshape(-1, 3)
ib = L.index('track3_beige_cup/object'); iu = L.index('track3_blue_cup/object'); iw = L.index('right_wrist_pz_body')
eb, eu = [], []
for f in range(len(q)):
    eb.append(np.linalg.norm(q[f, ib, :3] - RP[f, 1]) * 100); eu.append(np.linalg.norm(q[f, iu, :3] - RP[f, 0]) * 100)
for f in list(range(40, 161, 12)) + [160]:
    sb, su = q[f, ib, :3], q[f, iu, :3]
    print(f'f{f:3d} beige err {eb[f]:5.1f} (z sim {sb[2]*100:5.1f} ref {RP[f,1,2]*100:5.1f}) | blue err {eu[f]:4.1f} | beige-blue sim {np.linalg.norm(sb-su)*100:5.1f} ref {np.linalg.norm(RP[f,1]-RP[f,0])*100:5.1f} | wrist err {np.linalg.norm(q[f, iw, :3]-RW[f])*100:4.1f}')
print(f'mean err beige {np.mean(eb):.1f} cm, blue {np.mean(eu):.1f} cm; last-20-frames beige {np.mean(eb[-20:]):.1f}')
