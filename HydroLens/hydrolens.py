"""
HydroLens
Satellite observation of water systems.

A lightweight pipeline for detecting water regions and visualizing
water-related change from satellite imagery.

Usage:
    python hydrolens.py --before before.png --after after.png --out output_dir

Notes:
- Works with regular RGB images.
- If you later use multispectral imagery, replace the RGB water index
  with NDWI/MNDWI using the correct bands.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def load_image(path: str | Path) -> np.ndarray:
    """Load an image from disk as RGB uint8."""
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def normalize_image(img: np.ndarray) -> np.ndarray:
    """Normalize image to float32 in [0, 1]."""
    return img.astype(np.float32) / 255.0


def align_images(reference: np.ndarray, moving: np.ndarray) -> np.ndarray:
    """
    Align the moving image to the reference image using ECC registration.
    Falls back to resize if registration fails.
    """
    ref_gray = cv2.cvtColor((reference * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    mov_gray = cv2.cvtColor((moving * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)

    warp_matrix = np.eye(2, 3, dtype=np.float32)
    criteria = (
        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
        100,
        1e-6,
    )

    try:
        cv2.findTransformECC(
            ref_gray,
            mov_gray,
            warp_matrix,
            cv2.MOTION_EUCLIDEAN,
            criteria,
        )
        aligned = cv2.warpAffine(
            moving,
            warp_matrix,
            (reference.shape[1], reference.shape[0]),
            flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
            borderMode=cv2.BORDER_REFLECT,
        )
        return aligned
    except cv2.error:
        return cv2.resize(
            moving,
            (reference.shape[1], reference.shape[0]),
            interpolation=cv2.INTER_LINEAR,
        )


def compute_water_index_rgb(img: np.ndarray) -> np.ndarray:
    """
    Approximate water index for RGB imagery.
    Water often trends relatively stronger in blue/green and weaker in red.
    """
    r = img[:, :, 0]
    g = img[:, :, 1]
    b = img[:, :, 2]

    index = (0.5 * g + 1.0 * b - 0.75 * r)
    index = cv2.GaussianBlur(index, (5, 5), 0)
    return index


def detect_water_mask(img: np.ndarray) -> np.ndarray:
    """
    Detect likely water pixels from RGB imagery.
    Returns a binary mask with values 0 or 255.
    """
    index = compute_water_index_rgb(img)

    # Normalize to 8-bit for thresholding
    index_norm = cv2.normalize(index, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    # Automatic threshold
    _, mask = cv2.threshold(index_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Clean up noise
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    return mask


def compute_change_map(
    before_mask: np.ndarray, after_mask: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compare water masks and return:
    - gained_water: became water
    - lost_water: no longer water
    """
    before_bool = before_mask > 0
    after_bool = after_mask > 0

    gained = np.logical_and(~before_bool, after_bool).astype(np.uint8) * 255
    lost = np.logical_and(before_bool, ~after_bool).astype(np.uint8) * 255

    return gained, lost


def render_overlay(
    base_img: np.ndarray,
    gained_water: np.ndarray,
    lost_water: np.ndarray,
    alpha: float = 0.45,
) -> np.ndarray:
    """
    Render overlay on top of the aligned 'after' image.
    - New water: blue
    - Lost water: red
    """
    overlay = base_img.copy()

    gained_mask = gained_water > 0
    lost_mask = lost_water > 0

    # Blue overlay for gained water
    blue_overlay = np.zeros_like(base_img)
    blue_overlay[:, :, 1] = 80
    blue_overlay[:, :, 2] = gained_water

    # Red overlay for lost water
    red_overlay = np.zeros_like(base_img)
    red_overlay[:, :, 0] = lost_water
    red_overlay[:, :, 1] = 30

    overlay[gained_mask] = (
        (1 - alpha) * overlay[gained_mask] + alpha * blue_overlay[gained_mask]
    ).astype(np.uint8)

    overlay[lost_mask] = (
        (1 - alpha) * overlay[lost_mask] + alpha * red_overlay[lost_mask]
    ).astype(np.uint8)

    return overlay


def save_image(path: str | Path, img_rgb: np.ndarray) -> None:
    """Save RGB image to disk."""
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    success = cv2.imwrite(str(path), img_bgr)
    if not success:
        raise IOError(f"Could not write image: {path}")


def save_mask(path: str | Path, mask: np.ndarray) -> None:
    """Save single-channel mask to disk."""
    success = cv2.imwrite(str(path), mask)
    if not success:
        raise IOError(f"Could not write mask: {path}")


def summarize_masks(
    before_mask: np.ndarray,
    after_mask: np.ndarray,
    gained: np.ndarray,
    lost: np.ndarray,
) -> dict[str, float | int]:
    """Compute simple summary statistics."""
    total_pixels = before_mask.shape[0] * before_mask.shape[1]

    before_water = int(np.count_nonzero(before_mask))
    after_water = int(np.count_nonzero(after_mask))
    gained_pixels = int(np.count_nonzero(gained))
    lost_pixels = int(np.count_nonzero(lost))

    return {
        "total_pixels": total_pixels,
        "before_water_pixels": before_water,
        "after_water_pixels": after_water,
        "gained_water_pixels": gained_pixels,
        "lost_water_pixels": lost_pixels,
        "before_water_pct": round(100.0 * before_water / total_pixels, 4),
        "after_water_pct": round(100.0 * after_water / total_pixels, 4),
        "gained_water_pct": round(100.0 * gained_pixels / total_pixels, 4),
        "lost_water_pct": round(100.0 * lost_pixels / total_pixels, 4),
    }


def write_summary(path: str | Path, stats: dict[str, float | int]) -> None:
    """Write a text summary to disk."""
    lines = ["HydroLens Summary", "=================", ""]
    for key, value in stats.items():
        lines.append(f"{key}: {value}")

    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def process(before_path: str, after_path: str, out_dir: str) -> None:
    """Run the full HydroLens pipeline."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    before = normalize_image(load_image(before_path))
    after = normalize_image(load_image(after_path))

    after_aligned = align_images(before, after)

    before_mask = detect_water_mask(before)
    after_mask = detect_water_mask(after_aligned)

    gained, lost = compute_change_map(before_mask, after_mask)

    before_uint8 = (before * 255).astype(np.uint8)
    after_uint8 = (after_aligned * 255).astype(np.uint8)
    overlay = render_overlay(after_uint8, gained, lost)

    save_image(out_path / "before_aligned_reference.png", before_uint8)
    save_image(out_path / "after_aligned.png", after_uint8)
    save_mask(out_path / "before_water_mask.png", before_mask)
    save_mask(out_path / "after_water_mask.png", after_mask)
    save_mask(out_path / "gained_water_mask.png", gained)
    save_mask(out_path / "lost_water_mask.png", lost)
    save_image(out_path / "water_change_overlay.png", overlay)

    stats = summarize_masks(before_mask, after_mask, gained, lost)
    write_summary(out_path / "summary.txt", stats)

    print("HydroLens run complete.")
    print(f"Outputs saved to: {out_path}")
    for key, value in stats.items():
        print(f"{key}: {value}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="HydroLens water-change detection pipeline"
    )
    parser.add_argument("--before", required=True, help="Path to earlier image")
    parser.add_argument("--after", required=True, help="Path to later image")
    parser.add_argument(
        "--out",
        default="hydrolens_output",
        help="Output directory",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    process(args.before, args.after, args.out)
