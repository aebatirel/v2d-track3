"""Grasp summary per frame window for one object and its holding hand, from frames.py output + the same source.
Usage: summ.py FRAMES.jsonl SRC(trace npz | ref parquet) OBJ HULLS GLB SIDE WINDOWS [--ref] [--mm 5] [--json OUT]
WINDOWS = "a-b,c-d,..." frame windows. Per window (means over its frames):
 - object: lift (cm), lowest point above the table (mm; <= 2 = touching), tilt of the plate normal from vertical,
   turn from frame 0, slide (horizontal travel, mm), distance to the other object (mm), which part is lowest;
 - contacts of SIDE's hand within MM: links per frame, share of frames with thumb / fingers / palm in contact,
   faces (+axis3 / -axis3 / edge), regions, which side of the link (pad / radial / dorsal ...);
 - hand pose vs plate: |palm normal . plate normal|, palm normal z (world; -1 = palm down), finger direction . plate
   long axis (towards the head / pan), opposition axis thumb->fingers: |. plate normal| and its palm-frame components;
 - finger flexion (deg): MCP / PIP / DIP per finger, thumb CMC_FE / CMC_AA / MCP_FE / IP."""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from collections import Counter
from scipy.spatial.transform import Rotation as R
import xml.etree.ElementTree as ET
from rlgrasp_lib import ObjGeom, load_trace, load_ref, urdf_path

p = argparse.ArgumentParser(); p.add_argument('frames'); p.add_argument('src'); p.add_argument('obj'); p.add_argument('hulls'); p.add_argument('glb')
p.add_argument('side'); p.add_argument('windows'); p.add_argument('--ref', action='store_true'); p.add_argument('--mm', type=float, default=5.0)
p.add_argument('--json', default=None)
a = p.parse_args()
G = ObjGeom(a.hulls, a.glb); src = load_ref(a.src) if a.ref else load_trace(a.src)
recs = {}
for l in open(a.frames):
    r = json.loads(l); recs[r['f']] = r
S = a.side; SP = S[0].upper()
root = ET.parse(urdf_path(S)).getroot()
thumb_y = [float(x) for x in [j for j in root.findall('joint') if j.get('name') == f'{S}_thumb_CMC_FE'][0].find('origin').get('xyz').split()][1]
PALMAR, FING, RAD = np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), np.array([0, np.sign(thumb_y), 0])
FINGERS = ('index', 'middle', 'ring', 'pinky')


def frame_stats(f):
    r = recs[f]; o = r['obj'][a.obj]; op = src['obj'][a.obj][f]; Ro = R.from_quat(op[3:7])
    pn = Ro.apply(G.W[2]); la = Ro.apply(G.W[0]); pal = src['links'][f'{S}_hand_C_MC'][f]; Rp = R.from_quat(pal[3:7])
    nrm, fd, rd = Rp.apply(PALMAR), Rp.apply(FING), Rp.apply(RAD)
    L = {k: v for k, v in o['links'].items() if k.startswith(SP + ':') and v['d_mm'] <= a.mm}
    tp, fp = [], []
    for k, v in L.items():
        xw = Ro.apply(G.c + np.array(v['pca_cm']) / 100 @ G.W) + op[:3]
        (tp if 'thumb' in k else fp).append(xw)
    opp = None
    if tp and fp:
        u = np.mean(fp, 0) - np.mean(tp, 0); n_ = np.linalg.norm(u)
        if n_ > 1e-3:
            u /= n_; opp = dict(len_cm=100 * n_, dot_plate=abs(u @ pn), palm=(u @ nrm, u @ fd, u @ rd))
    js = r['hands'][S]['joints']
    return dict(o=o, L=L, nl=len(L), thumb=any('thumb' in k for k in L), palm=any('C_MC' in k for k in L),
                fingers=sorted({k.split(':')[1].split('_')[0] for k in L if k.split(':')[1].split('_')[0] in FINGERS}),
                palm_dot=abs(nrm @ pn), palm_z=nrm[2], fd_long=fd @ la, opp=opp, js=js)


def deg(x):
    return round(float(np.degrees(x)), 0)


out = []
for w in a.windows.split(','):
    f0, f1 = (int(x) for x in w.split('-')); fs = [f for f in range(f0, f1) if f in recs and f < src['T']]
    if not fs:
        continue
    st = [frame_stats(f) for f in fs]; n = len(st)
    O = lambda k: float(np.mean([s['o'][k] for s in st]))  # noqa: E731
    faces, regs, onl, links = Counter(), Counter(), Counter(), Counter()
    for s in st:
        for k, v in s['L'].items():
            faces[v['face']] += 1; regs[v['region']] += 1; onl[(k.split(':')[1].split('_')[0], v['on_link'])] += 1; links[k.split(':')[1]] += 1
    tot = max(1, sum(faces.values()))
    opps = [s['opp'] for s in st if s['opp']]
    J = lambda j: deg(np.mean([s['js'].get(j, np.nan) for s in st]))  # noqa: E731
    row = dict(win=w, n=n, lift_cm=round(O('lift_cm'), 1), max_lift=round(max(s['o']['lift_cm'] for s in st), 1), low_mm=round(O('low_mm'), 1),
               frac_on_table=round(float(np.mean([s['o']['low_mm'] <= 2 for s in st])), 2), low_region=Counter(s['o']['low_region'] for s in st).most_common(1)[0][0],
               tilt=round(O('tilt_deg'), 0), turn=round(O('turn_deg'), 0), slide_mm=round(O('slide_mm'), 0), oo_min_mm=round(min(s['o'].get('objobj_mm', 1e9) for s in st), 1),
               links=round(float(np.mean([s['nl'] for s in st])), 1), thumb=round(float(np.mean([s['thumb'] for s in st])), 2),
               palm=round(float(np.mean([s['palm'] for s in st])), 2),
               fingers={fi: round(float(np.mean([fi in s['fingers'] for s in st])), 2) for fi in FINGERS},
               faces={k: round(v / tot, 2) for k, v in faces.most_common()}, regions={k: round(v / tot, 2) for k, v in regs.most_common()},
               top_links={k: round(v / n, 2) for k, v in links.most_common(10)},
               on_link={f'{a_}:{b_}': round(v / tot, 2) for (a_, b_), v in onl.most_common(8)},
               palm_dot_plate=round(float(np.mean([s['palm_dot'] for s in st])), 2), palm_normal_z=round(float(np.mean([s['palm_z'] for s in st])), 2),
               fingerdir_dot_long=round(float(np.mean([s['fd_long'] for s in st])), 2),
               opp_frac=round(len(opps) / n, 2),
               opp_dot_plate=round(float(np.mean([q['dot_plate'] for q in opps])), 2) if opps else None,
               opp_len_cm=round(float(np.mean([q['len_cm'] for q in opps])), 1) if opps else None,
               opp_palm_nfr=[round(float(np.mean([q['palm'][i] for q in opps])), 2) for i in range(3)] if opps else None,
               flex={fi: (J(f'{fi}_MCP_FE'), J(f'{fi}_PIP'), J(f'{fi}_DIP')) for fi in FINGERS},
               thumb_j=(J('thumb_CMC_FE'), J('thumb_CMC_AA'), J('thumb_MCP_FE'), J('thumb_IP')),
               abd={fi: J(f'{fi}_MCP_AA') for fi in FINGERS})
    out.append(row)
    print(json.dumps(row))
if a.json:
    json.dump(out, open(a.json, 'w'), indent=1)
