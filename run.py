import json
import os
import sys

import requests
from dotenv import load_dotenv


def main() -> int:
    """Read payload.json, call /score, and print/save output."""
    load_dotenv()

    api_key = os.getenv("SCORING_API_KEY")
    host = os.getenv("API_HOST", "127.0.0.1")
    port = os.getenv("API_PORT", "8011")
    base_url = f"http://{host}:{port}"

    if not api_key:
        print("Error: SCORING_API_KEY not found in .env")
        return 1

    payload_path = "payload.json"
    if not os.path.exists(payload_path):
        print("Error: payload.json not found in current directory")
        return 1

    try:
        with open(payload_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:
        print(f"Error reading payload.json: {exc}")
        return 1

    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(f"{base_url}/score", json=payload, headers=headers, timeout=120)
    except Exception as exc:
        print(f"Error connecting to API: {exc}")
        return 1

    print(f"Status: {response.status_code}")

    try:
        result = response.json()
    except Exception:
        print(response.text)
        return 1

    print(json.dumps(result, indent=2))

    if response.status_code == 200:
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print("Saved response to output.json")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
