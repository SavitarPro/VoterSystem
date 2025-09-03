import os
import cv2
import numpy as np
import pickle
from sklearn import svm
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split


class FaceTraining:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_nics = []
        self.model = None
        self.label_encoder = LabelEncoder()

        # Load Haar cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def extract_face_embeddings(self, face_image):
        """Extract embeddings from face image"""
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

    def load_training_data(self, training_dir):
        """Load face images from training directory"""
        self.known_face_encodings = []
        self.known_face_nics = []

        if not os.path.exists(training_dir):
            print(f"Training directory '{training_dir}' does not exist!")
            return False

        for nic_number in os.listdir(training_dir):
            person_dir = os.path.join(training_dir, nic_number)
            if not os.path.isdir(person_dir):
                continue

            image_count = 0
            for image_name in os.listdir(person_dir):
                if image_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_path = os.path.join(person_dir, image_name)

                    # Load image using OpenCV
                    image = cv2.imread(image_path)
                    if image is None:
                        print(f"Could not load image: {image_path}")
                        continue

                    # Detect faces
                    faces = self.detect_faces(image)

                    if len(faces) > 0:
                        # Use the first detected face
                        x, y, w, h = faces[0]
                        face_roi = image[y:y + h, x:x + w]

                        try:
                            face_embedding = self.extract_face_embeddings(face_roi)
                            self.known_face_encodings.append(face_embedding)
                            self.known_face_nics.append(nic_number)
                            image_count += 1
                        except Exception as e:
                            print(f"Error processing {image_path}: {e}")
                            continue
                    else:
                        print(f"No face detected in {image_path}")

            if image_count > 0:
                print(f"Loaded {image_count} images for NIC: {nic_number}")

        print(f"Total: {len(self.known_face_encodings)} face encodings for {len(set(self.known_face_nics))} people")
        return len(self.known_face_encodings) > 0

    def train_model(self):
        """Train SVM classifier on face encodings"""
        training_dir = 'data/faces'

        if not self.load_training_data(training_dir):
            print("No training data available")
            return False

        # Convert to numpy arrays
        X = np.array(self.known_face_encodings)
        y = np.array(self.known_face_nics)

        # Split data for training and testing
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Encode labels
        encoded_labels_train = self.label_encoder.fit_transform(y_train)
        encoded_labels_test = self.label_encoder.transform(y_test)

        # Train SVM classifier
        self.model = svm.SVC(kernel='linear', probability=True, random_state=42)
        self.model.fit(X_train, encoded_labels_train)

        # Evaluate model
        train_accuracy = self.model.score(X_train, encoded_labels_train)
        test_accuracy = self.model.score(X_test, encoded_labels_test)

        print("Face recognition model trained successfully")
        print(f"Training Accuracy: {train_accuracy:.2f}")
        print(f"Testing Accuracy: {test_accuracy:.2f}")

        # Save model
        model_path = 'models/face_model.pkl'
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'label_encoder': self.label_encoder,
                'known_face_nics': self.known_face_nics
            }, f)

        print(f"Model saved to {model_path}")
        return True