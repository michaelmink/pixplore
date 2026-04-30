

import logging
import os
import glob
from typing import Any, Dict
import yaml
from tqdm import tqdm
from PIL import Image, ImageDraw
from pathlib import Path

from src.face_detection import FaceDetectorSCRFD

from src.common_tools import load_config

# Table schema für Tags
# -------------------------------
# GPS Location: TEXT
# City: TEXT
# Country: TEXT
# Year: INTEGER
# Month: INTEGER
# Day: INTEGER
# Peron_janine: BOOLEAN
# Person_micmink: BOOLEAN
# Person_other: BOOLEAN
# Count_faces: INTEGER
# ref_image_path: TEXT
# ref_thumbnail_path: TEXT

# read config
CONFIG = load_config('config.yaml')

# configuration for logger
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]  %(message)s",
    handlers=[
        logging.StreamHandler()
    ])





class ImageTagger():
    def __init__(self):
        logging.info("Starting ImageTagger...")

        # create output dirs
        os.makedirs(CONFIG['dataset']['label_path'], exist_ok=True)
        os.makedirs(CONFIG['dataset']['debug_path'], exist_ok=True)

        # init models
        self.face_detector = FaceDetectorSCRFD()

        # get image files
        image_files = self.get_files(CONFIG['dataset']['raw_path'])

        # run processing
        self.run(image_files)

    def get_files(self, raw_dir: str):
        """
        Get all image files from the raw directory
        """
        image_files = []
        for file in glob.glob(os.path.join(raw_dir, '**', '*'), recursive=True):
            if file.lower().endswith(tuple(CONFIG['image_formats'])):
                image_files.append(Path(file))

        logging.info(f"Found {len(image_files)} image files in {raw_dir}")
        for img_file in image_files[:5]:
            logging.info(f" - {img_file.resolve()}")

        return image_files

    def run(self, image_files):
        """
        Alle Labels im Rohordner durchgehen
        """
        for img_path in tqdm(image_files):
            print(f"processing {img_path}")

            # Bild öffnen
            try:
                img = Image.open(img_path).convert("RGB")
            except:
                print(f"⚠️ Cannot open {img_path}, skipping")
                continue

            # +++++++++++++++
            # FACE DETECTION
            # +++++++++++++++
            self.face_detector.detect_faces(img, img_path, debug=True)
            


if __name__ == "__main__":
    image_tagger = ImageTagger()
