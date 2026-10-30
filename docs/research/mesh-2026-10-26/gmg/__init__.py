"""gmg: the generalized mesh generator (SPEC.md and PREREG.md in this folder; build notes in build/).

Imported as `gmg` with docs/research/mesh-2026-10-26 on sys.path (as for autokit). Every module that reads an input
imports `gmg.guard` first; importing the guard installs its open() audit hook for the interpreter. This file imports
nothing, so tools that must not load the guard (tools/roster_public.py, tools/strace_audit.py) run as plain scripts.
"""
