import cv2
import numpy as np

# Use this class for handling video streaming (Probably also use this for the edge detection and position handling)
# Have 2 methods of score
# Distance based (High score the closer it is) -> 50 if same location, -1 per pixel distance (adjust weights later)
# Area -> 50 if same size
# Maybe have another score for orientationm but think about that one later

# Have it so it needs to refind the ellipse if none has been found for ~20 frames


class video:
    def __init__(self, URL):
        
        #Replace these with the final stream urls
        self.URL = URL
        self.cap = None
        self.running = False
        self.status = "OFFLINE"
        
        self.hasFound = False
        self.countFrames = 0
        
        self.lastCenter = None
        self.lastArea = None
        self.ellipse = None
        
        self.delay = 17 #elay between each frame (in ms)

    # Runs the streaming thread (all camera stuff will happen here)
    def stream_thread(self):
        while self.running:
            ret, frame = self.cap.read()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # ==== Rotating frame ==== (if needed)
            #frame_rgb = cv2.rotate(frame_rgb, cv2.ROTATE_90_CLOCKWISE)
            
            # =========== Edge Detection ===========
            grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(grey, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)
            
            annotated = frame_rgb.copy()
            edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

            # ========== Find contours ==========
            contours, _ = cv2.findContours(
                edges,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_NONE
            )
            
            bestEllipse = None
            Score = 1e9
            for cnt in contours:    #Filters out ellipses that are too small
                if len(cnt) < 30:
                    continue
                
                area = cv2.contourArea(cnt)
                if area < 500:
                    continue
                
                ellipse = cv2.fitEllipse(cnt)
                (cx, cy), (w, h), angle = ellipse
                area = np.pi * (w / 2) * (h / 2)
    
                if not self.hasFound:    # ===== Find first ellipse =====
                
                    pts = cnt.reshape(-1, 2).astype(np.float32)
                    ellipse_pts = cv2.ellipse2Poly(
                        (int(cx), int(cy)),
                        (int(w/2), int(h/2)),
                        int(angle),
                        0, 360, 10
                        )
                
                    dists = np.min(
                        np.linalg.norm(pts[:, None] - ellipse_pts[None, :], axis=2),
                        axis=1
                        )
                    fit_error = np.mean(dists)
                    
                    score = -fit_error
                    
                    if score > Score:
                        Score = score
                        bestEllipse = ellipse
                        self.hasFound = True
                    
                else:       #if there already was an ellipse, finds next
                    # With 1280x720, probably want a ellipse within 50 pixel of the last one (adjust this)
                    # Keep area withink 80% of the original
                    
                    # Score threshholds (change later)
                    maxDist = 50
                    maxDiff = 0.2
                    
                    #Currently only 2 scoring methods, add more later
                    
                    score = 0
                    
                    # ===== Distance check =====
                    x = cx - self.lastCenter(0)
                    y = cy - self.lastCenter(1)
                    
                    dist = int(np.sqrt(x^2+y^2*1.0))
                    temp = maxDist - dist
                    if temp < 0:
                        continue
                    score += temp
                    
                    # ===== Area Check =====
                    # if 0, score = 50
                    # if 0.2, score = 0
                    area = np.pi*(w/2)*(h/2)
                    diff = abs((area-self.lastArea)/self.lastArea)
                    
                    temp = 50 - diff*(50/maxDiff)
                    temp = maxDist - dist
                    if temp < 0:
                        continue
                    score += temp
                    
                    if score > Score:
                        Score = score
                        bestEllipse = ellipse
                    
            # Replaces the current ellipse with the new one (whether its a new one or an replacement)
            if not bestEllipse == None:
                self.ellipse = bestEllipse
                (cx, cy), (w, h), angle = self.ellipse
                self.lastCenter = [cx, cy]
                self.lastArea = np.pi*(w/2)*(h/2)
            
                
                
                
    def startStream(self):
        if self.running:
            return
        
        self.cap = cv2.VideoCapture(self.URL)
        
        if not self.cap.isOpened():
            self.status = "ERROR"
            print("Camera Failed")
            self.cap = None
            return
        
        self.running = True
        self.status = "ONLINE"
        
        self.stream_thread()    #Starts stream thread once running
        
    def endStream(self):
        self.running = False
        self.status = "OFFLINE"
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
    def getFrame(self):
        if not self.running or self.cap is None:
            return None
        
        ret, frame = self.cap.read()
        
        if not ret:
            self.status = "SEND FAILURE"
            return None
        
        return frame
    
    def getStatus(self):
        return self.status
    
    def getEllipse(self):
        return self.ellipse
        
        