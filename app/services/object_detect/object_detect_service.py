from typing import List

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from ultralytics import YOLO

from app.models.object_detect import DetectClosestResponse, Detection
from models.midas.dpt_depth import DPTDepthModel

yolo_model = YOLO("models/yolo/yolov8l.pt")
midas = DPTDepthModel(
    path="models/midas/dpt_hybrid_384.pt",
    backbone="vitb_rn50_384",
    non_negative=True,
)
midas_transform = transforms.Compose([
    transforms.Resize(384),
    transforms.CenterCrop(384),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
])
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
midas.to(device)
midas.eval()


def estimate_depth(image: np.ndarray) -> np.ndarray:
    """Run MiDaS depth estimation and return normalized depth map."""
    
    # Convert OpenCV BGR -> RGB and then to PIL
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(img_rgb)
    
    # Apply MiDaS transform (returns a tensor, shape [3, H, W])
    input_tensor = midas_transform(pil_image)
    
    # Add batch dimension: [1, 3, H, W]
    input_batch = input_tensor.unsqueeze(0).to(device)
    
    with torch.no_grad():
        prediction = midas(input_batch)
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=image.shape[:2],
            mode="bicubic",
            align_corners=False,
        ).squeeze()
    
    depth_map = prediction.cpu().numpy()
    # Normalize for easier comparison
    depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
    
    return depth_map

def detect_closest_objects_from_bytes(image_bytes: bytes, k: int = 3) -> DetectClosestResponse:
    """
    Core logic that works with raw bytes - reusable across different frameworks
    """
    # Read image into numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Could not decode image from bytes")
    
    return detect_closest_objects_from_cv2(img, k)


def detect_closest_objects_from_cv2(img: np.ndarray, k: int = 3) -> DetectClosestResponse:
    """
    Core logic that works with OpenCV image - most reusable version
    """
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
    
    filtered = [d for d in detections if d.label.lower() != "person" and d.confidence > 0.4]
    
    # Step 4: Sort by "closeness" (lowest depth = closest)
    detections_sorted = sorted(filtered, key=lambda d: d.depth_median or 9999.0)
    
    if not detections_sorted:
        return DetectClosestResponse(closest_objects=[], all_objects=[])
    
    # Compute dynamic cutoff — e.g. within 1.5× of the closest object
    closest_depth = detections_sorted[0].depth_median or 0
    depth_cutoff = closest_depth * 1.5
    
    # Filter out detections that are too far away
    closest_objects = [
        d for d in detections_sorted
        if (d.depth_median or 9999.0) <= depth_cutoff
    ]
    
    # Fallback: ensure we still have at least 'k' elements if all are similar
    if len(closest_objects) < k:
        closest_objects = detections_sorted[:k]
    
    return DetectClosestResponse(
        closest_objects=closest_objects,
        all_objects=detections_sorted
    )
