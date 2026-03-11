import cv2
import numpy as np
import threading

# Use this class for handling video streaming (Probably also use this for the edge detection and position handling)
# Have 2 methods of score
# Distance based (High score the closer it is) -> 50 if same location, -1 per pixel distance (adjust weights later)
# Area -> 50 if same size
# Maybe have another score for orientationm but think about that one later

# Have it so it needs to refind the ellipse if none has been found for ~20 frames

#For corner detection
#https://docs.opencv.org/4.x/dc/d0d/tutorial_py_features_harris.html
#https://docs.opencv.org/4.x/d4/d8c/tutorial_py_shi_tomasi.html

class video:
    def __init__(self, URL):
        
        #Replace these with the final stream urls
        self.URL = URL
        self.cap = None
        self.running = False
        self.status = "OFFLINE"
        self.mode = 3   #0 = Nothing, 1 = ellipse detection, 2 = ellipse detection (but contours), 3 = corner detection, 4 = vertical line detection (not sure if I will use it)
        
        self.hasFound = False
        self.countFrames = 0
        
        self.lastCenter = None
        self.lastArea = None
        self.ellipse = None
        
        self.output = None
        self.outVar = 0
        
        self.delay = 10 #elay between each frame (in ms)
        
        self.poly = None

    # Runs the streaming thread (all camera stuff will happen here)
    def stream_thread(self):
        while self.running:
            ret, frame = self.cap.read()
            
            if not ret:
                continue
            
            frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # ==== Rotating frame ==== (if needed)
            #frame_rgb = cv2.rotate(frame_rgb, cv2.ROTATE_90_CLOCKWISE)
            
            
            grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if self.mode == 1 or self.mode == 2:
                self.output = self.contourDetection(grey, frameRGB)
            
            elif self.mode == 3:
                self.output = self.cornerDetection(grey, frameRGB)
            
    def contourDetection(self, grey, frame):
        # =========== Edge Detection ===========
        blurred = cv2.GaussianBlur(grey, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        annotated = frame.copy()

        # ========== Find contours ==========
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE     #SWITCH SIMPLE <---> NONE
        )                               # TEST WHICH ONE PERFORMS BETTER
        
        bestEllipse = None
        Score = -1e9
        for cnt in contours:
            # ========== Contour Filters ========== (Adjust)
            if len(cnt) < 10:   # Minimum contour length
                continue
            
            contourArea = cv2.contourArea(cnt) # Sets minimum area
            if contourArea < 800:
                continue
            
            ellipse = cv2.fitEllipse(cnt)
            (cx, cy), (w, h), angle = ellipse
            
            ellipse_perimeter = np.pi * (3*(w+h) - np.sqrt((3*w+h)*(w+3*h)))    # Makes sure contour actually makes a full circle
            coverage = cv2.arcLength(cnt, True) / ellipse_perimeter
            if coverage < 0.3:
                continue
            
            ratio = min(w, h) / max(w, h)   # Masximum aspect ratio of ellipse
            if ratio < 0.2:
                continue
            
            area = np.pi * (w / 2) * (h / 2)
            
            fill = contourArea / area   #Checks Contour area vs. Ellipse area
            if fill < 0.5:
                continue

            # ====== Find first ellipse ======
            if not self.hasFound:    
            
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
            
            #========== Find Next Ellipse ===========
            else:
                # With 1280x720, probably want a ellipse within 50 pixel of the last one (adjust this)
                # Keep area withink 80% of the original
                
                # Score threshholds (change later)
                maxDist = 150
                maxDiff = 0.5
                
                #Currently only 2 scoring methods, add more later
                
                score = 0
                
                # ===== Distance check ====
                x = cx - self.lastCenter[0]
                y = cy - self.lastCenter[1]
                
                dist = np.sqrt(x**2+y**2)
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
                if temp < 0:
                    continue
                score += temp
                
                if score > Score:
                    Score = score
                    bestEllipse = ellipse
                
        # Replaces the current ellipse with the new one (whether its a new one or an replacement)
        if not bestEllipse == None:
            self.outVar = 0
            self.ellipse = bestEllipse
            (cx, cy), (w, h), angle = self.ellipse
            self.lastCenter = [cx, cy]
            self.lastArea = np.pi*(w/2)*(h/2)
        
        else:
            self.outVar += 1
        
        if self.hasFound:
            # Draws ellipse on the annotated frame
            (cx, cy), (w, h), angle = self.ellipse
            cv2.ellipse(annotated, self.ellipse, (0, 255, 0), 2)
            cv2.circle(annotated, (int(cx), int(cy)), 3, (255, 0, 0), -1)
            cv2.circle(edges, (int(cx), int(cy)), 3, (255, 0, 0), -1)
        
        # ===== if ellipse hasnt been found in 20 frames, try again =====
        if self.outVar >= 20:
            self.hasFound = False
        
        if self.mode == 1:
            return annotated
        elif self.mode == 2:
            return edges
        
    def cornerDetection(self, grey, frame):
        # Detect a square every so often (maybe every 60 frames (or every second))
        # Find corners in the right range
        blurred = cv2.GaussianBlur(grey, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        annotated = frame.copy()
        
        if self.countFrames%30 == 0:    #Refinds the square every X frames

            # ========== Find contours ==========
            contours, _ = cv2.findContours(
                edges,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE     #SWITCH SIMPLE <---> NONE
            )  
            
            for cnt in contours:
                epsilon = 0.02 * cv2.arcLength(cnt, True)
                square = cv2.approxPolyDP(cnt, epsilon, True)
                
                # ========== Filters ===========
                if not len(square) == 4:    #Makes sure it has 4 edges
                    continue
                
                area = cv2.contourArea(square)
                
                if area < 800:      #Min area
                    continue
                
                x, y, w, h = cv2.boundingRect(square)
                ratio = w / float(h)
                
                if ratio < 0.8 or ratio > 1.2:  #Makes sure its square shaped (maybe increase to make it)
                    continue
                
                self.poly = square
                
        if self.poly is None:   # Makes sure always finds a square before proceeding
            self.countFrames -= 1
        else:
            cv2.drawContours(annotated, [self.poly], 0, (0,255,0), 2)
            
            M = cv2.moments(self.poly)

            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            
            x, y, w, h = cv2.boundingRect(self.poly)
            
        
            # cv2.goodFeaturesToTrack(image, maxCorners, qualityLevel, minDistance)
            corners = cv2.goodFeaturesToTrack(blurred,200,0.003,20)
            
            if corners is not None:
                corners = corners.astype(int)
                for corner in corners:
                    x, y = corner.ravel()
                    
                    dist = np.sqrt((cx-x)**2 + (cy-y)**2)
                    ran = 1.1*np.sqrt((w/2)**2+(h/2)**2)  # Maximum distance away from center
                    
                    if dist > ran:
                        continue
                    
                    cv2.circle(annotated, (x, y), 5, (255, 0, 0), -1)
        
        self.countFrames += 1
        print(self.countFrames)
        return annotated
              
      # Starts Stream (Change camera info here)         
    def startStream(self):
        if self.running:
            return
        
        self.cap = cv2.VideoCapture(self.URL)
        
        # Change resolution here
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 60)
        
        if not self.cap.isOpened():
            self.status = "ERROR"
            print("Camera Failed")
            self.cap = None
            return
        
        self.running = True
        self.status = "ONLINE"
        
        threading.Thread(target=self.stream_thread, daemon=True).start()    #Starts stream thread once running
    
    def setMode(self, x):
        self.mode = x
        self.poly = None
        self.countFrames = 0
    
    # Ends stream
    def endStream(self):
        self.running = False
        self.status = "OFFLINE"
        
        if self.cap:
            self.cap.release()
            self.cap = None
    
    # Return Selected Captured Frame
    def getFrame(self):
        return self.output
    
    # Returns a txt of Camera Status
    def getStatus(self):
        return self.status
    
    # Returns the geometry (and position) of ellipse
    def getEllipse(self):
        return self.ellipse
        
        