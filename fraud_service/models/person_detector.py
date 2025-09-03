import cv2
import numpy as np
import torch
from PIL import Image


class PersonDetector:
    def __init__(self, model_type='yolo'):
        self.model_type = model_type
        self.model = self.load_model()

    def load_model(self):
        """Load person detection model"""
        try:
            if self.model_type == 'yolo':
                # Load YOLOv5 model (lightweight version)
                model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
                model.conf = 0.6  # Confidence threshold
                model.classes = [0]  # Only detect persons (class 0)
                return model
            else:
                # Fallback to OpenCV Haar Cascade
                cascade_path = cv2.data.haarcascades + 'haarcascade_fullbody.xml'
                return cv2.CascadeClassifier(cascade_path)

        except Exception as e:
            print(f"Error loading model: {e}")
            # Ultimate fallback - use OpenCV
            cascade_path = cv2.data.haarcascades + 'haarcascade_fullbody.xml'
            return cv2.CascadeClassifier(cascade_path)

    def detect_persons_yolo(self, frame):
        """Detect persons using YOLOv5"""
        results = self.model(frame)
        detections = results.pandas().xyxy[0]
        persons = detections[detections['class'] == 0]  # Filter for persons

        # Draw bounding boxes
        processed_frame = np.array(results.render()[0])
        return len(persons), processed_frame

    def detect_persons_opencv(self, frame):
        """Detect persons using OpenCV"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        persons = self.model.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        # Draw bounding boxes
        for (x, y, w, h) in persons:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, 'Person', (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        return len(persons), frame

    def detect_frame(self, frame):
        """Detect persons in a frame"""
        try:
            if hasattr(self.model, 'conf'):  # YOLO model
                return self.detect_persons_yolo(frame)
            else:  # OpenCV Haar Cascade
                return self.detect_persons_opencv(frame)

        except Exception as e:
            print(f"Error in detection: {e}")
            return 0, frame


# Global instance
person_detector = PersonDetector()