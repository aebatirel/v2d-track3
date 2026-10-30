"""gmg: the generalized mesh generator (SPEC.md and PREREG.md in this folder; build notes in build/).

Imported as `gmg` with docs/research/mesh-2026-10-26 on sys.path (as for autokit). Every module that reads an input
imports `gmg.guard` first; importing the guard installs its audit hook for the interpreter (opens, renames, links,
symlinks, removals, process arguments, URLs). This file imports
nothing. tools/roster_public.py never loads the guard (its hook would refuse the parquets it reads once, under audit).
tools/strace_audit.py does import the guard, for its rules only: it never sets the run folder (it drops GMG_RUN from its
own environment before the import and passes the environment unchanged to the audited command), and its own hashing
runs in the guard's internal context.
"""
