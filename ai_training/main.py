
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
        self.root.geometry("700x500")

        self.setup_gui()
        self.create_directories()

    def create_directories(self):
        
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
        
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        
        title_label = ttk.Label(main_frame, text="Face & Fingerprint Recognition System",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=20)

        
        add_btn = ttk.Button(main_frame, text="1. Add New Person (NIC)",
                             command=self.add_new_person, width=30)
        add_btn.grid(row=1, column=0, pady=10, padx=10)

        
        train_face_btn = ttk.Button(main_frame, text="2. Train Face Model (CNN)",
                                    command=self.train_face_model, width=30)
        train_face_btn.grid(row=1, column=1, pady=10, padx=10)

        
        train_fingerprint_btn = ttk.Button(main_frame, text="3. Train Fingerprint Model (CNN)",
                                           command=self.train_fingerprint_model, width=30)
        train_fingerprint_btn.grid(row=2, column=0, pady=10, padx=10)

        
        train_both_btn = ttk.Button(main_frame, text="4. Train Both Models (CNN)",
                                    command=self.train_both_models, width=30)
        train_both_btn.grid(row=2, column=1, pady=10, padx=10)

        
        verify_btn = ttk.Button(main_frame, text="5. Model Verification",
                                command=self.open_verifier, width=30)
        verify_btn.grid(row=3, column=0, pady=10, padx=10)

        
        exit_btn = ttk.Button(main_frame, text="6. Exit",
                              command=self.root.quit, width=30)
        exit_btn.grid(row=3, column=1, pady=10, padx=10)

        
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

            
            nic_pattern = r'^[0-9]{9,12}[VvXx]?$'
            import re
            if re.match(nic_pattern, nic):
                self.status_label.config(text=f"Starting capture for NIC: {nic}...")
                add_window.destroy()

                
                face_capture = FaceCapture()
                if face_capture.capture_face_images(nic, num_images):
                    
                    fingerprint_capture = FingerprintCapture()
                    fingerprint_capture.capture_fingerprint_images(nic, num_images)

                self.status_label.config(text="Ready")
            else:
                messagebox.showerror("Error", "Invalid NIC format! Please enter a valid NIC number.")

        
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
        self.status_label.config(text="Training face model (CNN)...")
        face_training = FaceTraining()

        
        def training_thread():
            if face_training.train_model():
                self.root.after(0, lambda: messagebox.showinfo("Success", "Face CNN training completed successfully!"))
                self.root.after(0, lambda: self.status_label.config(text="Face CNN training completed"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Face CNN training failed!"))

        import threading
        threading.Thread(target=training_thread, daemon=True).start()

    def train_fingerprint_model(self):
        self.status_label.config(text="Training fingerprint model (CNN)...")
        fingerprint_training = FingerprintTraining()

        
        def training_thread():
            if fingerprint_training.train_model():
                self.root.after(0,
                                lambda: messagebox.showinfo("Success",
                                                            "Fingerprint CNN training completed successfully!"))
                self.root.after(0, lambda: self.status_label.config(text="Fingerprint CNN training completed"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Fingerprint CNN training failed!"))

        import threading
        threading.Thread(target=training_thread, daemon=True).start()

    def train_both_models(self):
        self.status_label.config(text="Training both models (CNN)...")
        face_training = FaceTraining()
        fingerprint_training = FingerprintTraining()

        
        def training_thread():
            
            if face_training.train_model():
                self.root.after(0, lambda: self.status_label.config(
                    text="Face CNN model trained. Training fingerprint model..."))

                
                if fingerprint_training.train_model():
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Both CNN models trained successfully!"))
                    self.root.after(0, lambda: self.status_label.config(text="Both CNN models trained"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Fingerprint CNN training failed!"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Face CNN training failed!"))

        import threading
        threading.Thread(target=training_thread, daemon=True).start()

    def open_verifier(self):
        
        try:
            from model_verifier import ModelTesterGUI
            verifier_window = tk.Toplevel(self.root)
            ModelTesterGUI(verifier_window)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open verifier: {str(e)}")


def main():
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()