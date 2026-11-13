# 성분표 알레르기 분석 웹 서비스 (AllergyScan)

웹사이트(Frontend + Backend) 기반으로 식품 성분표 사진 촬영(및 바코드 스캔), **PaddleOCR** 텍스트/좌표 추출, **RapidFuzz + 공공데이터(HACCP/Open Food Facts)** 기반 알레르기 분석 및 시각화를 수행하는 프로젝트입니다.

> **주의사항**: 본 서비스의 분석 결과는 참고용이며, 최종 판단은 반드시 제품 포장지 원문을 확인해야 합니다.

---

## 문서 바로가기
- 📄 **[API 명세서 (외부 API & 자체 백엔드 API)](./docs/API_SPEC.md)**
- 🤝 **[1주차 필수 합의: 팀원 간 JSON 데이터 포맷 정의서](./docs/DATA_CONTRACTS.md)**

---

## 프로젝트 개요 및 기술 스택

| 구분 | 사용 기술 | 담당 역할 |
| :--- | :--- | :--- |
| **Frontend** | React (Vite), HTML/CSS | 사용자 웹 화면(UI/UX), 카메라 연동, Bounding Box 시각화 |
| **Backend** | Python, FastAPI | 사진 업로드, 모듈(OCR/분석) 연결 및 REST API 제공 |
| **Image & OCR** | OpenCV, PaddleOCR (PP-OCRv5) | 이미지 전처리, 한국어/영어 텍스트 및 좌표(Bounding Box) 추출 |
| **Analysis** | Python, RapidFuzz | 문자열 유사도 분석, 알레르기 19종 동의어 매칭 |
| **Database** | SQLite (SQLAlchemy) | 사용자 알레르기 설정, 바코드 캐시 및 검사 기록 저장 |
| **External API** | HACCP 포장지표기정보 API, 식품안전나라, Open Food Facts | 바코드/품목보고번호 기반 공식 원재료 및 알레르기 교차 확인 |

---

## 폴더 구조 (Directory Structure)

```text
allergy-scan/
├── docs/
│   ├── API_SPEC.md              # 외부 API 및 자체 백엔드 API 상세 명세서
│   └── DATA_CONTRACTS.md        # 팀원 1(OCR) ↔ 팀원 2(분석) ↔ 팀원 3(웹) JSON 데이터 포맷
├── sample_images/               # 테스트용 성분표 이미지 보관 폴더 (3~5장 확보용)
├── backend/                     # FastAPI 백엔드 및 OCR/분석 모듈
│   ├── .env.example             # 환경변수 템플릿 (공공데이터 API 키 등)
│   ├── requirements.txt         # Python 패키지 의존성 목록
│   └── app/
│       ├── main.py              # FastAPI 엔트리포인트
│       ├── config.py            # 환경변수 및 설정 로드
│       ├── schemas.py           # Pydantic 공통 요청/응답 모델
│       ├── api/
│       │   └── v1.py            # /api/v1/* 엔드포인트 라우터 (팀원 3)
│       ├── db/
│       │   └── database.py      # SQLite 테이블(User, Allergy, History, ProductCache) (팀원 3)
│       ├── ocr/                 # [팀원 1] 이미지 전처리 & PaddleOCR 모듈
│       │   ├── preprocessor.py  # OpenCV 리사이즈, 그레이스케일, 대비/기울기 보정
│       │   └── engine.py        # PaddleOCR 싱글톤 로드 및 텍스트/좌표/신뢰도 추출
│       └── analysis/            # [팀원 2] 알레르기 분석 & 외부 API 교차 검증 모듈
│           ├── allergens_ko.json# 국내 알레르기 의무 표시 19종 및 동의어 사전
│           ├── matcher.py       # OCR 후처리, 성분 분리, RapidFuzz 유사도 매칭 및 4단계 판정
│           └── external_api.py  # HACCP 공공데이터 & Open Food Facts 바코드 조회
└── frontend/                    # [팀원 3] React (Vite) 프론트엔드
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx
        ├── api/client.js        # FastAPI 백엔드 통신 클라이언트
        ├── components/          # BoundingBoxOverlay 등 시각화 컴포넌트
        └── pages/               # Home(설정), Scan(촬영/업로드), Result(결과), History(기록)
```

## Git 브랜치 전략 및 시작 가이드

### 브랜치 구조
- `main`: 배포 및 최종 통합 브랜치 (직접 Push 지양, PR을 통해 병합)
- `ocr`: 팀원 1 작업 브랜치 (`backend/app/ocr/` 중심)
- `analysis`: 팀원 2 작업 브랜치 (`backend/app/analysis/` 중심)
- `frontend`: 팀원 3 작업 브랜치 (`frontend/` 및 `backend/app/api/`, `db/` 중심)

### 로컬 실행 방법

#### 1) Backend (FastAPI)
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

uvicorn app.main:app --reload --port 8000
```
- 서버 실행 후 Swagger UI 문서: `http://localhost:8000/docs`

#### 2) Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
- 브라우저 접속: `http://localhost:5173`
