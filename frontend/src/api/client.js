const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export async function fetchSupportedAllergens() {
  const res = await fetch(`${API_BASE}/allergens`);
  if (!res.ok) throw new Error("알레르기 사전 조회 실패");
  return res.json();
}

export async function fetchMyAllergens() {
  const res = await fetch(`${API_BASE}/users/me/allergens`);
  if (!res.ok) throw new Error("사용자 알레르기 조회 실패");
  return res.json();
}

export async function saveMyAllergens(allergens, customAllergens = []) {
  const res = await fetch(`${API_BASE}/users/me/allergens`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ allergens, customAllergens }),
  });
  if (!res.ok) throw new Error("사용자 알레르기 저장 실패");
  return res.json();
}

export async function analyzeImage({ imageFile, barcode, userAllergens }) {
  const formData = new FormData();
  formData.append("image", imageFile);
  if (barcode) formData.append("barcode", barcode);
  if (userAllergens && userAllergens.length > 0) {
    formData.append("userAllergens", JSON.stringify(userAllergens));
  }

  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail?.message || "성분표 분석 요청 실패");
  }
  return res.json();
}

export async function fetchScanHistory() {
  const res = await fetch(`${API_BASE}/history`);
  if (!res.ok) throw new Error("검사 기록 조회 실패");
  return res.json();
}
