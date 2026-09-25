from pyiceberg.catalog.sql import SqlCatalog
import pyarrow as pa
import os
import hashlib
import json
from datetime import datetime, timezone
import gcsfs

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - \033[1;34m[StorageManager]\033[0m %(message)s",
)


# Iceberg-Katalog: SQLite-Zeiger lokal, Daten/Metadaten auf GCS
WATCH_DIR = os.getenv("WATCH_DIR", "/tmp/images")
ICEBERG_CATALOG_URI = os.getenv(
    "ICEBERG_CATALOG_URI",
    f"sqlite:///{os.path.join(WATCH_DIR, 'iceberg_catalog.db')}",
)
ICEBERG_WAREHOUSE = os.getenv("ICEBERG_WAREHOUSE", "gs://pixplore-bucket/warehouse")
GCS_PROJECT = os.getenv("GCS_PROJECT", "pixplore-503406")
THUMBNAIL_GCS_PREFIX = os.getenv(
    "THUMBNAIL_GCS_PREFIX", "gs://pixplore-bucket/thumbnails"
)
ICEBERG_NAMESPACE = "catalog"
ICEBERG_TABLE = f"{ICEBERG_NAMESPACE}.images"

# Schema der Katalog-Tabelle
CATALOG_SCHEMA = pa.schema(
    [
        ("image_id", pa.string()),
        ("content_hash", pa.string()),
        ("filepath_orig", pa.string()),
        ("metadata", pa.string()),
        ("embedding", pa.list_(pa.float32())),
        ("thumbnail_uri", pa.string()),
        ("processed_at", pa.timestamp("us", tz="UTC")),
    ]
)


class StorageManager:
    def __init__(self):
        self._catalog = None
        self.init_catalog()

    def get_catalog(self):
        if self._catalog is None:
            self._catalog = SqlCatalog(
                "pixplore",
                **{
                    "uri": ICEBERG_CATALOG_URI,
                    "warehouse": ICEBERG_WAREHOUSE,
                },
            )
        return self._catalog

    def init_catalog(self):
        self._catalog = self.get_catalog()
        self._catalog.create_namespace_if_not_exists(ICEBERG_NAMESPACE)
        self._catalog.create_table_if_not_exists(ICEBERG_TABLE, schema=CATALOG_SCHEMA)

    def check_consistency(self):
        """Check the consistency between the local thumbnails and the Iceberg catalog."""
        table = self.get_catalog().load_table(ICEBERG_TABLE)
        arrow = table.scan(selected_fields=("image_id", "thumbnail_uri")).to_arrow()

        # go through and check if thumbnail exists
        inconsistencies = []
        for row in arrow.to_pylist():
            if not row["thumbnail_uri"]:
                inconsistencies.append(row["image_id"])
                continue

            if not row["image_id"]:
                inconsistencies.append(row["image_id"])
                continue

            thumbnail_uri = row["thumbnail_uri"]
            if not gcsfs.GCSFileSystem().exists(thumbnail_uri):
                inconsistencies.append(row["image_id"])
                continue

        if inconsistencies:
            logger.warning("⚠️ Inconsistencies found for image_ids: %s", inconsistencies)
        else:
            logger.info("✅ All catalog entries are consistent with GCS thumbnails.")

    def get_catalog_image_ids(self):
        """Return the set of all image_ids already present in the Iceberg catalog."""
        table = self.get_catalog().load_table(ICEBERG_TABLE)
        arrow = table.scan(selected_fields=("image_id",)).to_arrow()
        return set(arrow.column("image_id").to_pylist())

    def get_catalog_all_rows(self):
        fields = ["image_id", "metadata", "embedding", "thumbnail_uri"]
        table = self.get_catalog().load_table(ICEBERG_TABLE)
        arrow = table.scan(selected_fields=tuple(fields)).to_arrow()
        rows = arrow.to_pylist()
        return rows

    def write_catalog_batch(self, results):
        """Upload thumbnails to GCS, then upsert catalog rows (upload-before-commit)."""
        # ohne project=, sonst weicht gcsfs bei User-ADC auf den VM-Metadata-SA aus
        fs = gcsfs.GCSFileSystem()
        prefix = THUMBNAIL_GCS_PREFIX.rstrip("/")
        rows = []
        for result in results:
            image_path_local = result["image_path_local"]
            image_id = os.path.basename(image_path_local)

            with open(image_path_local, "rb") as image_file:
                content_hash = hashlib.sha256(image_file.read()).hexdigest()

            # Thumbnail VOR dem Upsert nach GCS -> eine Zeile referenziert nie eine fehlende Datei
            thumb_name = os.path.basename(result["thumbnail_path"])
            thumbnail_uri = f"{prefix}/{thumb_name}"
            fs.put(result["thumbnail_path"], thumbnail_uri)

            rows.append(
                {
                    "image_id": image_id,
                    "content_hash": content_hash,
                    "filepath_orig": result["image_path"],
                    "metadata": json.dumps(result["metadata"], sort_keys=True),
                    "embedding": result["embedding"],
                    "thumbnail_uri": thumbnail_uri,
                    "processed_at": datetime.now(timezone.utc),
                }
            )

        # Alle Thumbnails liegen jetzt auf GCS -> atomarer Upsert
        arrow_table = pa.Table.from_pylist(rows, schema=CATALOG_SCHEMA)
        table = self.get_catalog().load_table(ICEBERG_TABLE)
        # Dedup direkt beim Schreiben über content_hash
        table.upsert(arrow_table, join_cols=["content_hash"])
        logger.info("📚 %d Bild(er) in den Iceberg-Katalog upserted.", len(rows))
