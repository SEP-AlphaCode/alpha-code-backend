from typing import List

import os
import shutil
import torch
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from ultralytics import YOLO

from app.models.object_detect import DetectResponse, DetectClosestResponse, Detection

router = APIRouter()

# --- Global device ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- Lazy-load YOLO ---
try:
    yolo_model = YOLO("yolov8l.pt")  # change to yolov8s/m/l for smaller/bigger models
    yolo_model.to(device)
    print("YOLO model loaded on", device)
except Exception as e:
    raise RuntimeError(f"Error loading YOLO: {e}")


# --- MiDaS loader with cache handling ---
def load_midas():
    try:
        midas = torch.hub.load("intel-isl/MiDaS", "DPT_Hybrid", pretrained=True)
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
    except Exception as e:
        print("Error loading MiDaS, clearing cache and retrying:", e)
        cache_dir = os.path.expanduser("~/.cache/torch/hub/intel-isl_MiDaS_master")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        midas = torch.hub.load("intel-isl/MiDaS", "DPT_Hybrid", pretrained=True)
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")

    midas.to(device).eval()
    return midas, midas_transforms.dpt_transform


midas, transform = load_midas()


# --- Utils ---
def estimate_depth(image: np.ndarray, resize: int = 512) -> np.ndarray:
    """
    Run MiDaS depth estimation and return normalized depth map.
    Optionally resize input to save memory.
    """
    # Optional resize
    h, w = image.shape[:2]
    if max(h, w) > resize:
        image_input = cv2.resize(image, (resize, resize))
    else:
        image_input = image

    input_batch = transform(image_input).to(device)
    with torch.no_grad():
        prediction = midas(input_batch)
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=image_input.shape[:2],
            mode="bicubic",
            align_corners=False,
        ).squeeze()

    depth_map = prediction.cpu().numpy()
    depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())

    # Resize back to original image size
    if depth_map.shape != (h, w):
        depth_map = cv2.resize(depth_map, (w, h))

    return depth_map


# --- API endpoints ---

@router.post("/detect", response_model=DetectResponse)
async def detect_object(file: UploadFile = File(...)) -> DetectResponse:
    """
    Upload an image and run YOLO object detection.
    """
    try:
        # Convert file to numpy array
        image_bytes = await file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Run YOLO inference
        results = yolo_model(img)

        detections = []
        for r in results:
            for box in r.boxes:
                detections.append({
                    "label": r.names[int(box.cls)],
                    "confidence": float(box.conf),
                    "bbox": box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                })

        return {"objects": detections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {e}")


@router.post("/detect_closest", response_model=DetectClosestResponse)
async def detect_closest_objects(file: UploadFile = File(...), k: int = 3) -> DetectClosestResponse:
    """
    Upload an image, detect objects with YOLO, estimate depth with MiDaS,
    and return the k closest objects.
    """
    try:
        # Read image into numpy array
        image_bytes = await file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Step 1: Run YOLO
        results = yolo_model(img)

        # Step 2: Run depth estimation
        depth_map = estimate_depth(img)

        # Step 3: Collect detections with depth metrics
        detections: List[Detection] = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                label = r.names[int(box.cls)]
                conf = float(box.conf)

                # Clip bounding box to image size
                h, w = depth_map.shape
                x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w - 1, x2), min(h - 1, y2)

                # Extract depth inside bounding box
                roi = depth_map[y1:y2, x1:x2]
                if roi.size == 0:
                    continue

                # Compute closeness metrics
                avg_depth = float(np.mean(roi))
                min_depth = float(np.min(roi))  # closest pixel
                median_depth = float(np.median(roi))

                detections.append(Detection(
                    label=label,
                    confidence=conf,
                    bbox=[x1, y1, x2, y2],
                    depth_avg=avg_depth,
                    depth_min=min_depth,
                    depth_median=median_depth,
                ))

        # Optional: filter persons
        filtered = [d for d in detections if d.label.lower() != "person"]

        # Step 4: Sort by "closeness" (lowest depth = closest)
        detections_sorted = sorted(filtered, key=lambda d: d.depth_min or 9999.0)

        return {
            "closest_objects": detections_sorted[:k],
            "all_objects": detections_sorted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection with depth failed: {e}")
