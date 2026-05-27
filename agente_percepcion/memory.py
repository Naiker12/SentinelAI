from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EventMemory:
    window_seconds: float = 24 * 60 * 60
    _events: list[tuple[float, str]] = field(default_factory=list)

    def snapshot(self, now: float) -> dict[str, int]:
        self._prune(now)
        alertas = sum(1 for _, risk in self._events if risk in {"alto", "critico", "ALTO", "CRITICO"})
        return {
            "eventos_previos_24h": len(self._events),
            "alertas_previas_24h": alertas,
        }

    def remember(self, now: float, risk: str) -> None:
        self._events.append((now, risk.lower()))
        self._prune(now)

    def _prune(self, now: float) -> None:
        self._events = [
            item for item in self._events if now - item[0] <= self.window_seconds
        ]


def should_emit_detection(
    label: str,
    camera_name: str,
    last_event_at: dict[str, float],
    now: float,
    cooldown_seconds: float,
) -> bool:
    key = f"{camera_name}:{label.strip().lower().replace(' ', '_')}"
    if key not in last_event_at:
        last_event_at[key] = now
        return True

    last_seen = last_event_at.get(key, 0)
    if cooldown_seconds <= 0 or now - last_seen >= cooldown_seconds:
        last_event_at[key] = now
        return True
    return False
