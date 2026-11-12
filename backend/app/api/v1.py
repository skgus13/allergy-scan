"""
[팀원 3] 자체 백엔드 REST API 라우터 (/api/v1/*)
명세서의 4대 핵심 엔드포인트 + 검사 기록 조회 제공:
- POST /api/v1/analyze
- GET  /api/v1/products/{barcode}
- GET  /api/v1/allergens
- GET/PUT /api/v1/users/me/allergens
- GET  /api/v1/history
"""
import json
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.analysis.external_api import fetch_product_by_barcode
from app.analysis.matcher import analyze_allergens, load_allergen_dictionary
from app.db.database import (
    get_user_allergens,
    list_scan_history,
    save_scan_history,
    save_user_allergens,
)
from app.ocr.engine import extract_ocr_data
from app.schemas import AnalyzeResponse, CrossCheckInfo, UserAllergensUpdateRequest

router = APIRouter(tags=["AllergyScan v1"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_ingredient_label(
    image: UploadFile = File(..., description="성분표 사진 (jpg/png, 10MB 이하)"),
    barcode: Optional[str] = Form(default=None, description="선택: 바코드 문자열"),
    userAllergens: Optional[str] = Form(
        default=None, description="선택: JSON 배열 문자열(예: '[\"우유\",\"땅콩\"]') 또는 콤마 구분 문자열"
    ),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_IMAGE", "message": "이미지 파일(jpg/png)만 업로드 가능합니다."},
        )

    image_bytes = await image.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_IMAGE", "message": "이미지 크기는 10MB 이하여야 합니다."},
        )

    # 1. 사용자 알레르기 목록 파악 (요청 파라미터 우선, 없으면 DB 저장 목록 사용)
    parsed_allergens: list[str] = []
    if userAllergens:
        try:
            loaded = json.loads(userAllergens)
            if isinstance(loaded, list):
                parsed_allergens = [str(x).strip() for x in loaded if str(x).strip()]
        except Exception:
            parsed_allergens = [x.strip() for x in userAllergens.split(",") if x.strip()]
    else:
        saved = get_user_allergens()
        parsed_allergens = saved.get("allergens", []) + saved.get("customAllergens", [])

    # 2. [팀원 1 모듈 호출] 이미지 전처리 및 PaddleOCR 텍스트·좌표 추출
    try:
        ocr_result = extract_ocr_data(image_bytes)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail={"code": "INVALID_IMAGE", "message": str(ve)})
    except Exception as e:
        raise HTTPException(status_code=502, detail={"code": "UPSTREAM_ERROR", "message": f"OCR 처리 오류: {e}"})

    # 3. 선택적 바코드 교차 검증
    cross_check = CrossCheckInfo(used=False)
    if barcode:
        ext_data = await fetch_product_by_barcode(barcode)
        if ext_data:
            cross_check = CrossCheckInfo(
                used=True,
                provider=ext_data.get("provider"),
                agrees=True,
                officialAllergens=ext_data.get("allergensTags", []),
            )

    # 4. [팀원 2 모듈 호출] 알레르기 사전 매칭 및 4단계 판정
    analysis_response = analyze_allergens(
        ocr_result=ocr_result,
        user_allergens=parsed_allergens,
        barcode=barcode,
        cross_check_info=cross_check,
    )

    # 5. DB에 검사 이력 저장
    save_scan_history(analysis_response.model_dump())

    return analysis_response


@router.get("/products/{barcode}")
async def get_product_by_barcode(barcode: str):
    product = await fetch_product_by_barcode(barcode)
    if not product:
        raise HTTPException(
            status_code=404,
            detail={"code": "PRODUCT_NOT_FOUND", "message": "해당 바코드의 제품 정보를 찾을 수 없습니다."},
        )
    return product


@router.get("/allergens")
def get_supported_allergens():
    """국내 의무 표시 19종 알레르기 표준 항목 및 동의어 사전을 반환합니다."""
    return load_allergen_dictionary()


@router.get("/users/me/allergens")
def get_my_allergens():
    return get_user_allergens()


@router.put("/users/me/allergens")
def update_my_allergens(payload: UserAllergensUpdateRequest):
    return save_user_allergens(payload.allergens, payload.customAllergens)


@router.get("/history")
def get_history(limit: int = 20):
    return {"items": list_scan_history(limit=limit)}
