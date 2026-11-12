"""
[팀원 1] PaddleOCR 엔진 래퍼 모듈
- 서버 시작 시 모델을 1회만 로드(Singleton)하여 재사용
- 텍스트, Bounding Box 좌표, 신뢰도(Confidence) 추출 후 OCRResult 반환
"""
from typing import Optional
from app.schemas import OCRBlock, OCRResult
from app.ocr.preprocessor import preprocess_image

_ocr_instance = None


def get_ocr_engine():
    """PaddleOCR 인스턴스를 싱글톤으로 로드합니다."""
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from paddleocr import PaddleOCR

            _ocr_instance = PaddleOCR(
                lang="korean",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        except Exception as e:
            print(f"[WARN] PaddleOCR 로드 실패 (개발용 Mock 모드로 동작합니다): {e}")
            _ocr_instance = None
    return _ocr_instance


def extract_ocr_data(image_bytes: bytes) -> OCRResult:
    """
    이미지 바이트에서 전처리 후 PaddleOCR을 실행해 표준 OCRResult 포맷을 반환합니다.
    """
    img, width, height = preprocess_image(image_bytes)
    ocr = get_ocr_engine()

    # PaddleOCR 미설치 환경에서도 프론트/분석 연동 테스트가 가능하도록 기본 Mock 제공
    if ocr is None:
        mock_blocks = [
            OCRBlock(
                text="원재료명: 밀가루(밀:미국산), 설탕, 전지분유(우유), 대두유",
                bbox=[80, 50, 720, 90],
                polygon=[[80, 50], [720, 50], [720, 90], [80, 90]],
                confidence=0.94,
            ),
            OCRBlock(
                text="밀, 우유, 대두, 땅콩 함유",
                bbox=[80, 110, 420, 145],
                polygon=[[80, 110], [420, 110], [420, 145], [80, 145]],
                confidence=0.91,
            ),
            OCRBlock(
                text="이 제품은 메밀을 사용한 제품과 같은 제조시설에서 제조하고 있습니다.",
                bbox=[80, 165, 840, 200],
                polygon=[[80, 165], [840, 165], [840, 200], [80, 200]],
                confidence=0.89,
            ),
        ]
        full_text = "\n".join(b.text for b in mock_blocks)
        avg_conf = sum(b.confidence for b in mock_blocks) / len(mock_blocks)
        return OCRResult(
            fullText=full_text,
            avgConfidence=round(avg_conf, 4),
            imageWidth=width,
            imageHeight=height,
            blocks=mock_blocks,
        )

    # TODO [팀원 1 - 1~2주차]: PaddleOCR 버전에 따른 predict() / ocr() 결과 구조 매핑 검증
    res = ocr.predict(img)[0]
    texts = res.get("rec_texts", [])
    scores = res.get("rec_scores", [])
    boxes = res.get("rec_boxes", [])

    blocks: list[OCRBlock] = []
    for idx, text in enumerate(texts):
        score = float(scores[idx]) if idx < len(scores) else 0.0
        raw_box = boxes[idx] if idx < len(boxes) else [0, 0, 0, 0]
        # raw_box가 [x_min, y_min, x_max, y_max] 형태라고 가정
        bbox = [int(v) for v in raw_box[:4]]
        blocks.append(OCRBlock(text=text, bbox=bbox, confidence=round(score, 4)))

    full_text = "\n".join(b.text for b in blocks)
    avg_conf = sum(b.confidence for b in blocks) / len(blocks) if blocks else 0.0

    return OCRResult(
        fullText=full_text,
        avgConfidence=round(avg_conf, 4),
        imageWidth=width,
        imageHeight=height,
        blocks=blocks,
    )
