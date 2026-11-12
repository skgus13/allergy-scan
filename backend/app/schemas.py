from typing import Literal, Optional
from pydantic import BaseModel, Field


# ============================================================
# [데이터 포맷 합의 1] 팀원 1(OCR) -> 팀원 2(분석)
# ============================================================
class OCRBlock(BaseModel):
    text: str = Field(..., description="인식된 한 줄/블록 문자열")
    bbox: list[int] = Field(..., description="[x_min, y_min, x_max, y_max] 정수 좌표")
    polygon: Optional[list[list[int]]] = Field(default=None, description="4점 다각형 좌표")
    confidence: float = Field(..., ge=0.0, le=1.0, description="블록 인식 신뢰도")


class OCRResult(BaseModel):
    fullText: str = Field(..., description="줄바꿈으로 합쳐진 전체 인식 텍스트")
    avgConfidence: float = Field(..., ge=0.0, le=1.0, description="전체 평균 신뢰도")
    imageWidth: int = Field(default=0, description="전처리된 이미지 가로 크기(px)")
    imageHeight: int = Field(default=0, description="전처리된 이미지 세로 크기(px)")
    blocks: list[OCRBlock] = Field(default_factory=list, description="줄/블록 단위 인식 리스트")


# ============================================================
# [데이터 포맷 합의 2] 팀원 2(분석) -> 팀원 3(웹/서버)
# ============================================================
class DetectedAllergen(BaseModel):
    allergen: str = Field(..., description="표준 알레르기 19종 항목명 (예: 우유, 땅콩)")
    matchedText: str = Field(..., description="실제 텍스트에서 매칭된 원재료/표기 문자열")
    source: Literal["ocr", "label_notice", "barcode_api"] = Field(
        default="ocr", description="감지 출처 (원재료명 / 함유 표시란 / 바코드 API)"
    )
    userAllergic: bool = Field(..., description="사용자가 설정한 알레르기 여부")
    similarity: float = Field(default=100.0, description="RapidFuzz 매칭 유사도 점수(0~100)")
    bbox: Optional[list[int]] = Field(default=None, description="원본 이미지 강조용 [x_min, y_min, x_max, y_max]")


class CrossCheckInfo(BaseModel):
    used: bool = False
    provider: Optional[str] = None
    agrees: Optional[bool] = None
    officialAllergens: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    requestId: str
    verdict: Literal["DANGER", "CAUTION", "SAFE", "UNCERTAIN"]
    confidence: float
    ocrText: str
    imageWidth: int = 0
    imageHeight: int = 0
    ingredients: list[str] = Field(default_factory=list)
    detected: list[DetectedAllergen] = Field(default_factory=list)
    cautionNotices: list[str] = Field(default_factory=list)
    crossCheck: CrossCheckInfo = Field(default_factory=CrossCheckInfo)


class UserAllergensUpdateRequest(BaseModel):
    allergens: list[str] = Field(..., description="사용자 알레르기 표준 항목 목록, 예: ['우유', '땅콩']")
    customAllergens: list[str] = Field(default_factory=list, description="기타 사용자 직접 입력 알레르기")
