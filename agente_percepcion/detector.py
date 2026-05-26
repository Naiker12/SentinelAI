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
                label = str(names[class_id])
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
        text = f"{detection.label} {detection.confidence:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (20, 180, 90), 2)
        cv2.putText(
            frame,
            text,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (20, 180, 90),
            2,
            cv2.LINE_AA,
        )
    return frame
