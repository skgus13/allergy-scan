"""
[팀원 3] SQLite 데이터베이스 초기 설정 및 테이블 스키마
- UserProfile: 사용자 알레르기 설정 저장
- ScanHistory: 이전 검사 기록 저장
- ProductCache: 바코드/품목보고번호별 외부 API 응답 24시간 캐시
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "allergy_scan.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_allergens (
            user_id TEXT PRIMARY KEY,
            allergens_json TEXT NOT NULL,
            custom_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scan_history (
            request_id TEXT PRIMARY KEY,
            verdict TEXT NOT NULL,
            confidence REAL NOT NULL,
            ocr_text TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS product_cache (
            barcode TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            cached_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def get_user_allergens(user_id: str = "default_user") -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT allergens_json, custom_json, updated_at FROM user_allergens WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return {"allergens": [], "customAllergens": [], "updatedAt": None}
    return {
        "allergens": json.loads(row["allergens_json"]),
        "customAllergens": json.loads(row["custom_json"]),
        "updatedAt": row["updated_at"],
    }


def save_user_allergens(allergens: list[str], custom: list[str], user_id: str = "default_user") -> dict:
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO user_allergens (user_id, allergens_json, custom_json, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            allergens_json = excluded.allergens_json,
            custom_json = excluded.custom_json,
            updated_at = excluded.updated_at
        """,
        (user_id, json.dumps(allergens, ensure_ascii=False), json.dumps(custom, ensure_ascii=False), now),
    )
    conn.commit()
    conn.close()
    return {"allergens": allergens, "customAllergens": custom, "updatedAt": now}


def save_scan_history(result_dict: dict) -> None:
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO scan_history (request_id, verdict, confidence, ocr_text, result_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            result_dict["requestId"],
            result_dict["verdict"],
            result_dict["confidence"],
            result_dict["ocrText"],
            json.dumps(result_dict, ensure_ascii=False),
            now,
        ),
    )
    conn.commit()
    conn.close()


def list_scan_history(limit: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT request_id, verdict, confidence, ocr_text, result_json, created_at FROM scan_history ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "requestId": r["request_id"],
            "verdict": r["verdict"],
            "confidence": r["confidence"],
            "ocrText": r["ocr_text"],
            "result": json.loads(r["result_json"]),
            "createdAt": r["created_at"],
        }
        for r in rows
    ]
