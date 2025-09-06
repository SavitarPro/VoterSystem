
import os
import cv2
import numpy as np
import pickle
import tensorflow as tf
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import time


class ModelTester:
    def __init__(self):
        self.cnn_model = None
        self.label_encoder = None
        self.known_face_nics = None
        self.input_shape = None

        
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        
        self.load_model()

    
    def load_model(self):
        
        model_path = 'models/face_model.h5'
        metadata_path = 'models/face_model_metadata.pkl'

        if not os.path.exists(model_path) or not os.path.exists(metadata_path):
            messagebox.showerror("Error", f"Model files not found. Please train the CNN model first.")
            return False

        try:
            
            self.cnn_model = tf.keras.models.load_model(model_path)

            
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
                self.label_to_nic = self.metadata['label_to_nic']
                self.nic_to_label = self.metadata['nic_to_label']
                self.unique_nics = self.metadata['unique_nics']
                self.input_shape = self.metadata['input_shape']

            print(f"CNN Model loaded successfully!")
            print(f"Trained on {len(self.unique_nics)} people: {self.unique_nics}")
            return True

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load model: {str(e)}")
            return False

    def extract_face_embeddings_cnn(self, face_image):
        
        
        face_resized = cv2.resize(face_image, (self.input_shape[0], self.input_shape[1]))

        
        if len(face_resized.shape) == 3:
            face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            face_gray = face_resized

        
        face_normalized = face_gray / 255.0

        
        face_normalized = np.expand_dims(face_normalized, axis=-1)

        return face_normalized

    def detect_faces(self, image):
        
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
        
        if self.cnn_model is None:
            messagebox.showerror("Error", "No model loaded! Please train the CNN model first.")
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Could not open webcam")
            return

        
        test_window = tk.Toplevel()
        test_window.title("CNN Model Testing - Live Webcam")
        test_window.geometry("800x600")

        
        video_label = ttk.Label(test_window)
        video_label.pack(pady=10)

        
        status_label = ttk.Label(test_window, text="Looking for faces...",
                                 font=('Arial', 12))
        status_label.pack(pady=5)

        
        result_label = ttk.Label(test_window, text="No face detected",
                                 font=('Arial', 14, 'bold'), foreground='red')
        result_label.pack(pady=5)

        
        confidence_label = ttk.Label(test_window, text="Confidence: N/A",
                                     font=('Arial', 10))
        confidence_label.pack(pady=2)

        
        controls_frame = ttk.Frame(test_window)
        controls_frame.pack(pady=10)

        
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

            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image=pil_image)

            video_label.configure(image=photo)
            video_label.image = photo

            
            if continuous_test_var.get():
                process_frame(frame)

            test_window.after(30, update_frame)

        
        def process_frame(self, frame):
            
            faces = self.detect_faces(frame)

            if len(faces) > 0:
                
                x, y, w, h = faces[0]

                
                frame_with_rect = frame.copy()
                cv2.rectangle(frame_with_rect, (x, y), (x + w, y + h), (0, 255, 0), 2)

                
                face_roi = frame[y:y + h, x:x + w]

                try:
                    
                    embedding = self.extract_face_embeddings_cnn(face_roi)
                    embedding = np.expand_dims(embedding, axis=0)

                    
                    predictions = self.cnn_model.predict(embedding, verbose=0)
                    predicted_label = np.argmax(predictions[0])
                    confidence = predictions[0][predicted_label]

                    
                    predicted_nic = self.metadata['label_to_nic'].get(predicted_label, "Unknown")

                    
                    result_label.config(text=f"Recognized: {predicted_nic}", foreground='green')
                    confidence_label.config(text=f"Confidence: {confidence:.2%}")
                    status_label.config(text="Face recognized!")

                    
                    cv2.putText(frame_with_rect, f"NIC: {predicted_nic}", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame_with_rect, f"Conf: {confidence:.2%}", (x, y + h + 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                except Exception as e:
                    result_label.config(text=f"Error: {str(e)}", foreground='red')
                    confidence_label.config(text="Confidence: N/A")

        def on_closing():
            nonlocal running
            running = False
            cap.release()
            test_window.destroy()

        test_window.protocol("WM_DELETE_WINDOW", on_closing)
        current_frame = None
        update_frame()

    def test_with_image(self, image_path):
        
        if self.cnn_model is None:
            messagebox.showerror("Error", "No model loaded! Please train the CNN model first.")
            return

        if not os.path.exists(image_path):
            messagebox.showerror("Error", f"Image file not found: {image_path}")
            return

        
        image = cv2.imread(image_path)
        if image is None:
            messagebox.showerror("Error", "Could not load image")
            return

        
        faces = self.detect_faces(image)

        if len(faces) == 0:
            messagebox.showinfo("Result", "No face detected in the image")
            return

        
        results = []
        for i, (x, y, w, h) in enumerate(faces):
            face_roi = image[y:y + h, x:x + w]

            try:
                
                embedding = self.extract_face_embeddings_cnn(face_roi)
                embedding = np.expand_dims(embedding, axis=0)

                
                predictions = self.cnn_model.predict(embedding, verbose=0)
                predicted_class = np.argmax(predictions[0])
                confidence = predictions[0][predicted_class]

                
                predicted_nic = self.label_encoder.inverse_transform([predicted_class])[0]

                results.append({
                    'face_id': i + 1,
                    'nic': predicted_nic,
                    'confidence': confidence,
                    'bbox': (x, y, w, h)
                })

            except Exception as e:
                results.append({
                    'face_id': i + 1,
                    'nic': f"Error: {str(e)}",
                    'confidence': 0.0,
                    'bbox': (x, y, w, h)
                })

        
        result_text = "Face Recognition Results:\n\n"
        for result in results:
            result_text += f"Face {result['face_id']}:\n"
            result_text += f"  NIC: {result['nic']}\n"
            result_text += f"  Confidence: {result['confidence']:.2%}\n\n"

        messagebox.showinfo("Recognition Results", result_text)

        
        result_image = image.copy()
        for result in results:
            x, y, w, h = result['bbox']
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(result_image, f"NIC: {result['nic']}", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(result_image, f"Conf: {result['confidence']:.2%}", (x, y + h + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        
        cv2.imshow("Recognition Results", result_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


class ModelTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CNN Model Tester")
        self.root.geometry("500x300")

        self.tester = ModelTester()

        self.setup_gui()

    def setup_gui(self):
        
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        
        title_label = ttk.Label(main_frame, text="CNN Model Testing Tool",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=20)

        
        webcam_btn = ttk.Button(main_frame, text="Test with Webcam",
                                command=self.test_webcam, width=25)
        webcam_btn.grid(row=1, column=0, pady=15, padx=10)

        
        image_btn = ttk.Button(main_frame, text="Test with Image File",
                               command=self.test_image_file, width=25)
        image_btn.grid(row=1, column=1, pady=15, padx=10)

        
        self.status_label = ttk.Label(main_frame, text="Ready to test CNN model", font=('Arial', 10))
        self.status_label.grid(row=2, column=0, columnspan=2, pady=10)

    def test_webcam(self):
        self.status_label.config(text="Starting webcam test...")
        self.tester.test_with_webcam()
        self.status_label.config(text="Webcam test completed")

    def test_image_file(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )

        if file_path:
            self.status_label.config(text=f"Testing image: {os.path.basename(file_path)}")
            self.tester.test_with_image(file_path)
            self.status_label.config(text="Image test completed")


def main():
    root = tk.Tk()
    app = ModelTesterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()