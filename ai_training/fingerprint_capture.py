import cv2
import os
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

class FingerprintCapture:
    def __init__(self):
        pass

    def capture_fingerprint_images(self, nic_number, num_images=20):


        fingerprint_dir = os.path.join('data/fingerprints', nic_number)
        os.makedirs(fingerprint_dir, exist_ok=True)


        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Could not open webcam")
            return False


        preview_window = tk.Toplevel()
        preview_window.title(f"Capturing Fingerprint Images for NIC: {nic_number}")
        preview_window.geometry("800x600")


        video_label = ttk.Label(preview_window)
        video_label.pack(pady=10)


        instructions_label = ttk.Label(preview_window,
                                       text="Place your finger on the scanner. Press 'C' to capture image manually\nor wait for auto-capture.",
                                       font=('Arial', 10),
                                       wraplength=400)
        instructions_label.pack(pady=5)


        status_label = ttk.Label(preview_window, text=f"Capturing {num_images} fingerprint images...",
                                 font=('Arial', 12))
        status_label.pack(pady=5)


        progress = ttk.Progressbar(preview_window, orient='horizontal',
                                   length=400, mode='determinate', maximum=num_images)
        progress.pack(pady=10)


        count_label = ttk.Label(preview_window, text=f"Fingerprint images captured: 0/{num_images}",
                                font=('Arial', 10))
        count_label.pack(pady=5)

        count = 0
        auto_capture = True

        def update_frame():
            nonlocal count
            ret, frame = cap.read()
            if not ret:
                return


            processed_frame = self.enhance_fingerprint_image(frame)


            rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image=pil_image)

            video_label.configure(image=photo)
            video_label.image = photo


            if auto_capture and count < num_images:

                if self.is_frame_clear(processed_frame):
                    save_fingerprint_image(processed_frame)

                    preview_window.after(1000, update_frame)
                    return

            if count < num_images:
                preview_window.after(30, update_frame)
            else:
                finish_capture()

        def save_fingerprint_image(frame):
            nonlocal count
            if count < num_images:
                image_path = os.path.join(fingerprint_dir, f'{nic_number}_fingerprint_{count}.jpg')
                cv2.imwrite(image_path, frame)

                count += 1
                progress['value'] = count
                count_label.config(text=f"Fingerprint images captured: {count}/{num_images}")


                video_label.configure(background='blue')
                preview_window.after(100, lambda: video_label.configure(background='SystemButtonFace'))

        def manual_capture(event=None):
            ret, frame = cap.read()
            if ret:
                processed_frame = self.enhance_fingerprint_image(frame)
                save_fingerprint_image(processed_frame)

        def toggle_auto_capture():
            nonlocal auto_capture
            auto_capture = not auto_capture
            mode = "Auto" if auto_capture else "Manual"
            status_label.config(text=f"Mode: {mode} - Capturing {num_images} fingerprint images...")

        def finish_capture():
            cap.release()
            status_label.config(text=f"Fingerprint capture completed! Saved {count} images for NIC: {nic_number}")
            progress['value'] = num_images


            close_btn = ttk.Button(preview_window, text="Finish", command=preview_window.destroy)
            close_btn.pack(pady=10)

        def on_closing():
            cap.release()
            preview_window.destroy()


        preview_window.bind('c', manual_capture)
        preview_window.bind('C', manual_capture)
        preview_window.bind('a', lambda e: toggle_auto_capture())
        preview_window.bind('A', lambda e: toggle_auto_capture())

        preview_window.protocol("WM_DELETE_WINDOW", on_closing)
        preview_window.focus_set()


        control_frame = ttk.Frame(preview_window)
        control_frame.pack(pady=10)

        manual_btn = ttk.Button(control_frame, text="Manual Capture (C)", command=manual_capture)
        manual_btn.pack(side=tk.LEFT, padx=5)

        auto_btn = ttk.Button(control_frame, text="Toggle Auto (A)", command=toggle_auto_capture)
        auto_btn.pack(side=tk.LEFT, padx=5)

        update_frame()


        preview_window.grab_set()
        preview_window.wait_window()

        print(f"Captured {count} fingerprint images for NIC: {nic_number}")
        return True

    def enhance_fingerprint_image(self, frame):


        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)


        blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)


        return cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)

    def is_frame_clear(self, frame):


        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()


        return laplacian_var > 100