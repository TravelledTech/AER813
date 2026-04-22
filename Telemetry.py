# Use this class to find the telemetry given the pixel coordinates
# Add calibration here and frames
import numpy as np
import cv2

class tele:
    def __init__(self, calib):
        self.calib = calib
        self.B = abs(self.calib['T'][0][0]) #Distance between cameras
        self.R1, self.R2, self.P1, self.P2, self.Q, _, _ = cv2.stereoRectify(
            calib['mtx0'], calib['dist0'], 
            calib['mtx1'], calib['dist1'], 
            (1280, 720), calib['R'], calib['T']
        )
        
        self.f = self.P1[0, 0]
        self.cx = self.P1[0, 2]
        self.cy = self.P1[1, 2]
        
        
    def calcTelemetry(self, lElip, rElip):
        if not lElip == None and not rElip == None:
            
            (cx1, cy1), (w1, h1), angle1 = lElip
            (cx2, cy2), (w2, h2), angle2 = rElip
            
            pt_l = np.array([[[cx1, cy1]]], dtype=np.float32)
            pt_r = np.array([[[cx2, cy2]]], dtype=np.float32)
            
            new_pt_l = cv2.undistortPoints(pt_l, self.calib['mtx0'], self.calib['dist0'], R=self.R1, P=self.P1)
            new_pt_r = cv2.undistortPoints(pt_r, self.calib['mtx1'], self.calib['dist1'], R=self.R2, P=self.P2)
            
            cx1 = new_pt_l[0][0][0]
            cx2 = new_pt_r[0][0][0]
            cy1 = new_pt_l[0][0][1]
            
            disp = cx1 - cx2
            if disp <= 0:
                return None
            
            z = (self.f * self.B) / disp
            x = ((cx1 - self.cx) * z / self.f) - (self.B / 2.0)
            y = (cy1 - self.cy) * z / self.f
            
            if w1 < h1:
                angle1 += 90
            angle1 = angle1 % 180
            angle1 = np.radians(angle1)
            major1 = max(w1, h1)
            minor1 = min(w1, h1)
            phi1 = np.arccos(minor1/major1)
            
            x1 = np.sin(phi1)*np.cos(angle1)
            y1 = np.sin(phi1)*np.sin(angle1)
            z1 = np.cos(phi1)
            
            if w2 < h2:
                angle2 += 90
            angle2 = angle2 % 180
            angle2 = np.radians(angle2)
            major2 = max(w2, h2)
            minor2 = min(w2, h2)
            phi2 = np.arccos(minor2/major2)
            
            x2 = np.sin(phi2)*np.cos(angle2)
            y2 = np.sin(phi2)*np.sin(angle2)
            z2 = np.cos(phi2)
            
            alpha = -np.arctan2(x1, z1)  #<This one is fine
            # alpha2 = np.arctan2(x2, z2)
            
            # if alpha1 >= alpha2:
            #     alpha = alpha1-np.deg2rad(15)
            # else:
            #     alpha = alpha1+np.deg2rad(15)
            
            beta1 = np.arctan2(y1, z1)   #< this one is not fine
            beta2 = np.arctan2(y2, z2)
            
            # if beta2 <= np.deg2rad(15):
            #     beta = -beta1+np.deg2rad(15)
            # else:
            #     beta = beta1+np.deg2rad(15)
            #     alpha = -alpha
            
            beta = (beta2**2 - beta1**2) / (4 * np.deg2rad(15))
            if beta > np.deg2rad(15):
                alpha = -alpha
            
            print(beta1, beta2)
            
            return [x, y, z, alpha, beta]
            
        else:
            return None
        
    def angleDiff(self, a, b):
        return np.abs(np.arctan2(np.sin(a-b), np.cos(a-b)))
        
        
        