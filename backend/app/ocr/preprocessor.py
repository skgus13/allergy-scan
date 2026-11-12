"""
[팀원 1] OpenCV 기반 성분표 이미지 전처리 모듈
- 리사이즈 (긴 변 1,500px 기준)
- 그레이스케일 및 대비 향상 (CLAHE)
- 기울기 회전 및 원근 왜곡 보정 (추후 고도화)
"""
import cv2
import numpy as np


def preprocess_image(image_bytes: bytes, max_side: int = 1500) -> tuple[np.ndarray, int, int]:
    """
    업로드된 이미지 바이트를 받아 OpenCV 배열로 변환하고 전처리를 수행합니다.
    Returns:
        (전처리된 BGR/Gray 이미지 ndarray, 가로 픽셀, 세로 픽셀)
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("INVALID_IMAGE: 이미지를 디코딩할 수 없습니다.")

    height, width = img.shape[:2]

    # 1. 긴 변 기준 리사이즈 (속도 및 PaddleOCR 인식률 최적화)
    if max(height, width) > max_side:
        scale = max_side / float(max(height, width))
        new_w, new_h = int(width * scale), int(height * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        height, width = new_h, new_w

    # TODO [팀원 1 - 2주차]: 그레이스케일 변환, CLAHE 대비 향상, 노이즈 제거, 기울기 보정 추가
    return img, width, height
