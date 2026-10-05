"""Shared NumPy array aliases; precision-agnostic so NumPy's own result types are accepted."""
from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.floating[Any]]
ComplexArray = NDArray[np.complexfloating[Any, Any]]
