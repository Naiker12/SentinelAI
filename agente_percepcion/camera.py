from __future__ import annotations

import platform
import threading
import time
from dataclasses import dataclass

import cv2
from cv2.typing import MatLike


@dataclass
class Camera:
    index: int = 0
    backend: str = "auto"
    width: int | None = None
    height: int | None = None
    fps: int | None = None
    fourcc: str | None = "MJPG"
    drop_stale_frames: int = 0
    read_retries: int = 15
    threaded: bool = True
    read_timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        self._capture = self._open_capture()
        self._latest_frame: MatLike | None = None
        self._latest_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._reader_thread: threading.Thread | None = None
        if self.threaded:
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()

    def read(self) -> MatLike:
        if self.threaded:
            frame = self._read_latest_frame()
            if frame is not None:
                return frame
            raise RuntimeError(
                "No se pudo leer un frame reciente de la camara. "
                "Prueba SENTINEL_CAMERA_THREADED=false o cambia el backend."
            )

        self._drop_stale_frames()
        frame = self._read_with_retries(self._capture)
        if frame is None:
            raise RuntimeError(
                "No se pudo leer un frame de la camara. "
                "Prueba cambiar SENTINEL_CAMERA_INDEX o SENTINEL_CAMERA_BACKEND=directshow."
            )
        return frame

    def release(self) -> None:
        self._stop_event.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1)
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

            _configure_capture(capture, self.width, self.height, self.fps, self.fourcc)
            frame = self._read_with_retries(capture)
            if frame is not None:
                height, width = frame.shape[:2]
                print(
                    "Camara abierta: "
                    f"index={self.index}, backend={name}, size={width}x{height}"
                )
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

    def _drop_stale_frames(self) -> None:
        for _ in range(max(0, self.drop_stale_frames)):
            if not self._capture.grab():
                break

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            frame = self._read_with_retries(self._capture)
            if frame is None:
                time.sleep(0.02)
                continue
            with self._latest_lock:
                self._latest_frame = frame

    def _read_latest_frame(self) -> MatLike | None:
        deadline = time.monotonic() + max(0.1, self.read_timeout_seconds)
        while time.monotonic() < deadline:
            with self._latest_lock:
                frame = self._latest_frame
            if frame is not None:
                return frame.copy()
            time.sleep(0.01)
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


def _configure_capture(
    capture: cv2.VideoCapture,
    width: int | None,
    height: int | None,
    fps: int | None,
    fourcc: str | None,
) -> None:
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if fourcc:
        normalized = fourcc.strip().upper()
        if len(normalized) == 4:
            capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*normalized))
    if width:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if fps:
        capture.set(cv2.CAP_PROP_FPS, fps)
