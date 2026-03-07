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
        
        self.root.bind("<Configure>", self.resize_main)
        
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

        #Canvas (for docking UI)
        self.dockingUI = tk.Canvas(self.BL_Frame, width = self.xFrameWidth, height = self.xFrameHeight, background="black", highlightthickness=0)
        self.dockingUI.pack(fill="both", expand=True)
        
        self.BL_Frame.bind("<Configure>", self.createUI)
        
# ========= UI Functions Buttons =======
    def print_size(self, event):    # Also resizes the photos
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
        
    def createUI(self, event):
        # Canvas
        #718 x 382
        # Center@ 359, 191
        
        self.xFrameWidth = event.width
        self.xFrameHeight = event.height
    
        x = self.xFrameWidth
        y = self.xFrameHeight
    
        # clear old drawings
        self.dockingUI.delete("all")
    
        self.dBoxW = int(x * (5.0/6))
        if self.dBoxW % 2 != 0:
            self.dBoxW += 1
    
        x2 = self.dBoxW
        mid = x2 / 2
        ymid = y/2
        
        zCenter = x2+10 + int((x-x2+10)/2)
        
        self.dockingUI.create_line(0, y/2, x2, y/2, fill="white", width=2)
        self.dockingUI.create_line(mid, 0, mid, y, fill="white", width=2)
        self.dockingUI.create_line(x2+1, 0, x2+1, y, fill="white", width=2)
        self.dockingUI.create_line(x2+9, 0, x2+9, y, fill="white", width=2)
        
        # Change this for pixel step
        step = 15
        step2 = 20
        
        for i in range(step, int(mid), step):
            if i%(step*2) == step:
                self.dockingUI.create_line(mid+i, ymid+5, mid+i, ymid-5, fill="white", width=2)
                self.dockingUI.create_line(mid-i, ymid+5, mid-i, ymid-5, fill="white", width=2)
            else:
                self.dockingUI.create_line(mid+i, ymid+8, mid+i, ymid-8, fill="white", width=2)
                self.dockingUI.create_line(mid-i, ymid+8, mid-i, ymid-8, fill="white", width=2)
                
        for i in range(step, int(y/2), step):
            if i%(step*2) == step:
                self.dockingUI.create_line(mid+5, ymid+i, mid-5, ymid+i, fill="white", width=2)
                self.dockingUI.create_line(mid+5, ymid-i, mid-5, ymid-i, fill="white", width=2)
            else:
                self.dockingUI.create_line(mid+8, ymid+i, mid-8, ymid+i, fill="white", width=2)
                self.dockingUI.create_line(mid+8, ymid-i, mid-8, ymid-i, fill="white", width=2)
                
        for i in range(step2, y, step2):
            if i%(step2*2) == step2:
                self.dockingUI.create_line(zCenter+8, i, zCenter-8, i, fill="white", width=2)
            else:
                self.dockingUI.create_line(zCenter+14, i, zCenter-14, i, fill="white", width=2)
        
        
# ---------------- RUN ----------------
root = tk.Tk()
app = Cam(root)
root.mainloop()