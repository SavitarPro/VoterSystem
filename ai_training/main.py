import tkinter as tk
from tkinter import ttk, messagebox
from face_capture import FaceCapture
from fingerprint_capture import FingerprintCapture
from face_training import FaceTraining
from fingerprint_training import FingerprintTraining
import os


class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Face and Fingerprint Recognition System")
        self.root.geometry("600x400")

        self.setup_gui()
        self.create_directories()

    def create_directories(self):
        """Create the necessary directory structure"""
        directories = [
            'data/faces',
            'data/fingerprints',
            'models',
            'temp'
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")

    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        title_label = ttk.Label(main_frame, text="Face & Fingerprint Recognition System",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=20)

        # Option 1: Add new person
        add_btn = ttk.Button(main_frame, text="1. Add New Person (NIC)",
                             command=self.add_new_person, width=30)
        add_btn.grid(row=1, column=0, pady=10, padx=10)

        # Option 2: Train face model
        train_face_btn = ttk.Button(main_frame, text="2. Train Face Model",
                                    command=self.train_face_model, width=30)
        train_face_btn.grid(row=1, column=1, pady=10, padx=10)

        # Option 3: Train fingerprint model
        train_fingerprint_btn = ttk.Button(main_frame, text="3. Train Fingerprint Model",
                                           command=self.train_fingerprint_model, width=30)
        train_fingerprint_btn.grid(row=2, column=0, pady=10, padx=10)

        # Option 4: Train both models
        train_both_btn = ttk.Button(main_frame, text="4. Train Both Models",
                                    command=self.train_both_models, width=30)
        train_both_btn.grid(row=2, column=1, pady=10, padx=10)

        # Option 5: Exit
        exit_btn = ttk.Button(main_frame, text="5. Exit",
                              command=self.root.quit, width=30)
        exit_btn.grid(row=3, column=0, columnspan=2, pady=20)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready", font=('Arial', 10))
        self.status_label.grid(row=4, column=0, columnspan=2, pady=10)

    def add_new_person(self):
        def on_submit():
            nic = nic_entry.get().strip()
            if not nic:
                messagebox.showerror("Error", "Please enter NIC number")
                return

            num_images = images_entry.get().strip()
            num_images = int(num_images) if num_images.isdigit() else 20

            # Validate NIC format
            nic_pattern = r'^[0-9]{9,12}[VvXx]?$'
            import re
            if re.match(nic_pattern, nic):
                self.status_label.config(text=f"Starting capture for NIC: {nic}...")
                add_window.destroy()

                # Start with face capture
                face_capture = FaceCapture()
                if face_capture.capture_face_images(nic, num_images):
                    # Then fingerprint capture
                    fingerprint_capture = FingerprintCapture()
                    fingerprint_capture.capture_fingerprint_images(nic, num_images)

                self.status_label.config(text="Ready")
            else:
                messagebox.showerror("Error", "Invalid NIC format! Please enter a valid NIC number.")

        # Create input window
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New Person")
        add_window.geometry("400x200")

        ttk.Label(add_window, text="NIC Number:").pack(pady=5)
        nic_entry = ttk.Entry(add_window, width=30)
        nic_entry.pack(pady=5)

        ttk.Label(add_window, text="Number of Images (default 20):").pack(pady=5)
        images_entry = ttk.Entry(add_window, width=30)
        images_entry.pack(pady=5)

        submit_btn = ttk.Button(add_window, text="Start Capture", command=on_submit)
        submit_btn.pack(pady=20)

    def train_face_model(self):
        self.status_label.config(text="Training face model...")
        face_training = FaceTraining()

        # Run training in a separate thread to avoid GUI freezing
        def training_thread():
            if face_training.train_model():
                self.root.after(0, lambda: messagebox.showinfo("Success", "Face training completed successfully!"))
                self.root.after(0, lambda: self.status_label.config(text="Face training completed"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Face training failed!"))

        import threading
        threading.Thread(target=training_thread, daemon=True).start()

    def train_fingerprint_model(self):
        self.status_label.config(text="Training fingerprint model...")
        fingerprint_training = FingerprintTraining()

        # Run training in a separate thread to avoid GUI freezing
        def training_thread():
            if fingerprint_training.train_model():
                self.root.after(0,
                                lambda: messagebox.showinfo("Success", "Fingerprint training completed successfully!"))
                self.root.after(0, lambda: self.status_label.config(text="Fingerprint training completed"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Fingerprint training failed!"))

        import threading
        threading.Thread(target=training_thread, daemon=True).start()

    def train_both_models(self):
        self.status_label.config(text="Training both models...")
        face_training = FaceTraining()
        fingerprint_training = FingerprintTraining()

        # Run training in a separate thread to avoid GUI freezing
        def training_thread():
            # Train face model
            if face_training.train_model():
                self.root.after(0, lambda: self.status_label.config(
                    text="Face model trained. Training fingerprint model..."))

                # Train fingerprint model
                if fingerprint_training.train_model():
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Both models trained successfully!"))
                    self.root.after(0, lambda: self.status_label.config(text="Both models trained"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Fingerprint training failed!"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Face training failed!"))

        import threading
        threading.Thread(target=training_thread, daemon=True).start()


def main():
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()