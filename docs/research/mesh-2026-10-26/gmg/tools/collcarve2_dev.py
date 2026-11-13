"""Round-2 driver of the collision carve (PREREG F-I5.15 / F-I5.16; INTERLOCK.md 21.13.12, 21.14.7).

A thin wrapper around the shared tools/interlock_dev.py (not edited by this lane): it selects the F-I5 revision and
then runs interlock_dev.main() with the remaining arguments, which must include --waiver-fi5. Revision 1 (F-I5 as
built, F-I5.11) stays the default of collcarve.run_episode and of interlock_dev.py itself.

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tools/collcarve2_dev.py --fi5-rev 2 --waiver-fi5 \
      --run <run> --ep <ep> --bundle <bundle> --cands <cands> --pick <obj=cid,...> --hands <hands.npz> \
      --identity eval --tag fi5r2

The round folder is <run>/sim/public/ep<ep>-<tag>/r0 (interlock_dev's naming); the report records fi5_rev.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    rev = 2
    if '--fi5-rev' in argv:
        i = argv.index('--fi5-rev')
        rev = int(argv[i + 1])
        del argv[i:i + 2]
    if '--waiver-fi5' not in argv:
        raise SystemExit('collcarve2_dev: --waiver-fi5 is required (the F-I5 branch of interlock_dev.py)')
    from gmg import collcarve as CC
    CC.REV = rev
    from gmg.tools import interlock_dev
    sys.argv = [os.path.join(HERE, 'interlock_dev.py')] + argv
    return interlock_dev.main()


if __name__ == '__main__':
    main()
