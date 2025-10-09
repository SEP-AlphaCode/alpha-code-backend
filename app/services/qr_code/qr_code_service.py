import cv2
import numpy as np


def preprocess_image_for_qr_detection(image_bytes):
    """
    Preprocess image with multiple techniques to improve QR code detection
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    original = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    
    if original is None:
        raise ValueError("Could not decode image from bytes")
    
    processed_variants = []
    
    # 1. Original grayscale
    processed_variants.append(('original', original))
    
    # 2. Adaptive thresholding
    adaptive_thresh = cv2.adaptiveThreshold(
        original, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    processed_variants.append(('adaptive_thresh', adaptive_thresh))
    
    # 3. Otsu's thresholding
    _, otsu_thresh = cv2.threshold(original, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    processed_variants.append(('otsu_thresh', otsu_thresh))
    
    # 4. Contrast enhancement using CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    contrast_enhanced = clahe.apply(original)
    processed_variants.append(('contrast_enhanced', contrast_enhanced))
    
    # 5. Denoised version
    denoised = cv2.medianBlur(original, 3)
    processed_variants.append(('denoised', denoised))
    
    # 6. Sharpened version
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpened = cv2.filter2D(original, -1, kernel)
    processed_variants.append(('sharpened', sharpened))
    
    # 7. Morphological operations to enhance QR code patterns
    kernel_morph = np.ones((3, 3), np.uint8)
    morph_closed = cv2.morphologyEx(original, cv2.MORPH_CLOSE, kernel_morph)
    processed_variants.append(('morph_closed', morph_closed))
    
    return processed_variants


def detect_qr_code(image_bytes: bytes) -> str:
    processed_images = preprocess_image_for_qr_detection(image_bytes)
    
    # Initialize QR code detector
    qr_detector = cv2.QRCodeDetector()
    
    decoded_text = None
    detection_details = []
    
    # Try detection on each preprocessed variant
    for variant_name, processed_img in processed_images:
        try:
            # For OpenCV QRCodeDetector, we need to convert back to BGR if using color
            if len(processed_img.shape) == 2:
                color_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)
            else:
                color_img = processed_img
            
            data, bbox, straight_qrcode = qr_detector.detectAndDecode(color_img)
            
            if data and len(data) > 0:
                decoded_text = data
                detection_details.append({
                    'variant': variant_name,
                    'success': True,
                    'data': data,
                    'bbox': bbox
                })
                break  # Stop at first successful detection
            else:
                detection_details.append({
                    'variant': variant_name,
                    'success': False,
                    'data': None
                })
        
        except Exception as e:
            detection_details.append({
                'variant': variant_name,
                'success': False,
                'error': str(e)
            })
    
    return decoded_text
