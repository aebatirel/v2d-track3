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
