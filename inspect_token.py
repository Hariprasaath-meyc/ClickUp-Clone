import base64
import json

id_token = input("Paste your ID token: ").strip()

parts = id_token.split(".")

if len(parts) != 3:
    raise ValueError("This is not a valid JWT structure.")

payload = parts[1]
payload += "=" * (-len(payload) % 4)

claims = json.loads(
    base64.urlsafe_b64decode(payload)
)

for key in ("sub", "username", "email", "iss", "aud"):
    if key in claims:
        print(f"{key}: {claims[key]}")