from __future__ import annotations

from dataclasses import dataclass

import cv2
from cv2.typing import MatLike


@dataclass
class Camera:
    index: int = 0

    def __post_init__(self) -> None:
        self._capture = cv2.VideoCapture(self.index)
        if not self._capture.isOpened():
            raise RuntimeError(f"No se pudo abrir la camara con indice {self.index}.")

    def read(self) -> MatLike:
        ok, frame = self._capture.read()
        if not ok:
            raise RuntimeError("No se pudo leer un frame de la camara.")
        return frame

    def release(self) -> None:
        self._capture.release()

    def __enter__(self) -> "Camera":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()
