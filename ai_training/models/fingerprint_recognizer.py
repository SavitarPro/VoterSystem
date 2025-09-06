import os
import cv2
import numpy as np
import pickle
from sklearn.preprocessing import LabelEncoder


class FingerprintRecognizer:
    def __init__(self):
        self.known_fingerprint_encodings = []
        self.known_fingerprint_nics = []
        self.model = None
        self.label_encoder = LabelEncoder()

    def extract_fingerprint_features(self, fingerprint_image):
        fingerprint_resized = cv2.resize(fingerprint_image, (100, 100))

        if len(fingerprint_resized.shape) == 3:
            fingerprint_gray = cv2.cvtColor(fingerprint_resized, cv2.COLOR_BGR2GRAY)
        else:
            fingerprint_gray = fingerprint_resized

        fingerprint_eq = cv2.equalizeHist(fingerprint_gray)

        fingerprint_blur = cv2.GaussianBlur(fingerprint_eq, (5, 5), 0)

        fingerprint_thresh = cv2.adaptiveThreshold(
            fingerprint_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        orb = cv2.ORB_create(nfeatures=100)
        keypoints, descriptors = orb.detectAndCompute(fingerprint_thresh, None)

        if descriptors is not None:
            if len(descriptors) > 0:
                features = descriptors[0].flatten()
                if len(features) < 100:
                    features = np.pad(features, (0, 100 - len(features)), 'constant')
                return features[:100]
        else:
            return fingerprint_thresh.flatten()[:100]

        return fingerprint_thresh.flatten()[:100]

    def load_model(self, model_path):

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

        if self.model is None:
            print("Fingerprint model not trained or loaded")
            return None

        try:

            features = self.extract_fingerprint_features(fingerprint_image)


            prediction = self.model.predict([features])


            nic_prediction = self.label_encoder.inverse_transform(prediction)

            return nic_prediction[0]
        except Exception as e:
            print(f"Error predicting fingerprint: {e}")
            return None