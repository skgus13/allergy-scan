# 성분표 알레르기 분석 앱 API 명세서

## 1. 개요

### 처리 흐름
1. 앱/웹에서 성분표 사진 촬영 (선택: 바코드 함께 스캔)
2. 자체 서버의 **PaddleOCR**로 텍스트 및 좌표(Bounding Box) 추출
3. “원재료명” 영역과 “○○ 함유” 알레르기 표시란을 파싱해 성분 목록 생성
4. 성분 목록을 알레르기 사전(국내 표시대상 19종 + 동의어)과 매칭 (**RapidFuzz** 유사도 보정 포함)
5. 바코드·품목보고번호가 있으면 공공데이터 API / Open Food Facts로 공식 알레르기 정보를 교차 확인
6. 결과(`DANGER` / `CAUTION` / `SAFE` / `UNCERTAIN`) 및 좌표 정보를 클라이언트에 반환

### 용어 정리
| 용어 | 뜻 |
| :--- | :--- |
| **API** | 다른 서비스의 기능·데이터를 프로그램에서 불러 쓰는 통로 |
| **인증키(API Key)** | API를 쓸 수 있도록 발급받는 비밀번호 같은 문자열 |
| **호출 제한(Rate limit / 트래픽)** | 일·분·월 단위로 허용되는 최대 호출 횟수 |
| **OCR** | 사진 속 글자를 텍스트로 바꾸는 기술 |

---

## 2. 외부 API 요약

OCR은 자체 서버에서 실행하는 **PaddleOCR**을 쓰고, 정확도가 부족할 때만 **Google Cloud Vision**을 대안으로 둔다. 식품 데이터는 **HACCP 포장지표기정보 API**를 주력으로 쓴다.

| API | 용도 | 제공처 | 인증 | 무료 한도 / 호출 제한 | 비용 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PaddleOCR (PP-OCRv5)** | 성분표 사진 → 텍스트 | PaddlePaddle (오픈소스, Apache-2.0) | 없음 (자체 서버에서 실행) | 호출 제한 없음, 서버 CPU/GPU 성능이 한도 | 무료 (서버 비용만 발생) |
| **Google Cloud Vision** | 성분표 사진 → 텍스트 (대안) | Google Cloud | API Key / 서비스 계정 | 기능별 월 1,000유닛 무료 | 1,001~500만 유닛: 1,000유닛당 $1.50 |
| **HACCP 제품이미지 및 포장지표기정보** | 제품별 원재료·알레르기·바코드 | 한국식품안전관리인증원 (공공데이터포털) | ServiceKey | 개발계정 일 10,000회, 운영계정은 활용사례 등록 시 증설 | 무료 |
| **식품안전나라 Open API** | 품목보고번호별 원재료 | 식품의약품안전처 | 식품안전나라 인증키 | 기관 정책에 따라 상이 (확인 필요) | 무료 |
| **Open Food Facts** | 바코드 → 성분·알레르기 (해외 제품 보완) | Open Food Facts | 키 없음, 커스텀 User-Agent 필수 | IP당 제품 조회 분당 100회, 검색 분당 10회 | 무료 |

---

## 3. OCR API 상세

PaddleOCR은 외부 API가 아니라 자체 서버에 설치해 쓰는 라이브러리다. 인증키·호출 제한·요금이 없는 대신 서버 성능과 인식 정확도를 직접 책임져야 한다. 성분표 인식률이 부족하면 Google Vision `DOCUMENT_TEXT_DETECTION`을 대안으로 둔다.

### 3.1 PaddleOCR (자체 서버 실행)

| 항목 | 내용 |
| :--- | :--- |
| **설치** | `pip install paddlepaddle paddleocr` (GPU 서버는 `paddlepaddle-gpu`) |
| **한국어 모델** | `lang="korean"` → `korean_PP-OCRv5_mobile_rec` (한국어·영어), 공식 한국어 데이터셋 정확도 88.0% |
| **라이선스** | Apache-2.0, 상업적 사용 가능 |
| **호출 제한** | 없음. 처리량은 서버 CPU/GPU와 메모리에 따라 결정 |
| **비용** | 라이브러리 무료, 서버 호스팅 비용만 발생 |
| **주의** | 모델 로딩에 수 초가 걸리므로 서버 시작 시 1번만 로드하고 재사용. 작은 글씨·곡면 포장은 인식률이 떨어질 수 있어 실제 성분표 사진으로 사전 테스트 필수 |

#### 사용 예시 (Python, FastAPI 서버 내부):
```python
from paddleocr import PaddleOCR

# 서버 시작 시 1회만 생성
ocr = PaddleOCR(
    lang="korean",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)

def extract_text(image_path: str) -> tuple[str, float]:
    res = ocr.predict(image_path)[0]
    texts, scores = res["rec_texts"], res["rec_scores"]
    avg = sum(scores) / len(scores) if scores else 0.0
    return "\n".join(texts), avg
```
- 결과의 `rec_texts`는 줄 단위 인식 텍스트, `rec_scores`는 줄별 신뢰도, `rec_boxes`는 줄 좌표다.
- 평균 신뢰도가 낮으면 `UNCERTAIN` 판정과 재촬영 안내에 쓴다.
- 결과 필드 구조는 버전마다 달라질 수 있으니 `save_to_json()` 출력으로 한 번 확인한다.

### 3.2 Google Cloud Vision (대안)

| 항목 | 내용 |
| :--- | :--- |
| **메서드 / URL** | `POST https://vision.googleapis.com/v1/images:annotate?key={API_KEY}` |
| **기능** | `DOCUMENT_TEXT_DETECTION` (촘촘한 글자용, 성분표에 적합) |
| **무료 한도** | 기능별 월 1,000유닛 (이미지 1장 × 기능 1개 = 1유닛) |
| **요금** | 1,001~5,000,000유닛: 1,000유닛당 $1.50 |
| **주의** | 한 이미지에 기능을 2개 쓰면 2유닛 차감 |

#### 요청 예시:
```json
{
  "requests": [{
    "image": { "content": "<base64>" },
    "features": [{ "type": "DOCUMENT_TEXT_DETECTION" }],
    "imageContext": { "languageHints": ["ko"] }
  }]
}
```
응답의 `responses[0].fullTextAnnotation.text`가 전체 텍스트다.

---

## 4. 식품 데이터 API 상세

사진 OCR만으로는 오인식 위험이 있으므로, 바코드나 제품명이 확인되면 공식 데이터로 알레르기 정보를 교차 확인한다.

### 4.1 HACCP 제품이미지 및 포장지표기정보 (주력)

| 항목 | 내용 |
| :--- | :--- |
| **메서드 / URL** | `GET https://apis.data.go.kr/B553748/CertImgListServiceV3/...` (세부 경로는 활용신청 후 참고문서 확인) |
| **제공 항목** | 품목보고번호, 제품명, 원재료, 알레르기유발물질, 영양성분, 바코드, 제조원, 제품이미지URL 등 |
| **트래픽** | 개발계정 일 10,000회 · 운영계정은 활용사례 등록 시 증설 신청 |
| **승인** | 개발·운영 모두 자동승인 |
| **범위** | HACCP 인증 제품, 2017년 이후 |
| **응답 형식** | JSON 또는 XML (`returnType`) |

#### 요청 변수
| 요청 변수 | 필수 | 예시 | 설명 |
| :--- | :---: | :--- | :--- |
| `ServiceKey` | 필수 | – | 공공데이터포털 인증키 |
| `prdlstReportNo` | 선택 | `201305230193` | 품목보고번호 |
| `prdlstNm` | 선택 | `해남에서만든반시고구마` | 제품명 |
| `allergy` | 선택 | `돼지고기, 밀 함유` | 알레르기 유발물질 |
| `manufacture` | 선택 | `해남고구마식품주식회사` | 제조원 |
| `pageNo` / `numOfRows` | 선택 | `1` / `10` | 페이지 번호 / 페이지당 건수 |
| `returnType` | 선택 | `json` | 응답 형식 |

### 4.2 공공데이터포털 공통 에러 코드

| 코드 | 메시지 | 대응 |
| :---: | :--- | :--- |
| `20` | `SERVICE_ACCESS_DENIED_ERROR` | 활용신청·승인 상태 확인 |
| `22` | `LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR` | 일일 한도 초과 → 다음 날 재시도 또는 증설 신청 |
| `23` | `LIMITED_NUMBER_OF_SERVICE_REQUESTS_PER_SECOND_EXCEEDS_ERROR` | 초당 한도 초과 → 잠시 후 재시도 |
| `30` | `SERVICE_KEY_IS_NOT_REGISTERED_ERROR` | 인증키 오타·미등록 확인 |
| `31` | `DEADLINE_HAS_EXPIRED_ERROR` | 인증키 사용 기한 갱신 |

### 4.3 식품안전나라 Open API (보조)
품목제조보고 원재료, 바코드 연계 제품정보 등을 제공한다. 호출 형식은 `http://openapi.foodsafetykorea.go.kr/api/{인증키}/{서비스ID}/json/{시작}/{끝}`이며, 공공데이터포털 안내상 트래픽은 기관 정책에 따라 다르다. 서비스ID와 1회 최대 조회 건수는 식품안전나라에서 직접 확인해야 한다.

### 4.4 Open Food Facts (해외 제품 보완)

| 항목 | 내용 |
| :--- | :--- |
| **메서드 / URL** | `GET https://world.openfoodfacts.org/api/v2/product/{바코드}?fields=product_name,ingredients_text,allergens_tags,traces_tags` |
| **인증** | 읽기는 키 불필요, 커스텀 `User-Agent` 헤더 필수 (예: `AllergyScan/1.0 (contact@example.com)`) |
| **제한** | IP당 제품 조회 분당 100회, 검색 분당 10회 |
| **테스트** | 개발 중에는 스테이징 `https://world.openfoodfacts.net` 사용 권장 |
| **주의** | 국내 제품 데이터는 적고 커뮤니티 입력이라 정확도 편차가 큼 |

---

## 5. 자체 백엔드 API 명세

앱/웹은 외부 API를 직접 부르지 않고 자체 서버만 호출한다. 인증키를 클라이언트에 넣으면 유출되고, 호출 제한도 서버에서 한곳에 모아 관리해야 하기 때문이다.

| 메서드 | 엔드포인트 | 설명 |
| :---: | :--- | :--- |
| `POST` | `/api/v1/analyze` | 성분표 사진 업로드 → 알레르기 분석 결과 반환 |
| `GET` | `/api/v1/products/{barcode}` | 바코드로 공식 원재료·알레르기 정보 조회 (캐시 우선) |
| `GET` | `/api/v1/allergens` | 지원하는 알레르기 항목·동의어 사전 조회 |
| `PUT` | `/api/v1/users/me/allergens` | 사용자 본인의 알레르기 목록 저장 |
| `GET` | `/api/v1/history` | 이전 검사 내역 목록 조회 |

### 5.1 `POST /api/v1/analyze`

- **요청**: `multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
| :--- | :--- | :---: | :--- |
| `image` | `file (jpg/png)` | 필수 | 성분표 사진, 10MB 이하로 클라이언트에서 리사이즈 |
| `barcode` | `string` | 선택 | 스캔한 바코드 (있으면 공식 데이터와 교차 확인) |
| `userAllergens` | `string[]` (JSON 문자열 또는 콤마 구분) | 선택 | 예: `["우유","땅콩"]`, 없으면 저장된 목록 사용 |

- **응답 `200 OK`**:
```json
{
  "requestId": "a1b2c3",
  "ocrText": "원재료명: 밀가루(밀:미국산), 설탕, 전지분유(우유) ... 대두, 땅콩 함유",
  "ingredients": ["밀가루", "설탕", "전지분유", "대두유"],
  "detected": [
    {
      "allergen": "밀",
      "matchedText": "밀가루",
      "source": "ocr",
      "userAllergic": false,
      "bbox": [120, 45, 210, 78]
    },
    {
      "allergen": "우유",
      "matchedText": "전지분유(우유)",
      "source": "ocr",
      "userAllergic": true,
      "bbox": [310, 45, 460, 78]
    },
    {
      "allergen": "땅콩",
      "matchedText": "땅콩 함유",
      "source": "label_notice",
      "userAllergic": true,
      "bbox": [120, 110, 240, 140]
    }
  ],
  "verdict": "DANGER",
  "crossCheck": { "used": true, "provider": "HACCP", "agrees": true },
  "confidence": 0.91
}
```
- **`verdict` 값**:
  - `DANGER`: 사용자 알레르기 포함 (섭취 주의)
  - `CAUTION`: 같은 제조시설에서 제조 문구 등 (혼입 가능)
  - `SAFE`: 감지 없음 (안전)
  - `UNCERTAIN`: OCR 신뢰도 낮음, 재촬영 권장 (확인 필요)

### 5.2 에러 응답

| HTTP | `code` | 상황 |
| :---: | :--- | :--- |
| `400` | `INVALID_IMAGE` | 형식·크기 오류 |
| `422` | `TEXT_NOT_FOUND` | 사진에서 원재료명을 찾지 못함 |
| `429` | `RATE_LIMITED` | 사용자별 호출 한도 초과 (`Retry-After` 헤더 포함) |
| `502` | `UPSTREAM_ERROR` | OCR·공공데이터 API 오류 |
| `503` | `QUOTA_EXHAUSTED` | 외부 API 일·월 한도 소진 |

---

## 6. 알레르기 유발물질 기준 데이터

국내 의무 표시 대상은 **19개 항목(세부 22개 식품)**이며, 함량과 관계없이 원재료명 근처 별도 표시란에 적어야 한다. 이 목록은 API가 아니라 서버에 직접 넣는 고정 사전(`backend/app/analysis/allergens_ko.json`)으로 관리한다.

| 표시 대상 | 매칭용 동의어·파생 원료 예시 |
| :--- | :--- |
| **알류(가금류)** | 계란, 달걀, 난백, 난황, 전란액, 메추리알 |
| **우유** | 전지분유, 탈지분유, 유청, 카제인, 버터, 치즈, 유당 |
| **메밀** | 메밀가루 |
| **땅콩** | 땅콩버터, 피넛 |
| **대두** | 대두유, 콩, 두부, 간장, 된장, 대두레시틴 |
| **밀** | 밀가루, 소맥분, 글루텐, 빵가루 |
| **고등어** | 고등어추출물 |
| **게** | 게살, 크랩 |
| **새우** | 새우분말, 새우젓 |
| **돼지고기** | 돈육, 돼지지방, 젤라틴(돈피 유래) |
| **복숭아** | 복숭아과즙 |
| **토마토** | 토마토페이스트, 케첩 |
| **아황산류** | 아황산나트륨, 메타중아황산칼륨 (최종 제품 SO₂ 10mg/kg 이상 시) |
| **호두** | 호두분태 |
| **닭고기** | 계육, 치킨스톡 |
| **쇠고기** | 우육, 소고기, 비프 |
| **오징어** | 오징어채 |
| **조개류** | 굴, 전복, 홍합, 바지락, 굴소스 |
| **잣** | 잣가루 |

---

## 7. 호출 제한 대응 전략 및 보안 주의사항

| 제한 | 대응 |
| :--- | :--- |
| **PaddleOCR 서버 처리 성능** | 모델을 서버 시작 시 1번만 로드, 요청은 작업 큐로 순차 처리, 촬영 이미지는 긴 변 1,500px 정도로 리사이즈, 같은 바코드 결과는 DB 캐시 |
| **Google Vision 대안 월 1,000유닛** | PaddleOCR 신뢰도가 낮을 때만 호출하는 보조 경로로 제한 |
| **공공데이터 일 10,000회** | 바코드·품목보고번호별 응답을 24시간 이상 캐시, 운영 전환 시 활용사례 등록 후 증설 신청 |
| **공공데이터 초당 제한(코드 23)** | 서버 큐에서 순차 처리, 실패 시 지수 백오프로 재시도 |
| **Open Food Facts 분당 10~100회** | 바코드 조회만 사용(검색 X), 서버 IP 하나에서 나가므로 서버 측 토큰 버킷 적용 |
| **사용자 남용** | 사용자당 분석 요청 분당 5회 등 자체 제한 후 429 반환 |

### 보안·법적 주의사항
1. 인증키는 서버 환경변수(`.env`)에만 저장하고 클라이언트 코드·깃허브에 절대 올리지 않는다.
2. 공공데이터 키는 URL 인코딩/디코딩 버전이 따로 있으니 호출 라이브러리에 맞는 쪽을 쓴다.
3. 결과 화면에 **“참고용이며 최종 판단은 포장지 원문을 확인”** 문구를 넣는다.
4. “같은 제조시설에서 제조” 같은 혼입 가능성 문구도 파싱해 `CAUTION`으로 처리한다.
