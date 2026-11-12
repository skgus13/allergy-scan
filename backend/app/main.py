from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import router as v1_router
from app.db.database import init_db

app = FastAPI(
    title="AllergyScan API",
    description="성분표 사진 OCR 및 알레르기 19종 분석 백엔드 API",
    version="0.1.0",
)

# React(Vite) 개발 서버 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AllergyScan Backend"}


app.include_router(v1_router, prefix="/api/v1")
