from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prueba el webhook de n8n con un JSON real ya analizado por Python."
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5678/webhook/sentinel-analysis",
        help="URL del webhook de n8n.",
    )
    parser.add_argument(
        "--payload",
        required=True,
        help="Archivo JSON analizado a enviar.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload_path = Path(args.payload)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    response = requests.post(args.url, json=payload, timeout=10)
    print(f"POST {args.url}")
    print(f"status={response.status_code}")
    print(response.text)
    response.raise_for_status()


if __name__ == "__main__":
    main()
