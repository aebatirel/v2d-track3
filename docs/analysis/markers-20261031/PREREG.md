# Pre-registration: GT-free marker correction layer (markers-20261031)

Written before any public object track corrected by this layer is scored against mocap. Ground truth (public mocap,
the `pose` field of `observation.objects`, public scans) is read ONLY by `pubscore.py`, after inference. Layouts come
from our own video + our own tracks (`census.py`), never from the scan catalogue of note 17 §A1.

## Block 1 — rule (2026-10-31 18:52 UTC)

**Units.** (public episode, object) pairs for the marker-bearing objects with mocap: white_pot (eps 0, 2, 26, 27,
41–45), white_pot_lid (0, 2), blue_cup (11, 12, 13, 21, 22), beige_cup (11), plastic_dish_rack (12, 13, 26, 27, 31),
water_pitcher (21, 22), mini_sweeper (18, 31), wooden_piece_1 / wooden_piece_2 (23, 24).
**Eligibility (GT-free, decided before scoring).** An object is tested when its layout discovery (pooled over its
public episodes) gives >= 3 markers and the stereo shape fit has median residual <= 3 mm. A unit is tested when its
object is eligible and the unit has >= 1 accepted fix. Non-eligible objects and units are listed, not scored into the rule.
**Tracks.** The 25 Oct public perc2 tracks (`runs/20261025-sweep-a894083`, `runs/20261025-guard-fe3f407`), library_v2/v3
templates, VO world. Baseline = these tracks as they are; candidate = the same tracks with every eligible object of
the episode corrected by `correct.py` (primary variant: gate + outlier rejection + 9-frame smoothing + carry + static
vote with abstain).
**Metric.** Kit Track 3 registered chain (`docs/analysis/rpe-decomp-20261031/rdlib.py`: kit registration of our
library_v3 mesh onto the public scan stand-in, frame-0 scene alignment, kit metric functions). Primary: per-object
AUC (`obj_AUC`) of the unit in its episode. Secondary (reported, not in the rule): episode AUC, RPE, MPPE.
**PASS** if all three hold over the tested units:
1. mean ΔAUC (candidate − baseline) >= +0.010;
2. >= 60 % of units improve (ΔAUC > 0);
3. no unit worse by more than 0.020.
Otherwise FAIL. Variants (no vote, no carry) are reported as secondary and do not decide.
**Eval consequence.** Only on PASS would the same layer be proposed for the eval spoon tracks; no eval reference or
pack is changed by this work in any case.

## Block 2 — method frozen, eligibility and units fixed (2026-10-31 19:38 UTC, before any public score)

No public track corrected by this layer has been scored yet; `pubscore.py` has not been run.

**Method (frozen; sha256 prefixes of the scripts in this folder):** mlib.py e23b5f5c, detect.py 2b1e7db4, scan.py
ed51a773, mklayout.py 96415b78, census.py ba9a5943, guided.py 13e6b1cc, correct.py c082546b, apply.py 54255fe2,
run_obj.sh 197d45f0, pubscore.py 925e48e6. Parameters as in the code: detector (visible radius 5.8 mm, 3-D radius
3.8–8.0 mm, support 0.35, interior sd 12, black-base contrast 30; guided pass 0.30 / 20 / 10 in 12 mm windows around
fixed poses and 30 mm around the track); layout-consistent sets (distance tol 7 mm, prior gate 5 cm / 30°); layout
pooled over the object's episodes in our tracks' body frame (free discovery for public objects: clusters with a
3-D radius >= 4.6 mm seen in >= 2 episodes; spoon: template labels, layout re-measured), placement from complete
sets; correction (2-marker weight 0.4, gate 3 cm / 20°, outlier 15 mm / 8°, 9-frame smoothing, carry across gaps
<= 60 frames else hold <= 15 frames, static vote: segments >= 10 frames, 5° clusters, >= 4 votes and >= 2x runner-up).
A cross-episode registration variant (`consensus.py`) was tried GT-free and dropped before scoring (3-point
registrations gave implausible offsets such as a 175° flip of pot ep42).

**Eligibility outcome (GT-free, block-1 rule: >= 3 pooled markers and stereo shape fit median <= 3 mm):**
- eligible: white_pot (3 markers, fit 1.99 mm), white_pot_lid (3, 1.00 mm), blue_cup (4, 1.13 mm);
- not eligible: plastic_dish_rack (2 markers), beige_cup (2), wooden_piece_1 (0), wooden_piece_2 (0),
  water_pitcher (0), mini_sweeper (0). They stay as tracked in every variant.

**Units (16; each has >= 1 accepted fix):** white_pot eps 0, 2, 26, 27, 41, 42, 43, 44, 45; white_pot_lid eps 0, 2;
blue_cup eps 11, 12, 13, 21, 22. Rule unchanged from block 1 (mean ΔAUC >= +0.010, >= 60 % of units improve, no unit
worse than −0.020; primary variant decides; per-object kit AUC).

## Block 3 — outcome (2026-10-31 19:40 UTC, after `pubscore.py`; `data/pubscore.json`, `public_validation.json`)

**FAIL.** Primary variant over the 16 units: mean ΔAUC **−0.083** (rule >= +0.010), **1/16** improved (rule >= 60 %),
worst **−0.407** (white_pot_lid ep2, rule >= −0.020). All secondary variants fail too: novote −0.080 (1/16),
nocarry −0.041 (2/16), fused −0.039 (1/16, worst −0.088). The layer is not adopted; no eval use follows.
