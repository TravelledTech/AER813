import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedStyle
from PIL import Image, ImageTk
from ultralytics import YOLO
import cv2
import requests
import threading
import socket
import time

#========== Initial Settings ===========
CamToggle = True 

# =========== Main ===========
class YOLOViewer:
    def __init__(self, root):
        
        # Add starting variables later (eg self.toggle = false)
        
        self.root = root
        
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

        right_frame = ttk.Frame(main_frame, padding=5)
        right_frame.pack(side="right", fill="y")

        # Video feed
        self.video_label = ttk.Label(left_frame)
        self.video_label.pack(expand=True, fill="both")

        ttk.Label(right_frame, text="Control Panel",
                  foreground="white",
                  font=("Segoe UI", 16, "bold")).pack(pady=5)
        
        # Buttons
        ttk.Button(right_frame, text="Start", width=15, command=self.start_stream).pack(pady=5, fill="x")
        ttk.Button(right_frame, text="Stop", width=15, command=self.stop_stream).pack(pady=5, fill="x")
        ttk.Button(right_frame, text="Exit", width=15, command=self.quit_app).pack(pady=5, fill="x")
        
        self.cap = cv2.VideoCapture(0)


    def stream_thread(self):

        while self.running:
            ret, frame = self.cap.read()
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # ==== Rotating frame ==== (if needed)
            #frame_rgb = cv2.rotate(frame_rgb, cv2.ROTATE_90_CLOCKWISE)
            
            # Edge Detection
            grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(grey, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)
            
            annotated = frame_rgb.copy()
            
            img = Image.fromarray(edges).resize((640, 480)) # Change annotated <---> edges
            tk_img = ImageTk.PhotoImage(img)
            self.root.after(0, self.update_frame, tk_img)

        if self.cap:
            self.cap.release()
            
    def update_frame(self, tk_img):
        self.video_label.imgtk = tk_img
        self.video_label.configure(image=tk_img)
        
# ========== Camera ==========
            
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

# ---------------- RUN ----------------
root = tk.Tk()
app = YOLOViewer(root)
root.mainloop()       
 