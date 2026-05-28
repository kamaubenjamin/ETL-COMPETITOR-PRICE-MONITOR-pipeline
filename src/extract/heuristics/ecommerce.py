"""
Heuristic extraction primitives for ecommerce and supermarket layouts.

These helpers intentionally avoid site-specific coupling. Future AI-assisted
extraction, LLM parsing, OCR, or vision models can plug in at this boundary and
return the same product record shape used by the connector.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse


# --- Core card selectors (generic ecommerce) ---
COMMON_CARD_SELECTORS = [
    "article",
    "[data-testid*='product' i]",
    "[data-test*='product' i]",
    "[class*='product' i]",
    "[class*='item' i]",
    "[class*='card' i]",
    "[class*='tile' i]",
    "li",
]

# --- Supermarket-specific selectors (React/Next.js ecommerce patterns) ---
SUPERMARKET_CARD_SELECTORS = [
    "div[class*='product-card' i]",
    "div[class*='productCard' i]",
    "div[class*='product_item' i]",
    "div[class*='productItem' i]",
    "div[class*='catalog-product' i]",
    "div[class*='catalog-product' i] > *",
    "div[class*='product-grid' i] > *",
    "div[class*='product-list' i] > *",
    "div[class*='product-tile' i]",
    "div[class*='productTile' i]",
    "a[class*='product' i]",
    "[data-component*='product' i]",
    "[data-component*='Product' i]",
    "[data-testid*='product-card' i]",
    "[class*='catalog'] [class*='product' i]",
    "[class*='catalog'] [class*='item' i]",
    ".product-grid > div",
    ".product-list > div",
    ".product-catalog > div",
    ".catalog-grid > div",
    ".catalog-list > div",
    ".catalog-product > div",
    ".catalog-product > a",
    # --- Repeated sibling-card selectors ---
    "div:has(img):has-text('KES')",
    # --- React ecommerce heuristics ---
    "div[role='listitem']",
    "div[class*='grid'] > div[class*='item' i]",
    "div[role='list'] > div",
    "section > div[class*='grid' i] > div",
    "div[class*='product'] > div[class*='image' i]",
    "div[data-component*='product' i]",
    "div[data-test*='product' i]",
]

# --- Hidden price selectors (for React-rendered or data-attribute prices) ---
HIDDEN_PRICE_SELECTORS = [
    "meta[itemprop='price']",
    "span[class*='price' i]",
    "span[class*='Price' i]",
    "[data-price]",
    "[data-product-price]",
    "[class*='price-value' i]",
    "[class*='current-price' i]",
    "[class*='sale-price' i]",
]

# --- Pagination selectors ---
COMMON_NEXT_SELECTORS = [
    "a[rel='next']",
    "button[aria-label*='next' i]",
    "a[aria-label*='next' i]",
    ".next",
    ".pagination-next",
    "a:has-text('Next')",
    "button:has-text('Next')",
]

# --- Popup/modal dismiss selectors ---
POPUP_ACCEPT_BUTTONS = [
    "button:has-text('Accept All')",
    "button:has-text('Accept')",
    "button:has-text('Allow')",
    "button:has-text('OK')",
    "button:has-text('Agree')",
    "button[aria-label*='Accept']",
    "button[aria-label*='accept']",
    "button[aria-label*='Allow']",
    "button[aria-label*='allow']",
    "[class*='cookie-accept' i]",
    "[class*='cookie-allow' i]",
    "[class*='consent-accept' i]",
    "[class*='consent-allow' i]",
    "[class*='cookie-banner'] button:first-child",
    "[id*='cookie-banner'] button:first-child",
    "[id*='consent'] button:first-child",
]

POPUP_DISMISS_BUTTONS = [
    "button:has-text('Reject')",
    "button:has-text('Decline')",
    "button:has-text('Close')",
    "button[aria-label*='Close']",
    "button[aria-label*='close']",
    "button[aria-label*='Dismiss']",
    "button[aria-label*='dismiss']",
    "[class*='cookie-close' i]",
    "[class*='cookie-dismiss' i]",
    "[class*='modal-close' i]",
    "[class*='modal-dismiss' i]",
    ".close",
    ".modal-close",
    ".popup-close",
    "button[class*='close']",
    "button[class*='dismiss']",
]

POPUP_LOCATION_BUTTONS = [
    "button:has-text('Select Branch')",
    "button:has-text('Choose Location')",
    "button:has-text('Set Location')",
    "button:has-text('Continue')",
    "button:has-text('Confirm')",
    "button[aria-label*='branch']",
    "button[aria-label*='location']",
    "button[aria-label*='location']",
    "[class*='location-continue' i]",
    "[class*='branch-select' i]",
    "[class*='location-modal'] button:first-child",
    "[id*='location-modal'] button:first-child",
    "[id*='branch-modal'] button:first-child",
    "[class*='store-locator'] button:first-child",
    # --- Extended branch/location init selectors ---
    "select[name*='branch' i]",
    "select[name*='location' i]",
    "select[class*='branch' i]",
    "div[class*='branch-list' i] > div",
    "div[class*='store-list' i] > div",
    "a[class*='branch' i]",
    "button[class*='branch' i]",
    "button:has-text('Select Branch')",
    "div:has-text('Select Branch')",
    "span:has-text('Select Branch')",
    "button:has-text('Nairobi')",
    "text=Nairobi",
    "button:has-text('Confirm')",
    "button:has-text('Continue')",
]

# --- Homepage initialization interactions (before category navigation) ---
HOMEPAGE_INTERACTIONS = [
    "button:has-text('Shop Now')",
    "a[href*='/soaps-detergents' i]",
    "a[href*='/shop' i]",
    "button[class*='dismiss' i]",
    "button[aria-label*='close' i]",
    "[class*='welcome'] button",
]

# --- Homepage category link selectors ---
HOMEPAGE_CATEGORY_SELECTORS = [
    # --- Category keywords in links/buttons/divs ---
    "a[href*='soap' i]",
    "a[href*='detergent' i]",
    "a[href*='cleaning' i]",
    "a[href*='laundry' i]",
    "a[href*='household' i]",
    "a[href*='homecare' i]",
    "button[class*='soap' i]",
    "button[class*='detergent' i]",
    "button[class*='cleaning' i]",
    "button[class*='laundry' i]",
    "div[class*='category'] a",
    "div[class*='category'] button",
    "div[class*='product-grid'] a:first-child",
    "div[class*='grid'] > a",
    "a[class*='category' i]",
    "button[class*='category' i]",
    "[data-category] a",
    "[data-category]",
    # --- Generic shop/category navigation ---
    "a[href*='/shop' i]",
    "a[href*='/category' i]",
    "a[href*='/products' i]",
    "nav a[href*='soap' i]",
    "nav a[href*='detergent' i]",
    "nav a[href*='cleaning' i]",
    "nav a[href*='laundry' i]",
]

INVALID_GENERIC_ROUTES = [
    "/home",
    "/shops",
    "/foods",
    "/fresh",
    "/personal-care",
    "/personalcare",
]

VALID_CATEGORY_KEYWORDS = [
    "soap",
    "detergent",
    "cleaning",
    "laundry",
    "household",
    "homecare",
    "dishwash",
    "fabric",
    "scour",
    "bleach",
]

CATEGORY_MENU_OPEN_SELECTORS = [
    "button:has-text('Shop by Category')",
    "button:has-text('All Categories')",
    "button:has-text('Shop All')",
    "button:has-text('View All')",
    "button[class*='hamburger' i]",
    "button[aria-label*='menu' i]",
    "button[aria-label*='navigation' i]",
    "a[href*='/shop' i]",
    "a[href*='/category' i]",
    "div[class*='mega-menu' i]",
]

INVALID_GENERIC_ROUTES = [
    "/home",
    "/shops",
    "/foods",
    "/fresh",
    "/personal-care",
    "/personalcare",
]

VALID_CATEGORY_KEYWORDS = [
    "soap",
    "detergent",
    "cleaning",
    "laundry",
    "household",
    "homecare",
    "dishwash",
    "fabric",
    "scour",
    "bleach",
]


def score_category_route(route: str, text: str = "") -> int:
    """Score category routes for likelihood of being a detergent/cleaning product collection."""
    route = route.lower().strip()
    text = text.lower().strip()
    score = 0

    if any(kw in route for kw in VALID_CATEGORY_KEYWORDS):
        score += 40
    if any(kw in text for kw in VALID_CATEGORY_KEYWORDS):
        score += 20
    if any(keyword in route for keyword in ["detergent", "laundry", "cleaning", "soap"]):
        score += 30
    if any(keyword in text for keyword in ["detergent", "laundry", "cleaning", "soap"]):
        score += 15

    path = urlparse(route).path.strip("/")
    depth = len([segment for segment in path.split("/") if segment])
    if depth >= 2:
        score += 10
    if depth >= 3:
        score += 15
    if "-" in path or "_" in path:
        score += 5

    if any(generic in route for generic in INVALID_GENERIC_ROUTES) and not any(valid in route for valid in VALID_CATEGORY_KEYWORDS):
        return -100

    if score < 30:
        score -= 10

    return score


def is_valid_category_route(route: str, text: str = "") -> bool:
    route_lower = route.lower()
    text_lower = text.lower()
    if any(keyword in route_lower for keyword in VALID_CATEGORY_KEYWORDS):
        return True
    if any(keyword in text_lower for keyword in VALID_CATEGORY_KEYWORDS):
        return True
    if any(generic in route_lower for generic in INVALID_GENERIC_ROUTES):
        return False
    return "/" in route_lower and len(urlparse(route_lower).path.strip("/")) > 1

POPUP_OVERLAYS = [
    "[class*='modal-overlay' i]",
    "[class*='modal-backdrop' i]",
    "[class*='popup-overlay' i]",
    "[class*='dialog-overlay' i]",
    "[id*='modal-overlay']",
    "[id*='dialog-overlay']",
    ".modal",
    ".popup",
    ".dialog",
    "[role='dialog']",
    "[role='alertdialog']",
]

# --- Cookie banner dismiss selectors (text-based, multi-element-type) ---
COOKIE_BANNER_SELECTORS = [
    # Buttons
    "button:has-text('Accept Cookies')",
    "button:has-text('Accept')",
    "button:has-text('Allow')",
    "button:has-text('I Agree')",
    "button:has-text('I agree')",
    # Divs
    "div:has-text('Accept Cookies')",
    "div:has-text('Accept')",
    "div:has-text('Allow')",
    "div:has-text('I Agree')",
    "div:has-text('I agree')",
    # Spans
    "span:has-text('Accept Cookies')",
    "span:has-text('Accept')",
    "span:has-text('Allow')",
    "span:has-text('I Agree')",
    "span:has-text('I agree')",
    # role=button
    "[role='button']:has-text('Accept Cookies')",
    "[role='button']:has-text('Accept')",
    "[role='button']:has-text('Allow')",
    "[role='button']:has-text('I Agree')",
    "[role='button']:has-text('I agree')",
]

# --- Category page verification selectors ---
CATEGORY_VERIFICATION_SELECTORS = [
    "[class*='breadcrumb' i]",
    "[class*='breadcrumb' i] a",
    "nav a[href*='soap' i]",
    "nav a[href*='detergent' i]",
    "nav a[href*='cleaning' i]",
    "h1, h2",
    "[class*='page-title' i]",
    "[class*='category-title' i]",
    "[class*='category-header' i]",
    "[class*='product-grid' i]",
    "[class*='product-listing' i]",
    "[class*='catalog' i]",
    # SPA route indicators
    "[data-category]",
    "[data-page='category']",
    "[class*='category-page' i]",
]

# --- Marketing/heromarketing text patterns (reject from extraction) ---
MARKETING_TEXT_PATTERNS = {
    "shop now", "banner", "offer", "deal", "limited time",
    "new arrival", "best seller", "trending", "popular",
    "subscribe", "newsletter", "featured", "collection",
    "hero", "carousel", "slide", "promotion",
    "free delivery", "free shipping", "order now",
    "today only", "flash sale", "clearance",
}

# --- Scroll stabilization selectors (elements that indicate loading) ---
SCROLL_STABILIZATION_SELECTORS = [
    "[class*='loading' i]",
    "[class*='spinner' i]",
    "[class*='skeleton' i]",
    "[class*='placeholder' i]",
    "[class*='lazy' i]",
    "[data-loading]",
    "[data-skeleton]",
]

CURRENCY_RE = re.compile(
    r"(?P<currency>KSh|KES|Ksh|USD|\$|£|€)?\s*(?P<amount>\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
DISCOUNT_RE = re.compile(r"(?P<discount>\d{1,2})\s?%\s?(?:off|discount|save)?", re.IGNORECASE)
SKU_RE = re.compile(r"\b(?:sku|item\s?no|code)[:#\s-]*([A-Z0-9\-_]{3,})\b", re.IGNORECASE)
SIZE_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?(kg|g|gram|grams|l|ml|litre|liter|pcs|pieces|pack|sachets?)\b", re.IGNORECASE)

NOISE_LINES = {
    "add to cart",
    "buy now",
    "quick view",
    "view details",
    "wishlist",
    "compare",
    "save",
}

SUPERMARKET_BRANDS = {
    "omo": ["omo"],
    "ariel": ["ariel"],
    "sunlight": ["sunlight"],
    "toss": ["toss"],
    "geisha": ["geisha"],
}


@dataclass(slots=True)
class CardScore:
    selector: str
    candidates: int
    price_hits: int
    avg_text_length: float

    @property
    def score(self) -> float:
        return (self.price_hits * 4) + min(self.candidates, 80) + min(self.avg_text_length / 80, 5)


@dataclass(slots=True)
class SelectorAttempt:
    selector: str
    candidate_count: int
    price_hits: int
    score: float
    error: Optional[str] = None


@dataclass(slots=True)
class SiblingCardScore:
    """Score for a sibling-card detection attempt."""
    selector: str
    candidate_count: int
    has_image: bool
    has_price: bool
    has_title: bool
    has_currency: bool
    repeated_dimensions: bool
    repeated_discount_badges: bool
    score: float
    error: Optional[str] = None


class EcommerceHeuristics:
    """Site-agnostic extraction heuristics for product card text."""

    @staticmethod
    def parse_price(text: str) -> tuple[Optional[float], Optional[str]]:
        if not text:
            return None, None
        matches = list(CURRENCY_RE.finditer(text))
        prices = []
        for match in matches:
            if EcommerceHeuristics._is_measurement_context(text, match):
                continue
            raw = match.group("amount").replace(",", "").replace(" ", "")
            try:
                amount = float(raw)
            except ValueError:
                continue
            if amount <= 0:
                continue
            currency = match.group("currency") or "KES"
            currency = "KES" if currency.lower().startswith(("ksh", "kes")) else currency
            prices.append((amount, currency))
        if not prices:
            return None, None
        return min(prices, key=lambda item: item[0])

    @staticmethod
    def parse_old_price(text: str, current_price: Optional[float]) -> Optional[float]:
        if current_price is None:
            return None
        prices = [price for price, _ in EcommerceHeuristics.parse_all_prices(text)]
        higher = [price for price in prices if price > current_price]
        return min(higher) if higher else None

    @staticmethod
    def parse_all_prices(text: str) -> list[tuple[float, str]]:
        values = []
        for match in CURRENCY_RE.finditer(text or ""):
            if EcommerceHeuristics._is_measurement_context(text or "", match):
                continue
            try:
                amount = float(match.group("amount").replace(",", "").replace(" ", ""))
            except ValueError:
                continue
            if amount > 0:
                currency = match.group("currency") or "KES"
                values.append((amount, "KES" if currency.lower().startswith(("ksh", "kes")) else currency))
        return values

    @staticmethod
    def parse_discount(text: str) -> Optional[float]:
        match = DISCOUNT_RE.search(text or "")
        return float(match.group("discount")) if match else None

    @staticmethod
    def _is_measurement_context(text: str, match: re.Match) -> bool:
        following = text[match.end(): match.end() + 8].lower()
        preceding = text[max(0, match.start() - 4): match.start()].lower()
        if re.match(r"\s?(kg|kgs|g|gram|grams|l|ltr|litre|liter|ml|pcs|pieces|pack|sachet)", following):
            return True
        if re.match(r"\s?%", following) or "%" in preceding:
            return True
        return False

    @staticmethod
    def parse_sku(text: str) -> Optional[str]:
        match = SKU_RE.search(text or "")
        return match.group(1).upper() if match else None

    @staticmethod
    def availability(text: str) -> Optional[str]:
        normalized = (text or "").lower()
        if any(token in normalized for token in ["out of stock", "sold out", "unavailable"]):
            return "out_of_stock"
        if any(token in normalized for token in ["in stock", "available", "add to cart", "buy now"]):
            return "available"
        return None

    @staticmethod
    def _is_price_or_discount_line(text: str) -> bool:
        """Check if text is exclusively a price or discount line.

        Returns True for lines like "KES 289", "$10.99", "20% off".
        Returns False for product names that happen to contain units (e.g. "1Kg").
        """
        if not text:
            return False

        # Check for discount-only lines: standalone discount percentage
        discount_match = DISCOUNT_RE.search(text)
        if discount_match:
            # Discount match must cover most of the line (no significant surrounding text)
            start, end = discount_match.span()
            before = text[:start].strip()
            after = text[end:].strip()
            if not before and not after:
                return True
            # Also accept "20% off", "20% discount", "20% save"
            if after and after.lower() in {"off", "discount", "save"} and not before:
                return True

        # Check for price-only lines via CURRENCY_RE
        for match in CURRENCY_RE.finditer(text):
            # If measurement context (e.g. "1Kg", "500ml"), skip this match
            if EcommerceHeuristics._is_measurement_context(text, match):
                continue
            currency = match.group("currency")
            amount_str = match.group("amount")
            # Only reject if:
            # 1. There's an explicit currency symbol (KES, $, KSh, etc.), OR
            # 2. The amount is isolated (whole line is just the number)
            #    This avoids rejecting "Ariel Original Perfume Detergent 1Kg"
            #    where "1" matches but is embedded in text.
            if currency:
                # Has explicit currency indicator — likely a price line
                return True
            # Check if amount is standalone (surrounded by boundaries / line edges)
            amount_match = re.search(re.escape(amount_str), text)
            if amount_match:
                start, end = amount_match.span()
                before_char = text[start - 1] if start > 0 else " "
                after_char = text[end] if end < len(text) else " "
                # If amount has whitespace or line boundary on both sides, it's standalone
                if not before_char.isalnum() and not after_char.isalnum():
                    return True

        return False

    @staticmethod
    def product_name(lines: Iterable[str]) -> Optional[str]:
        candidates = []
        for line in lines:
            cleaned = EcommerceHeuristics.clean_text(line)
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in NOISE_LINES:
                continue
            if EcommerceHeuristics._is_price_or_discount_line(cleaned):
                continue
            if len(cleaned) < 3 or len(cleaned) > 180:
                continue
            candidates.append(cleaned)
        if not candidates:
            return None
        return max(candidates, key=lambda item: (len(item.split()), len(item)))

    @staticmethod
    def clean_text(text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "")).strip()

    @staticmethod
    def split_lines(text: str) -> list[str]:
        return [line.strip() for line in re.split(r"[\n\r]+", text or "") if line.strip()]

    @staticmethod
    def normalize_url(base_url: str, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return urljoin(base_url, value)

    @staticmethod
    def confidence(record: Dict[str, Any], strategy: str) -> float:
        score = 0.0
        if record.get("product_name"):
            score += 0.35
        if record.get("current_price") is not None:
            score += 0.3
        if record.get("url"):
            score += 0.1
        if record.get("image_url"):
            score += 0.1
        if record.get("availability"):
            score += 0.05
        if record.get("brand"):
            score += 0.05
        if strategy == "semantic_card_auto":
            score += 0.05
        return round(min(score, 1.0), 3)

    @staticmethod
    def score_selector(selector: str, texts: list[str]) -> CardScore:
        non_empty = [text for text in texts if EcommerceHeuristics.clean_text(text)]
        price_hits = sum(1 for text in non_empty if CURRENCY_RE.search(text))
        avg_length = sum(len(text) for text in non_empty) / len(non_empty) if non_empty else 0
        return CardScore(selector=selector, candidates=len(non_empty), price_hits=price_hits, avg_text_length=avg_length)

    @staticmethod
    def score_selector_extended(selector: str, texts: list[str]) -> SelectorAttempt:
        """Extended scoring that returns full attempt details."""
        try:
            non_empty = [text for text in texts if EcommerceHeuristics.clean_text(text)]
            price_hits = sum(1 for text in non_empty if CURRENCY_RE.search(text))
            avg_length = sum(len(text) for text in non_empty) / len(non_empty) if non_empty else 0
            score = (price_hits * 4) + min(len(non_empty), 80) + min(avg_length / 80, 5)
            return SelectorAttempt(
                selector=selector,
                candidate_count=len(non_empty),
                price_hits=price_hits,
                score=round(score, 2),
            )
        except Exception as e:
            return SelectorAttempt(
                selector=selector,
                candidate_count=0,
                price_hits=0,
                score=0.0,
                error=str(e),
            )

    @staticmethod
    def get_all_card_selectors() -> List[str]:
        """Return combined list of all card selectors (generic + supermarket)."""
        seen = set()
        combined = []
        for s in COMMON_CARD_SELECTORS + SUPERMARKET_CARD_SELECTORS:
            if s not in seen:
                seen.add(s)
                combined.append(s)
        return combined

    @staticmethod
    def score_sibling_cards(selector: str, texts: list[str], bounding_boxes: Optional[list[dict]] = None) -> SiblingCardScore:
        """Score repeated sibling-card div structures for product detection.

        Analyzes text from repeated sibling divs to determine if they represent
        product cards. Scores higher when:
        - Currency symbols (KES, $, KSh) appear
        - Repeated widths/heights are detected (consistent grid layout)
        - Repeated discount badges exist (e.g. "20% off")
        """
        try:
            non_empty = [text for text in texts if EcommerceHeuristics.clean_text(text)]
            candidate_count = len(non_empty)

            if candidate_count == 0:
                return SiblingCardScore(
                    selector=selector, candidate_count=0,
                    has_image=False, has_price=False, has_title=False,
                    has_currency=False, repeated_dimensions=False,
                    repeated_discount_badges=False, score=0.0,
                )

            # Check for image indicator (img tags via text or bounding box)
            has_image = any(
                "img" in text.lower() or "src=" in text.lower() or ".jpg" in text.lower() or ".png" in text.lower()
                for text in non_empty
            )

            # Check for price-like text
            price_hits = sum(1 for text in non_empty if CURRENCY_RE.search(text))
            has_price = price_hits >= (candidate_count * 0.3)  # At least 30% have prices

            # Check for currency presence
            currency_hits = sum(
                1 for text in non_empty
                if re.search(r'(KES|KSh|Ksh|USD|\$|£|€)', text, re.IGNORECASE)
            )
            has_currency = currency_hits >= min(3, candidate_count)

            # Check for product title text (non-price, non-noise text)
            title_hits = 0
            for text in non_empty:
                lines = EcommerceHeuristics.split_lines(text)
                name = EcommerceHeuristics.product_name(lines)
                if name and len(name) >= 5:
                    title_hits += 1
            has_title = title_hits >= (candidate_count * 0.3)

            # Check for repeated discount badges
            discount_hits = sum(1 for text in non_empty if DISCOUNT_RE.search(text))
            repeated_discount_badges = discount_hits >= min(2, candidate_count)

            # Check for repeated dimensions (bounding boxes)
            repeated_dimensions = False
            if bounding_boxes and len(bounding_boxes) >= 3:
                widths = [box.get("width", 0) for box in bounding_boxes if box]
                heights = [box.get("height", 0) for box in bounding_boxes if box]
                # If most widths and heights are similar (within 10% tolerance)
                if widths and heights:
                    median_w = sorted(widths)[len(widths) // 2]
                    median_h = sorted(heights)[len(heights) // 2]
                    w_match = sum(1 for w in widths if median_w > 0 and abs(w - median_w) / median_w < 0.15)
                    h_match = sum(1 for h in heights if median_h > 0 and abs(h - median_h) / median_h < 0.15)
                    repeated_dimensions = (w_match >= len(widths) * 0.7 and h_match >= len(heights) * 0.7)

            # Compute score
            score = 0.0
            if candidate_count >= 3:
                score += 10
            if has_image:
                score += 5
            if has_price:
                score += 10
            if has_title:
                score += 5
            if has_currency:
                score += 8
            if repeated_dimensions:
                score += 7
            if repeated_discount_badges:
                score += 5

            return SiblingCardScore(
                selector=selector,
                candidate_count=candidate_count,
                has_image=has_image,
                has_price=has_price,
                has_title=has_title,
                has_currency=has_currency,
                repeated_dimensions=repeated_dimensions,
                repeated_discount_badges=repeated_discount_badges,
                score=round(score, 2),
            )
        except Exception as e:
            return SiblingCardScore(
                selector=selector, candidate_count=0,
                has_image=False, has_price=False, has_title=False,
                has_currency=False, repeated_dimensions=False,
                repeated_discount_badges=False, score=0.0, error=str(e),
            )

    @staticmethod
    def detect_loading_complete(page_text: str) -> bool:
        """Check if page text suggests loading is complete (no loading indicators)."""
        text = page_text.lower()
        for selector in SCROLL_STABILIZATION_SELECTORS:
            if selector.lower().strip("[]").split("*=")[0].strip() in text:
                return False
        return True

    @staticmethod
    def is_supermarket_pattern(text: str) -> bool:
        """Check if text contains supermarket-specific patterns."""
        patterns = [
            r"\b(?:kg|g|ml|l|pcs|pack|sachet)\b",
            r"\b(?:omo|ariel|sunlight|toss|geisha)\b",
            r"\b(?:detergent|soap|washing|laundry)\b",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False