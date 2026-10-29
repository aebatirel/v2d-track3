"""Install the full-inertia virtual object controller (ops/box/fc_v2d_voc.py) into a FlashCHORD checkout (2026-10-23).
Idempotent. Inert unless FC_VOC_INERTIA is set (not "" or "0") in the process, so an unset variable reproduces
upstream behaviour exactly (the hook only checks the variable at import).

1. copies fc_v2d_voc.py to flash_chord/runtime/v2d_voc.py (always, so the box runs the committed version);
2. appends a hook to flash_chord/runtime/object_control.py that rebinds the module's _object_control kernel
   (apply_object_control looks the name up at call time).
Usage: python patch_flashchord_voc.py <flash_chord dir>
"""
import os, shutil, sys

fc = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
pkg = os.path.join(fc, 'src/flash_chord')

shutil.copyfile(os.path.join(here, 'fc_v2d_voc.py'), os.path.join(pkg, 'runtime/v2d_voc.py'))
print('installed:', os.path.join(pkg, 'runtime/v2d_voc.py'))

p = os.path.join(pkg, 'runtime/object_control.py')
s = open(p).read()
tag = '# v2d patch: FC_VOC_INERTIA'
if tag in s:
    print('already patched:', p)
elif 'inertia_eff = (inertia[0, 0] + inertia[1, 1] + inertia[2, 2]) / 3.0' not in s or 'def _object_control(' not in s:
    sys.exit(f'stock VOC kernel not found in {p}: FlashCHORD changed, patch not applied')
else:
    s += f'''

{tag} (ops/box/patch_flashchord_voc.py); inert unless FC_VOC_INERTIA is set
def _v2d_voc_hook() -> None:
    import os

    global _object_control
    if os.environ.get("FC_VOC_INERTIA", "0") not in ("", "0"):
        from flash_chord.runtime.v2d_voc import object_control_full_inertia

        _object_control = object_control_full_inertia


_v2d_voc_hook()
'''
    open(p, 'w').write(s)
    print('patched:', p)
