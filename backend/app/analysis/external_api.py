"""
[팀원 2] 외부 식품 데이터 API 연동 모듈
1) 공공데이터포털 - HACCP 제품이미지 및 포장지표기정보 API (주력)
2) Open Food Facts API (해외 제품 및 바코드 보완)
"""
from typing import Optional
import httpx
from app.config import settings


async def fetch_product_by_barcode(barcode: str) -> Optional[dict]:
    """
    바코드로 제품 원재료 및 알레르기 정보를 조회합니다.
    TODO [팀원 2 - 3주차]: HACCP API 연동 및 SQLite 캐시 우선 조회 구현
    """
    # Open Food Facts 기본 조회 예시 (커스텀 User-Agent 필수)
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}"
    params = {"fields": "product_name,ingredients_text,allergens_tags,traces_tags"}
    headers = {"User-Agent": settings.openfoodfacts_user_agent}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1:
                    product = data.get("product", {})
                    return {
                        "barcode": barcode,
                        "provider": "OpenFoodFacts",
                        "productName": product.get("product_name", ""),
                        "ingredientsText": product.get("ingredients_text", ""),
                        "allergensTags": product.get("allergens_tags", []),
                        "tracesTags": product.get("traces_tags", []),
                    }
    except Exception as e:
        print(f"[WARN] 외부 바코드 API 조회 실패 ({barcode}): {e}")

    return None
