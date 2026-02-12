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

#========== Initial Settings ===========
CamToggle = True 

# =========== Main ===========
class Cam:
    def __init__(self, root):
        
        # Add starting variables later (eg self.toggle = false)
        
        self.running = False
        self.root = root
        self.display_mode = 0
        self.L_slider = 0
        self.R_slider = 0

        # GUI Layout
        root.title("Target Camera")
        root.geometry("900x560")

        style = ThemedStyle(root)
        style.set_theme("equilux")
        root.configure(bg=style.lookup(".", "background"))

        main_frame = ttk.Frame(root)
        main_frame.pack(fill="both", expand=True)
        
        # 2 frames within the frame (one for camera feed and other for controls)
        left_frame = ttk.Frame(main_frame, padding=5)
        left_frame.pack(side="left", fill="both", expand=True)

        right_frame = ttk.Frame(main_frame, padding=5, width = 200)
        right_frame.pack_propagate(False)
        right_frame.pack(side="right", fill="y")
        
        LT_frame = ttk.Frame(left_frame, padding=0, width = 640, height = 480)
        LT_frame.pack(side="top", fill="both", expand=True)
        
        LB_frame = ttk.Frame(left_frame, padding=0, height = 50, width = 480)
        LB_frame.pack(side="bottom", fill="x", expand=True)

        # Video input stuff
        self.video_label = ttk.Label(LT_frame)
        self.video_label.place(x=0, y=0, relwidth=1, relheight=1)

        ttk.Label(right_frame, text="Control Panel",
                  foreground="white",
                  font=("Segoe UI", 16, "bold")).pack(pady=5)
        
        # Sliders
        slider1 = ttk.Scale(LB_frame, from_=0, to=50, orient="horizontal",
                                command=self.L_slider_changed)
        slider2 = ttk.Scale(LB_frame, from_=100, to=50, orient="horizontal",
                                command=self.R_slider_changed)
        
        slider1.place(x=0, y=0, width=320)
        slider2.place(x=320, y=0, width=320)
        
        # Buttons
        ttk.Button(right_frame, text="Start", width=15, command=self.start_stream).pack(pady=5, fill="x")
        ttk.Button(right_frame, text="Stop", width=15, command=self.stop_stream).pack(pady=5, fill="x")
        ttk.Button(right_frame, text="Exit", width=15, command=self.quit_app).pack(pady=5, fill="x")
        
        self.UIOverlay = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Enable Overlay",
                        variable=self.UIOverlay,
                        command=self.toggle_UI).pack(anchor="center", pady=5)
        
        # Radio Buttons (Switch between camera types)
        self.mode_var = tk.StringVar(value=0)
        
        ttk.Radiobutton(
            right_frame,
            text="Temp1",
            variable=self.mode_var,
            value=0,
            command=self.temp1
        ).pack(anchor="w", pady=2)
        
        ttk.Radiobutton(
            right_frame,
            text="Temp2",
            variable=self.mode_var,
            value=1,
            command=self.temp2
        ).pack(anchor="w", pady=2)
        
        ttk.Radiobutton(
            right_frame,
            text="Temp3",
            variable=self.mode_var,
            value=2,
            command=self.temp3
        ).pack(anchor="w", pady=2)
        
        self.cap = cv2.VideoCapture(0)

# ========== Camera Display & Overlay ==========

    def stream_thread(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
    
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
            img = Image.fromarray(frame_rgb).resize((640, 480))
            tk_img = ImageTk.PhotoImage(img)
    
            self.root.after(0, self.update_frame, tk_img)
    
        if self.cap:
            self.cap.release()
        
    def update_frame(self, tk_img):
        self.video_label.imgtk = tk_img
        self.video_label.configure(image=tk_img)
        
# ========== Buttons ==========
            
    def start_stream(self):
        self.cap = cv2.VideoCapture(0)
        self.running = True
        threading.Thread(target=self.stream_thread, daemon=True).start()
        
    def stop_stream(self):
        self.running = False
        self.hasToggle = True

    def quit_app(self):
        self.running = False
        self.root.destroy()
        
    def temp1(self):
        self.display_mode = 0
    def temp2(self):
        self.display_mode = 1
    def temp3(self):
        self.display_mode = 2
        
    def toggle_UI(self):
        if self.UIOverlay.get() == True:
            print(True)
        else:
            print(False)
            
    #Sliders 
    def R_slider_changed(self, value):
        self.R_slider = float(value)
        print("Slider moved:", self.R_slider)
    def L_slider_changed(self, value):
        self.L_slider = float(value)
        print("Slider moved:", self.L_slider)
    

# ---------------- RUN ----------------
root = tk.Tk()
app = Cam(root)
root.mainloop()