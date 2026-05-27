from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import cv2
from cv2.typing import MatLike


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    box: tuple[int, int, int, int]


class YoloDetector:
    def __init__(self, model_path: str, confidence: float, allowed_classes: set[str]) -> None:
        _configure_ultralytics_runtime()
        from ultralytics import YOLO

        if model_path != "yolov8n.pt" and not Path(model_path).exists():
            raise FileNotFoundError(
                "No se encontro el modelo de SentinelAI. "
                f"Coloca el best.pt entrenado en {model_path} o ajusta SENTINEL_MODEL."
            )
        self._model = YOLO(model_path)
        self._confidence = confidence
        self._allowed_classes = allowed_classes

    def detect(self, frame: MatLike) -> list[Detection]:
        results = self._model.predict(frame, conf=self._confidence, verbose=False)
        detections: list[Detection] = []

        for result in results:
            names = result.names
            for box in result.boxes:
                class_id = int(box.cls[0])
                label = normalize_label(str(names[class_id]))
                if self._allowed_classes and label not in self._allowed_classes:
                    continue

                x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
                detections.append(
                    Detection(
                        label=label,
                        confidence=round(float(box.conf[0]), 4),
                        box=(x1, y1, x2, y2),
                    )
                )

        return detections


def draw_detections(frame: MatLike, detections: list[Detection]) -> MatLike:
    for detection in detections:
        x1, y1, x2, y2 = detection.box
        color = _color_for_label(detection.label)
        text = f"{detection.label.upper()} {detection.confidence:.2f}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        _draw_label(frame, text, x1, y1, color)

    return frame


def _draw_label(frame: MatLike, text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    padding = 6
    text_size, baseline = cv2.getTextSize(text, font, font_scale, thickness)
    text_width, text_height = text_size

    label_top = max(y - text_height - baseline - padding * 2, 0)
    label_bottom = label_top + text_height + baseline + padding * 2
    label_right = x + text_width + padding * 2

    cv2.rectangle(frame, (x, label_top), (label_right, label_bottom), color, cv2.FILLED)
    cv2.putText(
        frame,
        text,
        (x + padding, label_bottom - baseline - padding),
        font,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )


def _color_for_label(label: str) -> tuple[int, int, int]:
    normalized = normalize_label(label)
    high_risk = {"arma", "arma_blanca", "fusil", "violencia", "knife", "gun", "scissors", "violence"}
    medium_risk = {"multitud", "persona_sospechosa", "person", "persona", "car", "truck", "backpack", "cell_phone"}

    if normalized in high_risk:
        return (35, 35, 230)
    if normalized in medium_risk:
        return (20, 180, 230)
    return (20, 180, 90)


def normalize_label(label: str) -> str:
    normalized = "_".join(label.strip().lower().replace("-", "_").split())
    aliases = {
        "pistol": "arma",
        "handgun": "arma",
        "firearm": "arma",
        "weapon": "arma",
        "gun": "arma",
        "pistola": "arma",
        "rifle": "fusil",
        "knife": "arma_blanca",
        "cuchillo": "arma_blanca",
        "scissors": "arma_blanca",
        "cellphone": "cell_phone",
        "mobile_phone": "cell_phone",
        "phone": "cell_phone",
        "nonviolence": "no_violencia",
        "non_violence": "no_violencia",
        "no_violence": "no_violencia",
        "normal": "no_violencia",
        "person": "persona",
        "people": "multitud",
        "crowd": "multitud",
        "pelea": "violencia",
        "fight": "violencia",
        "fighting": "violencia",
        "violence": "violencia",
    }
    return aliases.get(normalized, normalized)


def _configure_ultralytics_runtime() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    yolo_dir = base_dir / ".ultralytics"
    mpl_dir = base_dir / ".matplotlib"
    yolo_dir.mkdir(parents=True, exist_ok=True)
    (yolo_dir / "Ultralytics").mkdir(parents=True, exist_ok=True)
    mpl_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(yolo_dir))
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_dir))
