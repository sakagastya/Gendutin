# ai_client.py — Gendutin AI Layer
# Menggunakan Gemini REST API via requests. Kompatibel Python 3.8+.
# Architecture: Per-user API key, passed from UI session state.
# Tidak ada server-side secrets, tidak ada .env reading.
# Setiap user menyediakan key mereka sendiri dari antarmuka aplikasi.

import json
import requests
from typing import Optional, List, Dict, Any


# ── Key Validation ─────────────────────────────────────────────────────────────

def is_key_valid(api_key: str) -> bool:
    """Returns True jika api_key non-empty dan bukan placeholder string."""
    key = (api_key or "").strip()
    return bool(key) and key != "your_api_key_here"


# ── Core REST caller ───────────────────────────────────────────────────────────

def _call_gemini_api(
    model_name: str,
    prompt: str,
    api_key: str,
    is_json: bool = False,
    temperature: float = 0.7,
) -> Optional[str]:
    """Memanggil Gemini REST API secara langsung menggunakan requests."""
    if not is_key_valid(api_key):
        return None

    key = api_key.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"

    payload: Dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }

    if is_json:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


# ── Function 1: Estimate Food Nutrition ───────────────────────────────────────

def estimate_food_nutrition(
    food_description: str,
    api_key: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Estimasi kandungan nutrisi dari deskripsi makanan bebas menggunakan Gemini REST API.

    Args:
        food_description: Teks bebas deskripsi makanan (e.g. "semangkuk bakso sapi 10 biji").
        api_key: Gemini API key dari session state pengguna.

    Returns dict dengan keys: food_name, calories, protein_g, carbs_g, fat_g,
    serving_description — atau None jika API gagal / key tidak valid.
    """
    prompt = f"""Anda adalah ahli gizi bersertifikat. Estimasikan kandungan nutrisi untuk makanan/minuman berikut dalam porsi yang disebutkan. Gunakan data gizi standar Indonesia. Jika jumlah tidak disebutkan, asumsikan 1 porsi standar.

Makanan/Minuman: {food_description}

Jawab HANYA dalam format JSON berikut tanpa teks tambahan apapun:
{{
  "food_name": "nama makanan dalam bahasa Indonesia",
  "calories": 250,
  "protein_g": 15.5,
  "carbs_g": 30.0,
  "fat_g": 8.0,
  "serving_description": "deskripsi porsi yang dimaksud"
}}"""

    raw_response = _call_gemini_api(
        "gemini-2.5-flash", prompt, api_key=api_key, is_json=True, temperature=0.1
    )
    if not raw_response:
        return None

    try:
        data = json.loads(raw_response.strip())
        required_numeric = ["calories", "protein_g", "carbs_g", "fat_g"]
        for key in ["food_name", "serving_description"] + required_numeric:
            if key not in data:
                return None
        for key in required_numeric:
            if not isinstance(data[key], (int, float)) or data[key] < 0:
                return None
        return {
            "food_name":           str(data["food_name"]),
            "calories":            float(data["calories"]),
            "protein_g":           float(data["protein_g"]),
            "carbs_g":             float(data["carbs_g"]),
            "fat_g":               float(data["fat_g"]),
            "serving_description": str(data["serving_description"]),
        }
    except Exception:
        return None


# ── Function 2: Get Personalized Bulking Advice ───────────────────────────────

def get_bulking_advice(
    deficit_kcal: float,
    target_kcal: float,
    likes_text: str = "",
    dislikes_text: str = "",
    api_key: str = "",
) -> Optional[List[Dict[str, Any]]]:
    """
    Rekomendasikan 3-5 makanan/snack bulking yang dipersonalisasi berdasarkan
    defisit kalori pengguna hari ini dan preferensi makanan bebas mereka.

    Args:
        deficit_kcal: Kalori yang masih perlu dipenuhi hari ini.
        target_kcal:  Target kalori harian pengguna.
        likes_text:   Makanan favorit (teks bebas).
        dislikes_text: Makanan yang tidak disukai (teks bebas).
        api_key:      Gemini API key dari session state pengguna.

    Returns list of dicts dengan keys: suggestion, reason, estimated_calories
    — atau None jika API gagal.
    """
    likes_ctx    = likes_text.strip() if likes_text.strip() else "tidak ada preferensi khusus"
    dislikes_ctx = dislikes_text.strip() if dislikes_text.strip() else "tidak ada"

    prompt = f"""Anda adalah ahli nutrisi bulking berpengalaman. Pengguna sedang menjalankan program weight gain (bulking sehat).

KONTEKS PENGGUNA HARI INI:
- Target kalori harian: {target_kcal:.0f} kkal (sudah termasuk surplus +400 kkal)
- Defisit kalori yang masih perlu dipenuhi: {deficit_kcal:.0f} kkal
- Makanan/minuman favorit pengguna: {likes_ctx}
- Makanan yang TIDAK disukai (JANGAN sarankan): {dislikes_ctx}

Berikan tepat 3 hingga 5 rekomendasi makanan/snack yang:
1. Membantu memenuhi defisit kalori tersebut
2. Mudah ditemukan di Indonesia
3. Sesuai preferensi pengguna (hindari yang tidak disukai)
4. Tinggi kalori dan protein untuk bulking
5. Praktis dan bisa dimakan segera

Jawab HANYA dalam format JSON array berikut tanpa teks tambahan:
[
  {{
    "suggestion": "nama/deskripsi makanan",
    "reason": "alasan singkat mengapa cocok untuk kondisi pengguna sekarang",
    "estimated_calories": 350
  }}
]"""

    raw_response = _call_gemini_api(
        "gemini-2.5-flash", prompt, api_key=api_key, is_json=True, temperature=0.7
    )
    if not raw_response:
        return None

    try:
        data = json.loads(raw_response.strip())
        if not isinstance(data, list) or len(data) == 0:
            return None
        valid = []
        for item in data:
            if all(k in item for k in ["suggestion", "reason", "estimated_calories"]):
                try:
                    kcal = int(item["estimated_calories"])
                    if kcal > 0:
                        valid.append({
                            "suggestion":         str(item["suggestion"]),
                            "reason":             str(item["reason"]),
                            "estimated_calories": kcal,
                        })
                except (ValueError, TypeError):
                    continue
        return valid if valid else None
    except Exception:
        return None


# ── Function 3: Extract Activity Multiplier from Natural Language ─────────────

def extract_activity_multiplier(
    description: str,
    api_key: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Analisis deskripsi aktivitas harian dalam teks bebas dan ekstrak
    multiplier TDEE yang tepat untuk kalkulasi kebutuhan kalori.

    Args:
        description: Deskripsi gaya hidup / aktivitas dalam bahasa bebas.
        api_key:     Gemini API key dari session state pengguna.

    Returns dict dengan keys: activity_level, multiplier, explanation
    — atau None jika API gagal.
    """
    prompt = f"""You are a certified fitness and nutrition expert specializing in TDEE calculation.

A user described their daily physical activity in their own words:
\"{description}\"

Determine the most accurate TDEE activity multiplier based on this description.
Use these standard Harris-Benedict / Mifflin-St Jeor activity categories:
- Sedentary (desk job, little/no exercise, mostly sitting): multiplier 1.2
- Lightly Active (light exercise 1-3 days/week, or daily short walks): multiplier 1.375
- Moderately Active (moderate exercise 3-5 days/week): multiplier 1.55
- Very Active (hard exercise 6-7 days/week, or physically active job): multiplier 1.725
- Extra Active (very hard exercise daily + physical labor job): multiplier 1.9

Respond ONLY in this exact JSON format with no additional text:
{{
  "activity_level": "Moderately Active",
  "multiplier": 1.55,
  "explanation": "One concise sentence explaining your classification based on their specific description."
}}"""

    raw_response = _call_gemini_api(
        "gemini-2.5-flash", prompt, api_key=api_key, is_json=True, temperature=0.1
    )
    if not raw_response:
        return None

    try:
        data = json.loads(raw_response.strip())
        for key in ["activity_level", "multiplier", "explanation"]:
            if key not in data:
                return None
        multiplier = float(data["multiplier"])
        # Sanity-check: valid TDEE multipliers sit between 1.0 and 2.5
        if not (1.0 <= multiplier <= 2.5):
            return None
        return {
            "activity_level": str(data["activity_level"]),
            "multiplier":     multiplier,
            "explanation":    str(data["explanation"]),
        }
    except Exception:
        return None


# ── Function 4: Generate Healthy Bulking Recipe ─────────────────────────────

def generate_recipe(
    ingredients: str,
    api_key: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Buat resep masakan sehat untuk bulking berdasarkan bahan-bahan yang tersedia.

    Args:
        ingredients: Daftar bahan-bahan yang tersedia (teks bebas).
        api_key:     Gemini API key dari session state pengguna.

    Returns dict dengan keys: recipe_name, servings, instructions,
    total_calories, total_protein_g, total_carbs_g, total_fat_g,
    ingredients_used — atau None jika API gagal.
    """
    prompt = f"""Anda adalah chef sekaligus ahli gizi bulking berpengalaman di Indonesia.

Pengguna memiliki bahan-bahan berikut:
{ingredients}

Buat SATU resep masakan sehat yang:
1. Cocok untuk program bulking (tinggi kalori & protein)
2. Menggunakan bahan-bahan yang tersedia di atas
3. Mudah dibuat di rumah (tidak perlu alat dapur canggih)
4. Menggunakan bumbu dapur umum Indonesia yang bisa diasumsikan ada
5. Lezat dan mengenyangkan

Hitung kandungan gizi total resep tersebut secara akurat.

Jawab HANYA dalam format JSON berikut tanpa teks tambahan apapun:
{{
  "recipe_name": "Nama Resep dalam Bahasa Indonesia",
  "servings": 1,
  "ingredients_used": ["100g bahan1", "2 butir bahan2"],
  "instructions": "Langkah 1: ...\\nLangkah 2: ...\\nLangkah 3: ...",
  "total_calories": 520,
  "total_protein_g": 35.0,
  "total_carbs_g": 48.0,
  "total_fat_g": 14.0
}}"""

    raw_response = _call_gemini_api(
        "gemini-2.5-flash", prompt, api_key=api_key, is_json=True, temperature=0.4
    )
    if not raw_response:
        return None

    try:
        data = json.loads(raw_response.strip())
        required_str = ["recipe_name", "instructions"]
        required_num = ["total_calories", "total_protein_g", "total_carbs_g", "total_fat_g"]
        required_lst = ["ingredients_used"]
        for key in required_str + required_num + required_lst:
            if key not in data:
                return None
        for key in required_num:
            if not isinstance(data[key], (int, float)) or data[key] < 0:
                return None
        return {
            "recipe_name":     str(data["recipe_name"]),
            "servings":        int(data.get("servings", 1)),
            "ingredients_used": [str(i) for i in data["ingredients_used"]],
            "instructions":    str(data["instructions"]),
            "total_calories":  float(data["total_calories"]),
            "total_protein_g": float(data["total_protein_g"]),
            "total_carbs_g":   float(data["total_carbs_g"]),
            "total_fat_g":     float(data["total_fat_g"]),
        }
    except Exception:
        return None


# ── Utility ───────────────────────────────────────────────────────────────────

def api_status(api_key: str = "") -> dict:
    """
    Returns status konfigurasi API untuk ditampilkan di header UI.

    Args:
        api_key: Gemini API key dari st.session_state.user_gemini_key.
    """
    configured = is_key_valid(api_key)
    return {
        "configured": configured,
        "message": (
            "Gemini API terhubung"
            if configured
            else "API key belum dimasukkan — buka tab Lifestyle Setup"
        ),
    }
