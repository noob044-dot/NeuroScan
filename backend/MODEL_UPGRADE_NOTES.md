## Current state

The deployed detectors are all `yolov8n` models. That keeps them light, but it also caps accuracy.

Observed training limits in this project:

- `garbage` and `open_manhole` were trained for only `20` epochs
- `crack` and `pothole` were trained for `50` epochs
- some training runs used `device: cpu`
- current project does not include dedicated datasets for the newly added categories such as traffic signal damage, illegal parking, graffiti, air pollution, or fallen wires

## What improves accuracy most

1. Better labels and more training images
2. Larger base model: `yolov8s.pt` or `yolov8m.pt`
3. Longer training with stronger validation discipline
4. Per-category threshold calibration after training

## What improves speed most

1. Export best model after training to ONNX or TensorRT for deployment
2. Use fused models and calibrated `imgsz` at inference
3. Keep separate lightweight models per issue family instead of one overloaded detector

## Practical next training step

From the `backend` folder:

```powershell
python train_models.py --base-model yolov8s.pt
```

If you later have a GPU-enabled environment:

- switch to `device=0`
- try `--base-model yolov8m.pt` for potholes and cracks
- export the final best weights for faster deployment

## Honest boundary

No code-only change can make all models genuinely "more accurate" without retraining or better data. The code in this repo now supports better calibrated inference and a stronger retraining path, but the real jump comes from dataset quality.
