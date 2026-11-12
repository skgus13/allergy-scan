import React, { useEffect, useState } from "react";
import {
  analyzeImage,
  fetchMyAllergens,
  fetchScanHistory,
  fetchSupportedAllergens,
  saveMyAllergens,
} from "./api/client";
import "./App.css";

const DEFAULT_19_ALLERGENS = [
  "알류(가금류)", "우유", "메밀", "땅콩", "대두", "밀", "고등어", "게", "새우",
  "돼지고기", "복숭아", "토마토", "아황산류", "호두", "닭고기", "쇠고기", "오징어", "조개류", "잣",
];

export default function App() {
  const [allergenList, setAllergenList] = useState(DEFAULT_19_ALLERGENS);
  const [selectedAllergens, setSelectedAllergens] = useState(["우유", "땅콩"]);
  const [imageFile, setImageFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [barcode, setBarcode] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    fetchSupportedAllergens()
      .then((data) => {
        if (data?.allergens) setAllergenList(Object.keys(data.allergens));
      })
      .catch(() => {});

    fetchMyAllergens()
      .then((data) => {
        if (data?.allergens?.length) setSelectedAllergens(data.allergens);
      })
      .catch(() => {});

    fetchScanHistory()
      .then((data) => setHistory(data?.items || []))
      .catch(() => {});
  }, []);

  const toggleAllergen = (item) => {
    setSelectedAllergens((prev) =>
      prev.includes(item) ? prev.filter((a) => a !== item) : [...prev, item]
    );
  };

  const handleSaveAllergens = async () => {
    try {
      await saveMyAllergens(selectedAllergens);
      alert("내 알레르기 설정이 저장되었습니다.");
    } catch (e) {
      alert(e.message);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setErrorMsg("");
  };

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!imageFile) {
      setErrorMsg("성분표 사진을 먼저 선택하거나 촬영해 주세요.");
      return;
    }
    setLoading(true);
    setErrorMsg("");
    try {
      const res = await analyzeImage({
        imageFile,
        barcode: barcode.trim() || undefined,
        userAllergens: selectedAllergens,
      });
      setResult(res);
      const hist = await fetchScanHistory();
      setHistory(hist?.items || []);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header className="header">
        <h1>🔍 AllergyScan</h1>
        <p>식품 성분표 OCR &amp; 알레르기 19종 자동 판별 웹 서비스</p>
      </header>

      {/* 1. 내 알레르기 설정 섹션 */}
      <section className="card">
        <h2>1. 내 알레르기 성분 선택 (식약처 의무표시 19종)</h2>
        <div className="chip-grid">
          {allergenList.map((item) => {
            const active = selectedAllergens.includes(item);
            return (
              <button
                key={item}
                type="button"
                className={`chip ${active ? "active" : ""}`}
                onClick={() => toggleAllergen(item)}
              >
                {active ? "✓ " : ""}
                {item}
              </button>
            );
          })}
        </div>
        <button type="button" className="btn-secondary" onClick={handleSaveAllergens}>
          선택한 알레르기 저장 ({selectedAllergens.length}개)
        </button>
      </section>

      {/* 2. 사진 촬영 / 업로드 및 바코드 입력 */}
      <section className="card">
        <h2>2. 성분표 사진 촬영 또는 업로드</h2>
        <form onSubmit={handleAnalyze} className="upload-form">
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
          />
          <input
            type="text"
            placeholder="(선택) 바코드 번호 입력 (예: 8801043014809)"
            value={barcode}
            onChange={(e) => setBarcode(e.target.value)}
            className="text-input"
          />
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "OCR 및 알레르기 분석 중..." : "성분표 분석 시작"}
          </button>
        </form>
        {errorMsg && <p className="error-text">{errorMsg}</p>}
      </section>

      {/* 3. 분석 결과 및 Bounding Box 시각화 */}
      {result && (
        <section className={`card verdict-${result.verdict.toLowerCase()}`}>
          <h2>
            3. 판정 결과: <span className="badge">{result.verdict}</span> (신뢰도:{" "}
            {Math.round(result.confidence * 100)}%)
          </h2>
          <p className="disclaimer">
            ⚠️ 본 결과는 참고용이며, 최종 판단은 반드시 포장지 원문을 확인하세요.
          </p>

          {previewUrl && (
            <div className="image-stage">
              <img src={previewUrl} alt="업로드된 성분표" className="preview-img" />
              {/* TODO [팀원 3 - 3주차]: result.imageWidth/Height 대비 비율로 result.detected[].bbox 오버레이 고도화 */}
            </div>
          )}

          <h3>감지된 알레르기 성분 ({result.detected.length}건)</h3>
          <ul className="detected-list">
            {result.detected.map((d, idx) => (
              <li key={idx} className={d.userAllergic ? "danger-item" : ""}>
                <strong>{d.allergen}</strong> (매칭: &ldquo;{d.matchedText}&rdquo;, 출처: {d.source})
                {d.userAllergic && <span className="tag-danger">내 알레르기 위험!</span>}
              </li>
            ))}
          </ul>

          {result.cautionNotices?.length > 0 && (
            <div className="caution-box">
              <strong>교차 오염 안내 문구:</strong>
              <ul>
                {result.cautionNotices.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            </div>
          )}

          <details>
            <summary>추출된 OCR 원문 보기</summary>
            <pre className="ocr-pre">{result.ocrText}</pre>
          </details>
        </section>
      )}

      {/* 4. 최근 검사 이력 */}
      <section className="card">
        <h2>4. 최근 검사 기록 ({history.length}건)</h2>
        {history.length === 0 ? (
          <p>아직 검사 기록이 없습니다.</p>
        ) : (
          <ul className="history-list">
            {history.map((item) => (
              <li key={item.requestId}>
                <strong>[{item.verdict}]</strong> {item.ocrText.slice(0, 50)}...{" "}
                <small>({item.createdAt})</small>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
