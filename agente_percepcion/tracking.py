from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from agente_percepcion.detector import Detection


@dataclass
class _Track:
    track_id: str
    label: str
    box: tuple[int, int, int, int]
    first_seen: float
    last_seen: float
    previous_center: tuple[float, float]
    velocity: float = 0.0
    directions: list[tuple[float, float]] = field(default_factory=list)


class MotionTracker:
    def __init__(self, max_lost_seconds: float = 3.0) -> None:
        self._tracks: dict[str, _Track] = {}
        self._next_id = 1
        self._max_lost_seconds = max_lost_seconds

    def update(self, detections: list[Detection], now: float) -> list[Detection]:
        self._prune(now)
        updated: list[Detection] = []
        used_tracks: set[str] = set()

        for detection in detections:
            track = self._match(detection, used_tracks)
            if track is None:
                track = self._new_track(detection, now)
            else:
                self._update_track(track, detection, now)

            used_tracks.add(track.track_id)
            updated.append(replace(detection, tracking=self._context_for(track)))

        return updated

    def _new_track(self, detection: Detection, now: float) -> _Track:
        seed_track_id = (detection.tracking or {}).get("track_id")
        if seed_track_id:
            track_id = str(seed_track_id)
        else:
            prefix = detection.label.replace(" ", "_")
            track_id = f"{prefix}_{self._next_id:04d}"
            self._next_id += 1
        center = _center(detection.box)
        track = _Track(
            track_id=track_id,
            label=detection.label,
            box=detection.box,
            first_seen=now,
            last_seen=now,
            previous_center=center,
        )
        self._tracks[track_id] = track
        return track

    def _match(self, detection: Detection, used_tracks: set[str]) -> _Track | None:
        seed_track_id = (detection.tracking or {}).get("track_id")
        if seed_track_id:
            seeded = self._tracks.get(str(seed_track_id))
            if seeded and seeded.track_id not in used_tracks:
                return seeded

        best_track: _Track | None = None
        best_score = 0.0
        detection_center = _center(detection.box)

        for track in self._tracks.values():
            if track.track_id in used_tracks or track.label != detection.label:
                continue

            iou_score = _iou(track.box, detection.box)
            distance_score = _distance_score(track.box, detection.box, detection_center)
            score = max(iou_score, distance_score)
            if score > best_score:
                best_score = score
                best_track = track

        return best_track if best_score >= 0.2 else None

    def _update_track(self, track: _Track, detection: Detection, now: float) -> None:
        center = _center(detection.box)
        dt = max(now - track.last_seen, 0.001)
        dx = center[0] - track.previous_center[0]
        dy = center[1] - track.previous_center[1]
        speed = math.hypot(dx, dy) / dt

        if abs(dx) + abs(dy) > 1:
            track.directions.append((dx, dy))
            track.directions = track.directions[-5:]

        track.velocity = round(speed, 2)
        track.previous_center = center
        track.box = detection.box
        track.last_seen = now

    def _context_for(self, track: _Track) -> dict:
        return {
            "track_id": track.track_id,
            "person_id": track.track_id if track.label == "persona" else None,
            "velocidad": track.velocity,
            "permanencia_segundos": int(track.last_seen - track.first_seen),
            "movimiento_erratico": _is_erratic(track.directions),
            "patron_movimiento": "movimiento_erratico"
            if _is_erratic(track.directions)
            else ("en_movimiento" if track.velocity >= 30 else "estable"),
        }

    def _prune(self, now: float) -> None:
        expired = [
            track_id
            for track_id, track in self._tracks.items()
            if now - track.last_seen > self._max_lost_seconds
        ]
        for track_id in expired:
            del self._tracks[track_id]


def _center(box: tuple[int, int, int, int]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _distance_score(
    previous_box: tuple[int, int, int, int],
    current_box: tuple[int, int, int, int],
    current_center: tuple[float, float],
) -> float:
    previous_center = _center(previous_box)
    distance = math.hypot(current_center[0] - previous_center[0], current_center[1] - previous_center[1])
    max_dimension = max(
        previous_box[2] - previous_box[0],
        previous_box[3] - previous_box[1],
        current_box[2] - current_box[0],
        current_box[3] - current_box[1],
        80,
    )
    return max(0.0, 1.0 - distance / max_dimension)


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def _is_erratic(directions: list[tuple[float, float]]) -> bool:
    if len(directions) < 3:
        return False

    sharp_turns = 0
    for previous, current in zip(directions, directions[1:]):
        previous_norm = math.hypot(*previous)
        current_norm = math.hypot(*current)
        if previous_norm < 1 or current_norm < 1:
            continue
        dot = previous[0] * current[0] + previous[1] * current[1]
        cosine = max(-1.0, min(1.0, dot / (previous_norm * current_norm)))
        if math.degrees(math.acos(cosine)) >= 70:
            sharp_turns += 1

    return sharp_turns >= 2
