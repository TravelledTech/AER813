import cv2

# Use this class for handling video streaming (Probably also use this for the edge detection and position handling)

class video:
    def __init__(self):
        
        #Replace these with the final stream urls
        self.URL1 = "temp"
        self.URL2 = "temp"
        
        self.cap1 = cv2.videocapture(self.URL1)
        self.cap2 = cv2.videocapture(self.URL2)
        
    def retVideo1(self):
        ret, frame  = self.cap1.read()
        return frame #add overlay somewhere
        