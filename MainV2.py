# Redo some of the code to account for 2, wireless cameras (can't really test right now)
# I guess also integrate the mace thing into this
# Cam1       | Cam2
# -----------+----------
# Docking GUI| Controls
# make 2 more files, one for docking vision one for mace that feeds the data into this file

# Main frame is 1536x824
# Each subframe is 718x382

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

#===== Inital Variables =====
cam1_URL = "Temp"
cam2_URL = "Temp"   #replace when have access to camera

# ===== Main =====
class Cam: 
    def __init__(self, root):
        #Self, variables.
        
        self.root = root
        self.UIToggle = True
        
        self.aspectRatio = 16/9
        
        # If cam is on or off
        self.cam1Status = False
        self.cam2Status = False
        
        self.cam1TxT = "OFFLINE"
        self.cam2TxT = "OFFLINE"
        self.generalTxT = "N/A"
        
        self.xFrameHeight = 0
        self.xFrameWidth = 0
        self.dBoxW = 0
        
        self.telemetry = [None, None, None, None, None, None, None, None, None]
        # [0] XPosition
        # [1] XVelocity
        # [2] YPosition
        # [3] YVelocity
        # [4] ZPosition
        # [5] ZVelocity
        # [6] XRotation
        # [7] YRotation
        # [8] ZRotation
        
        self.fallback_pil = Image.open("fallback.png")
        self.fallback = ImageTk.PhotoImage(self.fallback_pil, master=self.root)
        
        self.winSize = [root.winfo_screenwidth(), root.winfo_screenheight()]
        print(self.winSize)
        
        # Interface stuff
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
        self.main_frame.pack(fill="both", expand=True)
        
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
        ).pack(fill="x")
        
        self.cam2Label = ttk.Label(
            dataFrame,
            text=f"Camera 2 Status: \t\t\t{self.cam2TxT}",
            font=("Segoe UI", 10),
            foreground = "lightgray"
        ).pack(fill="x")
        
        self.generalLabel = ttk.Label(
            dataFrame,
            text="General Status:\t\t\tN/A\n",
            font=("Segoe UI", 10),
            foreground = "lightgray"
        ).pack(fill="x")
        
        ttk.Label(dataFrame, text = "Current Data", foreground = "lightgray", anchor="center", font = ("Segoe UI", 14, "bold")).pack(fill="x")
        ttk.Label(buttonFrame, text = "Controls", foreground = "lightgray", anchor="center", font = ("Segoe UI", 14, "bold")).pack(fill="x")
        
        ttk.Button(buttonFrame,
                                text = "EXIT",
                                command = self.exitApp).pack(fill="x")
        ttk.Button(buttonFrame,
                                text = "Start Camera",
                                command = self.exitApp).pack(fill="x")
        ttk.Button(buttonFrame,
                                text = "End Camera",
                                command = self.exitApp).pack(fill="x")
        
        self.UIOverlay = tk.BooleanVar(value=True)
        ttk.Checkbutton(buttonFrame, text="Enable Overlay",
                        variable=self.UIOverlay,
                        command=self.exitApp).pack()
        
        text = (
            f"\tX-Position: \t\t{self.telemetry[0]}\n"
            f"\tX-Velocity: \t\t{self.telemetry[1]}\n"
            f"\tY-Position: \t\t{self.telemetry[2]}\n"
            f"\tY-Velocity: \t\t{self.telemetry[3]}\n"
            f"\tZ-Position: \t\t{self.telemetry[4]}\n"
            f"\tZ-Velocity: \t\t{self.telemetry[5]}\n"
            f"\tX-Rotation: \t\t{self.telemetry[6]}\n"
            f"\tY-Rotation: \t\t{self.telemetry[7]}\n"
            f"\tZ-Rotation: \t\t{self.telemetry[8]}\n"
        )
        
        ttk.Label(dataFrame, text=text,
                  foreground = "lightgray",
                  font = ("Segoe UI", 10)).pack(anchor="w")
        # Add some systems info here too I guess like camera status and stuff
        
        self.cam1_label = ttk.Label(self.TL_Frame, image=self.fallback)
        self.cam1_label.image = self.fallback
        self.cam1_label.pack(fill="both", expand=True)
        
        self.cam2_label = ttk.Label(self.TR_Frame, image=self.fallback)
        self.cam2_label.image = self.fallback
        self.cam2_label.pack(fill="both", expand=True)
        
        #self.dock_label = ttk.Label(self.BL_Frame, image=self.fallback)
        #self.dock_label.image = self.fallback
        #self.dock_label.pack(fill="both", expand=True)

        # Canvas
        #718 x 382
        # Center@ 359, 191
        
        x = self.xFrameWidth
        y = self.xFrameHeight
        
        # Main docking takes up ~5/6th of the space (make sure its an even amount of pixels)
        self.dBoxW = int(self.xFrameWidth*(5.0/6))
        if not self.dBoxW%2 == 0:
            self.dBoxW += 1
        
        x2 = self.dBoxW
        mid = x2/2
        
        self.dockingUI = tk.Canvas(self.BL_Frame, width = self.xFrameWidth, height = self.xFrameHeight, background="black", highlightthickness=0)
        
        self.dockingUI.create_rectangle(0, y/2+1, x2, y/2-1, fill = "white")
        self.dockingUI.create_rectangle(mid-1, 0, mid+1, y, fill = "white")
        self.dockingUI.create_rectangle(x2, 0, x2+2, y, fill = "white")
        self.dockingUI.create_rectangle(x2+6, 0, x2+8, y, fill = "white")
        
# ========= UI Functions Buttons =======
    def print_size(self, event):
        self.xFrameWidth = event.width
        self.xFrameHeight = event.height
        
        print(self.xFrameWidth, self.xFrameHeight)
        
        if self.xFrameWidth > 0 and self.xFrameHeight > 0:
            resized = self.fallback_pil.resize(
                (self.xFrameWidth, self.xFrameHeight),
                Image.LANCZOS
            )
    
            photo = ImageTk.PhotoImage(resized)
    
            #Later change this so this only happens if camera is offline
            
            if self.cam1Status == False:
                self.cam1_label.configure(image=photo)
                self.cam1_label.image = photo
            
            if self.cam2Status == False:
                self.cam2_label.configure(image=photo)
                self.cam2_label.image = photo
            
    
    def updateStatus(self):
    
        self.cam1TxT = self.cam1Video.getStatus()
        self.cam2TxT = self.cam2Video.getStatus()
    
        self.cam1Status.config(text=f"Camera 1 Status: {self.cam1TxT}")
        self.cam2Status.config(text=f"Camera 2 Status: {self.cam2TxT}")
        
    def updateTelemetry(self):
        print("Not implemented yet")
    
    
    def exitApp(self):
        self.running = False
        self.root.destroy()
        
        
        
# ---------------- RUN ----------------
root = tk.Tk()
app = Cam(root)
root.mainloop()