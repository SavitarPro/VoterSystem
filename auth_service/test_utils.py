import numpy as np
from unittest.mock import MagicMock
from utils import FaceRecognizer

def test_extract_face_embeddings():

    mock_model = MagicMock()
    recognizer = FaceRecognizer('dummy_path')
    recognizer.model = mock_model
    recognizer.input_shape = (100, 100)

    dummy_image = np.random.randint(0, 255, (150, 150, 3), dtype=np.uint8)

    processed_image = recognizer.extract_face_embeddings(dummy_image)

    assert processed_image.shape == (1, 100, 100, 1)
    assert processed_image.max() <= 1.0
    assert processed_image.min() >= 0.0