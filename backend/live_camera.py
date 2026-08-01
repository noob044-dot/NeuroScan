import cv2
import time
from ultralytics import YOLO

model = YOLO("runs/detect/train12/weights/best.pt")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not accessible")
    exit()

print("Press C to capture image | Q to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow("Camera - Press C to Capture", frame)

    key = cv2.waitKey(1) & 0xFF

    # Capture image
    if key == ord('c'):
        filename = f"uploads/capture_{int(time.time())}.jpg"
        cv2.imwrite(filename, frame)
        print(f"Image saved: {filename}")

        # Run detection
        results = model(filename, conf=0.4)
        annotated = results[0].plot()

        cv2.imshow("Detection Result", annotated)
        cv2.waitKey(0)
        cv2.destroyWindow("Detection Result")

    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
