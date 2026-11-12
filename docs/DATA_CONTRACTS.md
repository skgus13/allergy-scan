# 🤝 팀원 간 데이터 포맷 합의서 (Data Contracts)

1주차 필수 체크리스트인 **팀원 1(OCR) → 팀원 2(분석) → 팀원 3(웹/서버)** 간의 인터페이스 JSON 포맷 정의입니다.
코드에서는 `backend/app/schemas.py`에 Pydantic 모델로 정의되어 있습니다.

---

## 1. [데이터 포맷 합의 1] 팀원 1 (OCR) → 팀원 2 (분석)

팀원 1의 OCR 함수(`extract_ocr_data(image_bytes)`)가 반환하고 팀원 2의 분석 함수가 입력으로 받는 구조입니다.

```json
{
  "fullText": "원재료명: 밀가루(밀:미국산), 설탕, 전지분유(우유)\n대두, 땅콩 함유\n이 제품은 메밀을 사용한 제품과 같은 제조시설에서 제조하고 있습니다.",
  "avgConfidence": 0.91,
  "imageWidth": 1200,
  "imageHeight": 900,
  "blocks": [
    {
      "text": "원재료명: 밀가루(밀:미국산), 설탕, 전지분유(우유)",
      "bbox": [100, 45, 680, 80],
      "polygon": [[100, 45], [680, 45], [680, 80], [100, 80]],
      "confidence": 0.94
    },
    {
      "text": "대두, 땅콩 함유",
      "bbox": [100, 95, 320, 125],
      "polygon": [[100, 95], [320, 95], [320, 125], [100, 125]],
      "confidence": 0.89
    },
    {
      "text": "이 제품은 메밀을 사용한 제품과 같은 제조시설에서 제조하고 있습니다.",
      "bbox": [100, 140, 850, 170],
      "polygon": [[100, 140], [850, 140], [850, 170], [100, 170]],
      "confidence": 0.90
    }
  ]
}
```

### 필드 설명
- `fullText` (`str`): 줄바꿈(`\n`)으로 합쳐진 전체 인식 텍스트
- `avgConfidence` (`float`): 전체 블록의 평균 신뢰도 (`0.0` ~ `1.0`). 기준치(예: `0.65`) 미만이면 `UNCERTAIN` 판정에 활용
- `imageWidth`, `imageHeight` (`int`): 전처리 후 OCR이 수행된 기준 이미지 해상도 (프론트엔드에서 Bounding Box 비율 계산 시 사용)
- `blocks` (`list`): 줄/단어 단위 인식 결과 리스트
  - `text` (`str`): 인식된 문자열
  - `bbox` (`[x_min, y_min, x_max, y_max]`): 사각형 좌표 (정수 픽셀)
  - `polygon` (`[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]`): 4점 다각형 좌표 (선택)
  - `confidence` (`float`): 해당 줄 신뢰도 (`0.0` ~ `1.0`)

---

## 2. [데이터 포맷 합의 2] 팀원 2 (분석) → 팀원 3 (웹/서버)

팀원 2의 분석 함수(`analyze_allergens(ocr_result, user_allergens, barcode)`)가 반환하고, FastAPI가 React 프론트엔드로 최종 응답하는 JSON 구조입니다.

```json
{
  "requestId": "req_20261111_a1b2c3",
  "verdict": "DANGER",
  "confidence": 0.91,
  "ocrText": "원재료명: 밀가루(밀:미국산), 설탕, 전지분유(우유) ... 대두, 땅콩 함유",
  "imageWidth": 1200,
  "imageHeight": 900,
  "ingredients": ["밀가루", "설탕", "전지분유"],
  "detected": [
    {
      "allergen": "밀",
      "matchedText": "밀가루",
      "source": "ocr",
      "userAllergic": false,
      "similarity": 100.0,
      "bbox": [100, 45, 680, 80]
    },
    {
      "allergen": "우유",
      "matchedText": "전지분유",
      "source": "ocr",
      "userAllergic": true,
      "similarity": 100.0,
      "bbox": [100, 45, 680, 80]
    },
    {
      "allergen": "땅콩",
      "matchedText": "땅콩 함유",
      "source": "label_notice",
      "userAllergic": true,
      "similarity": 100.0,
      "bbox": [100, 95, 320, 125]
    }
  ],
  "cautionNotices": [
    "이 제품은 메밀을 사용한 제품과 같은 제조시설에서 제조하고 있습니다."
  ],
  "crossCheck": {
    "used": true,
    "provider": "HACCP",
    "agrees": true,
    "officialAllergens": ["밀", "우유", "대두", "땅콩"]
  }
}
```

### 4단계 판정 (`verdict`) 기준
| 코드 | 한글 의미 | 판정 조건 |
| :--- | :--- | :--- |
| `DANGER` | **섭취 주의** | `detected` 중 `userAllergic == true`인 성분이 원재료 또는 함유 표시란에서 1개 이상 발견됨 |
| `CAUTION` | **혼입 가능** | 직접 함유는 없으나, 교차 오염 문구(“같은 제조시설”, `traces_tags`)에 사용자의 알레르기 성분이 포함됨 |
| `SAFE` | **안전** | OCR 신뢰도가 충분(`>= 0.65`)하며 사용자 알레르기 성분이 발견되지 않음 |
| `UNCERTAIN` | **확인 필요** | OCR 평균 신뢰도가 낮거나(`avgConfidence < 0.65`) 원재료 텍스트가 거의 추출되지 않아 재촬영이 필요함 |
