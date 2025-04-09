import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLO
from typing import List, Tuple

import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YoloProcessor:
    def __init__(self, model_path: str):
        """Khởi tạo với mô hình YOLO."""
        try:
            self.model = YOLO(model_path)
            logger.info(f"Loaded YOLO model from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    def detect_bounding_boxes(self, image: np.ndarray) -> np.ndarray:
        """Chạy YOLO để phát hiện và fill trắng các bounding box."""
        try:
            results = self.model.predict(image, verbose=True, conf=0.3, iou=0.99)[0]
            detections = sv.Detections.from_ultralytics(results)
            annotated_image = image.copy()

            for box in detections.xyxy:
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (255, 255, 255), thickness=-1)

            return annotated_image
        except Exception as e:
            logger.error(f"Error in detect_bounding_boxes: {e}")
            return image