# 🔍 성분표 알레르기 분석 웹 서비스 (AllergyScan)

웹사이트(Frontend + Backend) 기반으로 식품 성분표 사진 촬영(및 바코드 스캔), **PaddleOCR** 텍스트/좌표 추출, **RapidFuzz + 공공데이터(HACCP/Open Food Facts)** 기반 알레르기 분석 및 시각화를 수행하는 프로젝트입니다.

> ⚠️ **주의사항**: 본 서비스의 분석 결과는 참고용이며, 최종 판단은 반드시 제품 포장지 원문을 확인해야 합니다.

---

## 📚 문서 바로가기
- 📄 **[API 명세서 (외부 API & 자체 백엔드 API)](./docs/API_SPEC.md)**
- 🤝 **[1주차 필수 합의: 팀원 간 JSON 데이터 포맷 정의서](./docs/DATA_CONTRACTS.md)**

---

## 🛠️ 1. 프로젝트 개요 및 기술 스택

| 구분 | 사용 기술 | 담당 역할 |
| :--- | :--- | :--- |
| **Frontend** | React (Vite), HTML/CSS | 사용자 웹 화면(UI/UX), 카메라 연동, Bounding Box 시각화 |
| **Backend** | Python, FastAPI | 사진 업로드, 모듈(OCR/분석) 연결 및 REST API 제공 |
| **Image & OCR** | OpenCV, PaddleOCR (PP-OCRv5) | 이미지 전처리, 한국어/영어 텍스트 및 좌표(Bounding Box) 추출 |
| **Analysis** | Python, RapidFuzz | 문자열 유사도 분석, 알레르기 19종 동의어 매칭 |
| **Database** | SQLite (SQLAlchemy) | 사용자 알레르기 설정, 바코드 캐시 및 검사 기록 저장 |
| **External API** | HACCP 포장지표기정보 API, 식품안전나라, Open Food Facts | 바코드/품목보고번호 기반 공식 원재료 및 알레르기 교차 확인 |

---

## 📂 폴더 구조 (Directory Structure)

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

---

## 👥 2. 팀원별 역할 분담 및 세부 업무

### 🧑‍💻 팀원 1. 이미지 처리 및 OCR 담당 (`backend/app/ocr/`)
> **목표**: 업로드된 성분표 이미지에서 텍스트, 좌표, 신뢰도를 정확히 추출하여 JSON으로 반환
- [ ] **환경 구축**: Python, OpenCV, PaddleOCR 설치 및 기본 세팅
- [ ] **이미지 입력**: 웹에서 업로드된 이미지 파일 읽기
- [ ] **이미지 전처리**: 크기 조정(긴 변 1,500px 권장), 그레이스케일 변환, 대비 향상
- [ ] **이미지 보정**: 기울기 회전 및 원근 왜곡 보정
- [ ] **OCR 인식**: PaddleOCR 한국어/영어 텍스트 인식 모델(`lang="korean"`) 적용
- [ ] **데이터 추출**: 인식된 텍스트별 Bounding Box(좌표) 및 신뢰도(Confidence) 추출
- [ ] **모듈화**: FastAPI 서버에서 바로 호출할 수 있도록 함수화 및 JSON 반환
- [ ] **성능 테스트**: 다양한 악조건(빛 반사, 작은 글씨, 기울어짐) 이미지 인식률 테스트

### 🧑‍🔬 팀원 2. 알레르기 분석 및 데이터베이스 담당 (`backend/app/analysis/`)
> **목표**: OCR 텍스트를 분석해 사용자 등록 알레르기 성분과 대조하고 최종 판정 결과를 도출
- [ ] **OCR 후처리**: 분리된 줄바꿈 연결 및 불필요한 특수문자 제거
- [ ] **데이터 조사**: 국내 알레르기 표시 대상 19개 표준 항목 정리
- [ ] **사전 구축**: 알레르기 성분별 파생 원료명(동의어) JSON 데이터(`allergens_ko.json`) 생성
- [ ] **성분 분리**: OCR 전체 텍스트에서 개별 원재료 단위로 추출 및 분리
- [ ] **성분 정규화**: 다양한 원재료명을 표준 알레르기 항목으로 변환
- [ ] **유사도 매칭**: RapidFuzz를 활용한 OCR 오인식 및 오탈자 보정 매칭
- [ ] **알레르기 비교**: 사용자가 설정한 알레르기와 추출된 위험 성분 대조
- [ ] **외부 API 연동**: HACCP 공공데이터 및 Open Food Facts 바코드 조회, 교차 혼입 정보(traces) 확인
- [ ] **판정 로직 구현**: 4단계 판정 도출 (`DANGER` 섭취 주의 / `CAUTION` 혼입 가능 / `SAFE` 안전 / `UNCERTAIN` 확인 필요)
- [ ] **모듈화**: FastAPI에서 호출 가능하도록 분석 결과 JSON 반환 구조 세팅

### 🧑‍🎨 팀원 3. 웹사이트 및 서버 담당 (통합) (`frontend/`, `backend/app/api/`, `backend/app/db/`)
> **목표**: 사용자가 접속할 React 웹페이지를 만들고, FastAPI 서버를 통해 모든 모듈을 하나로 연결
- [ ] **프론트 환경 구축**: React 프로젝트(Vite) 생성 및 기본 UI/UX 설계
- [ ] **백엔드 환경 구축**: Python FastAPI 프로젝트 생성 및 초기 라우팅 세팅
- [ ] **DB 구축**: SQLite 초기 테이블(User, Allergy, History 등) 설계 및 세팅
- [ ] **메인 및 설정 페이지**: 서비스 소개, 사용자 알레르기 성분 중복 선택 및 저장 화면 구현
- [ ] **업로드 및 촬영 페이지**: 브라우저 카메라 연동 및 이미지 업로드 폼 구현
- [ ] **API 연동 1 (입력)**: React에서 사진을 FastAPI로 전송하고 OCR/분석 모듈 호출
- [ ] **API 연동 2 (출력)**: 분석 완료된 JSON 데이터를 React로 받아오기
- [ ] **결과 페이지 (시각화)**: 원본 이미지 위에 위험 성분 좌표(Bounding Box) 강조 표시
- [ ] **기록 관리**: 이전 검사 내역 저장 및 상세 조회 페이지 구현
- [ ] **전체 통합 테스트**: 사진 업로드부터 분석 결과 출력까지의 End-to-End 테스트

---

## 🗓️ 3. 4주 개발 일정

| 주차 | 주차별 공통 목표 | 팀원 1 (OCR) | 팀원 2 (분석) | 팀원 3 (웹/서버) |
| :---: | :--- | :--- | :--- | :--- |
| **1주차** | **기획 및 환경 구축** | PaddleOCR 설치 및 기본 샘플 인식 테스트 | 알레르기 데이터 조사 및 동의어 사전(JSON) 초안 작성 | React & FastAPI 초기 프로젝트 생성, 전체 API 명세 작성 |
| **2주차** | **핵심 기능 개별 구현** | OpenCV 전처리 로직 및 OCR 후처리(정제) 구현 | 텍스트 분리, 정규화 및 RapidFuzz 유사도 판정 구현 | 웹 UI(설정/업로드 화면) 및 SQLite DB 테이블 구현 |
| **3주차** | **모듈 통합 및 연결** | FastAPI 서버에 OCR 모듈 연동 및 좌표 데이터 전달 | 분석 모듈 서버 연동 및 공공데이터/Open Food Facts API 연동 | 프론트-백엔드 API 통신 연결, 결과 화면(이미지 강조) 구현 |
| **4주차** | **테스트 및 고도화** | 흐릿한 이미지 등 악조건 인식률 개선 및 디버깅 | 매칭 오류 보완 및 판정 로직 정확도 최종 점검 | 검사 기록(History) 조회 구현, UI 및 반응형 웹 디자인 개선 |

---

## ✅ 4. 1주차 필수 합의 및 세팅 체크리스트

본격적인 코딩 전, 첫 3일 이내에 팀원들과 반드시 확정해야 하는 항목들입니다.
- [x] **GitHub 세팅**: Repository 생성, 브랜치 전략(`main` / `frontend` / `ocr` / `analysis`) 및 폴더 구조 통일
- [x] **데이터 포맷 합의 1**: 팀원 1(OCR)이 팀원 2(분석)에게 넘겨줄 JSON 데이터 구조 초안 확정 (`docs/DATA_CONTRACTS.md` 참고)
- [x] **데이터 포맷 합의 2**: 팀원 2(분석)가 팀원 3(웹)에게 넘겨줄 최종 결과 JSON 구조 초안 확정 (`docs/DATA_CONTRACTS.md` 참고)
- [ ] **테스트 셋 확보**: 한글/영문, 크기, 빛 반사 등이 다른 테스트용 성분표 이미지 3~5장 사전 확보 (`sample_images/` 폴더에 추가)

---

## 🌿 5. Git 브랜치 전략 및 시작 가이드

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
