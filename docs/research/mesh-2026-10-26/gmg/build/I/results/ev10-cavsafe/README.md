# ev10-cavsafe: cavity-safe eval-10 cup pieces (candidate, measured; IN PROGRESS)

1 Nov 2026, CPU, $0. Status at 03:07 UTC. The full report replaces this note when the measures are done.

- **Pieces:** `ev10cs/`, laid out exactly like `meshes/carve/ev10`:
  - `blue_cup/` 53 pieces and `beige_cup/` 49 pieces, each with `inertia.json` and `lathe_collision.json`;
  - `carve.json` at the top.
  - Use: `pipeline/make_assets.py meshes/library_v3 OUT --pieces <this folder>/ev10cs`. Tested: it writes 53 / 49
    `<collision>` elements.
- **Pairs with** the packed eval-10 reference:
  - `runs/20261026-gl10A2-5e0e100/refs/glockt/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave/ref_gl_ilc.parquet`;
  - md5 `1a5003d94852c275519066645a1b9869`, as listed in focused-pascal's `packed_refs.json`;
  - visual meshes `meshes/library_v3/{blue_cup,beige_cup}.glb`.
- **Critical frames:**
  - f124-f160, the nested hands-off rest (all 37 frames have no hand-contact label);
  - pair-scene gate frames f111, f142, f116;
  - determined-wright's explicit frames f0, f124, f142, f160.
- **Gates** (`GATES.md`, written before any candidate number) [M]:
  - Gate 1, piece overlap f124-f160: median 1.92 cm3, max 6.82 cm3 against 11.86 / 32.67 for packed ev10. **FAIL**
    (the gate is <= 1.0 / 3.0).
  - Gate 2, plain-MuJoCo pair scene: max nefc 936, ncon 234, overflow in 40 / 48 copies, against 1,296 / 324, 48 / 48.
    **FAIL**.
  - Gate 3, cavity intrusion: 0.0 cm3. The depth is being re-measured after a floor-plane correction.
  - Gate 4a, piece volume / visual volume: blue 0.325 **FAIL**, beige 1.67 pass.
