"""Packer (SPEC section 14; build step B1): the shipped mesh of a candidate.

  pack(mesh, out_glb) -> (packed mesh, info)
      autokit/program.fit_budget(mesh, [], 4000) (so the kit's budget_mesh only welds), written as GLB, then decoded
      by the gmg's own copy of the kit decode (score.kit_decode) and checked for watertightness (veto V1).
      The markers.attach report (mesh.metadata['balls']) is kept on the packed mesh and its length is info['balls']
      (None without a report): score.score_pool counts the balls from it (B5 round 3; the GLB file does not carry it,
      so a caller that reloads the file passes Candidate.balls = info['balls']).
The budget 4000 < the kit's 4096 is PREREG A.6 'remesh, budget' (kit).
"""
from __future__ import annotations

import os

import numpy as np
import trimesh

from gmg import guard, score

BUDGET = 4000


def pack(mesh, out_glb):
    from autokit import program
    budget = guard.constant('pack_budget_faces', BUDGET, 'kit:PREREG A.6 4000 faces (kit 4096)')
    m, info = program.fit_budget(mesh, [], budget)
    m = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)
    md = getattr(mesh, 'metadata', None)
    report = list(md['balls']) if isinstance(md, dict) and md.get('balls') is not None else None
    os.makedirs(os.path.dirname(out_glb), exist_ok=True)
    m.export(out_glb)
    if report is not None:
        m.metadata['balls'] = report                   # after export: the file stays as before (B5 round 3)
    info = dict(info)
    info.update(path=out_glb, faces=int(len(m.faces)), vertices=int(len(m.vertices)),
                watertight_packed=bool(m.is_watertight), sha256=guard._sha256(os.path.realpath(out_glb)),
                balls=None if report is None else len(report))
    info['v1'] = score.v1(out_glb)
    return m, info
