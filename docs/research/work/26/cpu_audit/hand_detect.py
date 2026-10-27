"""CPU audit, stage 1: MediaPipe Hands on the colour ego_cam_a video of one public episode, with the exact detector
settings of pipeline/hands_mp.py (tracking mode, <= 2 hands, model_complexity 1, min_det 0.3, min_track 0.3).
Stores per colour frame: hand count, raw handedness labels and scores, 2-D landmarks (pixels). No ground truth is read.
Usage (MediaPipe 0.10.14 venv): python hand_detect.py <ep*_a.mp4 or episode_*.mp4> <out.npz>
"""
import sys, time
import cv2, numpy as np
import mediapipe as mp

video, out = sys.argv[1], sys.argv[2]
cap = cv2.VideoCapture(video)
W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
hands = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=2, model_complexity=1,
                                 min_detection_confidence=0.3, min_tracking_confidence=0.3)
n_h, lab, score, lm = [], [], [], []
t0 = time.time()
while True:
    ok, fr = cap.read()
    if not ok:
        break
    r = hands.process(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
    L = np.full((2, 21, 2), np.nan, np.float32); lb = ['', '']; sc = [np.nan, np.nan]
    k = 0
    if r.multi_hand_landmarks:
        for hl, hd in zip(r.multi_hand_landmarks, r.multi_handedness):
            if k == 2:
                break
            L[k] = [[p.x * W, p.y * H] for p in hl.landmark]
            lb[k] = hd.classification[0].label; sc[k] = hd.classification[0].score
            k += 1
    n_h.append(k); lab.append(lb); score.append(sc); lm.append(L)
np.savez_compressed(out, n_hands=np.array(n_h, np.int8), labels=np.array(lab), scores=np.array(score, np.float32),
                    landmarks=np.array(lm), width=W, height=H)
print(f'{video}: {len(n_h)} frames {W}x{H}, >=1 hand {np.mean(np.array(n_h) >= 1):.3f}, 2 hands '
      f'{np.mean(np.array(n_h) == 2):.3f}, {time.time() - t0:.0f} s')
