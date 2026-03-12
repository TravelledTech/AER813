#Videostream Test File (use MainV2 when cameras arrive)
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

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("")
        self.root.geometry("1500x800")
        self.running = False
        self.vid = video(0)
        
        # Theme
        style = ThemedStyle(self.root)
        style.set_theme("equilux")

        # ---- Main container ----
        container = ttk.Frame(self.root, width=1280, height=720)
        container.pack(fill="both", expand=True)

        # ---- Sidebar ----
        self.sidebar = ttk.Frame(container, width=180)
        self.sidebar.pack(side="left", fill="y")

        ttk.Button(self.sidebar, text="Start", command=self.startStream).pack(fill="x", padx=10, pady=10)
        ttk.Button(self.sidebar, text="End", command=self.endStream).pack(fill="x", padx=10, pady=10)
        
        self.display_mode = 0
        self.mode_var = tk.StringVar(value=0)
        
        ttk.Radiobutton(
            self.sidebar,
            text="Regular",
            variable=self.mode_var,
            value=0,
            command=self.temp0
        ).pack(anchor="w", pady=2)
        
        ttk.Radiobutton(
            self.sidebar,
            text="Position",
            variable=self.mode_var,
            value=1,
            command=self.temp1
        ).pack(anchor="w", pady=2)
        
        ttk.Radiobutton(
            self.sidebar,
            text="PositionC",
            variable=self.mode_var,
            value=2,
            command=self.temp2
        ).pack(anchor="w", pady=2)
        
        ttk.Radiobutton(
            self.sidebar,
            text="SpinRate",
            variable=self.mode_var,
            value=3,
            command=self.temp3
        ).pack(anchor="w", pady=2)
        
        ttk.Radiobutton(
            self.sidebar,
            text="SpinRateC",
            variable=self.mode_var,
            value=4,
            command=self.temp4
        ).pack(anchor="w", pady=2)
        
        ttk.Button(self.sidebar, text="Exit", command=self.quit_app).pack(fill="x", padx=10, pady=10)

        # ---- Main content frame ----
        self.main_frame = ttk.Frame(container)
        self.main_frame.pack(side="left", fill="both", expand=True)
        self.video_label = ttk.Label(self.main_frame)
        self.video_label.pack(fill="both", expand=True)
    
    # Streaming Thread
    
    def streamThread(self):
        while self.running:
            f = self.vid.getFrame()
            if f is None:
                continue
    
            frame = cv2.resize(f, (1280, 720))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
            tk_img = ImageTk.PhotoImage(Image.fromarray(frame))
    
            self.root.after(16, self.updateFrame, tk_img)
        
    def updateFrame(self, tk_img):
        self.video_label.imgtk = tk_img
        self.video_label.configure(image=tk_img)
    
    #Buttons
    def startStream(self):
        self.running = True
        self.vid.startStream()
        threading.Thread(target=self.streamThread, daemon=True).start()
        
    def endStream(self):
        self.running = False
        self.vid.endStream()
        
    def quit_app(self):
        self.running = False
        self.root.destroy()
        
    def temp0(self):
        self.vid.setMode(0)
        
    def temp1(self):
        self.vid.setMode(1)
        
    def temp2(self):
        self.vid.setMode(2)
        
    def temp3(self):
        self.vid.setMode(3)
        
    def temp4(self):
        self.vid.setMode(4)
        
    def temp5(self):
        self.vid.setMode(5)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()