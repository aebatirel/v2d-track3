"""C0b PREREG section 3: the GT-free replacement of every scan-derived (S) and unknown (U) record of AUDIT.json.

Reads AUDIT.json (same directory as PREREG.md), checks that every S and U record has exactly one replacement below,
and writes REPLACEMENTS.json and REPLACEMENTS.md (the table pasted into PREREG.md section 3.9). No data are read.

Replacement classes (PREREG section 3.1):
  MK     whole marker path replaced by gmg markers.py (frozen A.6 settings, radius free) + markers.attach
  TH     thickness chain: own two-wall measurement where the method has one (O, unchanged) -> gmg thickness.py on the
         same observations (>= 200 finite two-sided measurements: median) -> t0_C0b (thickness.aggregate, PREREG A.1
         rule, on the C0b public observations); never the 2.5 mm thickness.py FALLBACK; clamp [1.5, 8] mm (A.6)
  LIB    library_v3 input removed (ROI cube, own-point co-object carving, tsdf variant dropped)
  A6     a value frozen in gmg PREREG A.6 for the same meaning (documented generic / sensor / fitted:own)
  A6B    gmg PREREG A.6b extent table (E1-E4 of s = autokit parts.robust_scale), run x1 and x2
  OWN    own-observation estimate
  GEN    new generic value, rule stated here (value changes)
  KEEP   value unchanged, declared generic here with the stated rule (post hoc rationale; disclosed as such)
  NEVER  option exists but is never selected in C0b / E0b
  RULE   selection rule pre-registered in PREREG.md
  INPUT  not a constant (owner / organiser question)
Usage: python -I prereg_table.py   (run from anywhere)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
C0B = os.path.dirname(HERE)

MK = ('MK', 'gmg markers.py detect_episode (frozen A.6 settings, settings_sha256 checked) on the same observations; '
            'attach() per variant (fit/thick: posts by attach\'s stem rule; nostem: bare balls; nomk: none)',
      'generic: gmg PREREG A.6 ball detector and radius window (bounds the search only; no radius prior)',
      '--markers_json, --attach')

R = {
    6: ('A6', 'APP_D = 3 sigma (sigma = gmg A.2 estimator of the object-episode, clamp [0.5, 3] mm)',
        'generic: gmg A.6 grammar "appendage points > 3 sigma outside the body"; sigma fitted:own', '--app_d_sigma 3 --sigma S'),
    8: MK, 9: MK, 10: MK, 11: MK, 12: MK, 13: MK, 14: MK, 15: MK,
    16: ('A6', 'measured pot wall clipped to [1.5, 8] mm',
         'sensor: gmg A.6 thickness floor (about 2 sigma) and wall clip (two voxels)', '--t_clip 0.0015,0.008'),
    17: ('TH', 'fewer than 3 two-wall bins: thickness.py median on the same observations (>= 200 measurements), else t0_C0b',
         'fitted:own (thickness.py, A.1 rule); never 4 mm, never the 2.5 mm thickness.py fallback', '--t_fallback T'),
    18: ('TH', 'lid sheet t = thickness.py median on the same observations (>= 200 measurements), else t0_C0b '
               '[M on obs_all: 0 measurements on ep0 and ep2, so expected t0_C0b]',
         'fitted:own (thickness.py / A.1 t0)', '--t_lid T'),
    19: ('RULE', 'grid retired: one thickness, set by the chain; no value is chosen by a person',
         'n.a.', '-'),
    20: ('TH', 'BAR_T0 (strap / bar thickness without side evidence) = t0_C0b',
         'fitted:own (A.1 unseen-thickness default)', '--bar_t0 T'),
    25: MK, 26: MK, 27: MK,
    29: ('KEEP', 'unchanged (r < 0.4 R in the end 25 %)', 'generic: coarse geometric test; [M] C0 counts 21897 vs 0', '-'),
    30: ('KEEP', 'unchanged', 'generic: robust percentile window (not U-suspect)', '-'),
    32: ('KEEP', 'unchanged', 'generic: robust percentiles (not U-suspect)', '-'),
    33: ('GEN', 'hO = 0.5 x height (mid-height of the observed extent)',
         'generic: the symmetric interior point; no shape knowledge', '--h_o 0.5'),
    36: ('KEEP', 'unchanged', 'generic: robust percentile, sample size 30', '-'),
    39: ('KEEP', 'unchanged', 'generic: robust percentiles P3-P97, sample sizes', '-'),
    40: ('A6', 'bar thickness clip [1.5, 8] mm', 'sensor: gmg A.6 thickness floor and wall clip', '--strap_t_clip 0.0015,0.008'),
    41: ('KEEP', 'unchanged', 'generic: robust percentiles; search span (not U-suspect)', '-'),
    42: ('KEEP', 'unchanged', 'generic: occupancy-gap test (not U-suspect)', '-'),
    44: ('KEEP', 'unchanged (>= 200 points)', 'generic: sample size (= the A.1 measurement minimum)', '-'),
    45: ('GEN', 'handle cluster: P99 radius > 1.5 x rmax (reaches beyond the body by half its own radius)',
         'generic, relative to the own measured body radius', '--reach_rel 0.5'),
    46: ('LIB', 'tsdf variant not built; its family slot is taken by nomk (no balls)', 'n.a. (input removed)', 'variant list'),
    47: ('A6B', 'dome fit window r in [E1, E2] = [0.05 s, 0.2 s]; table x2: [0.1 s, 0.4 s]',
         'generic: gmg A.6b (sheet_of_revolution.dome_r0 / dome_r1), assigned by meaning', '--lid_win a6b1|a6b2'),
    50: ('A6B', 'flange window r in [E3, E4] = [0.6 s, 1.2 s] (x2: [1.2 s, 2.4 s]); height band +-3 sigma',
         'generic: gmg A.6b (flange_r0 / flange_r1); A.6 noise band 3 sigma', '--lid_win a6b1|a6b2'),
    51: ('KEEP', 'unchanged', 'generic: bins of 1-2 vote voxels, robust percentile (not U-suspect)', '-'),
    52: ('KEEP', 'unchanged (SURF_D 4 mm)', 'generic: one vote voxel', '-'),
    54: ('KEEP', 'unchanged', 'generic (not U-suspect)', '-'),
    55: ('GEN', 'arch = largest residual cluster with >= 100 points and in-plane extent > 0.5 x r_edge',
         'generic, relative to the own measured lid radius r_edge', '--arch_ext_rel 0.5'),
    56: ('KEEP', 'unchanged', 'generic: view-cosine classes, robust percentiles', '-'),
    57: ('KEEP', 'unchanged (8-30 mm; not binding in C0)', 'generic (not U-suspect)', '-'),
    58: ('A6', 'arch thickness clip [1.5, 8] mm; no side evidence: t0_C0b', 'sensor: gmg A.6 clip; fitted:own t0',
         '--strap_t_clip 0.0015,0.008 --bar_t0 T'),
    62: ('TH', 'rack wall / floor T = thickness.py median over the pooled measurements of the run\'s episodes (>= 200), '
               'else t0_C0b [M on obs_all: 0 measurements on all 5 rack episodes, so expected t0_C0b]',
         'fitted:own (thickness.py / A.1 t0)', '--t_wall T'),
    65: ('KEEP', 'unchanged (2 mm)', 'generic: robust-loss scale of the order of the stereo noise', '-'),
    66: ('KEEP', 'unchanged', 'generic (rack window, not U-suspect)', '-'),
    67: ('KEEP', 'unchanged', 'generic (rack window, not U-suspect)', '-'),
    69: ('KEEP', 'unchanged (round pegs; binds)', 'generic: the minimum-information section for an unseen back', '-'),
    71: ('MK', 'unused under C0b: the rack residual set feeds only the marker path, which is replaced',
         'n.a.', '--markers_json'),
    72: MK, 73: MK,
    77: ('NEVER', 'cup_upright() never used: CUP_LEAN = 1 passed explicitly', 'n.a.', 'PRIM_CUP_LEAN=1'),
    78: ('KEEP', 'unchanged (1.25; binds; ep26 near the cut in C0)', 'generic: 25 % consistency tolerance', '-'),
    80: ('KEEP', 'unchanged', 'generic: robust percentiles, refits', '-'),
    81: ('KEEP', 'unchanged', 'generic: robust percentiles', '-'),
    82: ('KEEP', 'unchanged', 'generic: robust percentiles', '-'),
    83: ('KEEP', 'unchanged', 'generic: bands and sample sizes (not U-suspect)', '-'),
    84: ('KEEP', 'unchanged (initial values only)', 'generic', '-'),
    85: ('KEEP', 'unchanged', 'generic (not U-suspect)', '-'),
    87: ('TH', 's0 lower bound S0_MIN = the rack wall thickness T (a lip is at least as wide as the wall it tops); '
               's1 >= 0 kept (a moulded basin has non-negative draft); other bounds unchanged (interior in C0)',
         'fitted:own T; generic (moulding draft)', '--s0_min_t'),
    88: ('KEEP', 'unchanged; the T_WALL terms use the C0b T', 'generic', '--t_wall T'),
    89: ('KEEP', 'unchanged (not binding in C0)', 'generic', '-'),
    90: ('KEEP', 'unchanged', 'generic', '-'),
    91: ('KEEP', 'unchanged (>= 50 points, else tray floor; binds: 43 in C0); T_WALL terms use the C0b T',
         'generic: sample size for a planar patch', '--t_wall T'),
    92: ('KEEP', 'unchanged', 'generic', '-'),
    93: ('KEEP', 'unchanged', 'generic', '-'),
    95: ('KEEP', 'unchanged', 'generic', '-'),
    97: ('KEEP', 'unchanged', 'generic', '-'),
    99: MK,
    101: ('MK', 'in_basin rule removed: every gmg-detected ball is attached (the gmg path has no basin rule)',
          'generic: gmg A.6 detector', '--markers_json'),
    107: ('GEN', 'TIE = 1.0: no tie-break, the best rotational consistency wins (also for pot_axis\'s fit_axis call)',
          'generic: argmin; [M] for the C0 cup TIE 1.1-2.0 gives the same axis', '--tie 1.0'),
    117: ('A6', 'app_d = 3 sigma (sigma = gmg A.2 of the observations used)', 'generic: gmg A.6 grammar; sigma fitted:own',
          '--app_d 3*sigma'),
    118: ('KEEP', 'unchanged (400 points)', 'generic: sample size', '-'),
    121: ('A6', 'tmin = 1.5 mm (same number)', 'sensor: gmg A.6 thickness floor (about 2 sigma)', '--tmin 0.0015'),
    122: ('NEVER', '--floor observed never used', 'n.a.', '--floor base_t'),
    128: ('TH', 'fewer than 3 two-wall bins: thickness.py median on the same observations (>= 200), else t0_C0b',
          'fitted:own; never 3 mm', '--t_fallback T'),
    130: ('KEEP', 'unchanged (3 mm)', 'generic: two 1.5 mm downsample voxels', '-'),
    131: ('GEN', 'floor = base + t always (new choice base_t); no cap-point density rule',
          'generic: a moulded vessel\'s floor is about one wall thick and rests on the support plane; '
          '[M] equals the C0 cup on ep21 (scripts/floorcheck.py)', '--floor base_t'),
    132: ('KEEP', 'unchanged', 'generic: splat morphology in voxel units', '-'),
    133: ('LIB', 'ROI = cube of half-side 0.30 m about the track-frame origin; guard: if > 0.1 % of kept points lie within '
               '8 mm of a cube face, rebuild that file at half-side 0.45 m',
          'generic: gmg A.6 crop (+-0.30 m cube, guard 1.5 x); recon_mesh +-30 cm', '--roi_cube 0.30'),
    134: ('LIB', 'co-objects = their own pass-A observed points (C0b options, no others), 20,000 random points (seed 0)',
          'own-observation', '--others_pts NAME=NPZ'),
    135: ('KEEP', 'unchanged (12 mm)', 'generic: 3 vote voxels', '-'),
    138: ('KEEP', 'unchanged (20 mm)', 'generic: recon_mesh flying-pixel filter', '-'),
    140: ('KEEP', 'unchanged (8 mm), re-declared: 2 vote voxels; suspect timing disclosed; not a scan quantity',
          'generic (post hoc rule)', '-'),
    142: ('A6', 'unchanged numbers (4 mm voxel, hits >= 3, ratio >= 0.5, free 10 mm; hit 4 mm = one voxel)',
          'generic: gmg A.6 vote voxel / OBSERVED / free carving', '-'),
    145: ('KEEP', 'unchanged', 'generic (recon_mesh v2; low risk)', '-'),
    149: ('KEEP', 'unchanged (6 mm)', 'generic (recon_mesh v0 default; low risk)', '-'),
    155: ('RULE', 'pick = lowest obs_fidelity sum on ALL, pre-registered for every object (PREREG section 5)', 'n.a.', '-'),
    157: ('TH', 'as id 18', 'fitted:own', '--t_lid T'),
    158: ('TH', 'as id 62', 'fitted:own', '--t_wall T'),
    160: ('LIB', 'as ids 133 and 134', 'generic / own-observation', '--roi_cube, --others_pts'),
    161: ('INPUT', 'sweep base tracks (store run 20261025-sweep-a894083) for every public object-episode, the blue cup '
                  'included (C0 used data/store perc2m tracks for its ep21 / ep22 lathes); eval: E0\'s evperc tracks',
          'owner / organiser question F4 (library_v3-seeded tracks, tier P1)', '--poses'),
}


def main():
    A = json.load(open(os.path.join(C0B, 'AUDIT.json')))
    su = [r for r in A['items'] if r['origin'] in ('S', 'U')]
    ids = {r['id'] for r in su}
    missing = sorted(ids - set(R)); extra = sorted(set(R) - ids)
    assert not missing and not extra, (missing, extra)
    rows = []
    for r in sorted(su, key=lambda r: r['id']):
        cls, rep, origin, flag = R[r['id']]
        fl = f"{os.path.basename(r['file'])}:{r['line']}" if r['line'] not in ('', '-', None) else os.path.basename(r['file'])
        rows.append(dict(id=r['id'], name=r['name'], where=fl, old=r['value'], audit=r['origin'] + (
            '/' + r['sub'] if r['sub'] else ''), c0_binding=r['c0_binding'], c0b_class=cls, c0b=rep,
            c0b_origin=origin, option=flag))
    cnt = {}
    for x in rows:
        cnt[x['c0b_class']] = cnt.get(x['c0b_class'], 0) + 1
    out = dict(schema='c0b-replacements/1', source='AUDIT.json (163 records; S and U only)', n=len(rows),
               counts=cnt, rows=rows)
    json.dump(out, open(os.path.join(C0B, 'REPLACEMENTS.json'), 'w'), indent=1)
    md = ['| id | item (file:line) | old value | audit | C0b replacement | origin of the replacement | option | class |',
          '|---|---|---|---|---|---|---|---|']
    esc = lambda s: str(s).replace('|', '/').replace('\n', ' ')
    for x in rows:
        md.append(f"| {x['id']} | {esc(x['name'])} ({esc(x['where'])}) | {esc(x['old'])} | {esc(x['audit'])} | "
                  f"{esc(x['c0b'])} | {esc(x['c0b_origin'])} | `{esc(x['option'])}` | {x['c0b_class']} |")
    open(os.path.join(C0B, 'REPLACEMENTS.md'), 'w').write('\n'.join(md) + '\n')
    print(json.dumps(dict(n=len(rows), counts=cnt)))


if __name__ == '__main__':
    main()
