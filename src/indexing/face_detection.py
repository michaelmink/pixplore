

import os
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from pathlib import Path

from src.common_tools import load_config


class FaceDetectorSCRFD():
    """
    Face detection using SCRFD model from insightface
    """
    def __init__(self):
        from insightface.model_zoo import SCRFD

        # read config
        self.CONFIG = load_config('config.yaml')

        # Modell laden
        model_name = self.CONFIG['models']['face_detection']['model_name']
        self.detector = SCRFD(os.path.join('models', model_name))
        self.detector.prepare(ctx_id=0)  # 0 = GPU, -1 = CPU
        self.detector.input_size = (640, 640)  # default 640x640

    def detect_faces(self, img: Image.Image, img_path: Path, debug=True, th=0.5) -> list:
        """
        Detect faces in an image using SCRFD model
        """
        # Inferenz
        img = ImageOps.exif_transpose(img)  # korrigiert Orientierung
        bboxes, landmarks = self.detector.detect(np.asarray(img))
        print(f"Detected {len(bboxes)} faces")

        # -------------------------------
        # Face Crops für Embeddings
        # -------------------------------
        for i, bbox in enumerate(bboxes):
            x1, y1, x2, y2 = map(int, bbox[:4])  # nur Box-Koordinaten
            crop_pil = img.crop((x1, y1, x2, y2))
            crop_pil.save(os.path.join(self.CONFIG['dataset']['label_path'], f"{img_path.stem}_face_crop_{i:03d}.jpg"))

            
        # Debug: Bounding Boxes visualisieren
        if debug:
            draw = ImageDraw.Draw(img)
            for i, bbox in enumerate(bboxes):
                x1, y1, x2, y2 = map(int, bbox[:4])  # nur Box-Koordinaten
                score = bbox[4]
                lm = landmarks[i]  # Landmarks für dieses Face
                # boxes
                draw.rectangle([x1, y1, x2, y2], outline="red", width=20)
                # scores
                draw.text((x1, max(0, y1-10)), f"{score:.2f}", fill="cyan")
                # landmarks
                for (x, y) in lm.astype(int):
                    draw.ellipse([x-2, y-2, x+2, y+2], fill="green")

                print(f"Face {i}: Score: {score:.2f}")

            # save
            img.save(os.path.join(self.CONFIG['dataset']['debug_path'], f"{img_path.stem}_debug.jpg"))


class FaceDetectorYolo():
    """
    Face detection using YOLO model
    """
    # TODO: NOT TESTED YET
    # NOTE: not performant for face detection compared to SCRFD!

    def __init__(self):
        from ultralytics import YOLO

        # read config
        CONFIG = load_config('config.yaml')

        # load model
        self.face_detection_model = YOLO("yolov8s.pt")


    def detect_faces(self, img, debug=True) -> list:
        """
        Detect faces in an image using YOLO model
        """
        # inference
        results = self.face_detection_model.predict(source=img, conf=0.5)
        # Zeichenobjekt
        draw = ImageDraw.Draw(img)
        # process results
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy
                print(f"Detected class {cls} with confidence {conf}")

                # for debugging: plot box in raw image
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
                draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                draw.text((x1, y1 - 10), f"{conf:.2f}", fill="red")

        # save
        # remove file extention
        img_name = img_path.split('.')[0]
        img.save(f"{img_name}_marked.jpg")







