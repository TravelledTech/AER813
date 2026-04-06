import cv2
import numpy as np
import threading
import time
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "protocol_whitelist;file,rtp,udp|fflags;nobuffer|flags;low_delay|framedrop;1"

# Use this class for handling video streaming (Probably also use this for the edge detection and position handling)
# Have 2 methods of score
# Distance based (High score the closer it is) -> 50 if same location, -1 per pixel distance (adjust weights later)
# Area -> 50 if same size
# Maybe have another score for orientationm but think about that one later

# Have it so it needs to refind the ellipse if none has been found for ~20 frames

#For corner detection
#https://docs.opencv.org/4.x/dc/d0d/tutorial_py_features_harris.html
#https://docs.opencv.org/4.x/d4/d8c/tutorial_py_shi_tomasi.html
#https://docs.opencv.org/3.4/d4/dee/tutorial_optical_flow.html
# https://arxiv.org/pdf/2209.02205 < not using this but interesting
#

#Maybe make a different file for spinning and circle detection?
#Maybe make a seperate version for horizontal viewing

# New pipeline for rotation detection
# (Starts the same as the original one)
# This time, instead of detection one face, detects multiple
# Continues to track them untill their aspect ration becomes too big
# Corners are the important part, use solvePnP to solve for rotation matrix
# Figure out how to prune the points and figure out how to deal with frame skips

class video:
    def __init__(self, URL, calib):
        
        #Stuff for camera
        self.URL = URL
        self.cap = None
        self.running = False
        self.status = "OFFLINE"
        self.mode = 0   #Starting Mode
        # 0 = Normal
        # 1 = Ellipse
        # 2 = Ellipse Contours
        # 3 = Spinning
        # 4 = Spinning contours
        
        self.conBool = False
        
        # Camera specs
        self.fps = 60
        self.frameTime = 1.0/60 #Time between frames
        self.xRes = 1280
        self.yRes = 720
        
        #Stuff for ellipse tracking
        self.hasFound = False
        self.countFrames = 0
        
        self.lastCenter = None
        self.lastArea = None
        self.ellipse = None
        
        self.output = None
        self.outVar = 0
        
        self.delay = 10 #delay between each frame (in ms)
        
        self.poly = None
        
        #Stuff for spin rate
        self.prev_grey = None   #Use previous frame combined with new one tp reduce motion blur effects
        self.prevPoly = None  
        
        self.velocity = 0
        
        #V2 velocity tracking for more complicated objects
        self.prev_grey2 = None   #This one is reused, remove one finialised the version I will use
        self.prev_pts = None
        self.prev_angle = None
        
        #V3 Stuff
        self.unit3Dpoints = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]
        ], dtype=np.float32)
        self.lastRVEC = {}
        self.lastTime = time.perf_counter()
        
        self.camMatrix = calib
        
        self.prevPts = None
        
        self.movingAvg = [0.0]
        self.movingAvgComponents = []
        self.velocityComponents = np.array([0.0, 0.0, 0.0])
        
        

    # Runs the streaming thread (all camera stuff will happen here) (moved to processes)
    def stream_thread(self):
        try:
            while self.running:
                if self.cap is None or not self.cap.isOpened():
                    break
                
                try:
                    if not self.cap.grab():
                        time.sleep(0.01)
                        continue
                    
                    ret, frame = self.cap.retrieve()
                    if not ret or frame is None:
                        continue
                    
                    self.processes(frame)
                except Exception as e:
                    print(f"Error grabbing frame: {e}")
                    break
        finally:
            print(f"Safely releasing camera {self.URL}...")
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            
                
    def processes(self, frame):
        grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.mode == 0:  #Normal
            self.output = frame
        elif self.mode == 1:    #Ellipse
            self.output = self.contourDetection(grey, frame)
        elif self.mode == 2:    #EllipseC
            self.output = self.rotationV2(grey, frame)
            self.angularVel()
        elif self.mode == 3:    #EllipseC
            self.output = self.rotationV3(grey, frame)
        
    
    def angularVel(self):   #Only used for rotationV2, uses the vectors of each side to determine rotation rate, swith to PnP solver for V3
        if not self.prevPoly is None:
            p1=[]
            p2=[]
            for i in range(4):
                p1.append(self.prevPoly[i][0])  #Use p1[i][ii], i for point and ii for x and y
                p2.append(self.poly[i][0])
            
            total = 0
            for i in range(4):
                x1 = (i+1)%4
                x2 = i
                a1 = (np.arctan2(p1[x1][1]-p1[x2][1], p1[x1][0]-p1[x2][0]))
                a2 = (np.arctan2(p2[x1][1]-p2[x2][1], p2[x1][0]-p2[x2][0]))
                total += (a2-a1+np.pi/4)%(np.pi/2)-np.pi/4
            deltaA = total/4
            self.velocity = deltaA/self.frameTime
            
            
        self.prevPoly = self.poly
    
    #Image preprocessing for contour (ellipse) Detection
    def contourPreprocessing(self, grey, frame):
        blurred = cv2.GaussianBlur(grey, (5, 5), 0)
        return cv2.Canny(blurred, 50, 150)
    
    #Image preprocessing for corner (spinning) Detection (USE THE OTHER ONE)
    def cornerPreprocessing(self, grey, frame):
        #Combines the previous and current frame to help reduce effects of motion blur
        if self.prev_grey is not None:
            blended = cv2.addWeighted(grey, 0.8, self.prev_grey, 0.2, 0)
            self.prev_grey = grey.copy()
        else:
            self.prev_grey = grey.copy()
            blended = grey
        
        #Different filters compared to the previous one
        thick_blur = cv2.medianBlur(blended, 7)
        thresh = cv2.adaptiveThreshold(thick_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 7)
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask
    
    def cornerPreprocessing2(self, grey, frame):    #seems to work better
        smooth = cv2.bilateralFilter(grey, 9, 75, 75)
        kernel = np.ones((3,3), np.uint8)
        opened = cv2.morphologyEx(smooth, cv2.MORPH_OPEN, kernel)
        edges = cv2.Canny(opened, 30, 120)
        return cv2.dilate(edges, None, iterations=1)

    #Finds the ellipse (or engine bell), actual coordinates will be processed in a different file
    def contourDetection(self, grey, frame):
        # =========== Edge Detection =========== (Moved to a different function)
        edges = self.contourPreprocessing(grey, frame)
        
        annotated = frame.copy()

        # ========== Find contours ==========
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_SIMPLE     #SWITCH SIMPLE <---> NONE
        )                               # TEST WHICH ONE PERFORMS BETTER
        
        bestEllipse = None
        Score = -1e9
        for cnt in contours:
            # ========== Contour Filters ========== (Adjust)
            if len(cnt) < 50:   # Minimum contour length
                continue
            
            contourArea = cv2.contourArea(cnt) # Sets minimum area
            if contourArea < 800:
                continue
            
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            
            # If it takes exactly 4 points to define the shape, it's a square. Reject it!
            if len(approx) == 4:
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
            if fill < 0.9 or fill > 1.1:
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
                
                if self.lastCenter is None:
                    continue
                
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
        
        if self.conBool:
            return edges
        else:
            return annotated
    
    #Finds the spin rate (kinda bad right now)
    def rotationV2(self, grey, frame):
        edges = self.cornerPreprocessing2(grey, frame)
        annotated = frame.copy()
        
        # Get image dimensions to set limits
        img_h, img_w = edges.shape[:2]
        screen_area = img_h * img_w

        # Using RETR_TREE gives us the hierarchy [Next, Previous, Child, Parent]
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        best_candidate = None
        max_area = 0

        if hierarchy is not None:
            for i, cnt in enumerate(contours):
                area = cv2.contourArea(cnt)
                
                if area > (screen_area * 0.8):  # Makes sure the area isnt just the entire screen
                    continue     
                
                if area < 1000:  # Filters small objects
                    continue
            
                hull = cv2.convexHull(cnt)  # Bounding Box
                peri = cv2.arcLength(hull, True)
                approx = cv2.approxPolyDP(hull, 0.04 * peri, True)

                if len(approx) == 4:    # Makes sure its 4 sided
                    x, y, w, h = cv2.boundingRect(hull)
                    parent_idx = hierarchy[0][i][3]
                    ratio = min(w, h) / max(w, h)
                    
                    if ratio < 0.8 or parent_idx == -1:
                        continue
                    
                    if x > 2 and y > 2 and (x + w) < (img_w - 2):   # Ensure it's not touching the very edge of the camera sensor
                        if area > max_area:
                            max_area = area
                            best_candidate = approx

        if best_candidate is not None:
            self.poly = best_candidate
            cv2.drawContours(annotated, [self.poly], 0, (0, 255, 0), 2)
        
        if self.conBool:
            return edges
        else:
            return annotated
    
    # Old (bad) code for rotation detection
    # def rotationV1(self, grey, frame):
    #     # Detect a square every so often (maybe every 60 frames (or every second))
    #     # Find corners in the right range
    #     blurred = cv2.GaussianBlur(grey, (5, 5), 0)
    #     edges = cv2.Canny(blurred, 50, 150)
        
    #     edges = self.testPreproccessing(grey, frame)
        
    #     #annotated = edges.copy()
    #     annotated = frame.copy()
        
    #     if True: #self.countFrames%20 == 0:    #Refinds the square every X frames

    #         # ========== Find contours ==========
    #         contours, _ = cv2.findContours(
    #             edges,
    #             cv2.RETR_TREE,              #SWITCH EXTERNAL <---> TREE
    #             cv2.CHAIN_APPROX_SIMPLE     #SWITCH SIMPLE <---> NONE
    #         )  
            
    #         for cnt in contours:
    #             epsilon = 0.02 * cv2.arcLength(cnt, True)
    #             square = cv2.approxPolyDP(cnt, epsilon, True)
    #             # ========== Filters ===========
    #             if not len(square) == 4:    #Makes sure it has 4 edges
    #                 continue
                
    #             area = cv2.contourArea(square)
                
    #             if area < 800:      #Min area
    #                 continue
                
    #             rect = cv2.minAreaRect(cnt)
    #             (x, y), (w, h), angle = rect
    #             if h == 0 or w == 0:
    #                 continue
    #             ratio = min(w, h) / max(w, h)
                
    #             if ratio < 0.8:
    #                 continue
                
    #             self.poly = square
                
    #     if self.poly is None:   # Makes sure always finds a square before proceeding
    #         self.countFrames -= 1
            
    #     # =========== Corner Detection ===========
    #     else:
    #         cv2.drawContours(annotated, [self.poly], 0, (0,255,0), 2)
            
    #         M = cv2.moments(self.poly)

    #         cx = int(M["m10"] / M["m00"])
    #         cy = int(M["m01"] / M["m00"])
            
    #         x, y, w, h = cv2.boundingRect(self.poly)
    #         area = cv2.contourArea(self.poly)
            
    #         ran = int((area**.5)/(2**.5))  # Maximum distance away from center
            
    #         mask = np.zeros(blurred.shape, dtype=np.uint8)
    #         cv2.circle(mask, (cx, cy), ran, 255, -1)
        
    #         # cv2.goodFeaturesToTrack(image, maxCorners, qualityLevel, minDistance)
    #         corners = cv2.goodFeaturesToTrack(edges,200,0.01,10, mask=mask)
            
    #         if corners is not None:
    #             corners = corners.astype(int)
    #             for corner in corners:
    #                 x, y = corner.ravel()
                    
    #                 dist = np.sqrt((cx-x)**2 + (cy-y)**2)
    #                 diff = abs((ran-dist)/ran)
                    
    #                 if diff > 0.1:
    #                     continue
    #                 cv2.circle(annotated, (x, y), 5, (255, 0, 0), -1)
        
    #     self.countFrames += 1
    #     print(self.countFrames)
    #     return annotated
        
    def rotationV3(self, grey, frame):
        edges = self.cornerPreprocessing2(grey, frame)
        annotated = frame.copy()
        img_h, img_w = edges.shape[:2]
        
        currTime = time.perf_counter()
        dt = currTime - self.lastTime   #Change in time
        deltaCurrFrame = []             #Stores change frame
        nextRVEC = {}   #Stores all orientations  in this frame
        
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_SIMPLE     #SWITCH SIMPLE <---> NONE
        )
        
        matchVel = []   # velocities for contours that match the prev
        matchOmega = [] # For XYZ component
        
        # Probably apply similar filters but not score.
        for cnt in contours:
            
            # ========== Filters ===========
            hull = cv2.convexHull(cnt)
            peri = cv2.arcLength(hull, True)
            approx = cv2.approxPolyDP(hull, 0.02 * peri, True)
            area = cv2.contourArea(cnt)
            
            if not len(approx) == 4:
                continue
            if cv2.contourArea(cnt) < 800:
                continue
            if len(cnt) < 100:
                continue
            
            x, y, w, h = cv2.boundingRect(hull)
            ratio = min(w, h) / max(w, h)
            
            if ratio < 0.6:
                continue
            if not(x > 2 and y > 2 and (x + w) < (img_w - 2)):
                continue
            
            hullArea = cv2.contourArea(hull)
            solidity = float(area) / hullArea if hullArea > 0 else 0
            
            if solidity < 0.9:
                continue
            
            # =========== PnP Stuff ==========
            #Makes sure [0] is top right
            cx, cy = self.getCentroid(approx)
            imgPoints = approx.astype(np.float32).reshape(4, 2)
            
            match = None    #Used to determine if it matches the previous frame
            for oldPos in self.lastRVEC.keys():
                if np.sqrt((cx-oldPos[0])**2 + (cy-oldPos[1])**2) < 60:
                    match = oldPos
                    break
            
            # Get previous points and sorts currebt
            prevPts = self.lastRVEC[match]['pts'] if match else None
            imgPoints = self.sortPoints(imgPoints, prevPts)
            
            #Refine corners
            imgPoints = cv2.cornerSubPix(grey, imgPoints, (5, 5), (-1, -1), (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001))
            success, rvec, tvec = cv2.solvePnP(self.unit3Dpoints, imgPoints, self.camMatrix, None, flags=cv2.SOLVEPNP_IPPE_SQUARE)
            
            if success:
                nextRVEC[(cx, cy)] = {'rvec': rvec, 'pts': imgPoints}
                cv2.drawContours(annotated, [approx], -1, (0, 255, 0), 2)
                
                imgPoints = approx.astype(np.float32).reshape(4, 2)
                imgPoints = self.sortPoints(imgPoints, prevPts)
                
                if match is not None and dt > 0:
                    Rcurr, _ = cv2.Rodrigues(rvec)
                    Rprev, _ = cv2.Rodrigues(self.lastRVEC[match]['rvec'])
                    Rdelta = np.dot(Rcurr, Rprev.T)
                    rvecDelta, _ = cv2.Rodrigues(Rdelta)
                    omegaVector = rvecDelta.ravel() / dt
                    matchVel.append(np.linalg.norm(rvecDelta) / dt)
                    matchOmega.append(omegaVector)
        
        #self.movingAvg[0] = self.movingAvg[1]
        #self.movingAvg[1] = self.movingAvg[2]
        
        if matchVel:
            vel = np.median(matchVel)
            omega = np.median(matchOmega, axis=0)
            
            # If velocity too low, just make it zero, reduces noise
            if vel < 0.2: 
                avgAngle = 0
                omega = np.array([0.0, 0.0, 0.0])
            #self.movingAvg[2] = avgAngle
            
        else:
            vel = self.movingAvg[-1] * 0.95
            if self.movingAvgComponents:
                omega = self.movingAvgComponents[-1] * 0.95
            else:
                omega = np.zeros(3)
        
        self.movingAvg.append(vel)
        if len(self.movingAvg) > 5:
            self.movingAvg.pop(0)
        self.velocity = sum(self.movingAvg) / len(self.movingAvg)
        
        self.movingAvgComponents.append(omega)
        if len(self.movingAvgComponents) > 5:
            self.movingAvgComponents.pop(0)
        self.velocityComponents = np.mean(self.movingAvgComponents, axis=0)
        
        self.lastTime = currTime
        self.lastRVEC = nextRVEC
        if self.conBool:
            return edges
        else:
            return annotated
    
    #Gets centroid of given polygon
    def getCentroid(self, poly):
        M = cv2.moments(poly)
        
        if M["m00"] == 0:
            return (0, 0)
        
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        
        return (cx, cy)
    
    def sortPoints(self, pts, prevPts = None):
        
        if prevPts is None:
            center = np.mean(pts, axis = 0)
            diff = pts - center
            angles = np.arctan2(diff[:, 1], diff[:, 0])
            return pts[np.argsort(angles)]
        
        orderedPts = np.zeros_like(pts)
        ptsCopy = pts.copy()
        
        for i in range(4):
            dists = np.linalg.norm(ptsCopy - prevPts[i], axis = 1)
            idx = np.argmin(dists)
            orderedPts[i] = ptsCopy[idx]
            
            ptsCopy[idx] = [np.inf, np.inf]
            
        return orderedPts
    
    # Starts Stream (Change camera info here)         
    def startStream(self):
        if self.running:
            return True
        
        self.cap = cv2.VideoCapture(self.URL, cv2.CAP_FFMPEG)   #Change to FFMEG for host camera
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            self.status = "ERROR"
            print("Camera Failed")
            self.cap = None
            return False
        
        # # Change resolution here
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.xRes)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.yRes)
        # self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        # self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  #REMOVE THIS LATER
        # self.cap.set(cv2.CAP_PROP_EXPOSURE, -9)
        
        self.running = True
        self.status = "ONLINE"
        
        threading.Thread(target=self.stream_thread, daemon=True).start()    #Starts stream thread once running
        return True
    
    # Ends stream
    def endStream(self):
        self.running = False
        self.status = "OFFLINE"
        
        # if self.cap:
        #     self.cap.release()
        #     self.cap = None
    
    # Return Selected Captured Frame
    def getFrame(self):
        if not self.running:
            return None
        return self.output
    
    # Returns a txt of Camera Status
    def getStatus(self):
        return self.status
    
    # Returns the geometry (and position) of ellipse
    def getEllipse(self):
        return self.ellipse
    
    # Set Camera modex
    def setMode(self, mode):
        self.hasFound = False
        self.mode = mode
        
    def setCon(self, mode):
        self.conBool = mode
        
    def getVel(self):
        return self.velocity
    
    def getVelocityComponents(self):
        return self.velocity_components
        
        