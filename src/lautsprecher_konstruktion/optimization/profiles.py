"""Documented, deterministic priorities for the assistant.

Weights are design policy, not acoustic measurements. Each technical metric is
normalized separately by score_design; absent measurements are never imputed.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SoundProfile:
    id: str
    label: str
    weights: dict[str, float]
    f3_to_fs_limit: float
    volume_ratios: tuple[float, ...]
    qtc_targets: tuple[float, ...]


PROFILES = {
    "neutral": SoundProfile("neutral", "Neutral", {"bass": 3, "size": 2, "headroom": 2,
        "port": 2, "delay": 1, "flatness": 2, "cost": 1}, 1.4, (0.55, 0.8, 1.1), (0.65, 0.707, 0.8)),
    "deep_bass": SoundProfile("deep_bass", "Tiefbass", {"bass": 5, "size": 1,
        "headroom": 3, "port": 3, "delay": 0.5, "flatness": 1, "cost": 1}, 1.1,
        (0.8, 1.1, 1.45), (0.7, 0.8, 0.9)),
    "punch": SoundProfile("punch", "Punch / Kickbass", {"bass": 1, "size": 1,
        "headroom": 4, "port": 2, "delay": 3, "flatness": 2, "cost": 1}, 1.6,
        (0.45, 0.65, 0.85), (0.65, 0.707, 0.75)),
    "compact": SoundProfile("compact", "Kompakt", {"bass": 1, "size": 5,
        "headroom": 2, "port": 2, "delay": 1, "flatness": 1, "cost": 1}, 1.8,
        (0.4, 0.6, 0.8), (0.75, 0.85, 0.95)),
    "precise": SoundProfile("precise", "Präzise / Studio", {"bass": 2, "size": 1,
        "headroom": 3, "port": 2, "delay": 4, "flatness": 4, "cost": 1}, 1.5,
        (0.55, 0.75, 1.0), (0.6, 0.65, 0.707)),
    "max_spl": SoundProfile("max_spl", "Maximaler Pegel", {"bass": 1, "size": 0.5,
        "headroom": 5, "port": 4, "delay": 1, "flatness": 1, "cost": 1}, 1.65,
        (0.7, 1.0, 1.3), (0.7, 0.8, 0.9)),
}


def get_profile(key: str) -> SoundProfile:
    return PROFILES[key]
