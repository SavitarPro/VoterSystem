import cv2
import numpy as np
import base64
import threading
import time
import psycopg2
from datetime import datetime

# Import config directly
try:
    from config import fraud_config
    from models.person_detector import person_detector
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import fraud_config
    from models.person_detector import person_detector


class FraudDetector:
    def __init__(self, model_path):
        self.model = self.load_model(model_path)

    def load_model(self, model_path):
        """Load the person detection model"""
        try:
            # Use OpenCV Haar Cascade for person detection
            cascade_path = cv2.data.haarcascades + 'haarcascade_fullbody.xml'
            return cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            print(f"Error loading model: {e}")
            return None

    def detect_persons_with_boxes(self, image_data):
        """Detect persons and return image with bounding boxes"""
        try:
            # Convert base64 to image
            nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return 0, None

            # Convert to grayscale for detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Detect persons with bounding boxes
            persons = self.model.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            # Draw bounding boxes on the image
            for (x, y, w, h) in persons:
                cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(image, 'Person', (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Convert image back to base64 for web display
            _, buffer = cv2.imencode('.jpg', image)
            image_with_boxes = base64.b64encode(buffer).decode('utf-8')

            return len(persons), f"data:image/jpeg;base64,{image_with_boxes}"

        except Exception as e:
            print(f"Error in person detection: {e}")
            return 0, None

    def detect_persons(self, image_data):
        """Detect number of persons in the image (without boxes)"""
        try:
            nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return 0

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            persons = self.model.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            return len(persons)

        except Exception as e:
            print(f"Error in person detection: {e}")
            return 0

    def create_connection_pool(self):
        """Create database connection pool"""
        try:
            return psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=fraud_config.DB_HOST,
                port=fraud_config.DB_PORT,
                user=fraud_config.DB_USER,
                password=fraud_config.DB_PASSWORD,
                database=fraud_config.VOTE_DB
            )
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

    def log_fraud_attempt(self, voter_nic, person_count, image_data, officer_action=None):
        """Log fraud detection attempt"""
        if not self.connection_pool:
            return

        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                               INSERT INTO fraud_attempts
                                   (voter_nic, person_count, image_data, officer_action, detected_at)
                               VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                               ''', (voter_nic, person_count, image_data, officer_action))
                conn.commit()
        except Exception as e:
            print(f"Error logging fraud attempt: {e}")
        finally:
            self.connection_pool.putconn(conn)

    def get_pending_fraud_cases(self):
        """Get pending fraud cases"""
        if not self.connection_pool:
            return []

        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                               SELECT fa.id,
                                      fa.voter_nic,
                                      fa.person_count,
                                      fa.detected_at,
                                      vs.start_time,
                                      vs.status
                               FROM fraud_attempts fa
                                        LEFT JOIN vote_sessions vs ON fa.voter_nic = vs.voter_nic
                               WHERE fa.officer_action IS NULL
                               ORDER BY fa.detected_at DESC
                               ''')
                return cursor.fetchall()
        except Exception as e:
            print(f"Error getting fraud cases: {e}")
            return []
        finally:
            self.connection_pool.putconn(conn)


class CameraManager:
    def __init__(self):
        self.cameras = {}
        self.is_running = False

    def start_camera(self, voter_nic):
        """Start camera - prioritize OBS virtual camera"""
        if voter_nic in self.cameras:
            return True

        # Priority order: OBS virtual camera first, then others
        camera_priority = [0, 2, 3, 1, 4, 5]  # OBS usually on 1 or 2

        for camera_index in camera_priority:
            try:
                cap = cv2.VideoCapture(camera_index)
                if cap.isOpened():
                    # Test if we can read a frame
                    ret, frame = cap.read()
                    if ret:
                        self.cameras[voter_nic] = {
                            'cap': cap,
                            'last_frame': None,
                            'last_detection': None,
                            'start_time': time.time(),
                            'camera_index': camera_index
                        }
                        print(f"✅ Started camera {camera_index} for {voter_nic}")
                        return True
                    cap.release()
                cap.release()
            except Exception as e:
                print(f"Error with camera {camera_index}: {e}")

        print(f"❌ No cameras available for {voter_nic}")
        return False

    def stop_camera(self, voter_nic):
        """Stop camera for a specific voter"""
        if voter_nic in self.cameras:
            self.cameras[voter_nic]['cap'].release()
            del self.cameras[voter_nic]

    def get_frame(self, voter_nic):
        """Get frame from camera with detection"""
        if voter_nic not in self.cameras:
            return None, 0

        try:
            cap = self.cameras[voter_nic]['cap']
            ret, frame = cap.read()

            if not ret:
                return None, 0

            # Detect persons
            person_count, processed_frame = self.detect_persons(frame)

            # Convert to base64 for web display
            _, buffer = cv2.imencode('.jpg', processed_frame)
            image_with_boxes = base64.b64encode(buffer).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{image_with_boxes}"

            # Update camera data
            self.cameras[voter_nic]['last_frame'] = image_url
            self.cameras[voter_nic]['last_detection'] = {
                'person_count': person_count,
                'timestamp': time.time()
            }

            return image_url, person_count

        except Exception as e:
            print(f"Error getting frame: {e}")
            return None, 0

    def detect_persons(self, frame):
        """Detect persons in frame using the person detector"""
        try:
            # Convert frame to RGB for YOLO
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Use the person detector
            person_count, processed_frame = person_detector.detect_frame(frame_rgb)

            return person_count, processed_frame

        except Exception as e:
            print(f"Error in detection: {e}")
            return 0, frame

    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.is_running:
            return

        self.is_running = True
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            for voter_nic in list(self.cameras.keys()):
                self.get_frame(voter_nic)
            time.sleep(0.1)  # 10 FPS

    def stop_all(self):
        """Stop all cameras"""
        self.is_running = False
        for voter_nic in list(self.cameras.keys()):
            self.stop_camera(voter_nic)


# Initialize camera manager
camera_manager = CameraManager()
camera_manager.start_monitoring()


class DatabaseManager:
    def __init__(self):
        self.connection_pool = self.create_connection_pool()

    def create_connection_pool(self):
        """Create database connection pools"""
        try:
            # Main vote database pool
            vote_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=fraud_config.DB_HOST,
                port=fraud_config.DB_PORT,
                user=fraud_config.DB_USER,
                password=fraud_config.DB_PASSWORD,
                database=fraud_config.VOTE_DB
            )

            # Voter auth database pool
            auth_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=fraud_config.DB_HOST,
                port=fraud_config.DB_PORT,
                user=fraud_config.DB_USER,
                password=fraud_config.DB_PASSWORD,
                database=fraud_config.VOTER_AUTH_DB
            )

            return {'vote': vote_pool, 'auth': auth_pool}

        except Exception as e:
            print(f"Database connection error: {e}")
            return None

    def get_voter_details(self, voter_nic):
        """Get voter details from auth database"""
        if not self.connection_pool:
            return None

        conn = self.connection_pool['auth'].getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT nic, full_name, electoral_division, status, auth_time
                    FROM authentications 
                    WHERE nic = %s 
                    ORDER BY auth_time DESC 
                    LIMIT 1
                ''', (voter_nic,))
                result = cursor.fetchone()

                if result:
                    return {
                        'nic': result[0],
                        'full_name': result[1],
                        'electoral_division': result[2],
                        'status': result[3],
                        'auth_time': result[4]
                    }
                return None

        except Exception as e:
            print(f"Error getting voter details: {e}")
            return None
        finally:
            self.connection_pool['auth'].putconn(conn)

    def log_fraud_attempt(self, voter_nic, person_count, image_data, officer_action=None):
        """Log fraud detection attempt"""
        if not self.connection_pool:
            return

        conn = self.connection_pool['vote'].getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO fraud_attempts 
                    (voter_nic, person_count, image_data, officer_action, detected_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ''', (voter_nic, person_count, image_data, officer_action))
                conn.commit()
        except Exception as e:
            print(f"Error logging fraud attempt: {e}")
        finally:
            self.connection_pool['vote'].putconn(conn)

    def get_pending_fraud_cases(self):
        """Get pending fraud cases with voter details"""
        if not self.connection_pool:
            return []

        conn = self.connection_pool['vote'].getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT fa.id, fa.voter_nic, fa.person_count, fa.detected_at,
                           fa.image_data, fa.officer_action
                    FROM fraud_attempts fa
                    WHERE fa.officer_action IS NULL
                    ORDER BY fa.detected_at DESC
                ''')
                return cursor.fetchall()
        except Exception as e:
            print(f"Error getting fraud cases: {e}")
            return []
        finally:
            self.connection_pool['vote'].putconn(conn)


# Initialize components
fraud_detector = FraudDetector(fraud_config.PERSON_DETECTION_MODEL)
db_manager = DatabaseManager()