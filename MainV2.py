# Redo some of the code to account for 2, wireless cameras (can't really test right now)
# I guess also integrate the mace thing into this
# Cam1       | Cam2
# -----------+----------
# Docking GUI| Controls
# make 2 more files, one for docking vision one for mace that feeds the data into this file

# Main frame is 1536x824
# Each subframe is 718x382

#Might be able to combine both the rotation and position tracking if I have enough processing power (look into it in the future)

import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedStyle
from PIL import Image, ImageTk
import cv2
import requests
import threading
import socket
import time
import numpy as np
from VideoStream import video

# ===== Main =====
class Cam: 
    def __init__(self, root):
        
        #========== Initial Variables ==========
        
        self.root = root
        self.UIToggle = True
        
        self.aspectRatio = 16/9
        
        # If cam is on or off
        self.cam1Status = False
        self.cam2Status = False
        
        # Status Text
        self.cam1TxT = "OFFLINE"
        self.cam2TxT = "OFFLINE"
        
        self.cam1URL = 0    # 0 for webcam
        self.cam2URL = 9999   #replace when have access to camera
        
        self.vid1 = video(self.cam1URL)
        self.vid2 = video(self.cam2URL)
        
        # Ellipse for each of the cameras (send to telemetry when done)
        self.elip1 = None
        self.elip2 = None
        
        #Ui sizing
        self.xFrameHeight = 0
        self.xFrameWidth = 0
        
        self.telemetry = [0, 0, 0, 0, 0, 0, 0, 0]
        # [0] XPosition
        # [1] YPosition
        # [2] ZPosition
        # [3] XRotation
        # [4] YRotation
        # [5] ZRotation
        # [6] Velocity
        
        self.root.bind("<Configure>", self.resize_main)
        
        self.fallback_pil = Image.open("fallback.png")
        self.fallback = ImageTk.PhotoImage(self.fallback_pil, master=self.root)
        
        self.winSize = [root.winfo_screenwidth(), root.winfo_screenheight()]
        print(self.winSize)
        
        self.fps = 60                   # Camera FPS
        self.frameTime = 1000.0/60      # Time between frames (ms)
        
        # ========== Interface stuff ==========
        root.title("oOOooOOooooOOo")
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
        
        self.cam2Label = ttk.Label(
            dataFrame,
            text=f"Camera 2 Status: \t\t\t{self.cam2TxT}",
            font=("Segoe UI", 10),
            foreground = "lightgray"
        )
        self.cam2Label.pack(anchor="center")
        
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
        
        self.UIOverlay = tk.BooleanVar(value=True)
        ttk.Checkbutton(buttonFrame, text="Enable Overlay",
                        variable=self.UIOverlay,
                        command=self.exitApp).pack()
        
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
            text="Ellipse Detection",
            variable=self.mode_var,
            value=1,
            command=self.setMode2
        ).pack(anchor="w", pady=2)
        
        ttk.Radiobutton(
            buttonFrame,
            text="Ellipse Detection (C)",
            variable=self.mode_var,
            value=2,
            command=self.setMode3
        ).pack(anchor="w", pady=2)
        
        ttk.Radiobutton(
            buttonFrame,
            text="Rotation Detection",
            variable=self.mode_var,
            value=3,
            command=self.setMode4
        ).pack(anchor="w", pady=2)
        
        ttk.Radiobutton(
            buttonFrame,
            text="Rotation Detection (C)",
            variable=self.mode_var,
            value=4,
            command=self.setMode5
        ).pack(anchor="w", pady=2)
        
        text = (
            f"\nX-Position: \t\t{self.telemetry[0]:.2f}\n"
            f"Y-Position: \t\t{self.telemetry[1]:.2f}\n"
            f"Z-Position: \t\t{self.telemetry[2]:.2f}\n"
            f"X-Rotation: \t\t{self.telemetry[3]:.2f}\n"
            f"Y-Rotation: \t\t{self.telemetry[4]:.2f}\n"
            f"Z-Rotation: \t\t{self.telemetry[5]:.2f}\n"
            f"Velocity: \t\t\t{self.telemetry[6]:.2f}\n"
        )
                
        self.info = ttk.Label(dataFrame, text=text,
                  foreground = "lightgray",
                  font = ("Segoe UI", 10))
        self.info.pack(anchor="center")
        # Add some systems info here too I guess like camera status and stuff
        
        self.cam1_label = ttk.Label(self.TL_Frame, image=self.fallback)
        self.cam1_label.image = self.fallback
        self.cam1_label.pack(fill="both", expand=True)
        
        self.cam2_label = ttk.Label(self.TR_Frame, image=self.fallback)
        self.cam2_label.image = self.fallback
        self.cam2_label.pack(fill="both", expand=True)

        #Canvas (for docking UI)
        self.dockingUI = tk.Canvas(self.BL_Frame, width = self.xFrameWidth, height = self.xFrameHeight, background="black", highlightthickness=0)
        self.dockingUI.pack(fill="both", expand=True)
        
        self.BL_Frame.bind("<Configure>", self.createUI)
    
    # =========== Stream stuff ===========
    def streamThread(self):
        if self.cam1Status or self.cam2Status:
            self.setFrame()
            if self.mode == 1:    #Change this later once I actually have both cameras (currently doing position and rotation calculations here, move it to telemetry later)
                self.elip1 = self.vid1.getEllipse()
                if not self.elip1 is None:
                    (cx, cy), (w, h), angle = self.elip1
                    if w < h:
                        angle += 90
                    angle = angle % 180
                    angle = np.radians(angle)
                    major = max(w, h)
                    minor = min(w, h)
                    phi = np.arccos(minor/major)
                    
                    x = np.sin(phi)*np.cos(angle)
                    y = np.sin(phi)*np.sin(angle)
                    z = np.cos(phi)
                    
                    alpha = np.arctan2(x, z)
                    beta = np.arctan2(y, z)
                    
                    self.telemetry[0] = cx-1280/2
                    self.telemetry[1] = cy-720/2
                    self.telemetry[3] = beta
                    self.telemetry[4] = alpha
            
            elif self.mode == 3:
                self.telemetry = [0, 0, 0, 0, 0, 0, 0]  #Add rotation here later
                self.telemetry[6] = self.vid1.getVel()
            else:
                self.telemetry = [0, 0, 0, 0, 0, 0, 0]
            
            self.changeBars()   #Make sure this only runs on option 1 or 2 later
            self.updateInfo()
            self.updateStatus()
            self.root.after(16, self.streamThread)
            
    # ========= UI Functions Buttons =======
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
        
        if self.cam2Status == False:
            self.cam2_label.configure(image=photo)
            self.cam2_label.image = photo
        else:
            f2 = self.vid2.getFrame()
            if f2 is not None:
                frame = cv2.resize(f2, (self.xFrameWidth, self.xFrameHeight))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
                tk_img = ImageTk.PhotoImage(Image.fromarray(frame))
                self.cam2_label.configure(image=tk_img)
                self.cam2_label.image = tk_img
            else:
                self.cam2_label.configure(image=photo)
                self.cam2_label.image = photo
            
    def startStream(self):
        self.cam1Status = self.vid1.startStream()
        self.cam2Status = self.vid2.startStream()
        self.streamThread()
    
    def endStream(self):
        self.vid1.endStream()
        self.vid2.endStream()
        
    def updateStatus(self):
    
        self.cam1TxT = self.vid1.getStatus()
        self.cam2TxT = self.vid2.getStatus()
    
        self.cam1Label.config(text=f"Camera 1 Status: {self.cam1TxT}")
        self.cam2Label.config(text=f"Camera 2 Status: {self.cam2TxT}")
        
    def updateTelemetry(self):
        print("Not implemented yet")
    
    def exitApp(self):
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
            f"X-Rotation: \t\t{self.telemetry[3]:.2f}\n"
            f"Y-Rotation: \t\t{self.telemetry[4]:.2f}\n"
            f"Z-Rotation: \t\t{self.telemetry[5]:.2f}\n"
            f"Velocity: \t\t\t{self.telemetry[6]:.2f}\n"
        )
        self.info.config(text=text)
    
    def setMode1(self): #Standard Cam
        self.vid1.setMode(0)
        self.vid2.setMode(0)
        self.mode = 0
    
    def setMode2(self): #Ellipse Cam
        self.vid1.setMode(1)
        self.vid2.setMode(1)
        self.mode = 1
    
    def setMode3(self): #Contour Ellipse Cam
        self.vid1.setMode(2)
        self.vid2.setMode(2)
        self.mode = 2
    
    def setMode4(self): #Rotation Cam
        self.vid1.setMode(3)
        self.vid2.setMode(3)
        self.mode = 3
    
    def setMode5(self): #Contour Rotation Cam
        self.vid1.setMode(4)
        self.vid2.setMode(4)
        self.mode = 4
        
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
        xPos = self.telemetry[0]    #Im assuming it will be in cm?
        yPos = self.telemetry[1]
        zPos = self.telemetry[2]
        xRot = self.telemetry[3]*100    #Im assuming in radians?
        yRot = self.telemetry[4]*100
        zRot = self.telemetry[5]
        zVel = self.telemetry[6]*10
        
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
        
        self.dockingUI.coords(self.rotBar, pc1, ymid+zVel, pc2, ymid+zVel)
# ---------------- RUN ----------------
root = tk.Tk()
app = Cam(root)
root.mainloop()