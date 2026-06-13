import cv2
import pytesseract
import numpy as np
import re

def deskew(image):
    coords = np.column_stack(np.where(image > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def parse_image_or_scanned_pdf(file_path):
    """
    OCR pipeline for scanned documents.
    """
    # 1. Load image
    image = cv2.imread(file_path)
    if image is None:
        raise ValueError("Could not load image")
        
    # 2. Grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 3. Deskew (invert first)
    gray = cv2.bitwise_not(gray)
    rotated = deskew(gray)
    rotated = cv2.bitwise_not(rotated)
    
    # 4. Denoise
    denoised = cv2.fastNlMeansDenoising(rotated, None, 10, 7, 21)
    
    # 5. Threshold
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # 6. OCR
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(thresh, config=custom_config)
    
    # 7. Basic Parsing via regex lines
    lines = text.split('\n')
    raw_transactions = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        raw_transactions.append({
            'raw_text': line,
            'parsed_data': line
        })
        
    return 'UNKNOWN', raw_transactions
