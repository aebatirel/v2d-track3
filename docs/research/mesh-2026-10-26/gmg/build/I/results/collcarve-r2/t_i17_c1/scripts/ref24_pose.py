"""T-I17 c1 input: object poses at one frame of OUR ep24 FlashCHORD reference (physS1 glockt, our P_sel + determined-
wright's constant z shifts; not ground truth) and the table top of its support stage, written to an npz. Standalone (no
gmg import: the gmg guard refuses .parquet paths). Columns read: object_body_names, object_body_position,
object_body_wxyz only."""
import sys, re, json, hashlib
import numpy as np, pyarrow.parquet as pq
ref, sup, frame, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
t = pq.read_table(ref, columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
row = t.to_pylist()[0]
names = list(row['object_body_names'])
pos = np.array(row['object_body_position'], float)
wxyz = np.array(row['object_body_wxyz'], float)
txt = open(sup).read()
tz = float(re.search(r'xformOp:translate = \(([-\d.e]+), ([-\d.e]+), ([-\d.e]+)\)', txt).group(3))
th = float(re.search(r'double height = ([-\d.e]+)', txt).group(1))
np.savez(out, names=np.array(names), pos=pos[frame], wxyz=wxyz[frame], table_top=tz + th / 2, frame=frame,
         n_frames=len(pos))
print(json.dumps(dict(names=names, n_frames=len(pos), frame=frame, table_top=tz + th / 2,
                      ref_md5=hashlib.md5(open(ref, 'rb').read()).hexdigest(),
                      sup_md5=hashlib.md5(open(sup, 'rb').read()).hexdigest(),
                      pos=pos[frame].tolist(), wxyz=wxyz[frame].tolist())))
