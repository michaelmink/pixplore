# pCloud Java API

Spring Boot API zum Synchronisieren von Bildern aus pCloud via WebDAV (Sardine).

## Endpoints

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/health` | Health-Check |
| GET | `/list_files?path=...&start_date=...&end_date=...` | Dateien in pCloud auflisten (optional nach Datum filtern) |
| GET | `/download_file?path=...` | Einzelne Datei aus pCloud herunterladen |

Swagger UI: [http://localhost:8080/swagger-ui.html](http://localhost:8080/swagger-ui.html)

## Umgebungsvariablen

| Variable | Beschreibung | Default |
|----------|--------------|---------|
| `PCLOUD_USERNAME` | pCloud Login-E-Mail | `default_username` |
| `PCLOUD_PASSWORD` | pCloud Passwort | `default_password` |
| `PCLOUD_DOWNLOAD_PATH` | Lokaler Speicherpfad für Downloads | `/tmp/images` |

## Lokal starten (ohne Docker)

```bash
./gradlew bootRun
```

## Docker

### Image bauen

```bash
docker build -t java-api .
```

### Container starten

```bash
docker run -p 8080:8080 \
  -e PCLOUD_USERNAME=deine@email.com \
  -e PCLOUD_PASSWORD=deinPasswort \
  -v /pfad/zu/lokalen/bildern:/tmp/images \
  java-api
```

### Testen

```bash
curl http://localhost:8080/health
curl "http://localhost:8080/list_files?path=/Automatic%20Upload/"
```

## Tech-Stack

- Java 17
- Spring Boot 3.4.2
- Sardine (WebDAV-Client)
- Gradle
