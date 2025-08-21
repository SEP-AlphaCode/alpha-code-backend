import cv2
import os
from typing import List, Optional
from app.models.marker import MarkerResponse
import base64

# Lấy tất cả dictionary ArUco/AprilTag có trong OpenCV
def get_all_dicts():
    dict_names = [a for a in dir(cv2.aruco) if a.startswith("DICT_")]
    return {name: getattr(cv2.aruco, name) for name in dict_names}

def image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

class MarkerService:
    def __init__(self, debug_dir: str = "outputs"):
        self.dicts = get_all_dicts()
        self.debug_dir = debug_dir
        os.makedirs(self.debug_dir, exist_ok=True)

    def preprocess(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        return thresh

    def detect_marker(self, image_path: str) -> MarkerResponse:
        img = cv2.imread(image_path)
        if img is None:
            return MarkerResponse(page_id=None, confidence=0.0, method="none")

        processed = self.preprocess(img)

        detected_ids: List[int] = []
        used_dict: Optional[str] = None
        corners_found = None

        # Thử tất cả dictionary
        for name, d in self.dicts.items():
            aruco_dict = cv2.aruco.getPredefinedDictionary(d)
            parameters = cv2.aruco.DetectorParameters()
            detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
            corners, ids, _ = detector.detectMarkers(processed)
            if ids is not None and len(ids) > 0:
                detected_ids = ids.flatten().tolist()
                used_dict = name
                corners_found = corners
                break  # detect thành công thì dừng lại

        if detected_ids:
            # Vẽ marker lên ảnh debug
            debug_path = os.path.join(
                self.debug_dir,
                f"debug_{os.path.basename(image_path)}"
            )
            img_marked = cv2.aruco.drawDetectedMarkers(img.copy(), corners_found, ids)
            cv2.imwrite(debug_path, img_marked)
            # debug_b64 = image_to_base64(debug_path)
            # data_url = f"data:image/png;base64,{debug_b64}"
            
            return MarkerResponse(
                page_id=f"{used_dict}_{'_'.join(map(str, detected_ids))}",
                confidence=1.0,
                method="aruco",
                marker_ids=detected_ids,  # list ID rõ ràng
                dict_used=used_dict,  # dictionary phát hiện
                # debug_image=data_url  # ảnh debug lưu ra file
                debug_image=debug_path
            )

        return MarkerResponse(page_id=None, confidence=0.0, method="none")
