from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class DesignWarning(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    frequency_hz: float | None = None
    value: float | None = None
    limit: float | None = None
