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
# https://docs.opencv.org/3.4/d4/dee/tutorial_optical_flow.html

class video:
    def __init__(self, URL):
        
        # Initial Variables
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
        
        self.corners = [None, None, None, None]
        
        #Temp
        self.prev_grey = None


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
                #self.output = self.testPreproccessing(grey, frameRGB)
    
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
    
    def testPreproccessing(self, grey, frame):  # Test different filters
        if self.prev_grey is not None:
            blended = cv2.addWeighted(grey, 0.8, self.prev_grey, 0.2, 0)
            self.prev_grey = grey.copy()
        else:
            self.prev_grey = grey.copy()
            blended = grey
        
        thick_blur = cv2.medianBlur(blended, 7)
        thresh = cv2.adaptiveThreshold(thick_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 7)
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask
    
    def cornerDetection(self, grey, frame):
        edges = self.testPreproccessing(grey, frame)
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
                
                # # 3. Hierarchy Check: If it's the outermost possible thing, 
                # # and it's huge, it's probably the frame.
                # # hierarchy[0][i][3] is the Parent index. -1 means no parent.

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
        
        return annotated
    
    # def cornerDetection(self, grey, frame):
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
    
    def setMode(self, mode):
        self.mode = mode
        
        