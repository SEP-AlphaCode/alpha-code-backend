import cv2
import os
from typing import List, Optional
from app.models.marker import MarkerResponse
import base64
import numpy as np

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

        # dictionary mặc định để embed marker
        self.embed_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)

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

        # # Thử tất cả dictionary
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

    # ---------------- Embed marker ----------------
    def embed_marker(
            self,
            image_path: str,
            page_id: int,
            size: int = 200,
            pos: Optional[tuple] = None
    ) -> str:
        """
        Nhúng marker ArUco đơn vào ảnh trang sách.
        :param image_path: đường dẫn ảnh gốc
        :param page_id: ID muốn encode thành marker
        :param size: kích thước marker (px)
        :param pos: tuple (x, y) vị trí chèn; mặc định góc phải dưới
        :return: đường dẫn ảnh output (đã nhúng marker)
        """
        page = cv2.imread(image_path)
        if page is None:
            raise ValueError("Không đọc được ảnh trang sách")

        # kiểm tra page_id hợp lệ với dictionary
        max_id = self.embed_dict.bytesList.shape[0] - 1
        if page_id < 0 or page_id > max_id:
            raise ValueError(f"page_id phải từ 0 đến {max_id}, bạn truyền {page_id}")

        # tạo marker
        marker_img = cv2.aruco.generateImageMarker(self.embed_dict, page_id, size)

        # nếu chưa có vị trí → mặc định góc phải dưới
        if pos is None:
            h, w = page.shape[:2]
            pos = (w - size - 20, h - size - 20)  # cách mép 20px

        x, y = pos
        h, w = page.shape[:2]
        # đảm bảo marker không vượt ra ngoài ảnh
        if x + size > w:
            x = w - size
        if y + size > h:
            y = h - size

        # chuyển GRAY → BGR để chèn vào trang màu
        marker_bgr = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)
        page[y:y + size, x:x + size] = marker_bgr

        # lưu output
        out_path = os.path.join(self.debug_dir, f"page_with_marker_{page_id}.png")
        cv2.imwrite(out_path, page)

        return out_path

    def find_low_detail_region(self, img, size: int = 200, grid: int = 5) -> tuple:
        """
        Tìm vị trí (x, y) có độ chi tiết thấp nhất để nhúng marker.
        :param img: ảnh gốc (numpy array BGR)
        :param size: kích thước marker px
        :param grid: số ô chia (grid x grid)
        :return: tuple (x, y)
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        cell_h, cell_w = h // grid, w // grid

        best_score = float("inf")
        best_pos = (w - size - 20, h - size - 20)  # fallback = góc phải dưới

        for i in range(grid):
            for j in range(grid):
                x, y = j * cell_w, i * cell_h
                # đảm bảo marker không vượt ngoài
                if x + size > w or y + size > h:
                    continue
                roi = gray[y:y+size, x:x+size]
                if roi.size == 0:
                    continue
                score = cv2.Laplacian(roi, cv2.CV_64F).var()
                if score < best_score:
                    best_score = score
                    best_pos = (x, y)

        return best_pos

    def embed_marker_hidden(
        self,
        image_path: str,
        page_id: int,
        size: int = 200,
    ) -> str:
        page = cv2.imread(image_path)
        if page is None:
            raise ValueError("Không đọc được ảnh trang sách")

        max_id = self.embed_dict.bytesList.shape[0] - 1
        if page_id < 0 or page_id > max_id:
            raise ValueError(f"page_id phải từ 0 đến {max_id}, bạn truyền {page_id}")

        marker_img = cv2.aruco.generateImageMarker(self.embed_dict, page_id, size)


        pos = self.find_low_detail_region(page, size)

        x, y = pos
        h, w = page.shape[:2]
        if x + size > w:
            x = w - size
        if y + size > h:
            y = h - size

        marker_bgr = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)
        page[y:y+size, x:x+size] = marker_bgr

        out_path = os.path.join(self.debug_dir, f"page_with_marker_{page_id}.png")
        cv2.imwrite(out_path, page)

        return out_path

