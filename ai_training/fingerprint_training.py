import os
import cv2
import numpy as np
import pickle
from sklearn import svm
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split


class FingerprintTraining:
    def __init__(self):
        self.known_fingerprint_encodings = []
        self.known_fingerprint_nics = []
        self.model = None
        self.label_encoder = LabelEncoder()

    def extract_fingerprint_features(self, fingerprint_image):
        """Extract features from fingerprint image using enhanced method"""
        # Resize to consistent size
        fingerprint_resized = cv2.resize(fingerprint_image, (100, 100))

        # Convert to grayscale if needed
        if len(fingerprint_resized.shape) == 3:
            fingerprint_gray = cv2.cvtColor(fingerprint_resized, cv2.COLOR_BGR2GRAY)
        else:
            fingerprint_gray = fingerprint_resized

        # Apply histogram equalization for better contrast
        fingerprint_eq = cv2.equalizeHist(fingerprint_gray)

        # Apply Gaussian blur to reduce noise
        fingerprint_blur = cv2.GaussianBlur(fingerprint_eq, (5, 5), 0)

        # Apply adaptive threshold to enhance ridges
        fingerprint_thresh = cv2.adaptiveThreshold(
            fingerprint_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Extract features using ORB (Oriented FAST and Rotated BRIEF)
        orb = cv2.ORB_create(nfeatures=100)
        keypoints, descriptors = orb.detectAndCompute(fingerprint_thresh, None)

        # If descriptors exist, use them as features
        if descriptors is not None:
            # Flatten descriptors and pad if necessary
            if len(descriptors) > 0:
                # Use the first descriptor (you might want to aggregate multiple descriptors)
                features = descriptors[0].flatten()
                if len(features) < 100:
                    features = np.pad(features, (0, 100 - len(features)), 'constant')
                return features[:100]  # Return first 100 features
        else:
            # Fallback: use the processed image as features
            return fingerprint_thresh.flatten()[:100]

        return fingerprint_thresh.flatten()[:100]

    def load_training_data(self, training_dir):
        """Load fingerprint images from training directory"""
        self.known_fingerprint_encodings = []
        self.known_fingerprint_nics = []

        if not os.path.exists(training_dir):
            print(f"Fingerprint training directory '{training_dir}' does not exist!")
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
                        print(f"Could not load fingerprint image: {image_path}")
                        continue

                    try:
                        fingerprint_features = self.extract_fingerprint_features(image)
                        self.known_fingerprint_encodings.append(fingerprint_features)
                        self.known_fingerprint_nics.append(nic_number)
                        image_count += 1
                    except Exception as e:
                        print(f"Error processing fingerprint {image_path}: {e}")
                        continue

            if image_count > 0:
                print(f"Loaded {image_count} fingerprint images for NIC: {nic_number}")

        print(
            f"Total: {len(self.known_fingerprint_encodings)} fingerprint encodings for {len(set(self.known_fingerprint_nics))} people")
        return len(self.known_fingerprint_encodings) > 0

    def train_model(self):
        """Train SVM classifier on fingerprint features"""
        training_dir = 'data/fingerprints'

        if not self.load_training_data(training_dir):
            print("No fingerprint training data available")
            return False

        # Convert to numpy arrays
        X = np.array(self.known_fingerprint_encodings)
        y = np.array(self.known_fingerprint_nics)

        # Split data for training and testing
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Encode labels
        encoded_labels_train = self.label_encoder.fit_transform(y_train)
        encoded_labels_test = self.label_encoder.transform(y_test)

        # Train SVM classifier
        self.model = svm.SVC(kernel='rbf', probability=True, random_state=42)
        self.model.fit(X_train, encoded_labels_train)

        # Evaluate model
        train_accuracy = self.model.score(X_train, encoded_labels_train)
        test_accuracy = self.model.score(X_test, encoded_labels_test)

        print(f"Fingerprint recognition model trained successfully")
        print(f"Training Accuracy: {train_accuracy:.2f}")
        print(f"Testing Accuracy: {test_accuracy:.2f}")

        # Save model
        model_path = 'models/fingerprint_model.pkl'
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'label_encoder': self.label_encoder,
                'known_fingerprint_nics': self.known_fingerprint_nics
            }, f)

        print(f"Fingerprint model saved to {model_path}")
        return True