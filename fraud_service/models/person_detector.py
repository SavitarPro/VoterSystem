import cv2
import numpy as np
import time
import sys


class PersonDetector:
    def __init__(self, model_type='yolo'):
        self.model_type = model_type
        self.model = self.load_model()
        print(f"✅ Person detector initialized with {self.model_type} model")

        
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if self.face_cascade.empty():
                print("❌ Failed to load face cascade")
                self.face_cascade = None
            else:
                print("✅ Face detection model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading face detection model: {e}")
            self.face_cascade = None

    def load_model(self):
        
        try:
            if self.model_type == 'yolo':
                print("Loading YOLOv5 model...")
                try:
                    
                    from ultralytics import YOLO
                    model = YOLO('yolov8n.pt')  
                    print("✅ YOLOv8 model loaded successfully")
                    return model
                except ImportError:
                    print("❌ ultralytics not available, trying torchhub YOLOv5...")
                    try:
                        import torch
                        
                        model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
                        model.conf = 0.5  
                        model.classes = [0]  
                        print("✅ YOLOv5 model loaded successfully from torchhub")
                        return model
                    except Exception as e:
                        print(f"❌ Failed to load YOLO: {e}")
                        raise Exception("YOLO loading failed")

            
            print("Loading OpenCV Haar Cascade model...")
            cascade_path = cv2.data.haarcascades + 'haarcascade_fullbody.xml'
            cascade = cv2.CascadeClassifier(cascade_path)
            if cascade.empty():
                raise Exception("Could not load Haar cascade")
            print("✅ Haar Cascade model loaded successfully")
            return cascade

        except Exception as e:
            print(f"Error loading model: {e}")
            
            print("Using HOG person detector as fallback")
            self.model_type = 'hog'
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            return hog

    def detect_persons_yolo(self, frame):
        
        try:
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            
            if hasattr(self.model, 'predict'):  
                results = self.model(frame_rgb)
                boxes = results[0].boxes
                persons = boxes[boxes.cls == 0] if boxes is not None else []

                
                processed_frame = frame.copy()
                for box in persons:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    conf = box.conf[0].item()

                    cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(processed_frame, f'Person: {conf:.2f}', (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                person_count = len(persons)

            else:  
                results = self.model(frame_rgb)
                detections = results.pandas().xyxy[0]
                persons = detections[detections['class'] == 0]  

                
                processed_frame = np.array(results.render()[0])

                
                processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_RGB2BGR)
                person_count = len(persons)

            
            if self.face_cascade is not None and person_count > 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                for person in persons:
                    if hasattr(self.model, 'predict'):  
                        x1, y1, x2, y2 = map(int, person.xyxy[0].tolist())
                    else:  
                        x1, y1, x2, y2 = int(person['xmin']), int(person['ymin']), int(person['xmax']), int(
                            person['ymax'])

                    
                    person_region = gray[max(0, y1):min(y2, gray.shape[0]), max(0, x1):min(x2, gray.shape[1])]

                    if person_region.size > 0:  
                        
                        faces = self.face_cascade.detectMultiScale(
                            person_region,
                            scaleFactor=1.1,
                            minNeighbors=5,
                            minSize=(30, 30)
                        )

                        
                        for (fx, fy, fw, fh) in faces:
                            face_x = x1 + fx
                            face_y = y1 + fy
                            cv2.rectangle(processed_frame, (face_x, face_y), (face_x + fw, face_y + fh), (255, 0, 0), 2)
                            cv2.putText(processed_frame, 'Face', (face_x, face_y - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            return person_count, processed_frame

        except Exception as e:
            print(f"Error in YOLO detection: {e}")
            return 0, frame

    def detect_persons_opencv(self, frame):
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            persons = self.model.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            
            processed_frame = frame.copy()
            for (x, y, w, h) in persons:
                cv2.rectangle(processed_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(processed_frame, 'Person', (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                
                if self.face_cascade is not None:
                    
                    person_region = gray[max(0, y):min(y + h, gray.shape[0]), max(0, x):min(x + w, gray.shape[1])]

                    if person_region.size > 0:  
                        faces = self.face_cascade.detectMultiScale(
                            person_region,
                            scaleFactor=1.1,
                            minNeighbors=5,
                            minSize=(30, 30)
                        )

                        
                        for (fx, fy, fw, fh) in faces:
                            face_x = x + fx
                            face_y = y + fy
                            cv2.rectangle(processed_frame, (face_x, face_y), (face_x + fw, face_y + fh), (255, 0, 0), 2)
                            cv2.putText(processed_frame, 'Face', (face_x, face_y - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            return len(persons), processed_frame

        except Exception as e:
            print(f"Error in OpenCV detection: {e}")
            return 0, frame

    def detect_persons_hog(self, frame):
        
        try:
            
            resized = cv2.resize(frame, (640, 480))

            
            boxes, weights = self.model.detectMultiScale(resized, winStride=(8, 8), padding=(4, 4), scale=1.05)

            
            processed_frame = frame.copy()
            for (x, y, w, h) in boxes:
                cv2.rectangle(processed_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(processed_frame, 'Person', (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            return len(boxes), processed_frame

        except Exception as e:
            print(f"Error in HOG detection: {e}")
            return 0, frame

    def detect_frame(self, frame):
        
        try:
            if self.model_type == 'yolo':
                return self.detect_persons_yolo(frame)
            elif self.model_type == 'hog':
                return self.detect_persons_hog(frame)
            else:  
                return self.detect_persons_opencv(frame)

        except Exception as e:
            print(f"Error in detection: {e}")
            return 0, frame



person_detector = PersonDetector()