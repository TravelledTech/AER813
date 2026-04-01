import cv2
import numpy as np
import threading
import json

class video:
    def __init__(self, URL):
        
        #Stuff for camera
        self.URL = URL
        self.cap = None
        self.output = None
        self.running = False
        self.status = "OFFLINE"
        self.mode = 0   #Starting Mode
        # 0 = Normal
        # 1 = ArUco
        
        # Camera specs
        self.fps = 60
        self.frameTime = 1.0/60 #Time between frames
        self.xRes = 1280
        self.yRes = 720
        
        #Calibration
        with open("kiyoCalibration.json", "r") as f:
            calib = json.load(f)
        
        self.mtx = np.array(calib["camera_matrix"])
        self.dist = np.array(calib["dist_coeff"])
        
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        parameters = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        
        MARKER_SIZE = 0.1
        
        self.obj_points = np.array([
            [-MARKER_SIZE/2,  MARKER_SIZE/2, 0],
            [ MARKER_SIZE/2,  MARKER_SIZE/2, 0],
            [ MARKER_SIZE/2, -MARKER_SIZE/2, 0],
            [-MARKER_SIZE/2, -MARKER_SIZE/2, 0]
        ], dtype=np.float32)
        
        self.Position = [0, 0, 0]
        self.Rotation = [0, 0, 0]
        

    # Runs the streaming thread (all camera stuff will happen here)
    def stream_thread(self):
        while self.running:
            ret, frame = self.cap.read()
            
            if not ret:
                continue
            
            frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # ==== Rotating frame ==== (if needed) (probably not)
            #frame_rgb = cv2.rotate(frame_rgb, cv2.ROTATE_90_CLOCKWISE)
            
            
            grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            #Change whats being outputted
            if self.mode == 0:      #Normal
                self.output = frame
                
            elif self.mode == 1:    # Ellipse
                self.output = self.ArUco(grey, frame)
    
    def ArUco(self, grey, frame):
        corners, ids, rejected = self.detector.detectMarkers(grey)
        if ids is not None:
            for i in range(len(ids)):
                # Estimate pose using SolvePnP (more robust for newer OpenCV)
                _, rvec, tvec = cv2.solvePnP(self.obj_points, corners[i], self.mtx, self.dist, False, cv2.SOLVEPNP_IPPE_SQUARE)
                
                # Draw the 3D axis (Red=X, Green=Y, Blue=Z)
                cv2.drawFrameAxes(frame, self.mtx, self.dist, rvec, tvec, 0.05)
                
                # Convert rotation vector to a 3x3 Rotation Matrix
                rmat, _ = cv2.Rodrigues(rvec)

                # Apply the flip matrix so "Head on" reads as 0,0,0
                flip_matrix = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]])
                rmat = rmat @ flip_matrix
                
                # Extract Euler Angles using Intrinsic Yaw->Pitch->Roll math
                # Pitch (Tilting up/down)
                pitch = np.arcsin(np.clip(-rmat[1, 2], -1.0, 1.0))
                
                # Yaw (Turning left/right)
                yaw = np.arctan2(rmat[0, 2], rmat[2, 2])
                
                # Roll (Spinning like a steering wheel)
                roll = np.arctan2(rmat[1, 0], rmat[1, 1])


                self.Rotation = [pitch, yaw, roll]

                pos = tvec.flatten()

                x_pos = -pos[0]

                y_pos = -pos[1]

                z_pos = pos[2]
                
                self.Position = [x_pos, y_pos, z_pos]
                
        return frame
                
                
    
    # Starts Stream (Change camera info here)         
    def startStream(self):
        if self.running:
            return True
        
        self.cap = cv2.VideoCapture(self.URL, cv2.CAP_DSHOW)   #Change to FFMEG for host camera
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            self.status = "ERROR"
            print("Camera Failed")
            self.cap = None
            return False
        
        # Change resolution here
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.xRes)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.yRes)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        
        self.running = True
        self.status = "ONLINE"
        
        threading.Thread(target=self.stream_thread, daemon=True).start()    #Starts stream thread once running
        return True
    
    # Ends stream
    def endStream(self):
        self.running = False
        self.status = "OFFLINE"
        
        if self.cap:
            self.cap.release()
            self.cap = None
    
    # Return Selected Captured Frame
    def getFrame(self):
        if not self.running:
            return None
        return self.output
    
    # Returns a txt of Camera Status
    def getStatus(self):
        return self.status
    
    # Set Camera modex
    def setMode(self, mode):
        self.hasFound = False
        self.mode = mode
        
    def getPos(self):
        return self.Position
    
    def getRot(self):
        return self.Rotation
        
        
        