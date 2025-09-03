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
        """Capture fingerprint images using webcam with GUI preview"""
        # Create fingerprint directory using NIC
        fingerprint_dir = os.path.join('data/fingerprints', nic_number)
        os.makedirs(fingerprint_dir, exist_ok=True)

        # Initialize webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Could not open webcam")
            return False

        # Create GUI window for preview
        preview_window = tk.Toplevel()
        preview_window.title(f"Capturing Fingerprint Images for NIC: {nic_number}")
        preview_window.geometry("800x600")

        # Create label for video feed
        video_label = ttk.Label(preview_window)
        video_label.pack(pady=10)

        # Create instructions label
        instructions_label = ttk.Label(preview_window,
                                       text="Place your finger on the scanner. Press 'C' to capture image manually\nor wait for auto-capture.",
                                       font=('Arial', 10),
                                       wraplength=400)
        instructions_label.pack(pady=5)

        # Create status label
        status_label = ttk.Label(preview_window, text=f"Capturing {num_images} fingerprint images...",
                                 font=('Arial', 12))
        status_label.pack(pady=5)

        # Create progress bar
        progress = ttk.Progressbar(preview_window, orient='horizontal',
                                   length=400, mode='determinate', maximum=num_images)
        progress.pack(pady=10)

        # Create count label
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

            # Process frame for better fingerprint visibility
            processed_frame = self.enhance_fingerprint_image(frame)

            # Convert frame to PhotoImage for Tkinter
            rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image=pil_image)

            video_label.configure(image=photo)
            video_label.image = photo

            # Auto-capture logic
            if auto_capture and count < num_images:
                # Simple auto-capture based on frame stability (you can enhance this)
                if self.is_frame_clear(processed_frame):
                    save_fingerprint_image(processed_frame)
                    # Add delay between auto-captures
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

                # Flash blue background to indicate capture
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

            # Add close button
            close_btn = ttk.Button(preview_window, text="Finish", command=preview_window.destroy)
            close_btn.pack(pady=10)

        def on_closing():
            cap.release()
            preview_window.destroy()

        # Bind keyboard events
        preview_window.bind('c', manual_capture)
        preview_window.bind('C', manual_capture)
        preview_window.bind('a', lambda e: toggle_auto_capture())
        preview_window.bind('A', lambda e: toggle_auto_capture())

        preview_window.protocol("WM_DELETE_WINDOW", on_closing)
        preview_window.focus_set()  # Set focus to receive keyboard events

        # Add control buttons
        control_frame = ttk.Frame(preview_window)
        control_frame.pack(pady=10)

        manual_btn = ttk.Button(control_frame, text="Manual Capture (C)", command=manual_capture)
        manual_btn.pack(side=tk.LEFT, padx=5)

        auto_btn = ttk.Button(control_frame, text="Toggle Auto (A)", command=toggle_auto_capture)
        auto_btn.pack(side=tk.LEFT, padx=5)

        update_frame()

        # Wait for window to close
        preview_window.grab_set()
        preview_window.wait_window()

        print(f"Captured {count} fingerprint images for NIC: {nic_number}")
        return True

    def enhance_fingerprint_image(self, frame):
        """Enhance fingerprint image for better visibility"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)

        # Convert back to BGR for display
        return cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)

    def is_frame_clear(self, frame):
        """Simple check if frame is clear enough for fingerprint capture"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Calculate variance of Laplacian to measure blurriness
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Frame is considered clear if variance is above threshold
        return laplacian_var > 100