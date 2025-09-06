import cv2
import numpy as np
import sys
import os


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.person_detector import PersonDetector


def test_detection():
    print("Testing person detection...")

    
    test_image = np.zeros((300, 300, 3), dtype=np.uint8)

    
    cv2.rectangle(test_image, (100, 50), (200, 250), (255, 255, 255), -1)  
    cv2.circle(test_image, (150, 30), 20, (255, 255, 255), -1)  

    
    detector = PersonDetector()
    person_count, processed_frame = detector.detect_frame(test_image)

    print(f"Detected {person_count} persons")

    
    cv2.imshow('Test Image', test_image)
    cv2.imshow('Processed Frame', processed_frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def test_with_real_image():
    
    print("Testing with real camera image...")

    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Cannot read frame from camera")
        return

    
    detector = PersonDetector()
    person_count, processed_frame = detector.detect_frame(frame)

    print(f"Detected {person_count} persons in real image")

    
    cv2.imshow('Real Image', frame)
    cv2.imshow('Processed Frame', processed_frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_detection()
    test_with_real_image()