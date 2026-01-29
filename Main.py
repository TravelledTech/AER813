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
        
        self.root = root
        self.display_mode = 0
        self.prev_ellipse = None
        self.prev_center = None
        self.velocity = np.zeros(2, dtype=np.float32)
        
        # Circle Geometry
        self.scale = 0 # How much the angle thing is scaled to (90 x scale for max), (Will depend on phi)
        self.phi = 0    # 3D position (Temporarly only works in half)
        self.theta = 0  # Rotation
        self.xPos = 0
        self.yPos = 0
        self.xRot = 0
        self.yRot = 0
        
        self.infoTxt = tk.StringVar()
        self.infoTxt.set("X = \nY = \nXRot = \nYRot = ")   # Show position info and stuff

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

        # Video input stuff
        self.video_label = ttk.Label(left_frame)
        self.video_label.place(x=0, y=0, relwidth=1, relheight=1)
        
        # # Display for the info (Switch to text that only appears when the video shows up)
        # tempText = ttk.Label(left_frame, textvariable=self.infoTxt,
        #                      background = "white",
        #                      foreground = "green",
        #                      width = 25,
        #                      font =("Segoe UI", 6))
        # tempText.place(
        #     relx=0.0,
        #     rely=0.0,
        #     anchor="nw",
        #     x=1,
        #     y=35
        # )
        # tempText.lift()

        ttk.Label(right_frame, text="Control Panel",
                  foreground="white",
                  font=("Segoe UI", 16, "bold")).pack(pady=5)
        
        # Buttons
        ttk.Button(right_frame, text="Start", width=15, command=self.start_stream).pack(pady=5, fill="x")
        ttk.Button(right_frame, text="Stop", width=15, command=self.stop_stream).pack(pady=5, fill="x")
        ttk.Button(right_frame, text="Exit", width=15, command=self.quit_app).pack(pady=5, fill="x")
        
        self.UIOverlay = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Enable Overlay",
                        variable=self.UIOverlay,
                        command=self.toggle_UI).pack(anchor="center", pady=5)
        
        # Radio Buttons (Switch between camera types)
        self.mode_var = tk.StringVar(value=1) # Determines which button it starts on (0, 1, 2)
        
        # Need to switch names and functions later (maybe to Normal, Contours, Normal + Contours)
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
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # ==== Rotating frame ==== (if needed)
            #frame_rgb = cv2.rotate(frame_rgb, cv2.ROTATE_90_CLOCKWISE)
            
            # =========== Edge Detection ===========
            grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(grey, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)
            
            annotated = frame_rgb.copy()
            edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

            # ========== Find contours ==========
            contours, _ = cv2.findContours(
                edges,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_NONE
            )
            
            # ==== Find best ellipse ====
            
            best_ellipse = None
            best_score = -1e9
            
            for cnt in contours:    # Removes some noise
                if len(cnt) < 30:
                    continue
            
                area = cv2.contourArea(cnt)
                if area < 500:
                    continue
            
                # --- Ellipse geometry ---
                ellipse = cv2.fitEllipse(cnt)
                (cx, cy), (w, h), angle = ellipse
                
                area = np.pi * (w / 2) * (h / 2)
                
                # --- Fit quality (angle-invariant) ---
                pts = cnt.reshape(-1, 2).astype(np.float32)
                ellipse_pts = cv2.ellipse2Poly(
                    (int(cx), int(cy)),
                    (int(w/2), int(h/2)),
                    int(angle),
                    0, 360, 10
                )
                
                dists = np.min(
                    np.linalg.norm(pts[:, None] - ellipse_pts[None, :], axis=2),
                    axis=1
                )
                fit_error = np.mean(dists)
                
                # --- Base score ---
                score = -fit_error   # lower error = higher score
            
                # ========== PREDICTION + ADAPTIVE GATING ========== (Smooths Motion)
                if self.prev_center is not None:
                    predicted = self.prev_center + self.velocity
                    dist = np.linalg.norm(np.array([cx, cy]) - predicted)
            
                    max_dist = 40 + np.linalg.norm(self.velocity) * 2.5
                    if dist > max_dist:
                        continue
            
                    score -= dist * 3
            
                if score > best_score:
                    best_score = score
                    best_ellipse = ellipse
            
            # ========== TRACK UPDATE ==========
            has_target = False
            
            if best_ellipse is not None:
                (cx, cy), _, _ = best_ellipse
                current_center = np.array([cx, cy], dtype=np.float32)
                has_target = True
            
                if self.prev_center is not None:
                    measured_vel = current_center - self.prev_center
                    self.velocity = 0.7 * self.velocity + 0.3 * measured_vel
                else:
                    self.velocity[:] = 0
            
                self.prev_center = current_center
            
                cv2.ellipse(annotated, best_ellipse, (0, 255, 0), 2)
                cv2.circle(annotated, (int(cx), int(cy)), 3, (255, 0, 0), -1)
            
            else:
                self.velocity *= 0.5
                self.prev_center = None

            
            overlay = frame_rgb.copy()
            # Color edges red
            overlay[edges > 0] = [255, 0, 0]   # RGB red

            if self.display_mode == 0:
                output = annotated
            elif self.display_mode == 1:
                output = edges_rgb
            else:
                output = overlay
            
            # Overlay
            if self.UIOverlay.get() == True:
                h, w, _ = output.shape
                
                if has_target:  # Only shows if ellipse is detected
                    # Stuff for determining the major, minor and angle
                    (cx, cy), (wid, hei), angle = best_ellipse
                    if w < h:
                        angle += 90
                        
                    angle = angle % 180
                        
                    major = max(wid, hei)
                    minor = min(wid, hei)
                    self.phi = np.arccos(minor/major)
                    self.theta = angle
                    
                    # Modify the scale of the scale here (but 200 seems to be pretty good)
                    self.scale = self.phi*200
                    
                    self.yPos = int(np.sin(np.deg2rad(self.theta))*self.scale)
                    self.xPos = int(np.cos(np.deg2rad(self.theta))*self.scale)
                    
                    # Draws target boxes
                    cv2.circle(output, (int(w/2) + self.xPos, int(h/2) + self.yPos), 14, (200, 0, 0), 2)
                    cv2.rectangle(output, (int(w/2)+self.xPos + 14, int(h/2) + self.yPos-1), (int(w/2)+self.xPos + 20, int(h/2) + self.yPos+1), (200, 0, 0), -1)
                    cv2.rectangle(output, (int(w/2)+self.xPos - 14, int(h/2) + self.yPos-1), (int(w/2)+self.xPos - 20, int(h/2) + self.yPos+1), (200, 0, 0), -1)
                    cv2.rectangle(output, (int(w/2)+self.xPos-1, int(h/2) + self.yPos+14), (int(w/2)+self.xPos+1, int(h/2) + self.yPos+20), (200, 0, 0), -1)
                    cv2.rectangle(output, (int(w/2)+self.xPos-1, int(h/2) + self.yPos-14), (int(w/2)+self.xPos+1, int(h/2) + self.yPos-20), (200, 0, 0), -1)
                    
                    # Position Lines
                    h2 = int(cy)
                    w2 = int(cx)
                    cv2.rectangle(output, (w2+1, h2), (w2, int(h/2)), (255, 0, 0), -1)
                    cv2.rectangle(output, (w2, h2+1), (int(w/2), h2), (255, 0, 0), -1)
                    
                    # Add the text box here after (need 4 total, xpos, ypos, xangle, yangle)
                    # For now, use pixel distance but later change to actual distances
                
                # Draws the rest of the overlay
                
                cv2.rectangle(output, (0, 0), (w, h), (255, 255, 255), 2)
                cv2.circle(output, (int(w/2), int(h/2)), 24, (255, 255, 255), 2)
                
                # cv2.rectangle(output, (0, int(h/2)+1), (int(w/2)-24, int(h/2)-1), (255, 255, 255), -1)
                # cv2.rectangle(output, (w, int(h/2)+1), (int(w/2)+24, int(h/2)-1), (255, 255, 255), -1)
                # cv2.rectangle(output, (int(w/2)+1, 0), (int(w/2)-1, int(h/2)-24), (255, 255, 255), -1)
                # cv2.rectangle(output, (int(w/2)+1, h), (int(w/2)-1, int(h/2)+24), (255, 255, 255), -1)
                
                cv2.rectangle(output, (w, int(h/2)+1), (0, int(h/2)-1), (255, 255, 255), -1)
                cv2.rectangle(output, (int(w/2)+1, 0), (int(w/2)-1, h), (255, 255, 255), -1)
            
            # Camera Stuff
            img = Image.fromarray(edges).resize((640, 480)) # Change annotated <---> edges <---> overlay
            tk_img = ImageTk.PhotoImage(img)
            self.root.after(0, self.update_frame, tk_img)
            
            cv2.putText(output, "X Position", (0, 0), cv2.FONT_HERSHEY_SIMPLEX, 8, (0, 200, 0), 1)
            cv2.putText(output, "Y Position", (0, 10), cv2.FONT_HERSHEY_SIMPLEX, 8, (0, 200, 0), 1)
            cv2.putText(output, "Y Rotation", (0, 20), cv2.FONT_HERSHEY_SIMPLEX, 8, (0, 200, 0), 1)
            cv2.putText(output, "X Rotation", (0, 30), cv2.FONT_HERSHEY_SIMPLEX, 8, (0, 200, 0), 1)
            
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
            
    #
    #0    | 180
    #-----+-----
    #180  | 0
    #
    # Check the location of the ellipse, if center is above the horizontal, reverse x and y for the rotation
    # After that check the position and which way it is facing, determine the actual direction from there

# ---------------- RUN ----------------
root = tk.Tk()
app = Cam(root)
root.mainloop()       
 