import hashlib
import requests
import httpx

username = "mink.m@gmx.de"
password = "Joris2016+"

# 1. Digest holen
digest = httpx.get("https://eapi.pcloud.com/getdigest").json()["digest"]

# 2. passworddigest berechnen (genau wie PyCloud es macht)
username_sha1 = hashlib.sha1(username.lower().encode("utf-8")).hexdigest()
password_digest = hashlib.sha1(
    password.encode("utf-8") + username_sha1.encode("utf-8") + digest.encode("utf-8")
).hexdigest()

# 3. Erster Versuch - löst E-Mail-Verifizierung aus
resp = httpx.get("https://eapi.pcloud.com/userinfo", params={
    "getauth": 1,
    "logout": 1,
    "username": username,
    "digest": digest,
    "passworddigest": password_digest,
    "authexpire": 31536000,
    "device": "pcloud-java-sync"
}).json()

print(resp)
