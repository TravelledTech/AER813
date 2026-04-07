# Code speficially used for the MACE test
# Instead of 2 cameras, use 1 calibrated camera with ardu

import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedStyle
from PIL import Image, ImageTk
import cv2
import time
import numpy as np
from maceVideoStream import video
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import serial
import control

# ===== Main =====
class Cam:
    def __init__(self, root):   
        
        #========== Initial Variables ==========
        self.sendTime = 1.0/10  #Sends the rotation data every 10hz
        
        self.timeH = [] # Used for angular velocity calculation
        self.angleH = []
        
        self.root = root
        self.UIToggle = True
        
        self.aspectRatio = 16/9
        
        # If cam is on or off
        self.cam1Status = False
        
        # Status Text
        self.cam1TxT = "OFFLINE"
        
        self.cam1URL = 0    # 0 for webcam
        
        self.vid1 = video(self.cam1URL)
        
        #Ui sizing
        self.xFrameHeight = 0
        self.xFrameWidth = 0
        
        self.telemetry = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        # [0] XPosition
        # [1] YPosition
        # [2] ZPosition
        # [3] Pitch
        # [4] Roll
        # [5] Yaw
        # [6] Yaw velocity
        # [7] Steady state
        # [8] Overshoot%
        # [9] Settling time
        
        # ========== CHANGE THIS DEPENDIGN ON WHICH PORT THE ARDUINO IS IN =========
        PORT = 'COM4' 
        BAUD = 115200
        
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=0.1, write_timeout=0)
            time.sleep(1.5) # Give the Arduino time to reboot after connection
            print(f"Successfully connected to {PORT}")
        except Exception as e:
            print(f"Serial connection failed: {e}")
            self.ser = None
            
        
        self.root.bind("<Configure>", self.resize_main)
        
        self.fallback_pil = Image.open("fallback.png")
        self.fallback = ImageTk.PhotoImage(self.fallback_pil, master=self.root)
        
        self.winSize = [root.winfo_screenwidth(), root.winfo_screenheight()]
        print(self.winSize)
        
        self.fps = 60                   # Camera FPS
        self.frameTime = 1000.0/60      # Time between frames (ms)
        
        # ========== Interface stuff ==========
        root.title("maceGUI")
        root.attributes("-fullscreen", True)
        #root.geometry("{0}x{1}+0+0".format(root.winfo_screenwidth(), root.winfo_screenheight()))
        #root.geometry("900x560")
        
        style = ThemedStyle(root)
        style.set_theme("equilux")
        root.configure(bg=style.lookup(".", "background"))
        root.configure(bg="black")
        
        #Use 7 frames (probably inefficient?), maybe 5 instread
        
        self.main_frame = ttk.Frame(root)
        self.main_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Used for making the cams full screen, make it so it expands if clicked and zooms back out when 'esc'
        self.LeftCamFull = ttk.Frame(root)
        self.RightCamFull = ttk.Frame(root)
        
        self.TL_Frame = ttk.Frame(self.main_frame)
        self.TR_Frame = ttk.Frame(self.main_frame)
        self.BL_Frame = ttk.Frame(self.main_frame)
        self.BR_Frame = ttk.Frame(self.main_frame)
        
        for i in range(2):
            self.main_frame.columnconfigure(i, weight=1, uniform="equal")
            self.main_frame.rowconfigure(i, weight=1, uniform="equal")
    
        self.TL_Frame.grid(column=0, row=0, sticky="nsew", padx=25, pady=25)
        self.TR_Frame.grid(column=1, row=0, sticky="nsew", padx=25, pady=25)
        self.BL_Frame.grid(column=0, row=1, sticky="nsew", padx=25, pady=25)
        self.BR_Frame.grid(column=1, row=1, sticky="nsew", padx=25, pady=25)
        
        for i in range(2):
            self.BR_Frame.columnconfigure(i, weight=1, uniform="equal")
        self.BR_Frame.rowconfigure(0, weight=0)
        self.BR_Frame.rowconfigure(1, weight=1)

        self.TL_Frame.bind("<Configure>", self.print_size)
        
        ttk.Label(self.BR_Frame, text = "Control Panel", foreground = "tomato3", font = ("Segoe UI", 30, "bold underline")).grid(column = 0, row = 0, columnspan=2)
        dataFrame = ttk.Frame(self.BR_Frame)
        buttonFrame = ttk.Frame(self.BR_Frame)
        dataFrame.grid(column=0, row=1, sticky="nsew", padx=5, pady=20)
        buttonFrame.grid(column=1, row=1, sticky="nsew", padx=5, pady=20)

        # ========== UI Elements ==========
        ttk.Label(dataFrame, text = "Status", foreground = "lightgray", anchor="center", font = ("Segoe UI", 14, "bold")).pack(fill="x")
        
        self.cam1Label = ttk.Label(
            dataFrame,
            text=f"Camera 1 Status: \t\t\t{self.cam1TxT}",
            font=("Segoe UI", 10),
            foreground = "lightgray"
        )
        self.cam1Label.pack(anchor="center")
        
        
        ttk.Label(dataFrame, text = "Current Data", foreground = "lightgray", anchor="center", font = ("Segoe UI", 14, "bold")).pack(fill="x")
        ttk.Label(buttonFrame, text = "Controls", foreground = "lightgray", anchor="center", font = ("Segoe UI", 14, "bold")).pack(fill="x")
        
        ttk.Button(buttonFrame,
                                text = "EXIT",
                                command = self.exitApp).pack(fill="x")
        ttk.Button(buttonFrame,
                                text = "Start Cameras",
                                command = self.startStream).pack(fill="x")
        ttk.Button(buttonFrame,
                                text = "End Cameras",
                                command = self.endStream).pack(fill="x")
        ttk.Button(buttonFrame,
                                text = "Reset Plot",
                                command = self.resetPlot).pack(fill="x")
        
        self.kpEntry = ttk.Entry(buttonFrame)
        self.kpEntry.pack(fill="x")
        self.kpEntry.bind("<Return>", self.Kp)
        
        self.kiEntry = ttk.Entry(buttonFrame)
        self.kiEntry.pack(fill="x")
        self.kiEntry.bind("<Return>", self.Ki)
        
        self.kdEntry = ttk.Entry(buttonFrame)
        self.kdEntry.pack(fill="x")
        self.kdEntry.bind("<Return>", self.Kd)
        
        self.mode_var = tk.StringVar(value=0)
        self.mode = 0
        ttk.Radiobutton(
            buttonFrame,
            text="Standard Camera",
            variable=self.mode_var,
            value=0,
            command=self.setMode1
        ).pack(anchor="w", pady=2)
        
        ttk.Radiobutton(
            buttonFrame,
            text="ArUco",
            variable=self.mode_var,
            value=1,
            command=self.setMode2
        ).pack(anchor="w", pady=2)

        
        text = (
            f"\nX-Position: \t\t{self.telemetry[0]:.2f}\n"
            f"Y-Position: \t\t{self.telemetry[1]:.2f}\n"
            f"Z-Position: \t\t{self.telemetry[2]:.2f}\n"
            f"Pitch: \t\t\t{self.telemetry[3]:.2f}\n"
            f"Roll: \t\t\t{self.telemetry[4]:.2f}\n"
            f"Yaw: \t\t\t{self.telemetry[5]:.2f}\n"
            f"Rotation: \t\t{self.telemetry[6]:.2f}\n\n"
            f"Error: \t\t\t{self.telemetry[7]:.2f}\n"
            f"Overshoot: \t\t{self.telemetry[8]:.2f}\n"
            f"Settling Time: \t\t{self.telemetry[9]:.2f}\n"
        )
                
        self.info = ttk.Label(dataFrame, text=text,
                  foreground = "lightgray",
                  font = ("Segoe UI", 10))
        self.info.pack(anchor="center")
        # Add some systems info here too I guess like camera status and stuff
        
        self.cam1_label = ttk.Label(self.TL_Frame, image=self.fallback)
        self.cam1_label.image = self.fallback
        self.cam1_label.pack(fill="both", expand=True)
        
        # self.cam2_label = ttk.Label(self.TR_Frame, image=self.fallback)
        # self.cam2_label.image = self.fallback
        # self.cam2_label.pack(fill="both", expand=True)
        # replace with matplot
        
        # ===== Plot =====
        self.yawHistory = []
        self.timeHistory = []
        self.startTime = 0

        
        self.fig = Figure(figsize=(5.33, 3), dpi=100, facecolor='#2b2b2b')
        self.yawPlot = self.fig.add_subplot(111)
        
        self.yawPlot.set_facecolor('black')
        self.yawPlot.tick_params(colors='white', labelsize=9)
        for spine in self.yawPlot.spines.values():
            spine.set_color('white')
        
        self.fig.tight_layout()
        self.plotLimit = 100
        
        self.yawPlot.set_xlabel("Time (s)", color='white', fontsize=10)
        self.yawPlot.set_ylabel("Angle (rad)", color='white', fontsize=10)
        self.yawPlot.set_title("Yaw", color='white', fontsize=12)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.TR_Frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        self.line, = self.yawPlot.plot([], [], color='lawngreen', linewidth=1.5)

        #Canvas (for docking UI)
        self.dockingUI = tk.Canvas(self.BL_Frame, width = self.xFrameWidth, height = self.xFrameHeight, background="black", highlightthickness=0)
        self.dockingUI.pack(fill="both", expand=True)
        
        self.BL_Frame.bind("<Configure>", self.createUI)
    
    # =========== Stream stuff ===========
    def streamThread(self):
        if self.cam1Status:
            self.setFrame()
            if self.mode == 1:
                 pos = self.vid1.getPos()
                 rot = self.vid1.getRot()
                 self.telemetry[0] = pos[0]
                 self.telemetry[1] = -pos[1]
                 self.telemetry[2] = pos[2]
                 
                 self.telemetry[3] = rot[0] #(rot[0] % (2 * np.pi)) - np.pi
                 self.telemetry[4] = rot[1]
                 self.telemetry[5] = rot[2]
                 
                 currentTime = time.time() - self.startTime
                 currentYaw = self.telemetry[4]
                 
                 if not hasattr(self, 'last_send'): 
                    self.last_send = 0
                 
                 # For Vel
                 self.timeH.append(currentTime)
                 self.angleH.append(currentYaw)
                 vel = 0
                 length = len(self.angleH)
                 if length >= 2:
                     if length > 5:
                         self.timeH.pop(0)
                         self.angleH.pop(0)
                         
                     dt = self.timeH[-1] - self.timeH[0]
                     if dt > 0:
                         vel = (self.angleH[-1]-self.angleH[0])/dt
                 
                 self.telemetry[6] = vel   
                 
                 # For plot
                 self.timeHistory.append(currentTime)
                 self.yawHistory.append(currentYaw)
                 
                 if self.yawHistory[0] == 0:
                     self.yawHistory.pop(0)
                     self.timeHistory.pop(0)
                 
                 if len(self.timeHistory) % 2 == 0:
                     self.updatePlots()
                     self.calcMetrics()
                
                # packet limiter (currently sending at 30hz)
                 if currentTime - self.last_send >= self.sendTime:
                     self.sendData("T", np.rad2deg(-self.telemetry[4]))
                     self.last_send = currentTime
 
            else:
                 self.telemetry = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                 self.yawHistory = []
                 self.timeHistory = []
                 self.startTime = time.time()
            
            self.changeBars()   #Make sure this only runs on option 1 or 2 later
            self.updateInfo()
            self.updateStatus()
            self.root.after(16, self.streamThread)
    
    def sendData(self, label, value):
        try:
            # Force it to a standard Python float to strip any hidden Numpy array formatting
            clean_value = float(np.squeeze(value))
            
            if self.ser and self.ser.is_open:
                # Format it strictly
                packet = f"{label}={clean_value:.4f}\n" 
                
                # Send it as strict ASCII
                self.ser.write(packet.encode('ascii'))
                
                # FORCE PYTHON TO CONFESS WHAT IT SENT
                print(f"PYTHON SENT: '{packet.strip()}'") 
                
        except Exception as e:
            print(f"Serial Error in sendData: {e}")
    
    def updatePlots(self):
        # 1. Push the updated lists to the line object
        self.line.set_data(self.timeHistory, self.yawHistory)
        
        self.yawPlot.relim()
        self.yawPlot.autoscale_view()
        
        self.yawPlot.set_ylim(-np.pi, np.pi)
        
        self.canvas.draw()
        
    # ========= UI Functions Buttons =======
    def resetPlot(self):
        self.timeH = [] # Used for angular velocity calculation
        self.angleH = []
        self.yawHistory = []
        self.timeHistory = []
        self.startTime = time.time()
        
    def calcMetrics(self):
        # self.yawHistory = []
        # self.timeHistory = []
        
        if len(self.yawHistory) < 2:
            return
        
        initialOffset = self.yawHistory[0]
        initialJump = abs(initialOffset)
        
        if initialOffset > 0:
            # Started positive -> Overshoot is the lowest negative number
            peak_past_zero = min(self.yawHistory)
            if peak_past_zero > 0: 
                peak_past_zero = 0.0 # Hasn't crossed the 0 line yet
        else:
            # Started negative -> Overshoot is the highest positive number
            peak_past_zero = max(self.yawHistory)
            if peak_past_zero < 0: 
                peak_past_zero = 0.0 # Hasn't crossed the 0 line yet
    
        overshoot = (abs(peak_past_zero) / initialJump) * 100
        steadyState = self.yawHistory[-1]
        
        if overshoot > 500: 
            overshoot = 0
        # [7] Steady state
        # [8] Overshoot%
        # [9] Settling time
        self.telemetry[7] = steadyState
        self.telemetry[8] = overshoot
        #self.telemetry[9] = sett
        
    def calcSettling(self):
        if len(self.timeHistory) < 10:
            return
        startTime = self.timeHistory[0]
        target = 0
        finalValue = self.yawHistory[-1]
        
        initialJump = abs(self.yawHistory[0] - target)
        band = 0.1 * initialJump   #5% of peak value
        
        settlingIndex = 0
        for i in range(len(self.timeHistory)-1, -1, -1):
            if abs(self.yawHistory[i] - finalValue) > band:
                settlingIndex = i
                break
        self.telemetry[9] = self.timeHistory[settlingIndex] - startTime
        
    def print_size(self, event):    # Also resizes the photos
        self.xFrameWidth = event.width
        self.xFrameHeight = event.height
        
        print(self.xFrameWidth, self.xFrameHeight)
        
        self.setFrame()
                
    def setFrame(self):
        resized = self.fallback_pil.resize(
            (self.xFrameWidth, self.xFrameHeight),
            Image.LANCZOS)

        photo = ImageTk.PhotoImage(resized)
        
        if self.cam1Status == False:
            self.cam1_label.configure(image=photo)
            self.cam1_label.image = photo
        
        else:
            f1 = self.vid1.getFrame()
            if f1 is not None:
                frame = cv2.resize(f1, (self.xFrameWidth, self.xFrameHeight))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
                tk_img = ImageTk.PhotoImage(Image.fromarray(frame))
                self.cam1_label.configure(image=tk_img)
                self.cam1_label.image = tk_img
            else:
                self.cam1_label.configure(image=photo)
                self.cam1_label.image = photo
        
            
    def startStream(self):
        self.cam1Status = self.vid1.startStream()
        
        self.yawHistory = []
        self.timeHistory = []
        self.startTime = time.time()
        
        self.streamThread()
    
    def endStream(self):
        self.calcSettling()
        self.updateInfo()
        self.cam1Status = False
        
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.reset_output_buffer() 
            self.ser.reset_input_buffer()
        
        self.vid1.endStream()
        
    def updateStatus(self):
    
        self.cam1TxT = self.vid1.getStatus()
    
        self.cam1Label.config(text=f"Camera 1 Status: {self.cam1TxT}")
    
    def exitApp(self):
        
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()

        self.root.destroy()
        
    # Makes sure it stays 16/9
    def resize_main(self, event):

        win_w = self.root.winfo_width()
        win_h = self.root.winfo_height()
    
        target_ratio = 16 / 9
    
        # determine max 16:9 size inside window
        if win_w / win_h > target_ratio:
            height = win_h
            width = int(height * target_ratio)
        else:
            width = win_w
            height = int(width / target_ratio)
    
        self.main_frame.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            width=width,
            height=height
        )
    
    def updateInfo(self):
        text = (
            f"\nX-Position: \t\t{self.telemetry[0]:.2f}\n"
            f"Y-Position: \t\t{self.telemetry[1]:.2f}\n"
            f"Z-Position: \t\t{self.telemetry[2]:.2f}\n"
            f"Pitch: \t\t\t{self.telemetry[3]:.2f}\n"
            f"Roll: \t\t\t{self.telemetry[4]:.2f}\n"
            f"Yaw: \t\t\t{self.telemetry[5]:.2f}\n"
            f"Rotation: \t\t{self.telemetry[6]:.2f}\n\n"
            f"Error: \t\t\t{self.telemetry[7]:.2f}\n"
            f"Overshoot: \t\t{self.telemetry[8]:.2f}\n"
            f"Settling Time: \t\t{self.telemetry[9]:.2f}\n"
        )
        self.info.config(text=text)
    
    def setMode1(self): #Standard Cam
        self.vid1.setMode(0)
        self.mode = 0
    
    def setMode2(self): #Ellipse Cam
        self.vid1.setMode(1)
        self.mode = 1
    
    def Kp(self, event):
        value = self.kpEntry.get()
        value = float(value)
        
        self.sendData("KP", value)
        
    def Ki(self, event):
        value = self.kiEntry.get()
        value = float(value)
        
        self.sendData("KI", value)
        
    def Kd(self, event):
        value = self.kdEntry.get()
        value = float(value)
        
        self.sendData("KD", value)
        
    def createUI(self, event):
        # Canvas
        #718 x 382 (on laptop)
        # Center@ 359, 191
        
        # Setting up the Canvas Boundaries
        # 10-3-3
        # Divider takes up 10 pixels
        # main control, Z axis, angular velocity
        self.xFrameWidth = event.width
        self.xFrameHeight = event.height
    
        x = self.xFrameWidth
        y = self.xFrameHeight
    
        # clear out everything
        self.dockingUI.delete("all")
        
        l = int((x-40)/16)
        
        # 1 for leftmost point, 2 for rightmost
        # a for main ui, b for z ui, c for spin
        pc2 = x-10
        pc1 = pc2-l*2
        pb2 = pc1-10
        pb1 = pb2-l*2
        pa1 = 10
        pa2 = pb1-10
        
        self.dockingUI.create_line(x-1, 0, x-1, y, fill="white", width=2)
        self.dockingUI.create_line(x-9, 0, x-9, y, fill="white", width=2)
        
        self.dockingUI.create_line(pc1-1, 0, pc1-1, y, fill="white", width=2)
        self.dockingUI.create_line(pc1-9, 0, pc1-9, y, fill="white", width=2)
        
        self.dockingUI.create_line(pb1-1, 0, pb1-1, y, fill="white", width=2)
        self.dockingUI.create_line(pb1-9, 0, pb1-9, y, fill="white", width=2)
        
        self.dockingUI.create_line(pa1-1, 0, pa1-1, y, fill="white", width=2)
        self.dockingUI.create_line(pa1-9, 0, pa1-9, y, fill="white", width=2)
        
        mid = (pa2-pa1)/2+pa1
        ymid = y/2
        
        zCenter = int((pb2-pb1)/2)+pb1
        vCenter = int((pc2-pc1)/2)+pc1
        
        # UI Background (the lines)
        self.dockingUI.create_line(pa1, ymid, pa2, ymid, fill="white", width=2)
        self.dockingUI.create_line(mid, 0, mid, y, fill="white", width=2)
        
        # Change this for pixel step
        step = 15
        
        # ========= UI Markers ==========
        for i in range(0, int(mid)-pa1, step):
            if i%(step*2) == step:
                self.dockingUI.create_line(mid+i, ymid+5, mid+i, ymid-5, fill="white", width=2)
                self.dockingUI.create_line(mid-i, ymid+5, mid-i, ymid-5, fill="white", width=2)
            else:
                self.dockingUI.create_line(mid+i, ymid+8, mid+i, ymid-8, fill="white", width=2)
                self.dockingUI.create_line(mid-i, ymid+8, mid-i, ymid-8, fill="white", width=2)
                
        for i in range(0, int(mid)-pa1, step):
            if i%(step*2) == step:
                self.dockingUI.create_line(mid+5, ymid+i, mid-5, ymid+i, fill="white", width=2)
                self.dockingUI.create_line(mid+5, ymid-i, mid-5, ymid-i, fill="white", width=2)
            else:
                self.dockingUI.create_line(mid+8, ymid+i, mid-8, ymid+i, fill="white", width=2)
                self.dockingUI.create_line(mid+8, ymid-i, mid-8, ymid-i, fill="white", width=2)
        
        # Z bar stuff
        for i in range(y-step, 0, -step):
            if (y-i)%(step*2) == step:
                self.dockingUI.create_line(zCenter+8, i, zCenter-8, i, fill="white", width=2)
            else:
                self.dockingUI.create_line(zCenter+14, i, zCenter-14, i, fill="white", width=2)
        
        #Spin bar stuff
        self.dockingUI.create_line(pc1, ymid, pc2, ymid, fill="white", width=2)
        for i in range(step, int(ymid), step):
            if i%(step*2) == step:
                self.dockingUI.create_line(vCenter+8, ymid+i, vCenter-8, ymid+i, fill="white", width=2)
                self.dockingUI.create_line(vCenter+8, ymid-i, vCenter-8, ymid-i, fill="white", width=2)
            else:
                self.dockingUI.create_line(vCenter+14, ymid+i, vCenter-14, ymid+i, fill="white", width=2)
                self.dockingUI.create_line(vCenter+14, ymid-i, vCenter-14, ymid-i, fill="white", width=2)
        
        # =========== Now add the position stuff ============
        # X and Y position
        self.xBar = self.dockingUI.create_line(mid, ymid, mid, ymid, fill="red", width=2)
        self.yBar = self.dockingUI.create_line(mid, ymid, mid, ymid, fill="red", width=2)
        self.cBar = self.dockingUI.create_oval(mid+4, ymid-4, mid-4, ymid+4, fill="red", width=0)
        
        self.dockingUI.tag_lower(self.xBar)
        self.dockingUI.tag_lower(self.yBar)
        self.dockingUI.tag_lower(self.cBar)
        
        # Angle reticle
        self.reticle = []
        self.reticle.append(self.dockingUI.create_oval(mid-15, ymid-15, mid+15, ymid+15, fill="black", outline = "lawngreen", width=3))
        self.reticle.append(self.dockingUI.create_line(mid, ymid+15, mid, ymid+25, fill="lawngreen", width=2))
        self.reticle.append(self.dockingUI.create_line(mid, ymid-15, mid, ymid-25, fill="lawngreen", width=2))
        self.reticle.append(self.dockingUI.create_line(mid+15, ymid, mid+25, ymid, fill="lawngreen", width=2))
        self.reticle.append(self.dockingUI.create_line(mid-15, ymid, mid-25, ymid, fill="lawngreen", width=2))
        
        for i in self.reticle:
            self.dockingUI.tag_lower(i)
        
        # Z Position
        self.zBar = self.dockingUI.create_line(pb1, y-1, pb2, y-1, fill="red", width=2)
        self.dockingUI.tag_lower(self.zBar)
        
        # Rot Position
        self.rotBar = self.dockingUI.create_line(pc1, ymid, pc2, ymid, fill="red", width=2)
        self.dockingUI.tag_lower(self.rotBar)
    
    def changeBars(self):
        # Add a proper Scale
        xPos = self.telemetry[0]*500    #Im assuming it will be in cm?
        yPos = self.telemetry[1]*500
        zPos = self.telemetry[2]*500
        xRot = self.telemetry[4]*100    #Im assuming in radians?
        yRot = self.telemetry[3]*100
        zRot = self.telemetry[5]
        
        #Currently the main scale is every 15pixels
        # every 20 pixels for the z position
        
        x = self.xFrameWidth
        y = self.xFrameHeight
        l = int((x-40)/16)
        pc2 = x-10
        pc1 = pc2-l*2
        pb2 = pc1-10
        pb1 = pb2-l*2
        pa1 = 10
        pa2 = pb1-10
        mid = (pa2-pa1)/2+pa1
        ymid = y/2
        zCenter = int((pb2-pb1)/2)+pb1
        vCenter = int((pc2-pc1)/2)+pc1
        
        self.dockingUI.coords(self.xBar, mid, ymid+yPos, mid+xPos, ymid+yPos)
        self.dockingUI.coords(self.yBar, mid+xPos, ymid, mid+xPos, ymid+yPos)
        self.dockingUI.coords(self.cBar, mid+xPos+4, ymid+yPos-4, mid+xPos-4, ymid+yPos+4)
        self.dockingUI.coords(self.zBar, pb1, y-zPos, pb2, y-zPos)
        
        self.dockingUI.coords(self.reticle[0], mid+xRot-15, ymid+yRot-15, mid+xRot+15, ymid+yRot+15)
        self.dockingUI.coords(self.reticle[1], mid+xRot, ymid+yRot+15, mid+xRot, ymid+yRot+25)
        self.dockingUI.coords(self.reticle[2], mid+xRot, ymid+yRot-15, mid+xRot, ymid+yRot-25)
        self.dockingUI.coords(self.reticle[3], mid+xRot+15, ymid+yRot, mid+xRot+25, ymid+yRot)
        self.dockingUI.coords(self.reticle[4], mid+xRot-15, ymid+yRot, mid+xRot-25, ymid+yRot)
        
        self.dockingUI.coords(self.rotBar, pc1, ymid+zPos, pc2, ymid+zPos)
# ---------------- RUN ----------------
root = tk.Tk()
app = Cam(root)
root.mainloop()