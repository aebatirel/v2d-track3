"""C0b constants audit: one record per numeric constant / prior / window / threshold / default (or a tight group of
them) used to build the C0 pot, lid, rack and blue cup, and the command-line settings C0 used. Writes AUDIT.json and
the tables of AUDIT.md (between the AUTO markers). Pure data; reads nothing but this file and AUDIT.md.

Origin classes:
  G  generic: physics, units, numerics (bin sizes, iteration counts, robust-statistics factors, sampling sizes/seeds)
  O  own-observation: measured or decided on our stereo / video, with a record
  S  scan-derived; sub-class S-value (a number measured on a public scan, directly or via a brief/doc that quoted
     scan measurements), S-dev (value or rule set in direct response to a scan diagnostic or scan score),
     S-input (an input file that the project's own deny-list marks as scan-derived: meshes/library_v3)
  U  unknown: no recorded derivation. U-suspect = also matches a scan number the author had in context, or was set
     in a development loop that read scans. "Unknown" is NOT "generic".
Line numbers: HEAD (14eaf37 for prim_potlid.py; identical code to 2971a10 / E0 jobs/frozen apart from the comment on
line 67). Binding = whether the value changed the C0 mesh, from the build records [M].
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PP, PR, LO, OP, OF, RM = ('prim_potlid.py', 'prim_rack.py', 'lathe_obs.py', 'obs_points.py', 'obs_fidelity.py',
                          'pipeline/recon_mesh.py')

# evidence shorthands (full references in AUDIT.md section 2)
E_BRIEF = 'the primitive-round brief carried scan numbers to the builders (AUDIT.md section 3.1)'
E_POTREAD = ('the potlid builder read the scan wall / bbox rows of README and the scan-profile figure before writing the '
             'code (section 3.1)')
E_RACKSCAN = 'the rack builder saw scan scores at 05:51 and a scan cup-holder / floor printout at 05:52-05:53 (section 3.1)'
E_LATHELOOP = 'lathe_obs scan-scored development loop, 26 Oct 15:51-16:12 (section 3.3)'
E_DENY = 'ops/provenance/denylist.json (mesh pipeline v5 spec 3.2) lists meshes/library_v3/*; ledger sec. 1 and 6'

R = []


def add(file, line, name, value, controls, origin, sub, evidence, binds, objs, action):
    R.append(dict(id=len(R) + 1, file=file, line=line, name=name, value=value, controls=controls, origin=origin,
                  sub=sub, evidence=evidence, c0_binding=binds, objects=objs, action=action))


# ------------------------------------------------------------------------------------------------ prim_potlid.py
o = 'pot,lid'
add(PP, '56', 'VOX', '1.5 mm', 'voxel downsample of observed points', 'G', '', 'sampling resolution, same in lathe_obs/prim_rack', 'yes (all)', 'pot,lid', 'keep')
add(PP, '57', 'NSEC', '24', 'azimuth sectors (profile, rim, lid tilt)', 'G', '', 'angular binning', 'yes', o, 'keep')
add(PP, '58', 'MINSEC', '6 of 24', 'sectors needed for a profile bin to count as body of revolution', 'O', '',
    'set in lathe_obs 26 Oct 16:11 after printing per-height sector counts of OUR ep41 pot points (16:10:55); "a handle or a marker fills 1-3 of 24 sectors". the same loop also read scans (section 3.3), but the stated basis is our own points',
    'yes', o, 'keep (flag loop)')
add(PP, '59', 'MIN_PTS', '8', 'points per (bin, sector) cell', 'G', '', 'minimum sample count', 'yes', o, 'keep')
add(PP, '60', 'DPHI', '2 deg', 'polar-angle bin of the pot profile', 'G', '', 'binning', 'yes', 'pot', 'keep')
add(PP, '61', 'APP_D', '8 mm', 'residual threshold: points farther than this outside the body are handle/arch/marker candidates; also tsdf variant face cut, bar/arch exclusion band', 'U', 'U-suspect',
    'comment "stereo noise reaches 5-10 mm". The only noise figures on record before 27 Oct 04:19 are [D] obs-vs-scan percentiles (obs_diag: pot ep41 p90 6.6 / p95 8.7 mm; cup p95 4.9-7.3 mm, README sec. 4). No own-observation noise measurement predates it (the [M] handle-plane spread 5.6-9.3 mm is from 27 Oct 13:20, later)',
    'yes (defines every residual set)', 'pot,lid,rack', 'replace by an own-observation value (e.g. a high percentile of |obs-to-fitted-body| distance on the episode) as an OPTION; or pre-register as a generic prior and test 2 values')
add(PP, '62', 'CL_VOX', '3 mm', 'residual clustering voxel', 'G', '', 'connectivity resolution', 'yes', 'pot,lid,rack', 'keep')
add(PP, '63', 'MK_MIN', '60 points', 'minimum residual points for marker processing / cluster size', 'U', '', 'no derivation recorded', 'yes (gating)', 'pot,lid,rack', 'superseded if gmg markers.py replaces markers_from; else flag')
add(PP, '64', 'MK_DIAG', '6-35 mm (3-97 % bbox diagonal)', 'size window for a marker cluster', 'U', 'U-suspect',
    'no derivation; written in the same block as MK_R0 = 7 mm (scan-derived) and the brief\'s "~7 mm"; a 7 mm ball cap is 14-20 mm across', 'yes (many size rejections in pot/lid/rack records)', 'pot,lid,rack', 'replace with gmg markers.py (PREREG A.6) or a declared generic window')
add(PP, '65', 'MK_RES', '2 mm', 'sphere-fit median residual acceptance', 'U', '', 'no derivation recorded', 'yes (pot cluster rejected at 2.13 mm)', 'pot,lid,rack', 'as MK_DIAG')
add(PP, '66', 'MK_GAP', '-3..+20 mm', 'ball surface to body/handle surface window (markers on short stems); also forces the prior radius when the free fit violates it', 'U', '',
    'no derivation; stage-1 audit (27 Oct 17:20) asked to re-check its provenance (not done). Spoon template mount height 10.9 mm is scan-derived but is not this window', 'yes (gating + prior switch)', 'pot,lid,rack', 'as MK_DIAG')
add(PP, '67', 'MK_R0', '7.0 mm', 'fixed ball radius used whenever the free sphere fit is rejected', 'S', 'S-value',
    'spoon/spoon_template.py:71 marker_radius 7.2 mm "note 17: fitted r 6.6-7.8 mm" = docs/research/notes/17 sec. A1 "Marker sphere catalogue from the scans"; stage-1 audit blocker 1 (work log 27 Oct ~17:20); comment fixed in 14eaf37; the brief called it "our own stereo" (false)',
    'YES: pot 4 of 5 accepted balls at 7.00 (free fits 11.96, 27.88, 3.67, 387 mm replaced; verify_0 sees 3 as separate 7.00 mm bodies), lid 2 of 3 at 7.00 (one is the floating body), rack 1 of 2 at 7.00 (free fit 9.51 mm)', 'pot,lid,rack', 'REPLACE (gmg markers.py free radius, or no balls)')
add(PP, '68', 'MK_RMIN, MK_RMAX', '5.0-9.5 mm', 'free-fit radius acceptance window', 'S', 'S-value',
    'window around the scan catalogue 6.6-7.8 mm; stage-1 audit blocker 1 ("MK_R0 = 7 mm (and the 5-9.5 mm free-fit window) traces to the scans")',
    'YES: free radii kept: pot 6.94, lid 7.35, rack 5.22 mm; free radii replaced by MK_R0: pot 11.96 / 27.88 / 3.67 / 387, lid 8.99 (gap) / 322, rack 9.51 mm', 'pot,lid,rack', 'REPLACE (with MK_R0)')
add(PP, '69', 'STEM_MIN', '15 points', 'points in the ball-to-surface gap needed for a stem', 'U', '', 'no derivation', 'gating only (no accepted C0 ball got a stem)', 'pot,lid,rack', 'flag')
add(PP, '70', 'STEM_R', '3.5 mm', 'stem cylinder radius; stem point count window STEM_R + 1.5 mm', 'U', '',
    'no derivation; stage-1 audit asked to re-check (not done). Spoon template stem foot 5.5 mm (scan) differs', 'no geometry in C0 (no stems)', 'pot,lid,rack', 'flag')
add(PP, '71', 'T_MIN, T_MAX', '2-6 mm', 'clip of the measured pot wall thickness', 'U', 'U-suspect', E_POTREAD + '; brackets the scan pot wall 3.9 mm / brief "~4 mm"; potlid auditor noted it',
    'no (C0 pot t_meas 4.77 mm, inside)', 'pot', 'flag; replace by gmg thickness.py bounds or drop the clip as an OPTION')
add(PP, '405', 'pot wall fallback', '4.0 mm', 'pot wall when < 3 profile bins see both walls', 'S', 'S-value', 'equals the brief\'s "thin wall (~4 mm)" = scan pot wall 3.9 mm (README sec. 1); ' + E_POTREAD,
    'no (C0 pot: 24 two-wall bins)', 'pot', 'REPLACE for eval builds (own thickness, gmg thickness.py) or fail the build instead of falling back')
add(PP, '72-75', 'T_LID', '2.5 mm (env PRIM_T_LID)', 'lid sheet thickness: underside = top surface - T_LID (underside never observed)', 'S', 'S-value',
    'leak: first brief quoted scan walls (work log 27 Oct "Leak"; scan lid 1.8 mm); clean-up round kept 2.5 as grid midpoint of 1.5/2.5/4.0 (passed at all three [D]); GT-free fidelity prefers 1.5 (1.436 < 1.686 < 2.259 mm) because the underside is unseen',
    'YES (C0 lid t_mm 2.5)', 'lid', 'REPLACE (own-observation thickness, gmg thickness.py; or a pre-registered generic grid that must pass at every value)')
add(PP, '74 (comment), clean round', 'T_LID grid', '1.5 / 2.5 / 4.0 mm', 'sensitivity grid of the clean-up round', 'U', 'U-suspect',
    'declared "generic thin-moulding range not taken from any scan" (work log), but centred on the leaked 2.5', 'n.a. (defines the verdict rule)', 'lid', 'if reused, re-derive the grid without reference to 2.5')
add(PP, '76', 'BAR_T0', '5 mm', 'handle / arch strap thickness when < 50 / 30 side-seen points', 'U', '', 'no derivation', 'no (pot T_src side 5.8 mm, lid T_src side)', 'pot,lid', 'flag')
add(PP, '77', 'NSEG', '64', 'revolve segments', 'G', '', 'tessellation', 'yes', o, 'keep')
add(PP, '124,145,169', 'q=50; fill_smooth med 5 / avg 3; poly_dist step 0.5 mm', 'see value', 'per-cell median, gap fill + smoothing windows, polyline sampling', 'G', '', 'robust statistics / numerics', 'yes', o, 'keep')
add(PP, '186-199', 'clusters()', '2-voxel pad, 1 dilation, 26-connectivity', 'residual clustering', 'G', '', 'numerics', 'yes', 'pot,lid,rack', 'keep')
add(PP, '214,230', 'sphere fit iterations', '10 GN (free), 15 (prior); prior start behind the cap', 'sphere fitting', 'G', '', 'numerics', 'yes', 'pot,lid,rack', 'keep')
add(PP, '224', 'free-fit acceptance', 'median res < 1.2 mm and spread > 0.08', 'whether the free radius is kept', 'U', '', 'no derivation', 'yes (with MK_RMIN/MAX decides free vs prior)', 'pot,lid,rack', 'replace with gmg markers.py rule')
add(PP, '257', 're-cluster height', 'APP_D + 4 mm (= 12 mm), level 0 only', 'splits oversize clusters into points standing high above the body', 'U', '', 'no derivation', 'yes (level-1 clusters in pot record)', 'pot,lid,rack', 'flag')
add(PP, '275-288', 'stem rule', 'gap > 3 mm; query 0.5 L + 5 mm; tp > r + 0.5 mm, < L - 3 mm; control offset 20 mm; n_stem >= 2 n_ctl; stem 2 mm into surface', 'stem evidence and geometry', 'U', '', 'no derivation (the 2 mm overlap is a union numeric, G)', 'gating only', 'pot,lid,rack', 'flag')
add(PP, '303,311-317,336-352', 'pot_axis search', '600 hemisphere directions; 20000 / 6000 subsamples (seed 0); top 3; local grids +-6 deg step 2, +-2 deg step 0.7', 'pot axis search', 'G', '', 'numerics; design reason recorded as own observation ("fit_axis gave axes 5-36 deg apart on three episodes of the same pot; the rim term agreed")', 'yes', 'pot', 'keep')
add(PP, '325,370-371', 'open-end test', 'points with r < 0.4 R in the end 25 % of the height', 'which end is open (floor only at the closed end)', 'U', '', 'geometric heuristic, no derivation', 'yes (C0 pot axial counts 21897 vs 0: not close)', 'pot', 'keep (insensitive here)')
add(PP, '329-331', 'rim window', 'r in [0.6 R, R + 20 mm]; P98 per sector; >= 10 pts; >= 12 of 24 sectors', 'rim-flatness term of the axis score', 'U', '', 'no derivation; 20 mm absolute', 'yes (axis score)', 'pot', 'flag')
add(PP, '363', 'rot_consistency subsample', '20000, seed 1', 'axis cost report', 'G', '', 'numerics', 'report only', 'pot', 'keep')
add(PP, '367-369', 'body extent', 'r < P60(r) + 20 mm; h P0.5/P99.5; Rb = P90(r)', 'pot body points for the extent / open-end test', 'U', '', 'no derivation; 20 mm absolute', 'yes', 'pot', 'flag')
add(PP, '379', 'hO', '0.6 x height', 'interior origin of the polar profile parameterization', 'U', 'U-suspect', 'no derivation; ' + E_POTREAD + ' (the scan-profile figure was viewed before this design)', 'yes (profile geometry)', 'pot', 'flag; insensitivity test is cheap (0.5 / 0.7)')
add(PP, '383,409', 'view split; normal floor', '|s| > 0.3; cos floor 0.3', 'outer- vs inner-seen classification; mid-surface offset guard', 'G', '', 'same 0.3 as lathe_obs; numerics', 'yes', 'pot', 'keep')
add(PP, '390', 'min profile bins', '10', 'abort if fewer bins', 'G', '', 'sanity check', 'no', 'pot', 'keep')
add(PP, '417-424', 'rim height', 'points within 8 mm of the mid curve, r > 0.5 rmax, > 30 pts per sector, P99, median over sectors', 'pot rim cap height', 'U', '', 'no derivation (8 mm = APP_D)', 'yes (h_top 118.4 mm)', 'pot', 'flag')
add(PP, '434,438', 'resample; radius floor', '3 mm; 0.1 mm', 'profile resampling', 'G', '', 'numerics', 'yes', 'pot', 'keep')
add(PP, '474-481', 'bar top plane', 'top-seen view > 0.3 (else all if <= 50); 4 trimmed refits at 2.5 x 1.4826 MAD', 'handle top plane', 'G', '', 'robust statistics', 'yes', 'pot', 'keep')
add(PP, '487-493', 'bar width', '5 mm bins, >= 15 pts, P3-P97 lateral extent, P1-P99 length range, line fit if >= 4 bins', 'handle width and centre line', 'U', '', 'no derivation', 'yes (width 29.1 mm)', 'pot', 'flag')
add(PP, '498-504', 'bar thickness', 'side-seen |v.w| > 0.5, > 50 pts; T = clip(2 x median depth, 3, 8 mm)', 'handle thickness', 'U', '', 'no derivation for the 3-8 mm clip', 'no (T 5.8 mm, inside)', 'pot', 'flag')
add(PP, '505-512', 'bar ends', 'tip P99.5; inner search from P0.5 - 60 mm, 400 steps; inner end where axis point radius < rmax - 2 t', 'handle length / attachment', 'U', '', 'no derivation', 'yes (length 172.3 mm)', 'pot', 'flag')
add(PP, '519-541', 'handle hole', '> 200 top pts; 2 mm grid; 1 closing; area >= 40 mm^2; within 60 mm of the tip; |a| < half width / 2', 'whether a hole is cut', 'U', '', 'no derivation', 'yes (decided "no hole")', 'pot', 'flag')
add(PP, '562', 'thick variant', 'x 2.0', 'variant "thick" (selection pool only)', 'G', '', 'sensitivity variant', 'no (fit selected)', 'pot,lid', 'keep')
add(PP, '571', 'handle cluster size', '>= 200 points', 'candidate handle clusters', 'U', '', 'no derivation', 'yes', 'pot', 'flag')
add(PP, '577', 'handle reach', 'P99 radius > rmax + 60 mm', 'which residual cluster is the handle', 'U', 'U-suspect', 'no derivation; the brief gave the handle as ~17 cm (scan bbox 35.7 - 18.9 cm; section 3.1)', 'yes (picks the handle cluster; insensitive if the handle reaches ~170 mm)', 'pot', 'flag; insensitivity test (40 / 80 mm)')
add(PP, '597-606, 818', '--lib (tsdf variant)', 'meshes/library_v3/<obj>.glb', 'tsdf variant appends library_v3 faces outside the body', 'S', 'S-input', E_DENY, 'no (fit selected), but tsdf candidates were in the pot (8) and lid (1 per T) selection pools', 'pot,lid', 'drop the tsdf variant in C0b (or document)')
add(PP, '615-624', 'lid dome', 'dr 2 mm; quadratic h = a + b r^2 fitted on r 15-35 mm, used for r < 15 mm, >= 4 bins', 'lid top profile under the arch', 'U', 'U-suspect', 'lid-specific absolute window; no derivation; brief carried scan lid size ("~19 cm across"); potlid auditor judged it "chosen from our own points" (judgement, no record)', 'yes (dome 4.4 mm)', 'lid', 'flag; express relative to r_edge as an OPTION')
add(PP, '632-634', 'lid up direction', 'smallest PCA axis, sign towards the cameras', 'lid normal', 'O', '', 'underside never seen (clean-up PREREG: median |view.axis| = 0.78 at the edge)', 'yes', 'lid', 'keep')
add(PP, '637-649', 'lid centre', '36 sectors; > 50 pts; P98 radius; 3 mm band; 3 circle-fit iterations', 'lid centre', 'G', '', 'robust geometry', 'yes', 'lid', 'keep')
add(PP, '652-654', 'lid flange window', 'r 40-80 mm; |h - median| < 6 mm', 'points used to re-fit the disc normal', 'U', 'U-suspect', 'lid-specific absolute window (r_edge 91 mm); brief carried scan lid size; no derivation', 'yes (axis)', 'lid', 'flag; relative-to-r_edge OPTION')
add(PP, '663-683', 'lid tilt refinement', 'r bins 2 mm / 4 mm; surface +-4 mm; R_hi = P98 - 2 mm; r > 20 mm; >= MIN_PTS; 3 iterations', 'lid axis tilt', 'U', '', 'no derivation for the absolute 20 mm / 4 mm values', 'yes (final tilt 0.023 deg)', 'lid', 'flag')
add(PP, '689-697', 'lid top surface', 'SURF_D 4 mm (two passes); fill_smooth(3, 3); r_edge = median per-sector P99.5 (> 30 pts)', 'top surface and edge radius', 'U', '', 'SURF_D no derivation; rest robust statistics', 'yes (r_edge 91.0 mm)', 'lid', 'flag')
add(PP, '702', 'lid resample', '3 mm', 'profile resampling', 'G', '', 'numerics', 'yes', 'lid', 'keep')
add(PP, '718', 'lid residual radius', 'r < r_edge + 15 mm', 'residual region (arch, markers)', 'U', '', 'no derivation', 'yes', 'lid', 'flag')
add(PP, '728-735', 'arch detector', 'cluster >= 100 pts; in-plane extent > 50 mm', 'which residual cluster is the arch', 'U', 'U-suspect', 'lid-specific; no derivation', 'yes (arch span 99 mm)', 'lid', 'flag')
add(PP, '755-764', 'arch sampling', 'top > 0.3, side > 0.5; 3 mm bins; >= 8 top pts; P75 height; P3-P97 width', 'arch top curve and width', 'U', '', 'no derivation (P75 choice)', 'yes', 'lid', 'flag')
add(PP, '766', 'arch width clip', '8-30 mm', 'strap width', 'U', '', 'no derivation', 'no (14.5 mm)', 'lid', 'flag')
add(PP, '770-775', 'arch thickness', 'hi part > P50(H); > 30 side pts; T = clip(2 x median depth, 3, 8 mm); else BAR_T0', 'strap thickness', 'U', '',
    'no derivation for the 3-8 mm clip', 'YES: C0 lid arch T = 3.0 mm = the lower clip', 'lid', 'flag: the clip floor decides the strap thickness; measure unclipped value or pre-register the bound')
add(PP, '776-784', 'arch smoothing / ends', 'median 3 + mean 3; ends extended 4 mm and run to the sheet mid-surface; resample 2 mm; 4000 samples for the exclusion tree', 'strap geometry', 'G', '', 'numerics; the mid-surface attachment is geometric (clean-up bug fix)', 'yes', 'lid', 'keep')
add(PP, '817', '--variant default', 'fit', 'variant', 'G', '', 'default', 'yes', o, 'keep')

# ------------------------------------------------------------------------------------------------ prim_rack.py
r = 'rack'
add(PR, '63', 'VOX', '1.5 mm', 'voxel downsample', 'G', '', 'numerics', 'yes', r, 'keep')
add(PR, '64', 'T_WALL', '2.5 mm (env PRIM_T_WALL)', 'floor plate thickness; cup-holder wall (inner/rim targets -T, -T/2); xa = xl - T; floor depth = max lip-above-cut + band - T; cavity inset', 'S', 'S-value',
    'equals the scan rack wall median (README sec. 1 "rack 2.5 mm" [D], scripts/scan_stats.py) passed in the brief ("fins ~2.5 mm thick"); rack auditor: "the floor top lands within about 0.2 mm of the scan"; clean-up kept 2.5 as grid midpoint (passed 1.5 / 2.5 / 4.0 [D])',
    'YES (h_tab, h_ft, cup wall, cavity)', r, 'REPLACE (own-observation thickness; floor never seen -> pre-registered generic grid or gmg thickness.py)')
add(PR, '65', 'CELL', '10 mm', 'lower-envelope cell for the table-cut plane', 'G', '', 'numerics', 'yes', r, 'keep')
add(PR, '66', 'VR', '0.25', 'in-plane view component deciding outer- vs inner-seen', 'G', '', 'view-geometry threshold (0.3 in lathe_obs)', 'yes', r, 'keep')
add(PR, '67', 'F_SCALE', '2 mm', 'soft_l1 robust loss scale', 'U', '', 'audit note "about stereo noise"; no own measurement recorded', 'yes (all LSQ fits)', r, 'flag')
add(PR, '68', 'PEG_SLICE', '12-35 mm above the cut', 'peg detection slice', 'U', '', 'rack-specific; written 05:22 before any scan score; no derivation', 'yes (2 rows, 7 + 6 pegs)', r, 'flag')
add(PR, '69', 'PEG_R', '14 mm', 'peg point radius around a centre', 'U', '', 'as PEG_SLICE', 'yes', r, 'flag')
add(PR, '70', 'PEG_H0', '2 mm', 'lowest peg knot', 'G', '', 'numerics', 'yes', r, 'keep')
add(PR, '71', 'PEG_KAPPA', '1.0 (round)', 'peg depth/width ratio; back of a peg never seen', 'U', '', 'shape prior; set 05:43 before any scan score; "a free depth/width ratio ... was unstable across episodes" (own observation of instability, not of the value)', 'YES (round pegs)', r, 'flag (prior on unseen shape)')
add(PR, '72', 'PEG_LEAN', 'False (upright)', 'peg lean', 'O', '', '"a free lean came out 0.04-0.4 (2-22 deg) between episodes and rows (stereo smear)" - own points, 05:46, before any scan score', 'YES (lean 0)', r, 'keep')
add(PR, '74', 'APP_D', '8 mm', 'marker residual', 'U', 'U-suspect', 'copy of prim_potlid APP_D (see there)', 'yes', r, 'as prim_potlid APP_D')
add(PR, '75', 'MK_FREE_R', '4-12 mm', 'free-fit radius that counts as a ball cap (marker_parts)', 'U', 'U-suspect', 'added 05:30 (pre-scan-score); window around the 7 mm prior the brief supplied; no derivation', 'yes (with MK_SPREAD)', r, 'replace with gmg markers.py')
add(PR, '76', 'MK_SPREAD', '0.05', 'or a cap this curved', 'U', '', 'no derivation', 'YES: the 9.51 mm ball (free_res 1.55 > 1.2) is kept only through spread 0.237 >= 0.05', r, 'replace with gmg markers.py')
add(PR, '77', 'SEG', '6', 'segments per rounded corner', 'G', '', 'tessellation', 'yes', r, 'keep')
add(PR, '78', 'S0_MIN', '4 mm', 'lower bound of the lip width s0', 'O', '', 'comment: "the lip tops seen from above span ~7-9 mm" (own points, 05:48, before any scan score); the 4 mm itself is an unexplained margin below that', 'YES: C0 s0 = 4.000 mm (at the bound)', r, 'flag: the bound decides the lip width')
add(PR, '79-82', 'CUP_LEAN', 'True (env PRIM_CUP_LEAN=1)', 'cup-holder lean and draft free (linear in h)', 'O', '',
    'clean-up round: GT-free fidelity preferred lean at every T_WALL (6.044/5.935/5.921 vs 6.242/6.116/6.138 mm); the alternative False was S-dev (set after diag_regions [D], ' + E_RACKSCAN + ')', 'yes (ux -0.052, uy 0.157)', r, 'keep')
add(PR, '324-357', 'cup_upright()', 'band H_r + 5 mm .. top - 5 mm; |n| > 0.8; >30 pts; r search 4 mm step 2 mm; error cap 4 mm, window 12 mm', 'upright cup estimator (only when CUP_LEAN False)', 'S', 'S-dev', 'written 05:54-05:57 right after the scan cup-holder extents were printed (' + E_RACKSCAN + ')', 'no (C0 uses lean)', r, 'leave unused; never select it')
add(PR, '83', 'JOINT_TOL', '1.25', 'episodes enter the joint fit if own full-fit fidelity <= 1.25 x best', 'U', '', 'set 05:46 before any scan score; no derivation', 'YES (joint = eps 12, 13, 27; first run ep26 7.802 vs cut 7.759)', r, 'flag; sensitivity is real (ep26 near the cut)')
add(PR, '91', 'band fallback', '8 mm', 'table band if the npz has no args', 'G', '', 'mirrors the obs_points default', 'no (args present)', r, 'keep')
add(PR, '98-120', 'lower_plane', 'P2 per cell; >= 20 pts/cell; lowest 30 % + 3 mm; 10 refits; 4 iterations', 'table-cut plane', 'U', '', 'robust-estimation choices; 30 % / 3 mm no derivation', 'yes', r, 'flag (low risk)')
add(PR, '136-137', 'joint offset', 'P2 per cell, P15 of the cell lows', 'cut offset under a fixed normal (joint fit)', 'U', '', 'no derivation', 'yes (joint)', r, 'flag (low risk)')
add(PR, '197-201', 'find_cup', 'tall = h > 0.65 x P99.8; P1/P99; P0.5/P99.5', 'which end holds the cup holder', 'U', '', 'rack-specific; no derivation', 'yes (insensitive: cup holder is the only tall part)', r, 'keep')
add(PR, '204-238', 'lip sampling', '12 mm edge bands; 10 mm segments; >= 50 / >= 30 pts; P98 height; plane: 5 iterations, 3 mm inliers', 'lip-top samples and lip plane', 'U', '', 'no derivation', 'yes (78 segments, sd 1.0 mm)', r, 'flag')
add(PR, '247-249', 'outline init', 'x > x0 + 30 mm; init rc 15 mm, s0 8 mm, s1 0.3', 'tray outline start values', 'U', '', 'init only; s0 8 mm matches the own-observed 7-9 mm lip', 'init only', r, 'keep')
add(PR, '264-267', 'outline point classes', 'near band -35..+15 mm; outer h 3 mm..H_r - 6 mm, |res| < 8 mm; inner h > 6 mm; lip H_r - 3..+4 mm, sd -20..+6 mm', 'which points enter the outline LSQ', 'U', '', 'no derivation', 'yes (21701 / 25541 / 9789 points)', r, 'flag')
add(PR, '271,309,453', 'LSQ subsamples', '60000 / 60000 / 40000, seeds it / it / 0', 'subsampling', 'G', '', 'numerics', 'yes', r, 'keep')
add(PR, '279-280', 'outline bounds', 'theta +-0.2 rad; so1 -0.3..1; hy 30-150 mm; rc 2-60 mm; s0 S0_MIN..30 mm; s1 0..1.5', 'tray outline parameter bounds', 'U', '', 'rack-size bounds, no derivation; brief carried the scan rack size (51 x 18 x 12 cm)', 'YES: s0 at 4 mm and s1 at 0 (bounds); others interior', r, 'flag (s1 = 0 means the sloped inner face is not identified)')
add(PR, '297-306', 'cup point classes', '|sd| < 12 mm; h < top + 4 mm; upper h > H_r + 4 mm; |n.up| < 0.7; outer sd > -6 mm; inner sd < 3 mm; below-lip inner from iteration 2: h > h_ft + 4 mm, -T_WALL - 8 mm < sd < -T_WALL + 3 mm; rim h >= top - 3 mm', 'cup-holder LSQ classes', 'U', '', 'no derivation; inner class tied to T_WALL', 'yes (32754 points)', r, 'flag; T_WALL part replaced with T_WALL')
add(PR, '316-318', 'cup bounds', 'lean/draft +-0.25; ex 10-80 mm; ey 10-120 mm; r 4-50 mm', 'cup-holder parameter bounds', 'U', '', 'rack-size bounds, no derivation', 'no (C0 values interior)', r, 'flag')
add(PR, '363-370', 'cup region / top', 'x < xr + 12 mm; top = median over 2 cm y-bands of P99 (> 30 pts above H_r); tall h > H_r + 10 mm; init r 20 mm', 'cup-holder region and top', 'U', '', 'no derivation', 'yes (top 105.1 mm)', r, 'flag')
add(PR, '382-383', 'cup inner floor', 'sd < -T_WALL - 4 mm; n.up > 0.85; h_ft < h < H_r; >= 50 pts else tray floor h_ft', 'cup-holder inner floor', 'U', '', 'no derivation', 'YES: n_floor 43 < 50 -> h_cf = h_ft (tray floor, which depends on T_WALL)', r, 'flag')
add(PR, '391-418', 'detect_pegs', '2 mm grid; >= 3 pts/cell; closing; blobs 10-150 cells; >= 100 slice pts; rows dy < 12 mm; >= 3 pegs', 'peg centres and rows', 'U', '', 'rack-specific; no derivation', 'yes', r, 'flag')
add(PR, '421-475', 'fit_peg_row', 'knots every 6 mm; query PEG_R + 4 / + 30 mm; >= 200 pts; P99 tops (> 30 pts); init a 6 mm; a 1-20 mm (floor 0.8 mm); centres +-8 mm; 2 rounds', 'peg template', 'U', '', 'no derivation', 'yes (a 9.4 -> 3.4 mm, H_p 51 / 48 mm)', r, 'flag')
add(PR, '607', 'normals k', '24', 'PCA normals', 'G', '', 'numerics', 'yes', r, 'keep')
add(PR, '608-613', 'tray x0 offsets', 'H_r and lip plane from x > xh + 15 mm; outline from x > xh + 10 mm (+30 mm inside fit_outline)', 'where the tray starts', 'U', '', 'no derivation', 'yes', r, 'flag')
add(PR, '626-627, 803', 'floor placement', 'h_ft = H_r - depth; depth = max over episodes of lip-above-cut + band - T_WALL; h_tab = h_ft - T_WALL', 'never-seen floor', 'O', '', 'geometric: no floor point is ever seen, the floor lies under the deepest cut (band = obs_points table_band); the T_WALL terms are S-value (see T_WALL)', 'YES (depth 33.2 mm)', r, 'keep rule; replace T_WALL')
add(PR, '636-642', 'peg gates', 'inside: sd < -(s(h) + 10 mm) and x > cup face + 6 mm; ok: inside or h > H_r + 2 mm; row kept only if H_p > H_r + 8 mm', 'which blobs are pegs', 'U', '', 'no derivation', 'yes', r, 'flag')
add(PR, '505-538', 'build_body', 'so1 floor -0.2; basin top H_r + 10 mm; inset radius floor 2 mm; cavity top + 10 mm; peg base h_ft - 1 mm; peg ring 16 segments, radius floor 0.8 mm', 'solid construction', 'G', '', 'construction numerics (overlaps for the union)', 'yes', r, 'keep')
add(PR, '573-582', 'marker_parts', 'free_r in MK_FREE_R and free_res <= 1.2 mm, or spread >= MK_SPREAD; sphere 20 segments', 'cap evidence for accepted balls', 'U', 'U-suspect', 'see MK_FREE_R', 'yes', r, 'replace with gmg markers.py')
add(PR, '666-669', 'rack residual', '200000 surface samples (seed 0); outside and d > APP_D', 'marker residual set', 'G', '', 'numerics (APP_D see above)', 'yes', r, 'keep')
add(PR, '675-682', 'in_basin rule', 'reject a ball whose centre is inside the inner face (sd < -s0) and right of the cup face', 'markers over the basin are treated as residuals', 'U', 'U-suspect',
    'added 06:03 after the first scan scores (05:51) and the [D] region diagnostic (05:52-05:53); stated reason GT-free ("after seeing 8 balls"); rack auditor: GT-free fidelity preferred the version without it (6.089 vs 6.116 mm), [D] it traded ADD 5.9 -> 6.4 for CD-O 0.463 -> 0.454',
    'YES: 9 candidate balls rejected in the C0 joint record (2 kept)', r, 'flag; decide in the C0b PREREG with a GT-free reason, or test both by fidelity')
add(PR, '703-721', 'icp_align', '30 iterations; trim P80; stop |t| < 1e-6 m', 'joint episode alignment', 'G', '', 'numerics', 'yes (12/13/27 aligned, <= 0.6 deg)', r, 'keep')
add(PR, '748-751', 'joint reference', 'episode with most points; 60000 subsamples (seed 0); up = mean of aligned cut normals', 'joint fit frame', 'G', '', 'numerics / geometry', 'yes', r, 'keep')
add(PR, '841', 'rack selection', 'min fid_sum over 12 candidates', 'GT-free pick (pre-registered 27 Oct)', 'O', '', 'obs_fidelity on our points', 'yes (joint)', r, 'keep')
add(PR, '865', '--episodes default', '12,13,26,27,31', 'public rack episodes', 'G', '', 'all public rack episodes', 'yes', r, 'eval list for E0b')

# ------------------------------------------------------------------------------------------------ lathe_obs.py
c = 'cup'
add(LO, '27, 205', 'DH (--dh)', '3 mm', 'height bin', 'G', '', 'binning', 'yes', c, 'keep')
add(LO, '28, 150-153', 'TIE', '1.25', 'axis candidates within 1.25 x best rotational consistency are near-ties; the one closest to the opening direction wins', 'U', 'U-suspect', 'set 16:08:59 inside the scan-scored loop (' + E_LATHELOOP + '); no derivation',
    'no [M]: for the C0 cup the pick is the best-consistency axis itself (2.196 mm); TIE 1.1 / 1.5 / 2.0 give the same axis (scripts/tiecheck.py)', c, 'keep (shown not binding); flag')
add(LO, '29', 'NSEC', '24', 'sectors', 'G', '', 'binning', 'yes', c, 'keep')
add(LO, '46, 206', 'sector_stat q / --min_pts', '50 / 8', 'per-cell median, min points', 'G', '', 'statistics', 'yes', c, 'keep')
add(LO, '60, 207', 'normals k (--knn)', '24', 'PCA normals', 'G', '', 'numerics', 'yes', c, 'keep')
add(LO, '82-95', 'IRLS', 'Cauchy scale 1.5 x median |res| (over w > 5 % of max), floor 0.1 mm; 8 / 6 iterations', 'line-complex axis fit', 'G', '', 'robust statistics (Pottmann & Randrup line complex)', 'yes', c, 'keep')
add(LO, '99', 'rot_consistency', 'angles 45/90/135 deg; trim 0.8', 'axis score', 'G', '', 'numerics', 'yes', c, 'keep')
add(LO, '114-141', 'fit_axis candidates', '6 k-means clusters (seed 0), > 500 pts; inside-facing > 100 pts; 20000 subsample (seed 1)', 'axis candidate set', 'G', '', 'numerics', 'yes (14 candidates)', c, 'keep')
add(LO, '157', 'smooth_fill win', '5 bins', 'profile gap fill + median', 'G', '', 'numerics', 'yes', c, 'keep')
add(LO, '166', 'revolve nseg', '96', 'tessellation', 'G', '', 'numerics', 'yes', c, 'keep')
add(LO, '197', '--solid', '0', 'hollow lathe', 'O', '', 'thin walls seen from both sides (inner/outer classes)', 'yes', c, 'keep')
add(LO, '198, 290-293', '--app_d', '4 mm', 'points beyond the profile by > 4 mm are appendage points', 'U', '', 'no derivation; differs from prim_potlid APP_D 8 mm', 'YES (3372 appendage points -> 4 parts)', c, 'flag; own-noise-based OPTION as for APP_D')
add(LO, '199, 306', '--app_min', '400 points', 'minimum appendage group', 'U', '', 'no derivation', 'yes', c, 'flag')
add(LO, '199', '--spheres', '0', 'documented "fit markers as spheres" option; never read by the code (dead flag)', 'G', '', 'code defect, no effect', 'no', c, 'note')
add(LO, '200, 212', '--vox_ds', '1.5 mm', 'voxel downsample', 'G', '', 'numerics', 'yes', c, 'keep')
add(LO, '200, 245, 249', '--tmin', '1.5 mm', 'lower bound of the wall t; inner radius <= outer - tmin', 'U', 'U-suspect', 'written 15:51 after scan_stats.py (15:33) showed scan walls 1.8-3.9 mm; no derivation', 'no for t (C0 t_meas 1.965 mm); the ri <= ro - tmin clamp not measured', c, 'flag; own-noise-based lower bound OPTION')
add(LO, '201-203', '--floor / --gap', 'base / 3', '"observed" mode: cavity only as deep as the inner wall was seen ("a scanner sees about as far in")', 'S', 'S-dev', 'added 16:00:27 together with area_prof.py [D] on the scan; default stays base', 'no (default base)', c, 'never select "observed" in C0b')
add(LO, '204, 229-230', '--minsec', '6', 'sectors needed per height bin', 'O', '', 'see prim_potlid MINSEC (same 16:11 edit, own sector counts)', 'yes', c, 'keep (flag loop)')
add(LO, '215', 'axis subsample', '60000 (seed 0)', 'points for fit_axis', 'G', '', 'numerics', 'yes', c, 'keep')
add(LO, '222', 'view split', '|vr| > 0.3', 'outer/inner/cap classes', 'G', '', 'view geometry', 'yes', c, 'keep')
add(LO, '236-237', 'body extent', 'r < max r_out + 5 mm; P0.5 / P99.5 of h', 'axial extent excluding the handle', 'O', '', 'same 16:11 edit, motivated by own pot sector table; 5 mm margin no derivation', 'yes (height 163.6 mm)', c, 'keep (flag)')
add(LO, '240', 'open-end vote', '>= 50 % of inner-wall bins above mid-height', 'which end is open', 'G', '', 'majority vote', 'yes (open_top false -> flipped)', c, 'keep')
add(LO, '244', 'wall fallback', '3 mm when < 3 two-wall bins', 'wall thickness without evidence', 'S', 'S-value', 'docstring of the same 15:51 write: "the TSDF mesher turns the 3 mm walls into 12-20 mm slabs" - the 3 mm walls are the scan walls measured 15:33 (cups 2.4-3.2 mm, README sec. 1)', 'no (C0 cup: 33 two-wall bins, t 1.965 mm)', c, 'REPLACE for eval builds (own thickness or fail)')
add(LO, '246-249', 'profile smoothing', 'smooth_fill on outer / inner; ri = min(.., ro - tmin)', 'profiles', 'G', '', 'numerics', 'yes', c, 'keep')
add(LO, '251', 'cap-in margin', 'r < ri - 3 mm', 'cap points inside the cavity (floor evidence)', 'U', '', 'no derivation', 'yes (267 points)', c, 'flag')
add(LO, '252-259', 'floor rule', 'floor raised only by a dense (> 200 pts) thin (q90 - q10 < 10 mm) layer in the lower 40 % of the height; else floor = base + t', 'cavity depth', 'S', 'S-dev',
    'introduced 15:56:38, 54 s after a [D] plot of the scan section over the a0 lathe (prof_plot2.py 15:55:44) and after a0/a1 scan scores (15:54); replaced "any > 50 cap points -> P5 height" (' + E_LATHELOOP + ')',
    'YES in structure [M, scripts/floorcheck.py]: C0 cup floor = base + t; the pre-15:56 rule would put the floor 106.9 mm above the base. The numbers do not bind: fractions 0.3-0.6 keep 2 points, 0.8 keeps 43, all < 200', c, 'decide in the C0b PREREG: keep the rule with a GT-free reason (a cup has a floor ~t thick; sparse cap points are not a floor) and record its S-dev origin; or flag the cup')
add(LO, '296-310', 'appendage splat', '2 mm voxels; pad 3; dilation 1; closing 2; Gaussian 0.7 voxel; iso 0.5', 'appendage meshes', 'U', '', 'no derivation for the morphology', 'YES (4 appendage bodies)', c, 'flag')

# ------------------------------------------------------------------------------------------------ obs_points.py
a = 'pot,lid,rack,cup'
add(OP, '32, 56', '--roi', 'meshes/library_v3/<obj>.glb (bounds + margin)', 'box that crops the depth samples', 'S', 'S-input', E_DENY + '; docstring: "any mesh of ours or a box size works"', 'yes (box only; cuts nothing of the object if the library mesh is about the right size - not measured)', a, 'REPLACE: a fixed box around the track origin (recon_mesh uses +-30 cm) or a box from our own detection')
add(OP, '33, 50-55, 106-110', '--others', 'meshes/library_v3/<other>.glb posed by our tracks', 'drops samples within other_r of a co-object', 'S', 'S-input', E_DENY, 'yes: lid ep2 (pot), rack ep12/13 (blue cup), rack ep27 (pot), cup ep21 (pitcher); pot ep41 none', 'lid,rack,cup', 'REPLACE: co-objects from our own points (gmg extract_joint ownership) or C0b meshes; or drop')
add(OP, '33', '--other_r', '12 mm', 'co-object exclusion radius', 'U', '', 'recon_mesh v1 (21 Oct, f9e04f2) default; v1 posed the SCANS as others; value never derived', 'yes (lid next to pot)', 'lid,rack,cup', 'flag')
add(OP, '34', '--stride', '2', 'frame stride', 'G', '', 'compute', 'yes', a, 'keep')
add(OP, '34, 56', '--margin', '20 mm', 'ROI margin', 'G', '', 'box padding', 'yes', a, 'keep (with a new ROI)')
add(OP, '35, 64, 70', '--edge_thr', '20 mm (5 x 5 max - min)', 'depth-edge (flying pixel) filter', 'U', '', 'recon_mesh v4 (21 Oct): value set once; switching it on/off was judged by registered AUC with the scans [D] ("mixed")', 'yes', a, 'flag (low risk)')
add(OP, '35, 84', '--zmax; depth > 5 cm', '1.5 m; 0.05 m', 'valid depth range', 'G', '', 'sensor range', 'yes', a, 'keep')
add(OP, '36, 99, 129', '--table_band', '8 mm', 'samples within 8 mm above the table plane are dropped (bottom 8 mm of a resting object is never seen)', 'U', 'U-suspect',
    'obs_points written 26 Oct 15:41, 8 min after scan_stats.py; recon_mesh uses 15 mm; no derivation for 8. prim_rack places the table at -band (exact whatever the value); lathe_obs / prim_potlid bases sit at the lowest observed point', 'yes (cut height of resting objects; rack floor depth includes it)', a, 'flag; pre-register; test 2 values')
add(OP, '37-38', '--hand_r, --arm_r, --arm_len', '30 mm, 45 mm, 150 mm', 'hand-bone and forearm capsules that drop samples', 'G', '', 'body-scale priors (recon_mesh v0, 21 Oct); the scans contain no hands, so no scan origin is possible', 'yes (where hands exist; rack ep12/27 have none)', a, 'keep')
add(OP, '39-41', '--vox, --hit, --free, --min_hits, --min_ratio', '4 mm, 4 mm, 10 mm, 3, 0.5', 'free-space vote: keep samples whose voxel was hit >= 3 times and >= 50 % of hits+free', 'U', '', 'no derivation (4 mm mirrors the TSDF voxel; 10 mm ~ the 12 mm truncation)', 'yes (cup kept 93 %)', a, 'flag (low risk)')
add(OP, '42', '--pix_stride', '1', 'pixel stride', 'G', '', 'compute', 'yes', a, 'keep')
add(OP, '75', 'ROI near camera', 'skip frame if a box corner is < 5 cm in front of the camera', 'projection guard', 'G', '', 'numerics', 'rare', a, 'keep')
add(OP, '87-96', 'per-frame table refit', 'inliers within 30 mm then 12 mm; >= 500 samples; subsample to 20000; accept if within 10 deg', 'table plane per frame', 'U', '', 'recon_mesh v2 (21 Oct) fix for the ep39 dust pan, developed in a loop scored by registered AUC with the scans [D]; values set once', 'yes', a, 'flag (low risk)')

# ------------------------------------------------------------------------------------------------ recon_mesh helpers
add(RM, '20-30', 'rectified_K', 'input 1280 x 800; output 1600 x 1000; alpha 0; CALIB_ZERO_DISPARITY; ego_cam_c / ego_cam_b', 'rectified intrinsics matching the depth cache', 'G', '', 'dataset calibration + rectification convention of the depth cache', 'yes', a, 'keep')
add(RM, '33-56', 'hand_segments', 'MediaPipe 21-joint bones; forearm from the wrist away from the middle knuckle (J0 - J9)', 'hand capsule geometry', 'G', '', 'hand model topology', 'yes', a, 'keep')
add(RM, '58-67', 'table_plane sampling', 'every 4th pixel; depth 0.2-1.5 m; 1500 RANSAC iterations; seed 0; least-squares refit', 'frame-0 support plane', 'G', '', 'numerics / sensor range', 'yes', a, 'keep')
add(RM, '58', 'table_plane thr', '6 mm', 'RANSAC inlier distance', 'U', '', 'recon_mesh v0 (85fbda1) default; no derivation', 'yes', a, 'flag (low risk)')
add(RM, '58', 'table_plane hmin, hmax', '-5 cm .. +30 cm under the object origin', 'which plane may be the table', 'O', '', 'docstring: the floor (~1 m down) was otherwise picked (2026-10-20 mkref bug)', 'yes', a, 'keep')
add(RM, '58', 'table_plane cone', '65 deg from camera up', 'admissible table normals', 'O', '', '45 -> 65 on 21 Oct (3946ba2): "the table normal is 48-50 deg from camera up in ep39/ep40" (own measurement; the failure was found through scan scoring)', 'yes', a, 'keep')

# ------------------------------------------------------------------------------------------------ obs_fidelity.py
add(OF, '11', 'trim', '0.9 (hard-coded; --trim ignored)', 'trimmed mean in both directions', 'G', '', 'robust statistic; set once (26 Oct 16:28)', 'yes (every selection)', 'all', 'keep; fix docstring (--trim, --icp are not implemented)')
add(OF, '13, 19', 'samples', '300 k observed points (seed 0); 200 k mesh samples (seed 0)', 'fidelity sampling', 'G', '', 'numerics', 'yes', 'all', 'keep')
add(OF, '14, 21', 'AABB gate', 'mesh samples inside the observations\' bounding box', 'mesh->obs counts only where we looked', 'G', '', 'design', 'yes', 'all', 'keep')
add(OF, 'whole file', 'selector design (blue cup)', 'sum of the two trimmed means; lowest wins', 'blue-cup episode / variant pick', 'S', 'S-dev',
    'written 26 Oct 16:28, after the five blue-cup lathes were scored on the scan; it picks the CD-O winner (README sec. 4; C0 flag F3). For pot, lid, rack the same selector was pre-registered on 27 Oct before their scorings', 'yes (picked ep21 g1)', 'cup', 'C0b: pre-register the selection (as the brief says)')

# ------------------------------------------------------------------------------------------------ C0 command lines / inputs
add('results/prim/potlid/run_fit.sh, select.py', '-', 'pot build + pick', 'prim_potlid.py pot obs_all/ep41_white_pot.npz --variant fit --lib library_v3/white_pot.glb --axis_cache ...; pick = min obs_fidelity sum over 32 candidates (8 episodes x fit/nostem/tsdf/thick) on all 8 episodes\' points', 'C0 pot', 'O', '',
    'pre-registered 27 Oct (work log); ep41 fit 3.035 vs ep41 tsdf 3.044 mm (margin 0.009 mm)', 'yes', 'pot', 'C0b: same rule, without the tsdf variant if library_v3 is dropped')
add('results/prim/clean (work log 27 Oct)', '-', 'lid build + pick', 'PRIM_T_LID=0.0025 prim_potlid.py lid obs_all/ep2_white_pot_lid.npz --variant fit --lib library_v3/white_pot_lid.glb; fit vs tsdf by fidelity (1.686 vs 1.913 mm)', 'C0 lid', 'S', 'S-value', 'the env value is T_LID (see there); variant pick is O', 'yes', 'lid', 'REPLACE T_LID')
add('results/prim/clean/run_rack.sh', '-', 'rack build + pick', 'PRIM_T_WALL=0.0025 PRIM_CUP_LEAN=1 prim_rack.py run --obs_dir obs_all --out ... (episodes 12,13,26,27,31); pick = joint (fid 5.935 mm); lean chosen by fidelity', 'C0 rack', 'S', 'S-value', 'the env value is T_WALL (see there); lean and variant picks are O', 'yes', 'rack', 'REPLACE T_WALL')
add('C1/T1-beige-lathe/NOTES.md 15:27; E0 NOTES 16:24', '-', 'blue-cup build', 'lathe_obs.py obs/ep21_blue_cup.npz (all defaults = g1), byte-identical rebuild [M]', 'C0 cup', 'O', '', 'defaults audited above', 'yes', 'cup', 'see lathe_obs rows')
add('scripts/prep_obs.sh; obs npz args', '-', 'obs_points command lines', 'all obs_points defaults (stride 2, vox 4 mm, hit 4 mm, free 10 mm, table_band 8 mm, other_r 12 mm, edge 20 mm, hands 30/45/150 mm, margin 20 mm); --roi/--others library_v3', 'C0 observed points', 'S', 'S-input', 'npz "args" of obs_all/ep41_white_pot, ep2_white_pot_lid, ep12/13/27_plastic_dish_rack and obs/ep21_blue_cup [M]', 'yes', a, 'see obs_points rows')
add('scripts/prep_obs.sh; obs/ep21 args', '-', 'tracks (--poses)', 'pot/lid/rack: store run 20261025-sweep-a894083 base tracks; cup: data/store/ep21 perc2m own-mesh tracks; eval (E0): 20261025-evperc-4f596df', 'object frame of the observed points', 'U', '',
    'perception seeded with our library meshes (library_v2/v3 = tier P1, ledger sec. 1); not a scan read, but the library itself was fused along scan-templated tracks (C0 flag F4, open organiser question). Needed: the pack poses are these tracks', 'yes (frame)', a, 'owner/organiser question F4; not a constant')
add('scripts/prep_obs.sh', '-', 'hands', 'G1 refs (store 20261025-g1-022fece) MediaPipe hands.npz where stored; none for rack ep12/27', 'hand capsules', 'G', '', 'MediaPipe on our video', 'yes', a, 'keep')
add('kit v2dlb/mesh_budget.py', '-', 'budget_mesh', '4096 faces, 4096 vertices (fast_simplification 0.2.0)', 'packing decimation', 'G', '', 'organiser kit', 'yes (packing)', a, 'keep')


def counts():
    from collections import Counter
    return dict(Counter(x['origin'] for x in R)), dict(Counter(x['sub'] for x in R if x['sub']))


def md_table(rows):
    out = ['| # | file:line | name | value | controls | origin | evidence | binds in C0 [M] | C0b action |',
           '|---|---|---|---|---|---|---|---|---|']
    for x in rows:
        org = x['origin'] + (f" ({x['sub']})" if x['sub'] else '')
        cells = [str(x['id']), f"{x['file'].split('/')[-1]}:{x['line']}", x['name'], x['value'], x['controls'], org,
                 x['evidence'], x['c0_binding'], x['action']]
        out.append('| ' + ' | '.join(str(cl).replace('|', '/').replace('\n', ' ') for cl in cells) + ' |')
    return '\n'.join(out)


def main():
    oc, sc = counts()
    meta = dict(written='2026-10-31', scope='constants, priors, windows, thresholds and defaults of prim_potlid.py, '
                'prim_rack.py, lathe_obs.py, obs_points.py, obs_fidelity.py, the pipeline/recon_mesh.py helpers they '
                'use, and the command lines / inputs that built the C0 pot, lid, rack and blue cup',
                origin_counts=oc, sub_counts=sc, ground_truth_read='none (scripts/floorcheck.py and tiecheck.py read '
                'only our observed points)', classes=__doc__)
    json.dump(dict(meta=meta, items=R), open(os.path.join(ROOT, 'AUDIT.json'), 'w'), indent=1)
    md = os.path.join(ROOT, 'AUDIT.md')
    s = open(md).read()
    groups = [('prim_potlid.py', PP), ('prim_rack.py', PR), ('lathe_obs.py', LO), ('obs_points.py', OP),
              ('pipeline/recon_mesh.py (helpers used by obs_points.py)', RM), ('obs_fidelity.py', OF)]
    parts = []
    for title, f in groups:
        parts.append(f'### {title}\n\n' + md_table([x for x in R if x['file'] == f]))
    parts.append('### C0 command lines and inputs\n\n' + md_table([x for x in R if x['file'] not in dict(groups).values()
                                                                   and x['file'] not in (PP, PR, LO, OP, RM, OF)]))
    a, b = '<!-- AUTO:TABLES -->', '<!-- /AUTO:TABLES -->'
    i, j = s.index(a) + len(a), s.index(b)
    s = s[:i] + '\n' + '\n\n'.join(parts) + '\n' + s[j:]
    open(md, 'w').write(s)
    print(json.dumps(dict(items=len(R), origin=oc, sub=sc)))


if __name__ == '__main__':
    main()
