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
        self.velocity = np.zeros(2, dtype=np.float32)   # <- used for estimating the next position of the ellipse
        
        # Circle Geometry
        self.scale = 0 # How much the angle thing is scaled to (90 x scale for max), (Will depend on phi)
        self.phi = 0    # 3D position (Temporarly only works in half)
        self.theta = 0  # Rotation
        self.xPos = 0   # Position of the angle thingy
        self.yPos = 0
        self.x = 0      # Position of the actual nozzle
        self.y = 0
        self.xAngl = 0      # Position of the actual nozzle
        self.yAngl = 0
        self.xQuad = 1    # Current position of x and y asis (1, -1 for position in quandrant)
        self.yQuad = 1      # Dont really need these (maybe)
        self.lastPos = [1, 1, 1]
        
        #For shadow instead of contour
        self.facing_dir = 0
        self.face_confidence = 0  # confidence accumulator
        self.CONF_THRESH = 3      # frames required to flip
        self.CONF_MAX = 5
        
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
        
        # tempText = ttk.Label(left_frame, textvariable=self.infoTxt, background = "white", foreground = "green", font =("Segoe UI", 8))
        # tempText.place(
        #     relx=0.0,
        #     rely=0.0,
        #     anchor="nw",
        #     x=5,
        #     y=40
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
                
                # --- Base score ---, improve this later
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
                    if wid < hei:
                        angle += 90
                        
                    angle = angle % 180
                    
                    # Add the edge positioning here
                    # do for cnt in contours again
                    # cx and cy for position of the target (find contours relative to that)
                    # CURRENTLY ONLY WORKS IF NO OTHER CONTOURS ARE VISIBLE
                    
                    countX = 0  #Maybe later add weights (and filter out background contours by checking size of contours)
                    countY = 0
                    for cnt in contours:
                        
                        CofM_C = cv2.moments(cnt)
                        
                        if CofM_C["m00"] != 0:
                            cCy = CofM_C["m10"]/CofM_C["m00"]
                            cCx = CofM_C["m01"]/CofM_C["m00"]
                        
                        # Adjust this later but if countour add if contour is above/right of
                        # Original and vice versa
                        
                        if cCy > cy:
                            countY+=1
                        else:
                            countY-=1
                            
                    # Only xquad is needed (for now)
                    if countY > 0:
                        self.facing_dir = -1
                    else:
                        self.facing_dir = 1

                    print(self.facing_dir)
                    
                    # For now, prevents a suddent bit flip but only works if its isolated. Does not work if its constantly flipping every 3 positions
                    temp = self.facing_dir
                    if self.facing_dir != self.lastPos[1]:
                        temp = self.lastPos[1]
                    elif self.facing_dir != self.lastPos[0]:
                        temp = self.lastPos[0]
                    elif self.facing_dir != self.lastPos[2]:
                        temp = self.lastPos[2]
                    
                    self.lastPos[0] = self.lastPos[1]
                    self.lastPos[1] = self.lastPos[2]
                    self.lastPos[2] = self.facing_dir
                    
                    self.facing_dir = temp
                    facing = self.facing_dir
                    
                    # # Colours instead
                    
                    # lab = cv2.cvtColor(output, cv2.COLOR_BGR2LAB)
                    # L = lab[:, :, 0]
                    # facing, Lf, Lb = self.resolve_facing_by_lightness(L, best_ellipse)
                    
                    # ===========================
                    major = max(wid, hei)
                    minor = min(wid, hei)
                    self.phi = np.arccos(minor/major)
                    self.theta = angle
                    
                    # Modify the scale of the scale here (but 200 seems to be pretty good)
                    self.scale = self.phi*150
                    
                    self.xPos = int(np.sin(np.deg2rad(self.theta))*self.scale)*facing  # Multiply by the quadrant multiplyer after 
                    self.yPos = -int(np.cos(np.deg2rad(self.theta))*self.scale)*facing
                    
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
                
                # Draws the rest of the overlay
                
                cv2.rectangle(output, (0, 0), (w, h), (255, 255, 255), 2)
                cv2.circle(output, (int(w/2), int(h/2)), 24, (255, 255, 255), 2)
                
                # cv2.rectangle(output, (0, int(h/2)+1), (int(w/2)-24, int(h/2)-1), (255, 255, 255), -1)
                # cv2.rectangle(output, (w, int(h/2)+1), (int(w/2)+24, int(h/2)-1), (255, 255, 255), -1)
                # cv2.rectangle(output, (int(w/2)+1, 0), (int(w/2)-1, int(h/2)-24), (255, 255, 255), -1)
                # cv2.rectangle(output, (int(w/2)+1, h), (int(w/2)-1, int(h/2)+24), (255, 255, 255), -1)
                
                cv2.rectangle(output, (w, int(h/2)+1), (0, int(h/2)-1), (255, 255, 255), -1)
                cv2.rectangle(output, (int(w/2)+1, 0), (int(w/2)-1, h), (255, 255, 255), -1)
                
                # Another overlay for info
                if has_target:
                    cv2.putText(output, "Pos_X  = 1234", (5, 15), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 220, 0), 1)
                    cv2.putText(output, "Pos_Y  = 1234", (5, 30), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 220, 0), 1)
                    cv2.putText(output, "Angl_X = 1234", (5, 45), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 220, 0), 1)
                    cv2.putText(output, "Angl_Y = 1234", (5, 60), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 220, 0), 1)
                    
            
            # Camera Stuff
            img = Image.fromarray(output).resize((640, 480)) # Change annotated <---> edges <---> Edges RBG
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
            
    # def resolve_facing_by_lightness(self, L, best_ellipse):
    #     (cx, cy), (w, h), angle = best_ellipse
    #     cx, cy = int(cx), int(cy)
    
    #     # Ensure major axis consistency
    #     if w < h:
    #         w, h = h, w
    #         angle += 90
    
    #     angle %= 180
    #     theta = np.deg2rad(angle)
    
    #     # Ellipse mask
    #     mask = np.zeros(L.shape, dtype=np.uint8)
    #     cv2.ellipse(
    #         mask,
    #         ((cx, cy), (int(w), int(h)), angle),
    #         255,
    #         -1
    #     )
    
    #     ys, xs = np.indices(L.shape)
    #     xs -= cx
    #     ys -= cy
    
    #     # Rotate coords into ellipse frame
    #     xr = xs * np.cos(theta) + ys * np.sin(theta)
    
    #     front = np.logical_and(mask == 255, xr > 0)
    #     back  = np.logical_and(mask == 255, xr < 0)
    
    #     if np.count_nonzero(front) < 50 or np.count_nonzero(back) < 50:
    #         return self.facing_dir, 0, 0
    
    #     front_L = np.mean(L[front])
    #     back_L  = np.mean(L[back])
    
    #     new_dir = 1 if front_L > back_L else -1
    
    #     # Temporal stability (very important)
    #     if new_dir == self.facing_dir:
    #         self.face_confidence += 1
    #     else:
    #         self.face_confidence -= 1
    
    #     self.face_confidence = np.clip(
    #         self.face_confidence, -self.CONF_MAX, self.CONF_MAX
    #     )
    
    #     if abs(self.face_confidence) >= self.CONF_THRESH:
    #         self.facing_dir = new_dir
    
    #     return self.facing_dir, front_L, back_L

# ---------------- RUN ----------------
root = tk.Tk()
app = Cam(root)
root.mainloop()