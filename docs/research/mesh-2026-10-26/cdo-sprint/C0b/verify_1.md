# C0b / E0b verification 1 (lens: FRAME, KIT, BYTES)

Status: IN PROGRESS (resume file for this verifier; final version replaces this line).

## Progress log
- 2026-10-31T22:29Z start; read NOTES tail, STATUS head. Library md5 listing done (scratch v1c0b).
- 22:33Z [M] MANIFEST_E0b byte check: 36 pairs, every mesh sha256/md5/bytes equals the file and its source; 8 swapped; ep8 -> e0bx only. library_e0b vs v3 and e0bx vs v3x: only white_pot.glb and beige_cup.glb differ; sidecars (*.recon.json, v3x beige_cup.v5.json) dropped, as library_e0 / e0x did. Ball radii on shipped files = detections within 0.001 mm (pots) / 0.008 mm (rack); all balls exposed; E0b pot 1 body, C0b pot 2 bodies (1 floating ball), rack 6 (5 floating balls). Frame/kit script running (scratch v1c0b/frame_kit.py).
- 22:47Z [M] scored/guarded sha = committed C0b picks (sha1_16 and sha256). GLB headers: 1 node, no transform, POSITION only (library_v3 also carries COLOR_0; library_c0 / e0 did not). Kit on library_v3 (raw / budget): pot 1 body / 6 bodies not watertight; beige 2 / 2 watertight; v3x beige 2 / 2 watertight; rack 5 / 10; blue 2 / 6; lid 1 / 1 watertight (scratch v1c0b/kitlib.json). frame_kit restarted (first try died silently) as a background task.
