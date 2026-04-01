import cv2
import numpy as np
import json

# 1. Load your EXCELLENT calibration data (0.1427 error)
try:
    with open("kiyoCalibration.json", "r") as f:
        calib = json.load(f)
    mtx = np.array(calib["camera_matrix"])
    dist = np.array(calib["dist_coeff"])
except FileNotFoundError:
    print("Error: calibration_data.json not found!")
    exit()

# 2. Setup ArUco - Using the new 4.8.x+ Detector API
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

# 3. Physical Marker Size in METERS
MARKER_SIZE = 0.1  # 100mm = 0.1 meters

# Define the 3D coordinates of the marker corners in its own coordinate system
# This is needed for the SolvePnP function
obj_points = np.array([
    [-MARKER_SIZE/2,  MARKER_SIZE/2, 0],
    [ MARKER_SIZE/2,  MARKER_SIZE/2, 0],
    [ MARKER_SIZE/2, -MARKER_SIZE/2, 0],
    [-MARKER_SIZE/2, -MARKER_SIZE/2, 0]
], dtype=np.float32)

cap = cv2.VideoCapture(0)
print("Tracking started. Press 'q' to quit.")

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 60)

while True:
    ret, frame = cap.read()
    if not ret: break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # New Method: detectMarkers is now a method of the detector object
    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None:
        for i in range(len(ids)):
            # Estimate pose using SolvePnP (more robust for newer OpenCV)
            _, rvec, tvec = cv2.solvePnP(obj_points, corners[i], mtx, dist, False, cv2.SOLVEPNP_IPPE_SQUARE)
            
            # Draw the 3D axis (Red=X, Green=Y, Blue=Z)
            cv2.drawFrameAxes(frame, mtx, dist, rvec, tvec, 0.05)
            
            # Convert rotation vector to a 3x3 Rotation Matrix
            rmat, _ = cv2.Rodrigues(rvec)
            
            # Extract Euler Angles (Roll, Pitch, Yaw)
            sy = np.sqrt(rmat[0,0]**2 + rmat[1,0]**2)
            if sy > 1e-6:
                x = np.arctan2(rmat[2,1], rmat[2,2])
                y = np.arctan2(-rmat[2,0], sy)
                z = np.arctan2(rmat[1,0], rmat[0,0])
            else:
                x = np.arctan2(-rmat[1,2], rmat[1,1])
                y = np.arctan2(-rmat[2,0], sy)
                z = 0

            # Convert to degrees
            roll, pitch, yaw = np.degrees([x, y, z])
            
            # Output for your PID loop
            # Note: Depending on marker orientation, Roll or Yaw might be your tilt
            print(f"ID: {ids[i][0]} | ROLL: {roll:6.2f} | PITCH: {pitch:6.2f} | YAW: {yaw:6.2f}")

    cv2.imshow('AER813 - ArUco Tracking', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()