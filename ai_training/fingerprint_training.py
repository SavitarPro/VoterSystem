import os
import cv2
import numpy as np
import pickle
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split


class FingerprintTraining:
    def __init__(self):
        self.known_fingerprint_encodings = []
        self.known_fingerprint_nics = []
        self.model = None
        self.label_encoder = LabelEncoder()
        self.cnn_model = None

    def build_cnn_model(self, input_shape, num_classes):

        model = models.Sequential([
            layers.Conv2D(32, (3, 3), activation='relu', input_shape=input_shape),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.Flatten(),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(num_classes, activation='softmax')
        ])

        model.compile(optimizer='adam',
                      loss='sparse_categorical_crossentropy',
                      metrics=['accuracy'])
        return model

    def extract_fingerprint_features_cnn(self, fingerprint_image):


        fingerprint_resized = cv2.resize(fingerprint_image, (100, 100))


        if len(fingerprint_resized.shape) == 3:
            fingerprint_gray = cv2.cvtColor(fingerprint_resized, cv2.COLOR_BGR2GRAY)
        else:
            fingerprint_gray = fingerprint_resized


        fingerprint_eq = cv2.equalizeHist(fingerprint_gray)


        fingerprint_normalized = fingerprint_eq / 255.0


        fingerprint_normalized = np.expand_dims(fingerprint_normalized, axis=-1)

        return fingerprint_normalized

    def load_training_data(self, training_dir):

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


                    image = cv2.imread(image_path)
                    if image is None:
                        print(f"Could not load fingerprint image: {image_path}")
                        continue

                    try:
                        fingerprint_features = self.extract_fingerprint_features_cnn(image)
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

        training_dir = 'data/fingerprints'

        if not self.load_training_data(training_dir):
            print("No fingerprint training data available")
            return False


        X = np.array(self.known_fingerprint_encodings)
        y = np.array(self.known_fingerprint_nics)

        unique_nics = sorted(set(self.known_face_nics))
        nic_to_label = {nic: idx for idx, nic in enumerate(unique_nics)}
        label_to_nic = {idx: nic for idx, nic in enumerate(unique_nics)}

        y_numeric = np.array([nic_to_label[nic] for nic in y])
        num_classes = len(unique_nics)


        X_train, X_test, y_train, y_test = train_test_split(
            X, y_numeric, test_size=0.2, random_state=42, stratify=y_numeric
        )


        input_shape = (100, 100, 1)
        self.cnn_model = self.build_cnn_model(input_shape, num_classes)


        history = self.cnn_model.fit(
            X_train, y_train,
            epochs=20,
            validation_data=(X_test, y_test),
            batch_size=32,
            verbose=1
        )


        train_loss, train_accuracy = self.cnn_model.evaluate(X_train, y_train, verbose=0)
        test_loss, test_accuracy = self.cnn_model.evaluate(X_test, y_test, verbose=0)

        print(f"Fingerprint recognition CNN model trained successfully")
        print(f"Training Accuracy: {train_accuracy:.2f}")
        print(f"Testing Accuracy: {test_accuracy:.2f}")


        model_path = 'models/fingerprint_model.h5'
        os.makedirs(os.path.dirname(model_path), exist_ok=True)


        self.cnn_model.save(model_path)


        metadata_path = 'models/fingerprint_metadata.pkl'
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                'label_to_nic': label_to_nic,
                'nic_to_label': nic_to_label,
                'unique_nics': unique_nics,
                'input_shape': input_shape,
                'num_classes': num_classes
            }, f)

        print(f"Model saved to {model_path}")
        print(f"Metadata saved to {metadata_path}")
        print(f"Trained on {num_classes} people: {unique_nics}")

        return True