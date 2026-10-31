"""Candidate producers (modules M7 and M12 of SPEC section 7). Each producer module has
produce(ctx, frames=None) -> [Candidate]; ctx = dict(bundle, obj, t0, ...); frames limits the build to training frames
(held-out refits, B5). B1 has the minimal SHELL and HULL producers; STRUCT (B8, B11) and GEN/FUSE (B15) follow."""
from __future__ import annotations

import dataclasses

CLASSES = ('STRUCT', 'FUSE', 'GEN', 'SHELL', 'HULL')


@dataclasses.dataclass
class Candidate:
    cid: str
    producer: str
    cls: str
    mesh: object
    params: dict
    n_params: int = 0
    t_mm: float | None = None
    balls: int = 0
    built_on_frames: str = 'all'
    flags: list = dataclasses.field(default_factory=list)
    report: dict = dataclasses.field(default_factory=dict)
    # the same candidate without its balls (set when markers.attach adds balls to mesh). score.score_pool measures
    # the V5 / A.5 self-ambiguity on it when the object's balls are not trusted; without it that value is unknown.
    base_mesh: object = None

    def meta(self):
        return dict(cid=self.cid, producer=self.producer, cls=self.cls, params=self.params, n_params=self.n_params,
                    t_mm=self.t_mm, balls=self.balls, built_on_frames=self.built_on_frames, flags=list(self.flags),
                    report=self.report)
