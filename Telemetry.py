# Use this class to find the telemetry given the pixel coordinates
# Add calibration here and frames

class tele:
    def __init__(self):
        self.lElip = None
        self.rElip = None
        
        self.Telemetry = [None, None, None, None, None, None]  #Pos X, Y and Z, Rot X, Y, Z
        
    def setElipse(self, elip1, elip2):
        self.lElip = elip1
        self.rElip = elip2
        
    def getTelemetry(self):
        return self.Telemetry
    
    def calcTelemetry(self):
        if not self.lElip == None and not self.rElip == None:
            (cx1, cy1), (w1, h1), angle1 = self.lElip
            (cx2, cy2), (w2, h2), angle2 = self.rElip
        
        
        