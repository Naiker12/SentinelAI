from __future__ import annotations

import platform
import time
from dataclasses import dataclass

import cv2
from cv2.typing import MatLike


@dataclass
class Camera:
    index: int = 0
    backend: str = "auto"
    read_retries: int = 15

    def __post_init__(self) -> None:
        self._capture = self._open_capture()

    def read(self) -> MatLike:
        frame = self._read_with_retries(self._capture)
        if frame is None:
            raise RuntimeError(
                "No se pudo leer un frame de la camara. "
                "Prueba cambiar SENTINEL_CAMERA_INDEX o SENTINEL_CAMERA_BACKEND=directshow."
            )
        return frame

    def release(self) -> None:
        self._capture.release()

    def __enter__(self) -> "Camera":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()

    def _open_capture(self) -> cv2.VideoCapture:
        errors: list[str] = []
        for name, backend_id in _backend_candidates(self.backend):
            capture = cv2.VideoCapture(self.index, backend_id)
            if not capture.isOpened():
                capture.release()
                errors.append(f"{name}: no abrio")
                continue

            frame = self._read_with_retries(capture)
            if frame is not None:
                print(f"Camara abierta: index={self.index}, backend={name}")
                return capture

            capture.release()
            errors.append(f"{name}: abrio pero no entrego frames")

        detail = "; ".join(errors) or "sin backends disponibles"
        raise RuntimeError(f"No se pudo abrir la camara con indice {self.index}. {detail}")

    def _read_with_retries(self, capture: cv2.VideoCapture) -> MatLike | None:
        for _ in range(self.read_retries):
            ok, frame = capture.read()
            if ok and frame is not None:
                return frame
            time.sleep(0.08)
        return None


def _backend_candidates(preferred: str) -> list[tuple[str, int]]:
    backends = {
        "any": cv2.CAP_ANY,
        "directshow": cv2.CAP_DSHOW,
        "dshow": cv2.CAP_DSHOW,
        "msmf": cv2.CAP_MSMF,
    }
    normalized = preferred.strip().lower()

    if normalized in backends and normalized != "any":
        return [(normalized, backends[normalized]), ("any", cv2.CAP_ANY)]

    if platform.system().lower() == "windows":
        return [
            ("directshow", cv2.CAP_DSHOW),
            ("msmf", cv2.CAP_MSMF),
            ("any", cv2.CAP_ANY),
        ]

    return [("any", cv2.CAP_ANY)]
