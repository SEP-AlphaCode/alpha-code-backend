# app/routers/object_router.py
from typing import List
import sys
import os

# Handle different directory structures between local and deployed environments
current_dir = os.path.dirname(os.path.abspath(__file__))

# Check if we're in a nested app/app structure (deployed) or app structure (local)
if current_dir.endswith('/app/app/routers') or current_dir.endswith('\\app\\app\\routers'):
    # Deployed environment: /app/app/routers -> /app/models
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    models_dir = os.path.join(project_root, 'models')
else:
    # Local environment: project_root/app/routers -> project_root/models
    project_root = os.path.dirname(os.path.dirname(current_dir))
    models_dir = os.path.join(project_root, 'models')

print(f"DEBUG: Current dir: {current_dir}")
print(f"DEBUG: Project root: {project_root}")
print(f"DEBUG: Models dir: {models_dir}")
print(f"DEBUG: Models dir exists: {os.path.exists(models_dir)}")

# Add paths for import resolution
sys.path.insert(0, models_dir)
sys.path.insert(0, project_root)

import torch
from PIL import Image
from fastapi import APIRouter, UploadFile, File, HTTPException
from ultralytics import YOLO
import cv2
import numpy as np

# Try multiple import approaches for maximum compatibility
try:
    print("DEBUG: Trying first import approach...")
    from midas.dpt_depth import DPTDepthModel
    print("DEBUG: First import successful")
except ImportError as e1:
    print(f"DEBUG: First import failed: {e1}")
    try:
        print("DEBUG: Trying second import approach...")
        from models.midas.dpt_depth import DPTDepthModel
        print("DEBUG: Second import successful")
    except ImportError as e2:
        print(f"DEBUG: Second import failed: {e2}")
        try:
            print("DEBUG: Trying third import approach (absolute path)...")
            # Absolute path import as last resort
            import importlib.util
            midas_path = os.path.join(models_dir, 'midas', 'dpt_depth.py')
            print(f"DEBUG: Trying to load from: {midas_path}")
            print(f"DEBUG: File exists: {os.path.exists(midas_path)}")

            if os.path.exists(midas_path):
                spec = importlib.util.spec_from_file_location("dpt_depth", midas_path)
                dpt_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(dpt_module)
                DPTDepthModel = dpt_module.DPTDepthModel
                print("DEBUG: Third import successful")
            else:
                raise ImportError(f"Could not find midas module at {midas_path}")
        except Exception as e3:
            print(f"DEBUG: All import attempts failed. Errors: {e1}, {e2}, {e3}")
            raise ImportError(f"Could not import DPTDepthModel. Tried multiple approaches. Last error: {e3}")

import torchvision.transforms as transforms
from app.models.object_detect import DetectClosestResponse, Detection

router = APIRouter()

# Load YOLO once (lazy load at module import)
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

@router.post("/detect_closest")
async def detect_closest_objects(file: UploadFile = File(...), k: int = 3) -> DetectClosestResponse:
    try:
        """
            Upload an image, detect objects with YOLO, estimate depth with MiDaS,
            and return the k closest objects.
            """
        # Read image into numpy array
        
        image_bytes = await file.read()
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        
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
        filtered = [d for d in detections if d.label.lower() != "person"]
        # Step 4: Sort by "closeness" (lowest depth = closest)
        detections_sorted = sorted(filtered, key=lambda d: d.depth_min or 9999.0)
        return DetectClosestResponse(closest_objects=detections_sorted[:k], all_objects=detections_sorted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))