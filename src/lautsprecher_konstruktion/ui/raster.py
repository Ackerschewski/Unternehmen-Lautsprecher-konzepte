"""Small z-buffer triangle rasteriser (numpy) for the 3D preview: correct hidden surfaces without OpenGL."""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Image = NDArray[np.float32]


def new_buffers(width: int, height: int, background: tuple[int, int, int]) -> tuple[Image, NDArray[np.float32]]:
    colour = np.empty((height, width, 3), dtype=np.float32)
    colour[:] = background
    return colour, np.full((height, width), np.inf, dtype=np.float32)


def draw_triangle(colour: Image, depth: NDArray[np.float32], xy: NDArray[np.float64], z: NDArray[np.float64],
                  rgb: tuple[float, float, float], alpha: float = 1.0, write_depth: bool = True) -> None:
    """Fill one triangle. xy: (3, 2) pixel coordinates, z: (3,) view depth (smaller = nearer)."""
    h, w = depth.shape
    x0, y0 = int(max(0, np.floor(xy[:, 0].min()))), int(max(0, np.floor(xy[:, 1].min())))
    x1, y1 = int(min(w - 1, np.ceil(xy[:, 0].max()))), int(min(h - 1, np.ceil(xy[:, 1].max())))
    if x1 < x0 or y1 < y0:
        return
    (ax, ay), (bx, by), (cx, cy) = xy
    det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(det) < 1e-9:
        return
    px, py = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    l1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / det
    l2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / det
    l3 = 1.0 - l1 - l2
    inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
    if not inside.any():
        return
    pz = (l1 * z[0] + l2 * z[1] + l3 * z[2]).astype(np.float32)
    region = depth[y0:y1 + 1, x0:x1 + 1]
    visible = inside & (pz < region)
    if not visible.any():
        return
    target = colour[y0:y1 + 1, x0:x1 + 1]
    target[visible] = target[visible] * (1.0 - alpha) + np.array(rgb, dtype=np.float32) * alpha
    if write_depth:
        region[visible] = pz[visible]
