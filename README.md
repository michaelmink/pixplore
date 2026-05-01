# pixplore
Pixplore - AI Image Explorer

Framework that contains the following basic functionalities:
* based on k3s or minikube
* sync images from cloud service provider (here: pcloud)
* training pipeline to finetune face recognition to family members
* pipeline to index images
* server to visualize / filter thumbnails
* integrate blip2/qwen3-vl emebddings to enable query based search
* local llm to leverage image search

## Pipelines/Services
* Sync Images
* Indexing Pipeline
* Frontend Server

## Internet Facing

Using [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) + [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/) for secure public access with authentication.

### Start Server

```bash
cd src/frontend
./venv/bin/streamlit run start_server.py --server.address 0.0.0.0 --server.port 8501
```

### Expose via Cloudflare Tunnel

```bash
cloudflared tunnel run pixplore
```

### Authentication

Cloudflare Access with email-based OTP. Only whitelisted emails can access the app.

### Setup Steps

1. Buy domain at Cloudflare Registrar
2. Install `cloudflared` on server
3. Create tunnel: `cloudflared tunnel create pixplore`
4. Configure tunnel to proxy to `http://localhost:8501`
5. Add DNS route: `cloudflared tunnel route dns pixplore <subdomain>`
6. Create Access policy: allow only whitelisted emails


## Tags

Table schema für Tags
-------------------------------
GPS Location: TEXT
City: TEXT
Country: TEXT
Year: INTEGER
Month: INTEGER
Day: INTEGER
Peron_janine: BOOLEAN
Person_micmink: BOOLEAN
Person_other: BOOLEAN
Count_faces: INTEGER
ref_image_path: TEXT
ref_thumbnail_path: TEXT