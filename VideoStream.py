import cv2

# Use this class for handling video streaming (Probably also use this for the edge detection and position handling)

class video:
    def __init__(self, URL):
        
        #Replace these with the final stream urls
        self.URL = URL
        self.cap = None
        self.running = False
        self.status = "OFFLINE"
    
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
        
        