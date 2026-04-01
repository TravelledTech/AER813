import numpy as np
import cv2
import json

# 1. Setup constants
# For a 9x7 board, there are 8x6 internal corners
CHESSBOARD_SIZE = (8, 6) 
SQUARE_SIZE = 25  # mm

# Termination criteria for sub-pixel accuracy
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Prepare object points (0,0,0), (25,0,0), (50,0,0) ...
objp = np.zeros((CHESSBOARD_SIZE[0] * CHESSBOARD_SIZE[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHESSBOARD_SIZE[0], 0:CHESSBOARD_SIZE[1]].T.reshape(-1, 2)
objp *= SQUARE_SIZE

objpoints = [] # 3d point in real world space
imgpoints = [] # 2d points in image plane

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
# cap.set(cv2.CAP_PROP_FOCUS, 70)
# cap.set(cv2.CAP_PROP_GAIN, 0)
# cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  #REMOVE THIS LATER
# cap.set(cv2.CAP_PROP_EXPOSURE, -6)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)
print("Press 's' to capture a frame, 'q' to calibrate and exit.")

while True:
    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Find the chess board corners
    ret_corners, corners = cv2.findChessboardCorners(gray, CHESSBOARD_SIZE, None)

    if ret_corners:
        # Draw and display the corners
        cv2.drawChessboardCorners(frame, CHESSBOARD_SIZE, corners, ret_corners)
        
    cv2.imshow('Calibration', frame)
    key = cv2.waitKey(1)

    if key == ord('s') and ret_corners:
        objpoints.append(objp)
        # Refine corner locations for better accuracy
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)
        print(f"Captured frame {len(imgpoints)}")

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# 2. Calibration Calculation
if len(imgpoints) > 10:
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
    
    # 3. Save the results
    data = {"camera_matrix": mtx.tolist(), "dist_coeff": dist.tolist()}
    with open("kiyoCalibration.json", "w") as f:
        json.dump(data, f)
    print("Calibration successful! Data saved to calibration_data.json")
    
    # ... (after the calibrateCamera line)
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
    
    print(f"Total Re-projection Error: {ret:.4f} pixels")
    
    if ret < 0.5:
        print("Status: Excellent. Very stable tracking.")
    elif ret < 1.0:
        print("Status: Good. Acceptable for most uses.")
    else:
        print("Status: Poor. Your reaction wheel might jitter. Try more light or lock focus.")
        
else:
    print("Not enough frames captured. Try to get at least 15-20.")