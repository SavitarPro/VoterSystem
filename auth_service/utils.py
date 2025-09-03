import cv2
import numpy as np
import pickle
from datetime import datetime
import psycopg2
from psycopg2 import pool
from config import config


class FaceRecognizer:
    def __init__(self, model_path):
        self.model = None
        self.label_encoder = None
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.load_model(model_path)

    def load_model(self, model_path):
        """Load the trained model from file"""
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            self.model = model_data['model']
            self.label_encoder = model_data['label_encoder']
            print("Model loaded successfully!")
        except Exception as e:
            print(f"Error loading model: {e}")

    def extract_face_embeddings(self, face_image):
        """Extract embeddings from face image"""
        face_resized = cv2.resize(face_image, (100, 100))

        if len(face_resized.shape) == 3:
            face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            face_gray = face_resized

        face_eq = cv2.equalizeHist(face_gray)
        embedding = face_eq.flatten().astype(np.float32) / 255.0
        return embedding

    def detect_faces(self, image):
        """Detect faces using Haar cascade"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        return faces

    def recognize_face(self, frame):
        """Recognize face in frame"""
        if self.model is None:
            return None, 0.0

        faces = self.detect_faces(frame)
        if len(faces) == 0:
            return None, 0.0

        x, y, w, h = faces[0]
        face_roi = frame[y:y + h, x:x + w]

        try:
            embedding = self.extract_face_embeddings(face_roi)
            embedding = embedding.reshape(1, -1)

            prediction = self.model.predict(embedding)
            confidence = np.max(self.model.predict_proba(embedding))

            if confidence < 0.6:
                return None, confidence

            predicted_nic = self.label_encoder.inverse_transform(prediction)[0]
            return predicted_nic, confidence

        except Exception as e:
            print(f"Recognition error: {e}")
            return None, 0.0


class DatabaseManager:
    def __init__(self):
        self.registration_pool = config.registration_pool
        self.auth_pool = config.auth_pool
        self.init_databases()

    def init_databases(self):
        """Initialize database tables if they don't exist"""
        self.init_registration_db()
        self.init_auth_db()

    def init_registration_db(self):
        """Initialize registration database tables"""
        conn = self.registration_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Voters table for registration database
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS voters
                               (
                                   id
                                   SERIAL
                                   PRIMARY
                                   KEY,
                                   unique_id
                                   VARCHAR
                               (
                                   50
                               ) UNIQUE NOT NULL,
                                   nic VARCHAR
                               (
                                   20
                               ) NOT NULL,
                                   full_name VARCHAR
                               (
                                   100
                               ) NOT NULL,
                                   
                                   address TEXT NOT NULL,
                                   electoral_division VARCHAR
                               (
                                   100
                               ) NOT NULL,
                                   face_image_path VARCHAR
                               (
                                    255
                               ) NOT NULL,
                                   fingerprint_path VARCHAR
                               (
                                   255
                               ) NOT NULL,
                                   registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                  )
                               ''')
                conn.commit()
                print("Registration database initialized successfully")
        except Exception as e:
            print(f"Error initializing registration DB: {e}")
        finally:
            self.registration_pool.putconn(conn)

    def init_auth_db(self):
        """Initialize authentication database tables"""
        conn = self.auth_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Authentications table for auth database
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS authentications
                               (
                                   id
                                   SERIAL
                                   PRIMARY
                                   KEY,
                                   unique_id
                                   VARCHAR
                               (
                                   50
                               ) NOT NULL,
                                   nic VARCHAR
                               (
                                   20
                               ) NOT NULL,
                                   full_name VARCHAR
                               (
                                   100
                               ) NOT NULL,
                                   officer_id VARCHAR
                               (
                                   255
                               ) NOT NULL,
                                   confidence REAL NOT NULL,
                                   status VARCHAR(20) NOT NULL,
                                   auth_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                   )
                               ''')
                conn.commit()
                print("Authentication database initialized successfully")
        except Exception as e:
            print(f"Error initializing auth DB: {e}")
        finally:
            self.auth_pool.putconn(conn)

    def get_voter_info(self, nic):
        """Get voter information from registration DB"""
        conn = self.registration_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Simple query without status check since there's no status column
                query = '''
                        SELECT unique_id, \
                               nic, \
                               full_name, \
                               address, \
                               electoral_division, \
                               face_image_path, \
                               fingerprint_path
                        FROM voters
                        WHERE nic = %s \
                        '''

                cursor.execute(query, (nic,))
                result = cursor.fetchone()

                if result:
                    return {
                        'unique_id': result[0],
                        'nic': result[1],
                        'full_name': result[2],
                        'address': result[3],
                        'electoral_division': result[4],
                        'face_image_path': result[5],
                        'fingerprint_path': result[6]
                    }
                else:
                    print(f"No voter found with NIC: {nic}")
        except Exception as e:
            print(f"Error getting voter info: {e}")
        finally:
            self.registration_pool.putconn(conn)
        return None

    def log_authentication(self, unique_id, nic, full_name, officer_id, confidence, status):
        """Log authentication attempt"""
        conn = self.auth_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                               INSERT INTO authentications
                                   (unique_id, nic, full_name, officer_id, confidence, status, auth_time)
                               VALUES (%s, %s, %s, %s, %s, %s, %s)
                               ''', (unique_id, nic, full_name, officer_id, confidence, status, datetime.now()))
                conn.commit()
                print(f"Authentication logged for {nic}")
        except Exception as e:
            print(f"Error logging authentication: {e}")
            print(
                f"Parameters: unique_id={unique_id}, nic={nic}, full_name={full_name}, officer_id={officer_id}, confidence={confidence}, status={status}")
        finally:
            self.auth_pool.putconn(conn)

    def get_auth_stats(self):
        """Get authentication statistics"""
        conn = self.auth_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Today's authentications
                cursor.execute('''
                               SELECT COUNT(*)
                               FROM authentications
                               WHERE DATE (auth_time) = CURRENT_DATE
                               ''')
                today_count = cursor.fetchone()[0]

                # Total authentications
                cursor.execute('SELECT COUNT(*) FROM authentications')
                total_count = cursor.fetchone()[0]

                return {'today': today_count, 'total': total_count}
        except Exception as e:
            print(f"Error getting auth stats: {e}")
            return {'today': 0, 'total': 0}
        finally:
            self.auth_pool.putconn(conn)