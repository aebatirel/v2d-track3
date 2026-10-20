# Dump frame k of a/b/c plus rectified c/b for a spoon episode (inspection only).
import sys, cv2, numpy as np
sys.path.insert(0, '.'); from b_lib import *
split, ep, k = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
for c in 'abc':
    f = read_frames(split, ep, c, [k])[k]
    cv2.imwrite(f'{OUT}/raw_{split[0]}{ep}_{c}{k}.png', f)
    if c != 'a': cv2.imwrite(f'{OUT}/rect_{split[0]}{ep}_{c}{k}.png', rect(f, c))
print('ok', FR, CXR, CYR, BASE, C.get('translation_units'))
