"""
[팀원 2] 알레르기 분석 및 RapidFuzz 유사도 매칭 모듈
- OCR 후처리 및 개별 원재료 분리
- 19종 알레르기 사전 및 동의어 매칭 (정확 매칭 + RapidFuzz 오탈자 보정)
- 4단계 판정 도출: DANGER / CAUTION / SAFE / UNCERTAIN
"""
import json
import re
import uuid
from pathlib import Path
from typing import Optional
from rapidfuzz import fuzz, process

from app.config import settings
from app.schemas import AnalyzeResponse, CrossCheckInfo, DetectedAllergen, OCRResult

DICT_PATH = Path(__file__).parent / "allergens_ko.json"


def load_allergen_dictionary() -> dict:
    with open(DICT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_ingredients(full_text: str) -> list[str]:
    """OCR 전체 텍스트에서 쉼표·괄호 기준으로 개별 원재료 목록을 추출합니다."""
    cleaned = re.sub(r"[\r\n]+", " ", full_text)
    tokens = re.split(r"[,，·/()\[\]:：]+", cleaned)
    return [t.strip() for t in tokens if len(t.strip()) >= 2]


def analyze_allergens(
    ocr_result: OCRResult,
    user_allergens: list[str],
    barcode: Optional[str] = None,
    cross_check_info: Optional[CrossCheckInfo] = None,
) -> AnalyzeResponse:
    """
    팀원 1의 OCRResult와 사용자 알레르기 설정을 받아 최종 AnalyzeResponse를 반환합니다.
    """
    data = load_allergen_dictionary()
    allergen_map: dict[str, list[str]] = data.get("allergens", {})
    caution_keywords: list[str] = data.get("cautionKeywords", [])

    user_set = set(user_allergens or [])
    detected: list[DetectedAllergen] = []
    caution_notices: list[str] = []

    # 1. 줄(Block) 단위 검사로 좌표(bbox)와 출처(원재료 vs 함유표시 vs 교차오염) 분류
    for block in ocr_result.blocks:
        line = block.text
        is_caution_line = any(kw in line for kw in caution_keywords)
        if is_caution_line:
            caution_notices.append(line)
            continue

        is_notice_line = "함유" in line
        source_type = "label_notice" if is_notice_line else "ocr"

        for std_allergen, synonyms in allergen_map.items():
            for syn in synonyms:
                if syn in line:
                    detected.append(
                        DetectedAllergen(
                            allergen=std_allergen,
                            matchedText=syn,
                            source=source_type,
                            userAllergic=(std_allergen in user_set),
                            similarity=100.0,
                            bbox=block.bbox,
                        )
                    )
                    break
                else:
                    # TODO [팀원 2 - 2주차]: RapidFuzz partial_ratio를 활용한 OCR 오인식 보정 정교화
                    score = fuzz.partial_ratio(syn, line)
                    if len(syn) >= 3 and score >= 88.0:
                        detected.append(
                            DetectedAllergen(
                                allergen=std_allergen,
                                matchedText=syn,
                                source=source_type,
                                userAllergic=(std_allergen in user_set),
                                similarity=round(score, 1),
                                bbox=block.bbox,
                            )
                        )
                        break

    # 중복 알레르기 제거 (사용자 알레르기 여부 및 첫 bbox 유지)
    unique_detected: dict[str, DetectedAllergen] = {}
    for item in detected:
        if item.allergen not in unique_detected:
            unique_detected[item.allergen] = item

    final_detected = list(unique_detected.values())
    ingredients = parse_ingredients(ocr_result.fullText)

    # 2. 4단계 판정 로직 (DANGER / CAUTION / SAFE / UNCERTAIN)
    has_user_danger = any(d.userAllergic for d in final_detected)

    has_user_caution = False
    for notice in caution_notices:
        for user_alg in user_set:
            synonyms = allergen_map.get(user_alg, [user_alg])
            if any(syn in notice for syn in synonyms):
                has_user_caution = True
                break

    if has_user_danger:
        verdict = "DANGER"
    elif has_user_caution:
        verdict = "CAUTION"
    elif ocr_result.avgConfidence < settings.ocr_confidence_threshold or not ocr_result.fullText.strip():
        verdict = "UNCERTAIN"
    else:
        verdict = "SAFE"

    return AnalyzeResponse(
        requestId=f"req_{uuid.uuid4().hex[:8]}",
        verdict=verdict,
        confidence=ocr_result.avgConfidence,
        ocrText=ocr_result.fullText,
        imageWidth=ocr_result.imageWidth,
        imageHeight=ocr_result.imageHeight,
        ingredients=ingredients[:30],
        detected=final_detected,
        cautionNotices=caution_notices,
        crossCheck=cross_check_info or CrossCheckInfo(used=False),
    )
