# Redo some of the code to account for 2, wireless cameras (can't really test right now)
# I guess also integrate the mace thing into this
# Cam1       | Cam2
# -----------+----------
# Docking GUI| Controls

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
        
        self.winSize = [root.winfo_screenwidth(), root.winfo_screenheight()]
        print(self.winSize)
        
        # Interface stuff
        root.title("")
        root.attributes("-fullscreen", True)
        #root.geometry("{0}x{1}+0+0".format(root.winfo_screenwidth(), root.winfo_screenheight()))
        #root.geometry("900x560")
        
        style = ThemedStyle(root)
        style.set_theme("equilux")
        root.configure(bg=style.lookup(".", "background"))
        
        #Use 7 frames (probably inefficient?), maybe 5 instread
        
        main_frame = ttk.Frame(root)
        main_frame.pack(fill="both", expand=True)
        
        TL_Frame = ttk.Frame(main_frame)
        TR_Frame = ttk.Frame(main_frame)
        BL_Frame = ttk.Frame(main_frame)
        BR_Frame = ttk.Frame(main_frame)
        
        for i in range(2):
            main_frame.columnconfigure(i, weight=1, uniform="equal")
            main_frame.rowconfigure(i, weight=1, uniform="equal")
    
        TL_Frame.grid(column=0, row=0, sticky="nsew", padx=25, pady=25)
        TR_Frame.grid(column=1, row=0, sticky="nsew", padx=25, pady=25)
        BL_Frame.grid(column=0, row=1, sticky="nsew", padx=25, pady=25)
        BR_Frame.grid(column=1, row=1, sticky="nsew", padx=25, pady=25)
        
        for i in range(2):
            BR_Frame.columnconfigure(i, weight=1, uniform="equal")
        BR_Frame.rowconfigure(0, weight=0)
        BR_Frame.rowconfigure(1, weight=1)


        
        ttk.Label(BR_Frame, text = "Control Panel", foreground = "gold", font = ("Segoe UI", 30, "bold underline")).grid(column = 0, row = 0, columnspan=2)
        dataFrame = ttk.Frame(BR_Frame)
        buttonFrame = ttk.Frame(BR_Frame)
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
        
        
        ttk.Label(TL_Frame, text="Camera 1",
                  foreground="lightgray",
                  background="darkgray",
                  font=("Segoe UI", 24, "bold")).pack(fill="both", expand = True)
        
        ttk.Label(TR_Frame, text="Camera 2",
                  foreground="lightgray",
                  background="darkgray",
                  font=("Segoe UI", 24, "bold")).pack(fill="both", expand = True)
        
        ttk.Label(BL_Frame, text="Target Cam",
                  foreground="lightgray",
                  background="darkgray",
                  font=("Segoe UI", 24, "bold")).pack(fill="both", expand = True)
        

# ========= UI Functions Buttons =======

    def exitApp(self):
        self.running = False
        self.root.destroy()
        
        
        
# ---------------- RUN ----------------
root = tk.Tk()
app = Cam(root)
root.mainloop()