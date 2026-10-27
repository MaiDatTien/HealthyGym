"""Cầu nối LLM cho AI Smart Coach (tuỳ chọn).

Khi cấu hình biến môi trường, chatbot sẽ gọi LLM thật với SYSTEM_INSTRUCTION
chuẩn PT/Dinh dưỡng. Khi chưa cấu hình (hoặc LLM lỗi), hệ thống tự động rơi về
engine rule-based nội bộ — website vẫn hoạt động đầy đủ, không phụ thuộc mạng.

Chỉ dùng thư viện chuẩn (urllib.request) nên KHÔNG cần cài thêm gói nào.

Cấu hình qua .env:
    LLM_PROVIDER=gemini            # gemini | openai
    LLM_API_KEY=...                # Bắt buộc để bật LLM
    LLM_MODEL=gemini-2.0-flash     # Tuỳ chọn, có giá trị mặc định theo provider
    LLM_BASE_URL=...               # Tuỳ chọn, cho endpoint OpenAI-compatible nội bộ
    LLM_TIMEOUT=30                 # Tuỳ chọn, giây
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Optional

logger = logging.getLogger("healthygym.llm")

#: Model mặc định theo từng nhà cung cấp
DEFAULT_MODELS = {
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
}

DEFAULT_BASE_URLS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "openai": "https://api.openai.com/v1",
}


def llm_config() -> dict[str, Any]:
    """Đọc cấu hình LLM từ biến môi trường."""
    provider = (os.getenv("LLM_PROVIDER") or "gemini").strip().lower()
    if provider not in DEFAULT_MODELS:
        provider = "gemini"
    return {
        "provider": provider,
        "api_key": (os.getenv("LLM_API_KEY") or "").strip(),
        "model": (os.getenv("LLM_MODEL") or DEFAULT_MODELS[provider]).strip(),
        "base_url": (os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URLS[provider]).strip().rstrip("/"),
        "timeout": float(os.getenv("LLM_TIMEOUT") or 30),
    }


def is_llm_enabled() -> bool:
    """LLM chỉ hoạt động khi đã có API key."""
    return bool(llm_config()["api_key"])


def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    """Gửi POST JSON bằng thư viện chuẩn (không cần requests/httpx)."""
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        request.add_header(key, value)

    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _build_system_prompt(system_instruction: str, profile: Optional[dict]) -> str:
    """Ghép System Instruction với dữ liệu chỉ số ĐÃ TÍNH SẴN.

    Điểm quan trọng: các chỉ số (BMI, LBM, BMR, TDEE, macros…) được engine nội bộ
    tính trước rồi truyền vào prompt. LLM chỉ diễn giải và tư vấn, KHÔNG tự tính —
    nhờ đó con số hiển thị luôn khớp tuyệt đối với phác đồ đã lưu và với biểu đồ.
    """
    if not profile:
        return system_instruction

    lines = [
        "\n\n## DỮ LIỆU HỘI VIÊN HIỆN TẠI (đã tính sẵn — dùng đúng số này, KHÔNG tự tính lại)",
    ]
    labels = {
        "gender": "Giới tính",
        "age": "Tuổi",
        "height_cm": "Chiều cao (cm)",
        "weight_kg": "Cân nặng (kg)",
        "body_fat_percentage": "Body Fat (%)",
        "goal": "Mục tiêu",
        "activity_level": "Mức vận động",
        "training_days_per_week": "Số buổi tập/tuần",
        "session_minutes": "Thời lượng mỗi buổi (phút)",
        "training_location": "Nơi tập",
        "injuries": "Chấn thương",
        "allergies": "Dị ứng thực phẩm",
    }
    for key, label in labels.items():
        value = profile.get(key)
        if value not in (None, "", [], "[]"):
            shown = ", ".join(value) if isinstance(value, list) else value
            lines.append(f"- {label}: {shown}")

    # Các chỉ số engine đã tính
    derived = [
        ("bmi", "BMI (đã tính)"),
        ("lean_body_mass_kg", "Khối lượng cơ nạc LBM (kg)"),
        ("fat_mass_kg", "Khối lượng mỡ (kg)"),
        ("bmr_kcal", "BMR Katch-McArdle (kcal)"),
        ("tdee_kcal", "TDEE (kcal)"),
        ("body_type_classification", "Tạng người (đã phân loại)"),
        ("target_daily_calories", "Calo mục tiêu/ngày (kcal)"),
        ("protein_grams", "Protein mục tiêu (g)"),
        ("carbs_grams", "Carbs mục tiêu (g)"),
        ("fat_grams", "Fat mục tiêu (g)"),
        ("estimated_weeks_to_goal", "Số tuần dự kiến đạt mục tiêu"),
    ]
    derived_lines = [
        f"- {label}: {profile[key]}"
        for key, label in derived
        if profile.get(key) not in (None, "")
    ]
    if derived_lines:
        lines.append("\n### Chỉ số engine đã tính")
        lines.extend(derived_lines)

    lines.append(
        "\nKhi hội viên hỏi lại bất kỳ chỉ số nào ở trên, hãy trả lời ĐÚNG con số này."
    )
    return system_instruction + "\n".join(lines)


def _call_gemini(cfg: dict, system_prompt: str, messages: list[dict]) -> str:
    """Gọi Google Gemini generateContent."""
    contents = [
        {
            "role": "user" if m.get("role") == "user" else "model",
            "parts": [{"text": m.get("content", "")}],
        }
        for m in messages
    ]
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 2048},
    }
    url = f"{cfg['base_url']}/models/{cfg['model']}:generateContent"
    result = _post_json(
        url, payload, {"x-goog-api-key": cfg["api_key"]}, cfg["timeout"]
    )

    candidates = result.get("candidates") or []
    if not candidates:
        raise RuntimeError("LLM không trả về nội dung")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError("LLM trả về nội dung rỗng")
    return text


def _call_openai(cfg: dict, system_prompt: str, messages: list[dict]) -> str:
    """Gọi endpoint OpenAI-compatible /chat/completions."""
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "temperature": 0.6,
        "max_tokens": 2048,
    }
    url = f"{cfg['base_url']}/chat/completions"
    result = _post_json(
        url, payload, {"Authorization": f"Bearer {cfg['api_key']}"}, cfg["timeout"]
    )
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("LLM không trả về nội dung")
    text = (choices[0].get("message") or {}).get("content", "").strip()
    if not text:
        raise RuntimeError("LLM trả về nội dung rỗng")
    return text


def ask_llm(
    system_instruction: str,
    message: str,
    profile: Optional[dict] = None,
    history: Optional[list[dict]] = None,
) -> Optional[str]:
    """Gọi LLM với System Instruction. Trả về None nếu LLM chưa bật hoặc gặp lỗi.

    Không bao giờ raise — người gọi luôn có thể rơi về engine rule-based.
    """
    cfg = llm_config()
    if not cfg["api_key"]:
        return None

    system_prompt = _build_system_prompt(system_instruction, profile)
    messages: list[dict] = list(history or [])
    messages.append({"role": "user", "content": message})

    try:
        if cfg["provider"] == "gemini":
            return _call_gemini(cfg, system_prompt, messages)
        return _call_openai(cfg, system_prompt, messages)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")[:300]
        logger.warning(
            "LLM HTTP %s (%s): %s — chuyển sang engine rule-based",
            exc.code, cfg["provider"], detail,
        )
    except urllib.error.URLError as exc:
        logger.warning("Không kết nối được LLM (%s) — dùng engine rule-based", exc.reason)
    except Exception as exc:  # noqa: BLE001 - không để LLM làm hỏng request
        logger.warning("Lỗi khi gọi LLM: %s — dùng engine rule-based", exc)

    return None