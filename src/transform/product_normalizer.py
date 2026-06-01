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


# =============================
# ADVANCED INTELLIGENCE METHODS
# =============================

def extract_features_advanced(text: str) -> dict:
    """
    Advanced feature extraction with synonym handling and better parsing.
    """
    if not text:
        return {
            "brand": None,
            "size": None,
            "model": None,
            "category": "other",
            "specifications": {},
            "normalized_name": "",
        }

    # Advanced normalization
    normalized = normalize_text_advanced(text)

    # Extract components with advanced methods
    brand = extract_brand_advanced(text)
    size = extract_size_advanced(text)
    model = extract_model_advanced(text)
    category = detect_category(text)
    specifications = extract_specifications(text)

    return {
        "brand": brand,
        "size": size,
        "model": model,
        "category": category,
        "specifications": specifications,
        "normalized_name": normalized,
    }


def normalize_text_advanced(text: str) -> str:
    """
    Advanced text normalization with synonym replacement.
    """
    if not text:
        return ""

    # Convert to lowercase and strip
    text = str(text).lower().strip()

    # Synonym replacements
    synonyms = {
        "television": "tv",
        "smart tv": "tv",
        "led tv": "tv",
        "qled tv": "tv",
        "oled tv": "tv",
        "4k tv": "tv",
        "uhd tv": "tv",
        "smart television": "tv",
        "inch": '"',
        "inches": '"',
        "samsung electronics": "samsung",
        "lg electronics": "lg",
        "sony corporation": "sony",
    }

    for synonym, replacement in synonyms.items():
        text = text.replace(synonym, replacement)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters but keep numbers and letters
    text = re.sub(r'[^a-z0-9\s\"\-]', '', text)

    return text.strip()


def extract_brand_advanced(text: str) -> Optional[str]:
    """
    Advanced brand extraction with variant handling.
    """
    if not text:
        return None

    normalized = normalize_text_advanced(text)

    # Brand variants mapping
    brand_variants = {
        "samsung": ["samsung", "samsung electronics", "samsung elec"],
        "lg": ["lg", "lg electronics", "lg elec", "life's good"],
        "sony": ["sony", "sony corporation", "sony corp"],
        "hisense": ["hisense", "hisense group"],
        "tcl": ["tcl", "tcl corporation"],
        "vitron": ["vitron", "vitron electronics"],
        "amtec": ["amtec", "amtec electronics"],
    }

    # Check for exact brand matches first
    for canonical_brand, variants in brand_variants.items():
        for variant in variants:
            if variant in normalized:
                return canonical_brand

    # Fallback to keyword matching
    for brand in BRAND_KEYWORDS:
        if brand in normalized:
            return brand

    # Final fallback to first word
    words = normalized.split()
    if words:
        first_word = words[0]
        if re.match(r'^[a-z]{2,15}$', first_word) and len(first_word) > 2:
            return first_word

    return None


def extract_model_advanced(text: str) -> Optional[str]:
    """
    Advanced model number extraction.
    """
    if not text:
        return None

    # Look for common model patterns
    patterns = [
        r'\b([A-Z]{2,}[\-_]?[0-9]{2,}[A-Z0-9\-_]*)\b',  # Samsung UN55AU8000
        r'\b([0-9]{2,}[A-Z]{2,}[0-9]*)\b',              # 55UN8000
        r'\b([A-Z]{1,3}[0-9]{3,}[A-Z0-9]*)\b',          # A55Q60A
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return None


def extract_size_advanced(text: str) -> Optional[str]:
    """
    Advanced size extraction for TVs/monitors.
    """
    if not text:
        return None

    # Look for size patterns
    patterns = [
        r'(\d{2,3})\s*(?:inch|inches|["\'])',  # 55 inch, 55" or 55'
        r'(\d{2,3})\s*inch',                      # 55inch (no space)
        r'(\d{2,3})["\']',                      # 55" or 55'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            size = int(match.group(1))
            # Validate reasonable TV/monitor sizes
            if 10 <= size <= 100:
                return str(size)

    return None


def extract_specifications(text: str) -> dict:
    """
    Extract technical specifications from product name.
    """
    specs = {}

    # Extract resolution
    resolution_patterns = [
        r'\b(4k|uhd|full\s*hd|hd|1080p|720p)\b',
        r'\b(\d{3,4}p)\b',
    ]
    for pattern in resolution_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            specs['resolution'] = match.group(1).upper()
            break

    # Extract technology
    tech_patterns = [
        r'\b(qled|oled|led|lcd|plasma|ips|va)\b',
    ]
    for pattern in tech_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            specs['technology'] = match.group(1).upper()
            break

    # Extract storage
    storage_match = re.search(r'(\d+)\s*(?:gb|tb)', text, re.IGNORECASE)
    if storage_match:
        specs['storage'] = f"{storage_match.group(1)}GB"

    # Extract RAM
    ram_match = re.search(r'(\d+)\s*gb\s*ram', text, re.IGNORECASE)
    if ram_match:
        specs['ram'] = f"{ram_match.group(1)}GB"

    return specs

