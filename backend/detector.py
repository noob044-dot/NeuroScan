from dataclasses import dataclass
from pathlib import Path
import os

import cv2


BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault("YOLO_CONFIG_DIR", str(BASE_DIR / ".ultralytics"))

from ultralytics import YOLO


@dataclass(frozen=True)
class ModelProfile:
    weights: str
    conf: float
    iou: float
    imgsz: int
    max_det: int


MODEL_PROFILES = {
    "pothole": ModelProfile(
        weights="runs/detect/train12/weights/best.pt",
        conf=0.28,
        iou=0.55,
        imgsz=704,
        max_det=25,
    ),
    "garbage": ModelProfile(
        weights="dataset/garbage/runs/detect/train6/weights/best.pt",
        conf=0.26,
        iou=0.50,
        imgsz=640,
        max_det=35,
    ),
    "manhole": ModelProfile(
        weights="dataset/manhole/open_manhole/runs/detect/train11/weights/best.pt",
        conf=0.30,
        iou=0.50,
        imgsz=640,
        max_det=20,
    ),
    "crack": ModelProfile(
        weights="dataset/manhole/cracks/runs/detect/train2/weights/best.pt",
        conf=0.22,
        iou=0.45,
        imgsz=768,
        max_det=40,
    ),
}

MODEL_CACHE = {}


def _load_model(model_key: str) -> YOLO | None:
    if model_key in MODEL_CACHE:
        return MODEL_CACHE[model_key]

    profile = MODEL_PROFILES.get(model_key)
    if profile is None:
        return None

    model = YOLO(str(BASE_DIR / profile.weights))

    try:
        model.fuse()
    except Exception:
        pass

    MODEL_CACHE[model_key] = model
    return model


def estimate_severity(detection_count: int, average_confidence: float, detection_mode: str) -> str:
    if detection_mode != "ai":
        return "Needs Review"

    if detection_count >= 4 or average_confidence >= 0.85:
        return "High"
    if detection_count >= 1 or average_confidence >= 0.45:
        return "Medium"
    return "Low"


def detect_damage(image_path: str, model_key: str):
    profile = MODEL_PROFILES.get(model_key)
    model = _load_model(model_key)

    if model is None or profile is None:
        return [], 0, None, "Needs Review"

    results = model.predict(
        source=image_path,
        conf=profile.conf,
        iou=profile.iou,
        imgsz=profile.imgsz,
        max_det=profile.max_det,
        verbose=False,
    )

    detections = []
    confidences = []
    annotated = None

    for result in results:
        for box in result.boxes:
            confidence = float(box.conf[0])
            confidences.append(confidence)
            detections.append({"confidence": round(confidence, 3)})
        annotated = result.plot()

    output_path = BASE_DIR / "outputs" / Path(image_path).name

    if annotated is None:
        annotated = cv2.imread(image_path)

    cv2.imwrite(str(output_path), annotated)

    average_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0
    severity = estimate_severity(len(detections), average_confidence, "ai")
    return detections, average_confidence, str(output_path), severity
