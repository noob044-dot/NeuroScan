from pathlib import Path
import argparse

from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent

TRAINING_JOBS = {
    "pothole": {
        "data": str(BASE_DIR / "dataset" / "data.yaml"),
        "project": str(BASE_DIR / "runs" / "detect"),
        "name": "pothole_plus",
        "imgsz": 896,
        "epochs": 120,
        "batch": 8,
    },
    "garbage": {
        "data": str(BASE_DIR / "dataset" / "garbage" / "data.yaml"),
        "project": str(BASE_DIR / "dataset" / "garbage" / "runs" / "detect"),
        "name": "garbage_plus",
        "imgsz": 768,
        "epochs": 100,
        "batch": 8,
    },
    "manhole": {
        "data": str(BASE_DIR / "dataset" / "manhole" / "open_manhole" / "data.yaml"),
        "project": str(BASE_DIR / "dataset" / "manhole" / "open_manhole" / "runs" / "detect"),
        "name": "manhole_plus",
        "imgsz": 768,
        "epochs": 100,
        "batch": 8,
    },
    "crack": {
        "data": str(BASE_DIR / "dataset" / "manhole" / "cracks" / "data.yaml"),
        "project": str(BASE_DIR / "dataset" / "manhole" / "cracks" / "runs" / "detect"),
        "name": "crack_plus",
        "imgsz": 960,
        "epochs": 140,
        "batch": 6,
    },
}


def train_job(job_name: str, base_model: str) -> None:
    config = TRAINING_JOBS[job_name]
    model = YOLO(base_model)

    model.train(
        data=config["data"],
        epochs=config["epochs"],
        imgsz=config["imgsz"],
        batch=config["batch"],
        project=config["project"],
        name=config["name"],
        pretrained=True,
        optimizer="AdamW",
        patience=30,
        cache=True,
        cos_lr=True,
        close_mosaic=15,
        degrees=3.0,
        translate=0.08,
        scale=0.30,
        fliplr=0.5,
        mosaic=0.7,
        mixup=0.05,
        copy_paste=0.0,
        erasing=0.2,
        hsv_h=0.01,
        hsv_s=0.5,
        hsv_v=0.3,
        save=True,
        amp=True,
        device="cpu",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrain NeuroScan detection models with stronger defaults.")
    parser.add_argument(
        "--jobs",
        nargs="+",
        choices=sorted(TRAINING_JOBS.keys()),
        default=sorted(TRAINING_JOBS.keys()),
        help="Model jobs to retrain.",
    )
    parser.add_argument(
        "--base-model",
        default="yolov8s.pt",
        help="Base Ultralytics model checkpoint. Use yolov8s.pt or yolov8m.pt for higher accuracy than yolov8n.pt.",
    )
    args = parser.parse_args()

    for job_name in args.jobs:
        print(f"Starting training job: {job_name}")
        train_job(job_name, args.base_model)


if __name__ == "__main__":
    main()
