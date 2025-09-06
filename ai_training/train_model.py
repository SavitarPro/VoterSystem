import os
import cv2
import numpy as np
import pickle
from sklearn import svm
from sklearn.preprocessing import LabelEncoder
import warnings

warnings.filterwarnings('ignore')


class FaceRecognizer:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
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

    def load_training_data(self, training_dir):
        
        self.known_face_encodings = []
        self.known_face_names = []

        if not os.path.exists(training_dir):
            print(f"Training directory '{training_dir}' does not exist!")
            return False

        for person_name in os.listdir(training_dir):
            person_dir = os.path.join(training_dir, person_name)
            if not os.path.isdir(person_dir):
                continue

            image_count = 0
            for image_name in os.listdir(person_dir):
                if image_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_path = os.path.join(person_dir, image_name)

                    
                    image = cv2.imread(image_path)
                    if image is None:
                        print(f"Could not load image: {image_path}")
                        continue

                    
                    faces = self.detect_faces(image)

                    if len(faces) > 0:
                        
                        x, y, w, h = faces[0]
                        face_roi = image[y:y + h, x:x + w]

                        try:
                            face_embedding = self.extract_face_embeddings(face_roi)
                            self.known_face_encodings.append(face_embedding)
                            self.known_face_names.append(person_name)
                            image_count += 1
                        except Exception as e:
                            print(f"Error processing {image_path}: {e}")
                            continue
                    else:
                        print(f"No face detected in {image_path}")

            if image_count > 0:
                print(f"Loaded {image_count} images for {person_name}")

        print(f"Total: {len(self.known_face_encodings)} face encodings for {len(set(self.known_face_names))} people")
        return len(self.known_face_encodings) > 0

    def train_model(self):
        
        if len(self.known_face_encodings) == 0:
            print("No training data available")
            return False

        
        X = np.array(self.known_face_encodings)
        y = np.array(self.known_face_names)

        
        encoded_labels = self.label_encoder.fit_transform(y)

        
        self.model = svm.SVC(kernel='linear', probability=True, random_state=42)
        self.model.fit(X, encoded_labels)

        print("Face recognition model trained successfully")
        return True

    def save_model(self, model_path):
        
        if self.model is None:
            print("No model to save")
            return False

        
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'label_encoder': self.label_encoder,
                'known_face_names': self.known_face_names
            }, f)

        print(f"Model saved to {model_path}")
        return True



def train_existing_model():
    face_recognizer = FaceRecognizer()
    training_dir = 'ai_training/data/faces'

    print("Loading training data...")
    if face_recognizer.load_training_data(training_dir):
        print("Training model...")
        if face_recognizer.train_model():
            face_recognizer.save_model('ai_training/models/face_model.pkl')
            print("Training completed successfully!")
            print("Model saved to: ai_training/models/face_model.pkl")
        else:
            print("Training failed!")
    else:
        print("No training data found!")


if __name__ == "__main__":
    train_existing_model()