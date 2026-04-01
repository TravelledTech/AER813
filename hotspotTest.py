import cv2
import threading
import time
import os

# Force FFMPEG to discard old frames immediately
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "protocol_whitelist;file,rtp,udp|fflags;nobuffer|flags;low_delay|framedrop;1"

class VideoStream:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Set buffer to minimum
        self.frame = None
        self.status = False
        self.stopped = False
        self.t = threading.Thread(target=self.update, args=())
        self.t.daemon = True

    def start(self):
        self.t.start()
        return self

    def update(self):
        while not self.stopped:
            self.status, self.frame = self.cap.read()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.cap.release()

# --- START STREAMS ---
print("Connecting to AER813 Dual Multicast...")
cam0 = VideoStream("udp://@239.0.1.1:5000").start()
cam1 = VideoStream("udp://@239.0.1.1:5001").start()

prev_time = 0

while True:
    f0 = cam0.read()
    f1 = cam1.read()

    if f0 is None or f1 is None:
        continue

    # --- VISION PROCESSING ---
    for frame in [f0, f1]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners = cv2.goodFeaturesToTrack(gray, 4, 0.1, 50)
        if corners is not None:
            for i in corners:
                x, y = i.ravel()
                cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)

    # Show feeds
    cv2.imshow('Camera 0 (Live)', f0)
    cv2.imshow('Camera 1 (Live)', f1)

    # Monitor Performance
    now = time.time()
    fps = 1 / (now - prev_time) if (now - prev_time) > 0 else 0
    prev_time = now
    
    # Print real FPS to console every 60 frames
    if int(time.time() * 60) % 60 == 0:
        print(f"Current System FPS: {int(fps)}")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam0.stop()
cam1.stop()
cv2.destroyAllWindows()
