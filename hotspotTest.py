import cv2
import numpy as np
import os
import threading
import time

# --- SETTINGS ---
# Adjust these to match your physical chessboard
CHECKERBOARD = (8, 6)  # Number of internal corners (width, height)
SQUARE_SIZE = 25.0     # Size of one square side (e.g., in mm or cm)

# FFMPEG optimization for low latency
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "protocol_whitelist;file,rtp,udp|fflags;nobuffer|flags;low_delay|framedrop;1"

class VideoStream:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
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

# --- PREPARE CALIBRATION DATA ---
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Prepare object points (0,0,0), (1,0,0), (2,0,0) ... (8,5,0)
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
objp *= SQUARE_SIZE

objpoints = []  # 3d point in real world space
imgpoints0 = [] # 2d points in image plane for Cam 0
imgpoints1 = [] # 2d points in image plane for Cam 1

# --- START STREAMS ---
print("Connecting to AER813 Dual Multicast...")
cam0 = VideoStream("udp://@239.0.1.1:5001").start()
cam1 = VideoStream("udp://@239.0.1.1:5000").start()

print("\n=== CALIBRATION MODE ===")
print("1. Hold the chessboard so both cameras can see it.")
print("2. Press 's' to save a pair of images.")
print("3. Capture at least 15-20 pairs from different angles/distances.")
print("4. Press 'q' to calculate and save calibration results.")

while True:
    f0 = cam0.read()
    f1 = cam1.read()

    if f0 is None or f1 is None:
        continue

    # Create copies for display so we don't draw on the raw frames
    disp0 = f0.copy()
    disp1 = f1.copy()

    gray0 = cv2.cvtColor(f0, cv2.COLOR_BGR2GRAY)
    gray1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)

    # Find corners for visual feedback
    ret0, corners0 = cv2.findChessboardCorners(gray0, CHECKERBOARD, None)
    ret1, corners1 = cv2.findChessboardCorners(gray1, CHECKERBOARD, None)

    if ret0:
        cv2.drawChessboardCorners(disp0, CHECKERBOARD, corners0, ret0)
    if ret1:
        cv2.drawChessboardCorners(disp1, CHECKERBOARD, corners1, ret1)

    # Show live feed
    cv2.imshow('Camera 0 (S to Save)', disp0)
    cv2.imshow('Camera 1 (S to Save)', disp1)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        if ret0 and ret1:
            objpoints.append(objp)
            # Refine corner locations for sub-pixel accuracy
            corners0_refined = cv2.cornerSubPix(gray0, corners0, (11, 11), (-1, -1), criteria)
            corners1_refined = cv2.cornerSubPix(gray1, corners1, (11, 11), (-1, -1), criteria)
            imgpoints0.append(corners0_refined)
            imgpoints1.append(corners1_refined)
            print(f"Captured pair {len(objpoints)} successfully.")
        else:
            print("Failed! Chessboard must be visible in BOTH cameras.")

    elif key == ord('q'):
        break

# --- CALCULATION ---
if len(objpoints) >= 10:
    print("\nProcessing Calibration... this may take a moment.")
    h, w = f0.shape[:2]

    # 1. Individual Camera Calibration (Intrinsics)
    err0, mtx0, dist0, _, _ = cv2.calibrateCamera(objpoints, imgpoints0, (w, h), None, None)
    err1, mtx1, dist1, _, _ = cv2.calibrateCamera(objpoints, imgpoints1, (w, h), None, None)

    # 2. Stereo Calibration (Extrinsics)
    # We fix the intrinsics to keep the individual accuracies we just found
    flags = cv2.CALIB_FIX_INTRINSIC
    errS, _, _, _, _, R, T, E, F = cv2.stereoCalibrate(
        objpoints, imgpoints0, imgpoints1, 
        mtx0, dist0, mtx1, dist1, (w, h), 
        criteria=criteria, flags=flags)

    # --- REPORT ACCURACY ---
    print("\n" + "="*30)
    print("CALIBRATION RESULTS")
    print("="*30)
    print(f"Cam 0 Reprojection Error: {err0:.4f} px")
    print(f"Cam 1 Reprojection Error: {err1:.4f} px")
    print(f"Stereo (Combined) Error:  {errS:.4f} px")
    print("-" * 30)
    
    if errS < 1.0:
        print("Status: SUCCESS (Good Accuracy)")
    else:
        print("Status: WARNING (High Error, check lighting/focus)")

    # Save to disk
    np.savez('stereo_calib.npz', 
             mtx0=mtx0, dist0=dist0, err0=err0,
             mtx1=mtx1, dist1=dist1, err1=err1,
             R=R, T=T, errS=errS)
    
    print("\nFiles saved to 'stereo_calib.npz'")
else:
    print("\nCancelled. Not enough data captured (Minimum 10 pairs).")

cam0.stop()
cam1.stop()
cv2.destroyAllWindows()