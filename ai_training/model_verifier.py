import os
import cv2
import numpy as np
import pickle
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import time


class ModelTester:
    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.known_face_nics = None

        # Load Haar cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        # Load the trained model
        self.load_model()

    def load_model(self):
        """Load the trained model from file"""
        model_path = 'models/face_model.pkl'

        if not os.path.exists(model_path):
            messagebox.showerror("Error", f"Model file not found at: {model_path}")
            return False

        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)

            self.model = model_data['model']
            self.label_encoder = model_data['label_encoder']
            self.known_face_nics = model_data['known_face_nics']

            print(f"Model loaded successfully!")
            print(f"Trained on {len(self.known_face_nics)} samples")
            print(f"Number of classes: {len(self.label_encoder.classes_)}")
            return True

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load model: {str(e)}")
            return False

    def extract_face_embeddings(self, face_image):
        """Extract embeddings from face image (same as training)"""
        # Resize to consistent size
        face_resized = cv2.resize(face_image, (100, 100))

        # Convert to grayscale if needed
        if len(face_resized.shape) == 3:
            face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            face_gray = face_resized

        # Apply histogram equalization for better contrast
        face_eq = cv2.equalizeHist(face_gray)

        # Flatten and normalize
        embedding = face_eq.flatten().astype(np.float32) / 255.0

        return embedding

    def detect_faces(self, image):
        """Detect faces using Haar cascade"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        return faces

    def test_with_webcam(self):
        """Test the model with live webcam feed"""
        if self.model is None:
            messagebox.showerror("Error", "No model loaded! Please train the model first.")
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Could not open webcam")
            return

        # Create test window
        test_window = tk.Toplevel()
        test_window.title("Model Testing - Live Webcam")
        test_window.geometry("800x600")

        # Create video label
        video_label = ttk.Label(test_window)
        video_label.pack(pady=10)

        # Create status label
        status_label = ttk.Label(test_window, text="Looking for faces...",
                                 font=('Arial', 12))
        status_label.pack(pady=5)

        # Create result label
        result_label = ttk.Label(test_window, text="No face detected",
                                 font=('Arial', 14, 'bold'), foreground='red')
        result_label.pack(pady=5)

        # Create confidence label
        confidence_label = ttk.Label(test_window, text="Confidence: N/A",
                                     font=('Arial', 10))
        confidence_label.pack(pady=2)

        # Create test controls frame
        controls_frame = ttk.Frame(test_window)
        controls_frame.pack(pady=10)

        # Add test buttons
        test_single_btn = ttk.Button(controls_frame, text="Test Current Frame",
                                     command=lambda: test_single_frame())
        test_single_btn.pack(side=tk.LEFT, padx=5)

        continuous_test_var = tk.BooleanVar(value=True)
        continuous_test_btn = ttk.Checkbutton(controls_frame, text="Continuous Test",
                                              variable=continuous_test_var)
        continuous_test_btn.pack(side=tk.LEFT, padx=5)

        running = True

        def test_single_frame():
            nonlocal current_frame
            if current_frame is not None:
                process_frame(current_frame)

        def update_frame():
            nonlocal current_frame
            if not running:
                return

            ret, frame = cap.read()
            if not ret:
                return

            current_frame = frame.copy()

            # Display frame
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image=pil_image)

            video_label.configure(image=photo)
            video_label.image = photo

            # Process frame if continuous testing is enabled
            if continuous_test_var.get():
                process_frame(frame)

            test_window.after(30, update_frame)

        def process_frame(frame):
            # Detect faces
            faces = self.detect_faces(frame)

            if len(faces) > 0:
                # Use the first detected face
                x, y, w, h = faces[0]

                # Draw rectangle around face
                frame_with_rect = frame.copy()
                cv2.rectangle(frame_with_rect, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Extract face region
                face_roi = frame[y:y + h, x:x + w]

                try:
                    # Extract embeddings
                    embedding = self.extract_face_embeddings(face_roi)
                    embedding = embedding.reshape(1, -1)

                    # Predict
                    prediction = self.model.predict(embedding)
                    confidence = np.max(self.model.predict_proba(embedding))

                    # Decode prediction
                    predicted_nic = self.label_encoder.inverse_transform(prediction)[0]

                    # Update labels
                    result_label.config(text=f"Recognized: {predicted_nic}", foreground='green')
                    confidence_label.config(text=f"Confidence: {confidence:.2%}")
                    status_label.config(text="Face recognized!")

                    # Display result on frame
                    cv2.putText(frame_with_rect, f"NIC: {predicted_nic}", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame_with_rect, f"Conf: {confidence:.2%}", (x, y + h + 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                except Exception as e:
                    result_label.config(text=f"Error: {str(e)}", foreground='red')
                    confidence_label.config(text="Confidence: N/A")
            else:
                result_label.config(text="No face detected", foreground='red')
                confidence_label.config(text="Confidence: N/A")
                status_label.config(text="Looking for faces...")

        def on_closing():
            nonlocal running
            running = False
            cap.release()
            test_window.destroy()

        test_window.protocol("WM_DELETE_WINDOW", on_closing)
        current_frame = None
        update_frame()

    def test_with_image(self, image_path):
        """Test the model with a single image file"""
        if self.model is None:
            messagebox.showerror("Error", "No model loaded! Please train the model first.")
            return

        if not os.path.exists(image_path):
            messagebox.showerror("Error", f"Image file not found: {image_path}")
            return

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            messagebox.showerror("Error", "Could not load image")
            return

        # Detect faces
        faces = self.detect_faces(image)

        if len(faces) == 0:
            messagebox.showinfo("Result", "No face detected in the image")
            return

        # Process each face
        results = []
        for i, (x, y, w, h) in enumerate(faces):
            face_roi = image[y:y + h, x:x + w]

            try:
                # Extract embeddings
                embedding = self.extract_face_embeddings(face_roi)
                embedding = embedding.reshape(1, -1)

                # Predict
                prediction = self.model.predict(embedding)
                confidence = np.max(self.model.predict_proba(embedding))

                # Decode prediction
                predicted_nic = self.label_encoder.inverse_transform(prediction)[0]

                results.append({
                    'face_index': i + 1,
                    'nic': predicted_nic,
                    'confidence': confidence,
                    'position': (x, y, w, h)
                })

            except Exception as e:
                results.append({
                    'face_index': i + 1,
                    'nic': f"Error: {str(e)}",
                    'confidence': 0.0,
                    'position': (x, y, w, h)
                })

        # Show results
        result_text = "Face Recognition Results:\n\n"
        for result in results:
            result_text += f"Face {result['face_index']}:\n"
            result_text += f"  NIC: {result['nic']}\n"
            result_text += f"  Confidence: {result['confidence']:.2%}\n"
            result_text += f"  Position: {result['position']}\n\n"

        messagebox.showinfo("Test Results", result_text)

    def test_with_dataset(self):
        """Test the model with the training dataset"""
        if self.model is None:
            messagebox.showerror("Error", "No model loaded! Please train the model first.")
            return

        training_dir = 'data/faces'
        if not os.path.exists(training_dir):
            messagebox.showerror("Error", f"Training directory not found: {training_dir}")
            return

        total_tests = 0
        correct_predictions = 0
        results = []

        # Test each person in the dataset
        for nic_number in os.listdir(training_dir):
            person_dir = os.path.join(training_dir, nic_number)
            if not os.path.isdir(person_dir):
                continue

            person_correct = 0
            person_total = 0

            # Test each image for this person
            for image_name in os.listdir(person_dir):
                if image_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_path = os.path.join(person_dir, image_name)

                    # Load and process image
                    image = cv2.imread(image_path)
                    if image is not None:
                        faces = self.detect_faces(image)

                        if len(faces) > 0:
                            x, y, w, h = faces[0]
                            face_roi = image[y:y + h, x:x + w]

                            try:
                                embedding = self.extract_face_embeddings(face_roi)
                                embedding = embedding.reshape(1, -1)

                                prediction = self.model.predict(embedding)
                                confidence = np.max(self.model.predict_proba(embedding))
                                predicted_nic = self.label_encoder.inverse_transform(prediction)[0]

                                is_correct = (predicted_nic == nic_number)
                                if is_correct:
                                    correct_predictions += 1
                                    person_correct += 1

                                total_tests += 1
                                person_total += 1

                            except Exception as e:
                                print(f"Error processing {image_path}: {e}")

            if person_total > 0:
                accuracy = person_correct / person_total
                results.append(f"NIC {nic_number}: {person_correct}/{person_total} ({accuracy:.2%})")

        # Calculate overall accuracy
        overall_accuracy = correct_predictions / total_tests if total_tests > 0 else 0

        # Show results
        result_text = f"Dataset Test Results:\n\n"
        result_text += f"Overall Accuracy: {overall_accuracy:.2%} ({correct_predictions}/{total_tests})\n\n"
        result_text += "Per Person Results:\n"
        result_text += "\n".join(results)

        messagebox.showinfo("Dataset Test Results", result_text)


class ModelTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Model Verification Tool")
        self.root.geometry("500x400")

        self.tester = ModelTester()

        self.setup_gui()

    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        title_label = ttk.Label(main_frame, text="Face Recognition Model Verifier",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=20)

        # Model status
        status_text = "Model Status: " + ("Loaded" if self.tester.model is not None else "Not Loaded")
        self.status_label = ttk.Label(main_frame, text=status_text, font=('Arial', 12))
        self.status_label.grid(row=1, column=0, pady=10)

        if self.tester.model is not None:
            classes_text = f"Classes: {len(self.tester.label_encoder.classes_)} people"
            classes_label = ttk.Label(main_frame, text=classes_text, font=('Arial', 10))
            classes_label.grid(row=2, column=0, pady=5)

        # Test options
        test_frame = ttk.LabelFrame(main_frame, text="Test Options", padding="10")
        test_frame.grid(row=3, column=0, pady=20, sticky=(tk.W, tk.E))

        # Live webcam test
        webcam_btn = ttk.Button(test_frame, text="Live Webcam Test",
                                command=self.tester.test_with_webcam, width=25)
        webcam_btn.grid(row=0, column=0, pady=10, padx=5)

        # Test with image file
        image_btn = ttk.Button(test_frame, text="Test Single Image",
                               command=self.test_single_image, width=25)
        image_btn.grid(row=0, column=1, pady=10, padx=5)

        # Test with dataset
        dataset_btn = ttk.Button(test_frame, text="Test Entire Dataset",
                                 command=self.tester.test_with_dataset, width=25)
        dataset_btn.grid(row=1, column=0, pady=10, padx=5, columnspan=2)

        # Instructions
        instructions = ttk.Label(main_frame,
                                 text="Instructions:\n"
                                      "1. Live Webcam: Real-time face recognition\n"
                                      "2. Single Image: Test with a specific image file\n"
                                      "3. Entire Dataset: Test accuracy on training data",
                                 font=('Arial', 9), justify=tk.LEFT)
        instructions.grid(row=4, column=0, pady=10, sticky=tk.W)

        # Refresh button
        refresh_btn = ttk.Button(main_frame, text="Refresh Model Status",
                                 command=self.refresh_status)
        refresh_btn.grid(row=5, column=0, pady=10)

    def test_single_image(self):
        """Open file dialog to select test image"""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Select Test Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*")]
        )

        if file_path:
            self.tester.test_with_image(file_path)

    def refresh_status(self):
        """Refresh model status"""
        self.tester.load_model()
        status_text = "Model Status: " + ("Loaded" if self.tester.model is not None else "Not Loaded")
        self.status_label.config(text=status_text)


def main():
    root = tk.Tk()
    app = ModelTesterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    # Create necessary directories if they don't exist
    os.makedirs('models', exist_ok=True)
    os.makedirs('data/faces', exist_ok=True)

    main()