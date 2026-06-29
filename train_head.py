from ultralytics import YOLO

model = YOLO("yolov8n.pt")

model.train(
    data="mounted_screw_dataset/data.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    name="head_detect",
)
