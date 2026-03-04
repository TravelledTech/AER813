# Redo some of the code to account for 2, wireless cameras (can't really test right now)
# I guess also integrate the mace thing into this
# Cam1       | Cam2
# -----------+----------
# Docking GUI| Controls
# make 2 more files, one for docking vision one for mace that feeds the data into this file

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
        
        # If cam is on or off
        self.cam1Status = False
        self.cam2Status = False
        
        self.xFrameHeight = 0
        self.xFrameWidth = 0
        
        self.fallback_pil = Image.open("fallback.png")
        self.fallback = ImageTk.PhotoImage(self.fallback_pil)
        
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
        
        ttk.Label(self.BR_Frame, text = "Control Panel", foreground = "crimson", font = ("Segoe UI", 30, "bold underline")).grid(column = 0, row = 0, columnspan=2)
        dataFrame = ttk.Frame(self.BR_Frame)
        buttonFrame = ttk.Frame(self.BR_Frame)
        dataFrame.grid(column=0, row=1, sticky="nsew", padx=5, pady=20)
        buttonFrame.grid(column=1, row=1, sticky="nsew", padx=5, pady=20)

        # Buttons
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
        
        ttk.Label(dataFrame, text = "xPosition = N/A\nxVelocity = N/A\nyPosition = N/A\nyVelocity = N/A\nzPosition = N/A\nzVelocity = N/A",
                  foreground = "lightgray",
                  font = ("Segoe UI", 12)).pack(anchor="w")
        # Add some systems info here too I guess like camera status and stuff
        
        self.cam1_label = ttk.Label(self.TL_Frame, image=self.fallback)
        self.cam1_label.image = self.fallback
        self.cam1_label.pack(fill="both", expand=True)
        
        self.cam2_label = ttk.Label(self.TR_Frame, image=self.fallback)
        self.cam2_label.image = self.fallback
        self.cam2_label.pack(fill="both", expand=True)
        
        self.dock_label = ttk.Label(self.BL_Frame, image=self.fallback)
        self.dock_label.image = self.fallback
        self.dock_label.pack(fill="both", expand=True)
        
        # ttk.Label(self.TL_Frame, text="Camera 1",
        #           foreground="lightgray",
        #           background="darkgray",
        #           font=("Segoe UI", 24, "bold")).pack(fill="both", expand = True)
        
        # ttk.Label(self.TR_Frame, text="Camera 2",
        #           foreground="lightgray",
        #           background="darkgray",
        #           font=("Segoe UI", 24, "bold")).pack(fill="both", expand = True)
        
        # ttk.Label(self.BL_Frame, text="Target Cam",
        #           foreground="lightgray",
        #           background="darkgray",
        #           font=("Segoe UI", 24, "bold")).pack(fill="both", expand = True)
        

# ========= UI Functions Buttons =======
    def print_size(self, event):
        self.xFrameWidth = event.width
        self.xFrameHeight = event.height
    
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
            
            # Delete this one later once size is determined
            self.dock_label.configure(image=photo)
            self.dock_label.image = photo
    
    def exitApp(self):
        self.running = False
        self.root.destroy()
        
        
        
# ---------------- RUN ----------------
root = tk.Tk()
app = Cam(root)
root.mainloop()