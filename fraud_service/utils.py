import cv2
import numpy as np
import base64
import threading
import time
import psycopg2
from datetime import datetime


try:
    from config import fraud_config
    from models.person_detector import person_detector
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import fraud_config
    from models.person_detector import person_detector


class CameraManager:
    def __init__(self):
        self.cameras = {}
        self.is_running = False
        
        self.camera_priority = [0, 2, 1, 3, 4, 5]  

    def start_camera(self, voter_nic):
        
        if voter_nic in self.cameras:
            return True

        print(f"🔍 Looking for cameras for {voter_nic}...")

        
        for camera_index in self.camera_priority:
            if self.try_camera(voter_nic, camera_index):
                camera_type = "OBS virtual" if camera_index in [1, 2] else "Main" if camera_index == 0 else f"Fallback {camera_index}"
                print(f"Started {camera_type} camera {camera_index} for {voter_nic}")
                return True

        print(f"No cameras available for {voter_nic}")
        return False

    def try_camera(self, voter_nic, camera_index):
        
        try:
            print(f"  Trying camera index {camera_index}...")
            cap = cv2.VideoCapture(camera_index)

            if not cap.isOpened():
                print(f"Camera {camera_index} not opened")
                return False

            
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)

            
            ret, frame = cap.read()
            if not ret:
                print(f"    Could not read frame from camera {camera_index}")
                cap.release()
                return False

            print(f"    Camera {camera_index} works! Frame shape: {frame.shape}")
            self.cameras[voter_nic] = {
                'cap': cap,
                'last_frame': None,
                'last_detection': None,
                'start_time': time.time(),
                'camera_index': camera_index,
                'camera_type': self.get_camera_type(camera_index)
            }
            return True

        except Exception as e:
            print(f"    Error with camera {camera_index}: {e}")
            return False

    def get_camera_type(self, camera_index):
        
        if camera_index in [1, 2]:
            return "OBS Virtual Camera"
        elif camera_index == 0:
            return "Main Camera"
        else:
            return f"Camera {camera_index}"

    def stop_camera(self, voter_nic):
        
        if voter_nic in self.cameras:
            self.cameras[voter_nic]['cap'].release()
            del self.cameras[voter_nic]

    def get_frame(self, voter_nic):
        
        if voter_nic not in self.cameras:
            return None, 0

        try:
            cap = self.cameras[voter_nic]['cap']
            ret, frame = cap.read()

            if not ret:
                return None, 0

            
            person_count, processed_frame = self.detect_persons(frame)

            
            _, buffer = cv2.imencode('.jpg', processed_frame)
            image_with_boxes = base64.b64encode(buffer).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{image_with_boxes}"

            
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
        
        try:
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            
            person_count, processed_frame = person_detector.detect_frame(frame_rgb)

            return person_count, processed_frame

        except Exception as e:
            print(f"Error in detection: {e}")
            return 0, frame

    def start_monitoring(self):
        
        if self.is_running:
            return

        self.is_running = True
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()

    def _monitor_loop(self):
        
        while self.is_running:
            for voter_nic in list(self.cameras.keys()):
                self.get_frame(voter_nic)
            time.sleep(0.1)  

    def stop_all(self):
        
        self.is_running = False
        for voter_nic in list(self.cameras.keys()):
            self.stop_camera(voter_nic)

    def start_monitoring_voter(self, voter_nic):
        
        if not self.is_running:
            self.start_monitoring()

        if voter_nic not in self.cameras:
            self.start_camera(voter_nic)

    def stop_monitoring_voter(self, voter_nic):
        
        if voter_nic in self.cameras:
            self.stop_camera(voter_nic)

        
        if not self.cameras and self.is_running:
            self.stop_monitoring()



camera_manager = CameraManager()



class DatabaseManager:
    def __init__(self):
        self.connection_pool = self.create_connection_pool()

    def create_connection_pool(self):
        
        try:
            
            vote_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=fraud_config.DB_HOST,
                port=fraud_config.DB_PORT,
                user=fraud_config.DB_USER,
                password=fraud_config.DB_PASSWORD,
                database=fraud_config.VOTE_DB
            )

            return {'vote': vote_pool}

        except Exception as e:
            print(f"Database connection error: {e}")
            return None

    def get_voter_details(self, voter_nic):
        
        if not self.connection_pool:
            return None

        conn = self.connection_pool['vote'].getconn()
        try:
            with conn.cursor() as cursor:
                
                cursor.execute('''
                    SELECT nic, full_name, electoral_division, status
                    FROM voters 
                    WHERE nic = %s 
                    LIMIT 1
                ''', (voter_nic,))
                result = cursor.fetchone()

                if result:
                    return {
                        'nic': result[0],
                        'full_name': result[1],
                        'electoral_division': result[2],
                        'status': result[3]
                    }
                return None

        except Exception as e:
            print(f"Error getting voter details: {e}")
            return None
        finally:
            self.connection_pool['vote'].putconn(conn)

    def log_fraud_attempt(self, voter_nic, person_count, officer_action=None):
        
        if not self.connection_pool:
            return

        conn = self.connection_pool['vote'].getconn()
        try:
            with conn.cursor() as cursor:
                
                if officer_action:
                    
                    cursor.execute('''
                                   SELECT id
                                   FROM fraud_attempts
                                   WHERE voter_nic = %s
                                     AND officer_action IS NULL
                                   ORDER BY detected_at DESC LIMIT 1
                                   ''', (voter_nic,))

                    existing_record = cursor.fetchone()

                    if existing_record:
                        
                        cursor.execute('''
                                       UPDATE fraud_attempts
                                       SET officer_action = %s,
                                           resolved_at    = CURRENT_TIMESTAMP
                                       WHERE id = %s
                                       ''', (officer_action, existing_record[0]))
                    else:
                        
                        cursor.execute('''
                                       INSERT INTO fraud_attempts
                                           (voter_nic, person_count, officer_action, detected_at)
                                       VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                                       ''', (voter_nic, person_count, officer_action))
                else:
                    
                    
                    cursor.execute('''
                                   SELECT id
                                   FROM fraud_attempts
                                   WHERE voter_nic = %s
                                     AND officer_action IS NULL
                                   LIMIT 1
                                   ''', (voter_nic,))

                    if not cursor.fetchone():
                        
                        cursor.execute('''
                                       INSERT INTO fraud_attempts
                                           (voter_nic, person_count, detected_at)
                                       VALUES (%s, %s, CURRENT_TIMESTAMP)
                                       ''', (voter_nic, person_count))

                conn.commit()
                print(f"Fraud attempt logged for {voter_nic}: {officer_action or 'New detection'}")

        except Exception as e:
            print(f"Error logging fraud attempt: {e}")
            conn.rollback()
        finally:
            self.connection_pool['vote'].putconn(conn)

    def get_pending_fraud_cases(self):
        
        if not self.connection_pool:
            return []

        conn = self.connection_pool['vote'].getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                               SELECT fa.id,
                                      fa.voter_nic,
                                      fa.person_count,
                                      fa.detected_at,
                                      fa.officer_action,
                                      v.full_name,
                                      v.electoral_division
                               FROM fraud_attempts fa
                                        LEFT JOIN voters v ON fa.voter_nic = v.nic
                               WHERE fa.officer_action IS NULL
                               ORDER BY fa.detected_at DESC
                               ''')
                return cursor.fetchall()
        except Exception as e:
            print(f"Error getting fraud cases: {e}")
            return []
        finally:
            self.connection_pool['vote'].putconn(conn)



db_manager = DatabaseManager()