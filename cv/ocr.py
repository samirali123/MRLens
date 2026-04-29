import cv2
import numpy as np
import easyocr
from config.settings import OCR_CONFIDENCE_THRESHOLD
from cv.capture import capture_all_enemy_regions

_reader = None


def _get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def _preprocess(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    upscaled = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    return upscaled


def extract_name_from_region(image: np.ndarray) -> str | None:
    processed = _preprocess(image)
    reader = _get_reader()
    results = reader.readtext(processed)
    if not results:
        return None
    best = max(results, key=lambda r: r[2])
    if best[2] < OCR_CONFIDENCE_THRESHOLD:
        return None
    return best[1].strip()


def extract_all_enemy_names() -> list[str]:
    regions = capture_all_enemy_regions()
    names = []
    for img in regions:
        name = extract_name_from_region(img)
        if name:
            names.append(name)
    return names
