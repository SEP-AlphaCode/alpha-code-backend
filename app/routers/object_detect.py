from typing import List
import os
import sys
import torch
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from ultralytics import YOLO

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MIDAS_DIR = os.path.join(BASE_DIR, "midas_repo")

if MIDAS_DIR not in sys.path:
    sys.path.append(MIDAS_DIR)

from midas.dpt_depth import DPTDepthModel
from midas.transforms import dpt_transform


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


# --- MiDaS loader (no torch.hub) ---
def load_midas():
    weights_path = os.path.join("weights", "dpt_hybrid_384.pt")
    if not os.path.exists(weights_path):
        raise RuntimeError(f"MiDaS weights not found at {weights_path}")

    model = DPTDepthModel(
        path=weights_path,
        backbone="vitb_rn50_384",
        non_negative=True,
    )
    model.to(device).eval()
    return model, dpt_transform


midas, transform = load_midas()


# --- Utils ---
def estimate_depth(image: np.ndarray, resize: int = 512) -> np.ndarray:
    """
    Run MiDaS depth estimation and return normalized depth map.
    Optionally resize input to save memory.
    """
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
        image_bytes = await file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        results = yolo_model(img)

        detections = []
        for r in results:
            for box in r.boxes:
                detections.append({
                    "label": r.names[int(box.cls)],
                    "confidence": float(box.conf),
                    "bbox": box.xyxy[0].tolist()
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
        image_bytes = await file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        results = yolo_model(img)
        depth_map = estimate_depth(img)

        detections: List[Detection] = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                label = r.names[int(box.cls)]
                conf = float(box.conf)

                h, w = depth_map.shape
                x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w - 1, x2), min(h - 1, y2)

                roi = depth_map[y1:y2, x1:x2]
                if roi.size == 0:
                    continue

                avg_depth = float(np.mean(roi))
                min_depth = float(np.min(roi))
                median_depth = float(np.median(roi))

                detections.append(Detection(
                    label=label,
                    confidence=conf,
                    bbox=[x1, y1, x2, y2],
                    depth_avg=avg_depth,
                    depth_min=min_depth,
                    depth_median=median_depth,
                ))

        filtered = [d for d in detections if d.label.lower() != "person"]
        detections_sorted = sorted(filtered, key=lambda d: d.depth_min or 9999.0)

        return {
            "closest_objects": detections_sorted[:k],
            "all_objects": detections_sorted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection with depth failed: {e}")
