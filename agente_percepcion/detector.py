from __future__ import annotations

from dataclasses import dataclass

import cv2
from cv2.typing import MatLike


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    box: tuple[int, int, int, int]


class YoloDetector:
    def __init__(self, model_path: str, confidence: float, allowed_classes: set[str]) -> None:
        from ultralytics import YOLO

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
    high_risk = {"knife", "gun", "scissors"}
    medium_risk = {"person", "car", "truck", "backpack", "cell phone"}

    if normalized in high_risk:
        return (35, 35, 230)
    if normalized in medium_risk:
        return (20, 180, 230)
    return (20, 180, 90)


def normalize_label(label: str) -> str:
    normalized = label.strip().lower().replace("_", " ")
    aliases = {
        "pistol": "gun",
        "handgun": "gun",
        "firearm": "gun",
        "weapon": "gun",
        "arma": "gun",
        "pistola": "gun",
        "cellphone": "cell phone",
        "mobile phone": "cell phone",
        "phone": "cell phone",
    }
    return aliases.get(normalized, normalized)
