import cv2
import os
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

class FaceCapture:
    def __init__(self):
        # Load Haar cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def capture_face_images(self, nic_number, num_images=20):
        """Capture face images using webcam with GUI preview"""
        # Create face directory using NIC
        face_dir = os.path.join('data/faces', nic_number)
        os.makedirs(face_dir, exist_ok=True)

        # Initialize webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Could not open webcam")
            return False

        # Create GUI window for preview
        preview_window = tk.Toplevel()
        preview_window.title(f"Capturing Face Images for NIC: {nic_number}")
        preview_window.geometry("800x600")

        # Create label for video feed
        video_label = ttk.Label(preview_window)
        video_label.pack(pady=10)

        # Create status label
        status_label = ttk.Label(preview_window, text=f"Capturing {num_images} face images... Look at the camera",
                                 font=('Arial', 12))
        status_label.pack(pady=5)

        # Create progress bar
        progress = ttk.Progressbar(preview_window, orient='horizontal',
                                   length=400, mode='determinate', maximum=num_images)
        progress.pack(pady=10)

        # Create count label
        count_label = ttk.Label(preview_window, text=f"Face images captured: 0/{num_images}",
                                font=('Arial', 10))
        count_label.pack(pady=5)

        count = 0
        captured_images = []

        def update_frame():
            nonlocal count
            ret, frame = cap.read()
            if not ret:
                return

            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

            # Draw rectangle around detected face
            frame_with_rect = frame.copy()
            face_detected = False

            if len(faces) > 0:
                face_detected = True
                x, y, w, h = faces[0]
                cv2.rectangle(frame_with_rect, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Auto-capture if face is detected and it's time to capture
                if count < num_images and len(captured_images) == count:
                    face_roi = frame[y:y + h, x:x + w]
                    if face_roi.size > 0:
                        captured_images.append(face_roi)
                        # Save image after a short delay to show feedback
                        preview_window.after(100, save_captured_image)

            # Convert frame to PhotoImage for Tkinter
            rgb_frame = cv2.cvtColor(frame_with_rect, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image=pil_image)

            video_label.configure(image=photo)
            video_label.image = photo

            if count < num_images:
                preview_window.after(30, update_frame)
            else:
                finish_capture()

        def save_captured_image():
            nonlocal count
            if count < len(captured_images):
                face_roi = captured_images[count]
                image_path = os.path.join(face_dir, f'{nic_number}_face_{count}.jpg')
                cv2.imwrite(image_path, face_roi)

                count += 1
                progress['value'] = count
                count_label.config(text=f"Face images captured: {count}/{num_images}")

                # Flash green background to indicate capture
                video_label.configure(background='green')
                preview_window.after(100, lambda: video_label.configure(background='SystemButtonFace'))

        def finish_capture():
            cap.release()
            status_label.config(text=f"Face capture completed! Saved {count} images for NIC: {nic_number}")
            progress['value'] = num_images

            # Add close button
            close_btn = ttk.Button(preview_window, text="Finish", command=preview_window.destroy)
            close_btn.pack(pady=10)

        def on_closing():
            cap.release()
            preview_window.destroy()

        preview_window.protocol("WM_DELETE_WINDOW", on_closing)
        update_frame()

        # Wait for window to close
        preview_window.grab_set()
        preview_window.wait_window()

        print(f"Captured {count} face images for NIC: {nic_number}")
        return True