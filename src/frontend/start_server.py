# app.py
import streamlit as st
from PIL import Image
import os
import math
import chromadb
import base64
import shutil
import requests

# -------------------------------
# Konfiguration
# -------------------------------

# Base path (GCS FUSE mount on Cloud Run, local dir otherwise)
BASE_PATH = os.getenv("BASE_PATH", "/tmp/images")
THUMBNAIL_PATH = os.path.join(BASE_PATH, "thumbnails")
TEXT2VEC_URL = os.getenv("TEXT2VEC_URL", "http://localhost:8081")

# SQLite doesn't work over GCS FUSE — copy vectordb to a local writable path if needed.
_chroma_src = os.path.join(BASE_PATH, "vectordb")
LOCAL_CHROMA_PATH = "/tmp/local_vectordb"
if os.access(_chroma_src, os.W_OK):
    CHROMA_PATH = _chroma_src
else:
    if not os.path.exists(LOCAL_CHROMA_PATH):
        shutil.copytree(_chroma_src, LOCAL_CHROMA_PATH)
    CHROMA_PATH = LOCAL_CHROMA_PATH


# chromadb client
@st.cache_resource(ttl=60)
def get_chromadb_data():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    print(f"Using ChromaDB PersistentClient: {CHROMA_PATH}")
    collection = client.get_collection("image_tags")
    results = collection.get(include=["metadatas", "documents"])
    print(f"Loaded {len(results['ids'])} images from ChromaDB collection 'image_tags'")
    metadata = {}
    for doc_id, meta in zip(results["ids"], results["metadatas"]):
        metadata[doc_id] = meta
    return metadata


image_metadata = get_chromadb_data()


@st.cache_resource(ttl=60)
def get_embedding_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection("image_embeddings")


def search_by_text(query: str, n_results: int = 50):
    """Get text embedding from text2vec service and query ChromaDB for similar images."""
    try:
        resp = requests.post(
            f"{TEXT2VEC_URL}/embed_text", json={"text": query}, timeout=30
        )
        resp.raise_for_status()
        text_embedding = resp.json()["embedding"]

        collection = get_embedding_collection()
        results = collection.query(
            query_embeddings=[text_embedding],
            n_results=n_results,
            include=["distances"],
        )
        return list(zip(results["ids"][0], results["distances"][0]))
    except Exception as e:
        st.error(f"Text-Suche fehlgeschlagen: {e}")
        return None


# Beispiel: Labels / Scores (kann aus DB kommen)
labels_scores = {
    "face_001.jpg": ("Person A", 0.97),
    "face_002.jpg": ("Person B", 0.88),
}

st.set_page_config(page_title="Pixplore", layout="wide")
st.title("Pixplore - AI Image Explorer")

if st.sidebar.button("🔄 Daten neu laden"):
    st.cache_resource.clear()
    st.rerun()

# -------------------------------
# Filter & Suche
# -------------------------------
# Jahre und Modelle aus ChromaDB-Metadaten extrahieren
years = sorted(
    set(
        meta.get("date_taken", "")[:4]
        for meta in image_metadata.values()
        if meta.get("date_taken")
    )
)
months = sorted(
    set(
        meta.get("date_taken", "")[:7].replace(":", "-")
        for meta in image_metadata.values()
        if meta.get("date_taken")
    )
)
models = sorted(
    set(meta.get("model", "") for meta in image_metadata.values() if meta.get("model"))
)

with st.sidebar.form(key="search_form"):
    llm_input = st.text_input("Search images (e.g., 'A sunset over mountains')")
    selected_year = st.selectbox("Jahr", options=["Alle"] + years)
    selected_month = st.selectbox("Monat", options=["Alle"] + months)
    selected_model = st.selectbox("Kamera", options=["Alle"] + models)
    search_submitted = st.form_submit_button("🔍 Suchen")

# Perform text similarity search if query is provided
search_results = None
if search_submitted and llm_input:
    search_results = search_by_text(llm_input)

# -------------------------------
# Alle Bilder laden
# -------------------------------
all_image_files = [
    f
    for f in os.listdir(THUMBNAIL_PATH)
    if f.lower().endswith((".png", ".jpg", ".jpeg"))
]

# Build set of matching filenames from text search (ranked by similarity)
search_ranked_names = None
if search_results:
    search_ranked_names = {name: dist for name, dist in search_results}


# Filter anwenden — Thumbnail-Name zu Original-Name mappen für Metadaten-Lookup
def thumb_to_original(thumb_name):
    return thumb_name.replace("_thumb", "")


image_files = []
for f in all_image_files:
    original_name = thumb_to_original(f)
    meta = image_metadata.get(original_name, {})
    date_taken = meta.get("date_taken", "")
    model = meta.get("model", "")

    # Text search filter: only show images that matched
    if search_ranked_names is not None and original_name not in search_ranked_names:
        continue

    if selected_year != "Alle" and not date_taken.startswith(selected_year):
        continue
    if selected_month != "Alle" and not date_taken[:7].replace(":", "-").startswith(
        selected_month
    ):
        continue
    if selected_model != "Alle" and model != selected_model:
        continue
    image_files.append(f)

# Sort by similarity score when text search is active
if search_ranked_names is not None:
    image_files.sort(
        key=lambda f: search_ranked_names.get(thumb_to_original(f), float("inf"))
    )

# -------------------------------
# Pagination
# -------------------------------
IMAGES_PER_PAGE = 30

if "page" not in st.session_state:
    st.session_state.page = 0

total_pages = max(1, math.ceil(len(image_files) / IMAGES_PER_PAGE))
st.session_state.page = min(st.session_state.page, total_pages - 1)

start_idx = st.session_state.page * IMAGES_PER_PAGE
end_idx = start_idx + IMAGES_PER_PAGE
page_files = image_files[start_idx:end_idx]

st.write(
    f"{len(image_files)} Bilder | Seite {st.session_state.page + 1} von {total_pages}"
)

# -------------------------------
# Dynamische Spaltenzahl
# -------------------------------
max_width_per_image = 150
num_cols = 6

# -------------------------------
# Vergrößertes Bild anzeigen (wenn ausgewählt)
# -------------------------------
if "selected_image" not in st.session_state:
    st.session_state.selected_image = None

if st.session_state.selected_image:
    filename = st.session_state.selected_image
    path = os.path.join(THUMBNAIL_PATH, filename)
    original_name = thumb_to_original(filename)
    meta = image_metadata.get(original_name, {})

    col_img, col_info = st.columns([3, 1])
    with col_img:
        st.image(Image.open(path), caption=original_name, use_container_width=True)
    with col_info:
        st.subheader("Metadaten")
        for key, value in meta.items():
            st.write(f"**{key}:** {value}")
    if st.button("← Zurück zur Galerie"):
        st.session_state.selected_image = None
        st.rerun()

# -------------------------------
# Galerie mit Klick auf Thumbnail
# -------------------------------
cols = st.columns(num_cols)

for idx, filename in enumerate(page_files):
    path = os.path.join(THUMBNAIL_PATH, filename)
    col = cols[idx % num_cols]

    with col:
        with open(path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""<a href="?selected={filename}" target="_self">
                <img src="data:image/jpeg;base64,{img_data}" style="width:100%; aspect-ratio:1; object-fit:cover; border-radius:4px; cursor:pointer; margin-bottom:8px;">
            </a>""",
            unsafe_allow_html=True,
        )

    if (idx + 1) % num_cols == 0:
        cols = st.columns(num_cols)

# Handle click via query param
params = st.query_params
if "selected" in params:
    st.session_state.selected_image = params["selected"]
    st.query_params.clear()
    st.rerun()

# -------------------------------
# Pagination Buttons
# -------------------------------
col_prev, col_info, col_next = st.columns([1, 2, 1])
with col_prev:
    if st.button("← Zurück", disabled=st.session_state.page == 0):
        st.session_state.page -= 1
        st.rerun()
with col_next:
    if st.button("Weiter →", disabled=st.session_state.page >= total_pages - 1):
        st.session_state.page += 1
        st.rerun()
