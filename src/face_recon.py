import os
from PIL import Image, ImageEnhance, ImageDraw
from facenet_pytorch import MTCNN
from tqdm import tqdm
import torch
from torchvision.transforms import ToPILImage
import torchvision.transforms.functional as TF

# ---------------- CONFIG ----------------
RAW_DIR = "raw"         # z.B. raw/me, raw/other
OUT_DIR = "dataset"     # z.B. dataset/me, dataset/other
IMAGE_SIZE = 224 # 112
MARGIN = 100 # 20
# ----------------------------------------

# Gerät: CUDA, falls verfügbar
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🔧 Using device: {DEVICE}")

# Face Detector
mtcnn = MTCNN(
    image_size=IMAGE_SIZE,
    margin=MARGIN,
    keep_all=True,       # nur größtes Gesicht pro Bild
    device=DEVICE,
    post_process=True
)

# Ausgabeordner erstellen
os.makedirs(OUT_DIR, exist_ok=True)

# Alle Labels im Rohordner durchgehen
for label in os.listdir(RAW_DIR):
    print(f"processing {label}")
    label_in = os.path.join(RAW_DIR, label)
    label_out = os.path.join(OUT_DIR, label)

    if not os.path.isdir(label_in):
        continue

    os.makedirs(label_out, exist_ok=True)
    idx = 0

    print(f"🔍 Processing label: {label}")

    for img_name in tqdm(os.listdir(label_in)):
        print(f"processing {img_name}")
        img_path = os.path.join(label_in, img_name)

        # Bild öffnen
        try:
            img = Image.open(img_path).convert("RGB")
        except:
            print(f"⚠️ Cannot open {img_path}, skipping")
            continue

        # Gesicht erkennen & Crop
        faces, probs = mtcnn(img, return_prob=True)
        boxes, _ = mtcnn.detect(img)

        if faces is None:
            print("Keine Gesichter erkannt")
            continue
        
        # falls nur 1 Gesicht, faces ist Tensor [3,H,W], machen wir Liste
        if isinstance(faces, torch.Tensor) and faces.ndim == 3:
            faces = [faces]

        # Tensor to PIL
        to_pil = ToPILImage()

        # Zeichenobjekt
        draw = ImageDraw.Draw(img)

        # alle Gesichter speichern
        for face, prob, box in zip(faces, probs, boxes):
            #print(f"found face {idx} with prob {prob}.")

            # for debugging: plot box in raw image
            x1, y1, x2, y2 = map(int, box)
            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
            draw.text((x1, y1 - 10), f"{prob:.2f}", fill="red")

            # 1. Tensor Werte clampen
            face = torch.clamp(face, 0, 1)

            # 2. Tensor → PIL Image
            face_pil = TF.to_pil_image(face.cpu())

            # 3. Optional hochskalieren
            face_pil = face_pil.resize((224, 224), Image.BICUBIC)

            # 5. Optional: leichtes Brightness/Contrast
            enhancer = ImageEnhance.Brightness(face_pil)
            face_pil = enhancer.enhance(1.0)  # 1.0 = Original, >1 = heller, <1 = dunkler

            #face_pil = to_pil(face.cpu())
            out_name = f"{label}_{idx:04d}.jpg"
            face_pil.save(os.path.join(label_out, out_name))
            idx += 1

        # save
        img.save(f"{img_name}_marked.jpg")

    print(f"✅ {idx} faces saved for '{label}'")

# docker run -it --rm -v .:/app --gpus all face_recon /bin/bash

