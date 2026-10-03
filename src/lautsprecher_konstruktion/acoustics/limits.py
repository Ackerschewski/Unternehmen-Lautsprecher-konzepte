"""Configurable advisory limits. They are design guidance, not physical laws."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PortVelocityLimits:
    caution_m_s: float = 17.0
    high_m_s: float = 25.0


DEFAULT_PORT_VELOCITY_LIMITS = PortVelocityLimits()
