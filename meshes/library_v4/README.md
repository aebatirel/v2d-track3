# Mesh library v4 (2026-10-22, experimental, not yet validated on GPU)

`library_v3` (flattened sweeper underside) plus the two ep24 planter boards with one edge flattened by
`pipeline/flatten_base.py --depth 0.008` along the world up of our own ep24 reference at a standing frame
(`wooden_piece_1 --frame 150`, `wooden_piece_2 --frame 250`; `*.flatten.json`). Reason: in our ep24 reference both
boards stand on an edge (assembling the planter), but our reconstructed edges are rounded (the cameras see the faces,
not the edges): no stable standing pose existed (board 1: 0.1 cm^2 within 2 mm, centre of mass 89 mm outside; board 2:
nearest stable faces 87-89 deg away, i.e. lying flat), so in the simulator the policy can only lay the boards down
(every ep24 rollout fails from ~f100). After flattening: board 2 has a stable standing face at 0 deg (27 cm^2, centre of
mass 5.7 mm inside); board 1 only marginal (centre of mass at the footprint edge: our standing pose leans a few
degrees; in the video a hand steadies it and it ends leaning on board 2). Test: ep24 with `LIB=library_v4` and
`contact_retarget --rest_settle 1` vs the 0.31-0.32 of tonight's variants.
