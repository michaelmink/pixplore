# app.py
import streamlit as st
from PIL import Image
import os
import math
import yaml
import chromadb

# -------------------------------
# Konfiguration
# -------------------------------
# load config
with open('config.yaml', "r") as f:
    CONFIG = yaml.safe_load(f)

RAW_DIR = CONFIG['pcloud']['local_path']       # Originalbilder
THUMBNAIL_DIR = CONFIG['thumbnails']['thumbnail_dir']  # Thumbnails
THUMBNAIL_SIZE = tuple(CONFIG['thumbnails']['thumbnail_size'])
MAX_IMAGE_WIDTH = CONFIG['thumbnails']['max_image_width']

# chromadb client (read-only, PersistentClient reicht)
CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/images/vectordb")
client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_collection("image_tags")
results = collection.get(include=["metadatas", "documents"])

# Build lookup: filename -> metadata
image_metadata = {}
for doc_id, meta in zip(results["ids"], results["metadatas"]):
    image_metadata[doc_id] = meta

# Beispiel: Labels / Scores (kann aus DB kommen)
labels_scores = {
    "face_001.jpg": ("Person A", 0.97),
    "face_002.jpg": ("Person B", 0.88),
}

st.set_page_config(
    page_title="Pixplore",
    layout="wide"
)
st.title("Pixplore - AI Image Explorer")

# -------------------------------
# LLM Filter Input
# -------------------------------
#llm_input = st.text_input("Search images (e.g., 'Person A outdoors smiling')")
llm_input = st.sidebar.text_input("Search images (e.g., 'Person A outdoors smiling')")

# -------------------------------
# Harte Filter Dropdowns
# -------------------------------
# Jahre und Modelle aus ChromaDB-Metadaten extrahieren
years = sorted(set(
    meta.get("date_taken", "")[:4]
    for meta in image_metadata.values()
    if meta.get("date_taken")
))
months = sorted(set(
    meta.get("date_taken", "")[:7].replace(":", "-")
    for meta in image_metadata.values()
    if meta.get("date_taken")
))
models = sorted(set(
    meta.get("model", "")
    for meta in image_metadata.values()
    if meta.get("model")
))

selected_year = st.sidebar.selectbox("Jahr", options=["Alle"] + years)
selected_month = st.sidebar.selectbox("Monat", options=["Alle"] + months)
selected_model = st.sidebar.selectbox("Kamera", options=["Alle"] + models)

# -------------------------------
# Alle Bilder laden
# -------------------------------
all_image_files = [f for f in os.listdir(RAW_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

# Filter anwenden
image_files = []
for f in all_image_files:
    meta = image_metadata.get(f, {})
    date_taken = meta.get("date_taken", "")
    model = meta.get("model", "")

    if selected_year != "Alle" and not date_taken.startswith(selected_year):
        continue
    if selected_month != "Alle" and not date_taken[:7].replace(":", "-").startswith(selected_month):
        continue
    if selected_model != "Alle" and model != selected_model:
        continue
    image_files.append(f)

st.write(f"{len(image_files)} von {len(all_image_files)} Bildern (gefiltert)")

# -------------------------------
# Dynamische Spaltenzahl
# -------------------------------
max_width_per_image = 150
page_width = st.slider("Page width in px (approx)", min_value=600, max_value=1500, value=900)
num_cols = max(1, page_width // max_width_per_image)
st.write(f"Using {num_cols} columns")

# -------------------------------
# Galerie mit Klick auf Thumbnail
# -------------------------------
cols = st.columns(num_cols)

for idx, filename in enumerate(image_files):
    path = os.path.join(RAW_DIR, filename)
    thumb_img = Image.open(path)
    thumb_img.thumbnail(THUMBNAIL_SIZE)

    col = cols[idx % num_cols]

    # Thumbnail als klickbarer Button
    if col.button("", key=f"thumb_{idx}", help=f"Show full image: {filename}"):
        # Vergrößertes Bild anzeigen
        full_img = Image.open(path)
        st.image(full_img, caption=filename, width=MAX_IMAGE_WIDTH)

    # Thumbnail anzeigen
    col.image(thumb_img, width=max_width_per_image, caption=filename)

    # Neue Reihe, wenn Spalten voll
    if (idx + 1) % num_cols == 0:
        cols = st.columns(num_cols)
