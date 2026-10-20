"""Left-edge crops (x<500 px of 2028) at given frames of several clips. usage: edgecrop.py out.png vid:frame ..."""
import sys, cv2, numpy as np
out = sys.argv[1]; tiles = []
for spec in sys.argv[2:]:
    vid, f = spec.rsplit(':', 1); f = int(f)
    cap = cv2.VideoCapture(vid); cap.set(cv2.CAP_PROP_POS_FRAMES, f); ok, fr = cap.read()
    c = fr[:, :520].copy(); c = cv2.resize(c, (260, 760))
    cv2.putText(c, vid.split('_')[-1][-7:-4] + f' f{f}', (5, 20), 0, 0.6, (0, 255, 255), 2); tiles.append(c)
cv2.imwrite(out, np.hstack(tiles)); print(out)
