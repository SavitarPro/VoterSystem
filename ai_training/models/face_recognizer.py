import os
import cv2
import numpy as np
import pickle
from sklearn.preprocessing import LabelEncoder

class FaceRecognizer:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_nics = []
        self.model = None
        self.label_encoder = LabelEncoder()

        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def extract_face_embeddings(self, face_image):
        face_resized = cv2.resize(face_image, (100, 100))


        if len(face_resized.shape) == 3:
            face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            face_gray = face_resized

        face_eq = cv2.equalizeHist(face_gray)


        embedding = face_eq.flatten().astype(np.float32) / 255.0

        return embedding

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

    def load_model(self, model_path):

        if not os.path.exists(model_path):
            print(f"Model file '{model_path}' does not exist!")
            return False

        try:
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.label_encoder = data['label_encoder']
                self.known_face_nics = data['known_face_nics']

            print(f"Model loaded from {model_path}")
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def predict_face(self, face_image):

        if self.model is None:
            print("Face model not trained or loaded")
            return None

        try:

            features = self.extract_face_embeddings(face_image)


            prediction = self.model.predict([features])


            nic_prediction = self.label_encoder.inverse_transform(prediction)

            return nic_prediction[0]
        except Exception as e:
            print(f"Error predicting face: {e}")
            return None