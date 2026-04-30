# app.py
import streamlit as st
from PIL import Image
import os
import math

# -------------------------------
# Konfiguration
# -------------------------------
RAW_DIR = "images/debug"       # Originalbilder
THUMBNAIL_SIZE = (150, 150)  # Max Thumbnail Größe
MAX_IMAGE_WIDTH = 800        # Breite für vergrößertes Bild

# Beispiel: Labels / Scores (kann aus DB kommen)
labels_scores = {
    "face_001.jpg": ("Person A", 0.97),
    "face_002.jpg": ("Person B", 0.88),
    # Füge hier alle weiteren Bilder hinzu
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
# Beispiel: Jahre aus DB auslesen
#conn = sqlite3.connect(DB_PATH)
#c = conn.cursor()
#c.execute("SELECT DISTINCT strftime('%Y', created_at) FROM images")  # assuming created_at exists
#years = [y[0] for y in c.fetchall() if y[0] is not None]
years = ["2021", "2022", "2023"]  # Beispielhafte Jahre
years.sort()
#selected_year = st.selectbox("Year", options=["All"] + years)
selected_year = st.sidebar.selectbox("Year", options=["All"] + years)

# Labels Dropdown
#c.execute("SELECT DISTINCT label FROM images")
#labels = [l[0] for l in c.fetchall() if l[0] is not None]
labels = ["Person A", "Person B", "Person C"]  # Beispielhafte Labels
#selected_label = st.selectbox("Label", options=["All"] + labels)
selected_label = st.sidebar.selectbox("Label", options=["All"] + labels)

# -------------------------------
# Alle Bilder laden
# -------------------------------
image_files = [f for f in os.listdir(RAW_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
st.write(f"Found {len(image_files)} images in '{RAW_DIR}' folder.")

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
