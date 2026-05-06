import re
from typing import Optional

# Core normalization and feature extraction for product matching.
# This module supports the SME pricing intelligence platform roadmap.

STOP_WORDS = {
    "smart", "android", "tv", "led", "qled", "smarttv", "ultra", "hdr",
    "digital", "wireless", "with", "and", "plus", "edition", "series",
    "inch", "inches", "inch", "screen", "inch", "inch", "display"
}

UNIT_ALIASES = {
    "inches": "",
    "inch": "",
    '"': "",
    "ksh": "",
    "gb": "",
    "gbp": "",
    "usd": ""
}

BRAND_KEYWORDS = [
    "samsung", "lg", "sony", "hisense", "vitron", "amtec", "vision",
    "toshiba", "sharp", "philips", "xbox", "apple", "lenovo", "hp"
]

CATEGORY_KEYWORDS = {
    "electronics": ["tv", "speaker", "headphone", "earphone", "monitor", "tablet"],
    "wearables": ["watch", "smartwatch", "fitbit"],
    "accessories": ["cable", "charger", "adapter", "remote", "case"],
    "kitchen": ["oven", "blender", "microwave", "mixer"],
    "mobile": ["phone", "smartphone", "iphone", "android"],
}

MODEL_REGEX = re.compile(r"\b([A-Z0-9]{3,}[A-Z0-9\-]*)\b", re.IGNORECASE)
SIZE_REGEX = re.compile(r"(\d{2,3})\s?(?:\"|inch|inches)", re.IGNORECASE)


def normalize_name(text: str) -> str:
    if text is None:
        return ""

    text = str(text).lower().strip()

    # Remove punctuation and common measurement units
    text = re.sub(r"[\[\]\(\)\.,:;!@#$%^&*\/\\]", " ", text)

    for alias, replacement in UNIT_ALIASES.items():
        text = text.replace(alias, replacement)

    words = [w for w in text.split() if w and w not in STOP_WORDS]
    words = [re.sub(r"[^a-z0-9\-]", "", w) for w in words]
    words = [w for w in words if w]

    return " ".join(words).strip()


def extract_brand(text: str) -> Optional[str]:
    if not text:
        return None

    normalized = str(text).lower()
    for brand in BRAND_KEYWORDS:
        if brand in normalized:
            return brand

    first_word = normalized.split()[0] if normalized.split() else None
    return first_word


def detect_category(text: str) -> str:
    normalized = str(text).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return category
    return "other"


def extract_features(text: str) -> dict:
    normalized = normalize_name(text)
    brand = extract_brand(text)

    size_match = SIZE_REGEX.search(text)
    size = size_match.group(1) if size_match else None

    model_match = MODEL_REGEX.search(text)
    model = model_match.group(1) if model_match else None

    category = detect_category(text)

    return {
        "normalized_name": normalized,
        "brand": brand,
        "size": size,
        "model": model,
        "category": category,
    }
