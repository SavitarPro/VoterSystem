import os
import cv2
import numpy as np
import pickle
from sklearn import svm
from sklearn.preprocessing import LabelEncoder


class FingerprintRecognizer:
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

    def load_model(self, model_path):
        """Load trained fingerprint model from file"""
        if not os.path.exists(model_path):
            print(f"Fingerprint model file '{model_path}' does not exist!")
            return False

        try:
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.label_encoder = data['label_encoder']
                self.known_fingerprint_nics = data['known_fingerprint_nics']

            print(f"Fingerprint model loaded from {model_path}")
            return True
        except Exception as e:
            print(f"Error loading fingerprint model: {e}")
            return False

    def predict_fingerprint(self, fingerprint_image):
        """Predict NIC from fingerprint image"""
        if self.model is None:
            print("Fingerprint model not trained or loaded")
            return None

        try:
            # Extract features from the fingerprint image
            features = self.extract_fingerprint_features(fingerprint_image)

            # Predict
            prediction = self.model.predict([features])

            # Convert back to NIC
            nic_prediction = self.label_encoder.inverse_transform(prediction)

            return nic_prediction[0]
        except Exception as e:
            print(f"Error predicting fingerprint: {e}")
            return None