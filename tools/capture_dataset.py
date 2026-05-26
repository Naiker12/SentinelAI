from __future__ import annotations

import argparse
import csv
import time
from datetime import datetime
from pathlib import Path

import cv2

from agente_percepcion.camera import Camera


SCENARIOS = {
    "normal",
    "objeto_sospechoso",
    "objeto_no_sospechoso",
    "pelea",
    "robo",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Captura imagenes para el dataset SentinelAI.")
    parser.add_argument("--camera", type=int, default=0, help="Indice de la camara.")
    parser.add_argument(
        "--backend",
        default="auto",
        help="Backend de OpenCV: auto, directshow, dshow, msmf o any.",
    )
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    parser.add_argument("--label", required=True, help="Clase esperada: person, knife, gun, etc.")
    parser.add_argument("--output", default="dataset/raw", help="Directorio base del dataset raw.")
    parser.add_argument("--interval", type=float, default=2.0, help="Segundos entre capturas automaticas.")
    return parser.parse_args()


def safe_name(value: str) -> str:
    allowed = []
    for char in value.strip().lower().replace(" ", "_"):
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
    return "".join(allowed) or "unknown"


def build_capture_path(base_dir: Path, scenario: str, label: str, timestamp: datetime) -> Path:
    filename = f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_{safe_name(label)}.jpg"
    return base_dir / safe_name(scenario) / safe_name(label) / filename


def append_metadata(metadata_path: Path, image_path: Path, scenario: str, label: str) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    exists = metadata_path.exists()
    with metadata_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not exists:
            writer.writerow(["image_path", "scenario", "label", "captured_at"])
        writer.writerow([str(image_path), scenario, label, datetime.now().isoformat()])


def save_frame(frame, base_dir: Path, scenario: str, label: str) -> Path:
    path = build_capture_path(base_dir, scenario, label, datetime.now())
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), frame)
    append_metadata(base_dir / "metadata.csv", path, scenario, label)
    return path


def draw_overlay(frame, scenario: str, label: str, auto_capture: bool) -> None:
    mode = "AUTO" if auto_capture else "MANUAL"
    lines = [
        f"Scenario: {scenario}",
        f"Label: {label}",
        f"Mode: {mode}",
        "S guardar | A auto | Q salir",
    ]
    y = 28
    for line in lines:
        cv2.putText(frame, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 220, 255), 2)
        y += 28


def main() -> None:
    args = parse_args()
    base_dir = Path(args.output)
    scenario = safe_name(args.scenario)
    label = safe_name(args.label)
    auto_capture = False
    last_capture_at = 0.0

    try:
        with Camera(args.camera, backend=args.backend) as camera:
            while True:
                frame = camera.read()

                preview = frame.copy()
                draw_overlay(preview, scenario, label, auto_capture)
                cv2.imshow("SentinelAI Dataset Capture", preview)

                now = time.monotonic()
                if auto_capture and now - last_capture_at >= args.interval:
                    path = save_frame(frame, base_dir, scenario, label)
                    print(f"Imagen guardada: {path}")
                    last_capture_at = now

                key = cv2.waitKey(1) & 0xFF
                if key == ord("s"):
                    path = save_frame(frame, base_dir, scenario, label)
                    print(f"Imagen guardada: {path}")
                elif key == ord("a"):
                    auto_capture = not auto_capture
                    last_capture_at = 0.0
                    print(f"Captura automatica: {'ON' if auto_capture else 'OFF'}")
                elif key == ord("q"):
                    break
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
