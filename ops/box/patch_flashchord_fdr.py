"""Install the FlashDexRetarget-style training rewards (ops/box/fc_v2d_fdr.py) into a FlashCHORD checkout (2026-10-22).
Idempotent. Inert unless FC_FDR_OBJ or FC_FDR_TIPS is set in the training process, so an unset variable reproduces
upstream behaviour exactly (the hook only checks the variables at import).

1. copies fc_v2d_fdr.py to flash_chord/objectives/v2d_fdr.py (always, so the box runs the committed version);
2. appends the import hook to flash_chord/objectives/tracking.py;
3. writes configs/curriculum/tracking_250m_mixed_reset_v2d.yaml: the stock curriculum with the stage weights of
   missed_contact and unintended_contact read from objective.<term>.weight (their stock values, -1 and -10, are the
   objective defaults, so selecting this curriculum alone changes nothing; TRAIN_ARGS can then set them).
The checkpoint's resolved config keeps FlashCHORD's own term names, so the unpatched evaluator loads it.
Usage: python patch_flashchord_fdr.py <flash_chord dir>
"""
import os, shutil, sys

fc = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
pkg = os.path.join(fc, 'src/flash_chord')

shutil.copyfile(os.path.join(here, 'fc_v2d_fdr.py'), os.path.join(pkg, 'objectives/v2d_fdr.py'))
print('installed:', os.path.join(pkg, 'objectives/v2d_fdr.py'))

p = os.path.join(pkg, 'objectives/tracking.py')
s = open(p).read()
tag = '# v2d patch: FC_FDR'
if tag in s:
    print('already patched:', p)
elif 'class TrackingObjective:' not in s:
    sys.exit(f'TrackingObjective not found in {p}: FlashCHORD changed, patch not applied')
else:
    s += f'''

{tag} (ops/box/patch_flashchord_fdr.py); inert unless FC_FDR_OBJ or FC_FDR_TIPS is set
def _v2d_fdr_hook() -> None:
    import os

    if any(os.environ.get(name, "0") not in ("", "0") for name in ("FC_FDR_OBJ", "FC_FDR_TIPS")):
        from flash_chord.objectives.v2d_fdr import install

        install(TrackingObjective)


_v2d_fdr_hook()
'''
    open(p, 'w').write(s)
    print('patched:', p)

src = os.path.join(pkg, 'configs/curriculum/tracking_250m_mixed_reset.yaml')
dst = os.path.join(pkg, 'configs/curriculum/tracking_250m_mixed_reset_v2d.yaml')
c = open(src).read()
for line, term in (('      missed_contact: -1.0\n', 'missed_contact'), ('      unintended_contact: -10.0\n', 'unintended_contact')):
    if c.count(line) != 1:
        sys.exit(f'{term} weight line not found once in {src}: FlashCHORD changed, curriculum not written')
    c = c.replace(line, f'      {term}: ${{objective.{term}.weight}}\n')
open(dst, 'w').write('# v2d (ops/box/patch_flashchord_fdr.py): stock tracking_250m_mixed_reset with the missed/unintended contact\n'
                     '# stage weights read from the objective config (defaults equal the stock values).\n' + c)
print('wrote:', dst)
