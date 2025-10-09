import cv2
import numpy as np
from pyzbar.pyzbar import decode
import qrcode
from PIL import Image
import io


def detect_qr_from_bytes(image_bytes, enable_preprocessing=True):
    """
    Detect and decode QR code from image bytes with extensive preprocessing for difficult cases.

    Args:
        image_bytes: Image data as bytes
        enable_preprocessing: Whether to apply preprocessing techniques

    Returns:
        str: Decoded QR code content

    Raises:
        ValueError: If no QR code found or cannot decode
    """
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Could not decode image from bytes")
        
        # Try direct decoding first (for easy cases)
        if enable_preprocessing:
            decoded_data = try_multiple_preprocessing(image)
        else:
            decoded_data = decode_qr_code(image)
        
        if decoded_data:
            return decoded_data
        else:
            raise ValueError("No QR code found or cannot decode QR code")
    
    except Exception as e:
        raise ValueError(f"QR code detection failed: {str(e)}")


def decode_qr_code(image):
    """Try to decode QR code from image using pyzbar"""
    # Convert to grayscale for pyzbar
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Try decoding
    decoded_objects = decode(gray)
    
    if decoded_objects:
        return decoded_objects[0].data.decode('utf-8')
    return None


def try_multiple_preprocessing(image):
    """
    Apply multiple preprocessing techniques to handle difficult QR codes
    """
    preprocessing_techniques = [
        # Original image
        lambda img: img,
        
        # Basic grayscale
        lambda img: cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img,
        
        # Adaptive threshold
        lambda img: apply_adaptive_threshold(img),
        
        # Histogram equalization
        lambda img: apply_histogram_equalization(img),
        
        # Bilateral filter + threshold
        lambda img: apply_bilateral_filter(img),
        
        # Morphological operations
        lambda img: apply_morphological_ops(img),
        
        # Sharpening
        lambda img: apply_sharpening(img),
        
        # Contrast enhancement
        lambda img: enhance_contrast(img),
        
        # Multiple threshold levels
        lambda img: try_multiple_thresholds(img),
        
        # Resize for better detection
        lambda img: resize_image(img, 2.0),  # Scale up
        lambda img: resize_image(img, 0.5),  # Scale down
        
        # Edge enhancement
        lambda img: enhance_edges(img),
        
        # Noise reduction + contrast
        lambda img: denoise_and_contrast(img),
    ]
    
    # Try each preprocessing technique
    for technique in preprocessing_techniques:
        try:
            processed_img = technique(image)
            result = decode_qr_code(processed_img)
            if result:
                print(f"Success with technique: {technique.__name__ if hasattr(technique, '__name__') else 'unknown'}")
                return result
        except Exception as e:
            continue
    
    # If standard techniques fail, try advanced methods
    return try_advanced_techniques(image)


def apply_adaptive_threshold(image):
    """Apply adaptive thresholding"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )


def apply_histogram_equalization(image):
    """Apply histogram equalization"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    return cv2.equalizeHist(gray)


def apply_bilateral_filter(image):
    """Apply bilateral filter for noise reduction while preserving edges"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    _, thresh = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def apply_morphological_ops(image):
    """Apply morphological operations to clean up the image"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
    return cleaned


def apply_sharpening(image):
    """Apply sharpening filter"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    kernel = np.array([[-1, -1, -1],
                       [-1, 9, -1],
                       [-1, -1, -1]])
    sharpened = cv2.filter2D(gray, -1, kernel)
    return sharpened


def enhance_contrast(image):
    """Enhance contrast using CLAHE"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def try_multiple_thresholds(image):
    """Try multiple threshold values"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    thresholds = [50, 100, 150, 200]
    for thresh_val in thresholds:
        _, binary = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
        result = decode_qr_code(binary)
        if result:
            return result
    
    return None


def resize_image(image, scale_factor):
    """Resize image by scale factor"""
    if len(image.shape) == 3:
        height, width = image.shape[:2]
    else:
        height, width = image.shape
    
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)
    
    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)


def enhance_edges(image):
    """Enhance edges using Canny"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    edges = cv2.Canny(gray, 50, 150)
    return cv2.bitwise_not(edges)  # Invert for dark background


def denoise_and_contrast(image):
    """Combine denoising and contrast enhancement"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    return enhanced


def try_advanced_techniques(image):
    """Advanced techniques for very difficult cases"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Try different color channel separations
    if len(image.shape) == 3:
        for channel in range(3):
            channel_img = image[:, :, channel]
            result = decode_qr_code(channel_img)
            if result:
                return result
    
    # Try inverted image
    inverted = cv2.bitwise_not(gray)
    result = decode_qr_code(inverted)
    if result:
        return result
    
    # Try multiple blur levels followed by sharpening
    for ksize in [3, 5, 7]:
        blurred = cv2.GaussianBlur(gray, (ksize, ksize), 0)
        sharpened = apply_sharpening(blurred)
        result = decode_qr_code(sharpened)
        if result:
            return result
    
    return None


# Example usage and test function
def test_qr_detection():
    """Test function to demonstrate usage"""
    # Example: Create a test QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data("Test QR Code Content")
    qr.make(fit=True)
    
    # Convert to bytes
    img = qr.make_image(fill_color="black", back_color="white")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    try:
        result = detect_qr_from_bytes(img_bytes)
        print(f"Decoded QR code: {result}")
        return result
    except ValueError as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    test_qr_detection()