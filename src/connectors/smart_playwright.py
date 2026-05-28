from __future__ import annotations

import json
import os
import time
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import pandas as pd
from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from src.connectors.base import BaseConnector
from src.extract.heuristics import (
    COMMON_CARD_SELECTORS,
    COMMON_NEXT_SELECTORS,
    SUPERMARKET_CARD_SELECTORS,
    POPUP_ACCEPT_BUTTONS,
    POPUP_DISMISS_BUTTONS,
    POPUP_LOCATION_BUTTONS,
    POPUP_OVERLAYS,
    COOKIE_BANNER_SELECTORS,
    HOMEPAGE_INTERACTIONS,
    HOMEPAGE_CATEGORY_SELECTORS,
    CATEGORY_VERIFICATION_SELECTORS,
    MARKETING_TEXT_PATTERNS,
    VALID_CATEGORY_KEYWORDS,
    score_category_route,
    EcommerceHeuristics,
    SelectorAttempt,
    SiblingCardScore,
)
from src.transforms.product_identity import enrich_product_identity


class SmartPlaywrightConnector(BaseConnector):
    """
    Adaptive ecommerce/supermarket Playwright connector with Phase 1 stabilization.

    Improvements over baseline:
    - Network idle waiting + configurable post-load stabilization
    - Adaptive scroll-until-no-change with lazy-loading support
    - Popup/modal/cookie banner/branch selector handling
    - Improved supermarket + React ecommerce selectors
    - Extraction retry logic with delayed re-attempts
    - Lightweight diagnostics logging (selectors, candidates, confidence)
    - Debug mode: headed browser, slow_mo, viewport, tracing, screenshots

    The connector uses semantic DOM/card heuristics first, configured selectors
    second, and generic ecommerce structures last. Future AI-assisted parsing,
    OCR, vision extraction, supplier feed ingestion, ERP ingestion, Kafka
    streams, and distributed workers should plug in behind `_extract_page()`
    while preserving this connector contract and canonical output schema.
    """

    # JavaScript for DOM stabilization: returns element count
    _JS_ELEMENT_COUNT = """
    () => document.querySelectorAll('*').length
    """

    # JavaScript for scroll-until-no-change: returns new element count
    _JS_SCROLL_AND_COUNT = """
    () => {
        window.scrollBy(0, %d);
        return document.querySelectorAll('*').length;
    }
    """

    # JavaScript to check for loading indicators
    _JS_CHECK_LOADING = """
    () => {
        const loading = document.querySelectorAll('[class*="loading"], [class*="spinner"], [class*="skeleton"], [class*="placeholder"], [data-loading]');
        return loading.length;
    }
    """

    # JavaScript to count visible elements matching a pattern
    _JS_VISIBLE_CANDIDATES = """
    (selector) => {
        const elements = document.querySelectorAll(selector);
        const visible = [];
        for (const el of elements) {
            const box = el.getBoundingClientRect();
            if (box.width > 0 && box.height > 0 && box.top < window.innerHeight) {
                visible.push(el);
            }
        }
        return visible.length;
    }
    """

    # JavaScript to detect repeated classes on sibling divs
    _JS_REPEATED_CLASSES = """
    () => {
        const divs = document.querySelectorAll('div');
        const classCounts = {};
        for (const div of divs) {
            const cls = div.className;
            if (cls && typeof cls === 'string') {
                const parts = cls.trim().split(/\\s+/);
                for (const p of parts) {
                    classCounts[p] = (classCounts[p] || 0) + 1;
                }
            }
        }
        return Object.entries(classCounts)
            .filter(([_, count]) => count >= 3)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .map(([cls, count]) => ({ class: cls, count }));
    }
    """

    def __init__(
        self,
        url: str,
        selector: str | None = None,
        keyword: str | None = None,
        max_pages: int = 3,
        scroll_depth: int = 4,
        category: str | None = None,
        wait_for_timeout: int = 15000,
        retry_attempts: int = 2,
        scroll_step: int = 500,
        pre_actions: Optional[List[Dict[str, Any]]] = None,
        debug_mode: bool = False,
        **kwargs,
    ):
        super().__init__(
            url=url,
            selector=selector,
            keyword=keyword,
            source_type="smart_playwright",
            **kwargs,
        )
        self.max_pages = max_pages
        self.scroll_depth = scroll_depth
        self.category = category
        self.wait_for_timeout = wait_for_timeout
        self.retry_attempts = retry_attempts
        self.scroll_step = scroll_step
        self.pre_actions = pre_actions or []
        self.debug_mode = debug_mode
        self._trace_path: Optional[str] = None
        self.metrics: Dict[str, Any] = {
            "products_extracted": 0,
            "pages_crawled": 0,
            "extraction_confidence": 0.0,
            "selector_fallback_used": False,
            "extraction_failures": [],
            "extraction_strategy": None,
            "pagination_depth": 0,
            "duplicate_collapse_count": 0,
            "selector_attempts": [],
            "retry_attempts_used": 0,
            "popups_dismissed": 0,
            "cookie_banner_dismissed": 0,
            "scroll_iterations": 0,
            "dom_stabilization_ms": 0,
            "sibling_cards_detected": False,
            "sibling_card_score": 0.0,
            "debug_summary": {},
            "lazy_load_detected": False,
            "hydration_wait_ms": 0,
            "successful_selector": None,
            # --- Redirect detection metrics ---
            "redirect_detected": False,
            "redirect_fallback_detected": False,
            "redirect_retried": False,
            "redirect_count": 0,
            "initial_url": url,
            "final_url": None,
            # --- Navigation metrics ---
            "category_navigation_attempted": False,
            "category_navigation_success": False,
            "category_clicked": None,
            # --- Category verification metrics ---
            "category_verified": False,
            "breadcrumb_verified": False,
            "product_grid_verified": False,
            "route_changed": False,
            "category_confidence_score": 0.0,
            "category_item_count": 0,
            "xhr_endpoints_discovered": [],
            "extraction_quality_passed": False,
            "marketing_text_ratio": 0.0,
            "price_density": 0.0,
        }

    def _capture_debug_summary(self, page: Page, stage: str) -> None:
        """Capture a debug snapshot of page state at a given lifecycle stage."""
        try:
            dom_count = page.evaluate(self._JS_ELEMENT_COUNT)
            repeated = []
            try:
                repeated = page.evaluate(self._JS_REPEATED_CLASSES)
            except Exception:
                pass

            self.metrics["debug_summary"] = {
                "stage": stage,
                "page_title": page.title(),
                "final_url": page.url,
                "dom_node_count": dom_count,
                "html_length": len(page.content()),
                "repeated_classes": repeated[:5] if repeated else [],
            }
        except Exception:
            pass

    def _start_tracing(self, context: BrowserContext) -> None:
        """Start Playwright tracing for debug sessions."""
        if self.debug_mode:
            try:
                context.tracing.start(screenshots=True, snapshots=True, sources=True)
                self.logger.info("trace_started", event="tracing")
            except Exception as exc:
                self.logger.warning("trace_start_failed", event="tracing", error=str(exc))

    def _stop_tracing(self, context: BrowserContext, run_id: Optional[str] = None) -> Optional[str]:
        """Stop Playwright tracing and save trace.zip."""
        if not self.debug_mode:
            return None
        try:
            trace_dir = os.path.join(os.getcwd(), "traces")
            os.makedirs(trace_dir, exist_ok=True)
            trace_path = os.path.join(trace_dir, f"trace_{run_id or int(time.time())}.zip")
            context.tracing.stop(path=trace_path)
            self._trace_path = trace_path
            self.logger.info("trace_saved", event="trace_saved", trace_path=trace_path)
            return trace_path
        except Exception as exc:
            self.logger.warning("trace_stop_failed", event="tracing", error=str(exc))
            return None

    def _capture_screenshot(self, page: Page, name: str) -> Optional[str]:
        """Capture a screenshot if debug_mode is enabled."""
        if not self.debug_mode:
            return None
        try:
            screenshot_dir = os.path.join(os.getcwd(), "screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            path = os.path.join(screenshot_dir, f"{name}.png")
            page.screenshot(path=path, full_page=True)
            self.logger.info("screenshot_captured", event="screenshot", name=name, path=path)
            return path
        except Exception as exc:
            self.logger.warning("screenshot_failed", event="screenshot", name=name, error=str(exc))
            return None

    def _log_storage_diagnostics(self, page: Page, stage: str) -> None:
        """Log localStorage, sessionStorage, and cookies for debugging."""
        try:
            local_storage = page.evaluate("JSON.stringify(window.localStorage || {})")
            session_storage = page.evaluate("JSON.stringify(window.sessionStorage || {})")
        except Exception:
            local_storage = "{}"
            session_storage = "{}"

        try:
            cookies = page.context.cookies()
            cookie_names = [c["name"] for c in cookies[:20]]
        except Exception:
            cookie_names = []

        self.logger.info(
            "storage_diagnostics",
            event="storage_diagnostics",
            stage=stage,
            cookie_count=len(cookie_names),
            cookie_names=cookie_names[:10],
            has_local_storage=local_storage != "{}",
            has_session_storage=session_storage != "{}",
        )

    def _robust_click(self, page: Page, element, selector: str, description: str = "") -> bool:
        """Try multiple strategies to click an element, with retry."""
        # Pre-compute bounding box so None is handled gracefully
        try:
            box = element.bounding_box()
        except Exception:
            box = None

        for attempt in range(3):
            strategies = [
                ("scroll_normal", lambda: element.scroll_into_view_if_needed() or (time.sleep(0.2) or element.click(timeout=2000))),
                ("force_click", lambda: page.locator(selector).first.click(force=True, timeout=2000)),
                ("js_click", lambda: page.evaluate("el => el.click()", element)),
            ]
            # Only add mouse_click strategy if bounding_box is available
            if box:
                strategies.append(("mouse_click", lambda: page.mouse.click(
                    box["x"] + box["width"] / 2,
                    box["y"] + box["height"] / 2,
                )))

            for strategy_name, strategy_fn in strategies:
                try:
                    strategy_fn()
                    self.logger.info(
                        "robust_click_success",
                        event="click",
                        strategy=strategy_name,
                        description=description,
                        attempt=attempt + 1,
                    )
                    time.sleep(0.3)
                    return True
                except Exception:
                    continue
            time.sleep(0.5)
        self.logger.warning("robust_click_failed", event="click", description=description, selector=selector)
        return False

    def _verify_category_page(self, page: Page, category_keyword: str) -> Dict[str, Any]:
        """Verify that the current page is a valid category page.

        Checks breadcrumb text, H1/H2 headings, product-grid existence,
        URL route change, and page title. Returns a dict with all
        verification flags and a category_confidence_score.
        """
        current_url = page.url
        page_title = page.title().lower()
        result: Dict[str, Any] = {
            "category_verified": False,
            "breadcrumb_verified": False,
            "heading_verified": False,
            "product_grid_verified": False,
            "homepage_detected": False,
            "route_changed": False,
            "category_confidence_score": 0.0,
            "category_item_count": 0,
            "breadcrumb_text": "",
            "page_title": page.title(),
        }

        # 1. Route changed: URL path is not just base URL
        parsed = urlparse(current_url)
        base_path = urlparse(self.metrics.get("initial_url", self.url)).path.rstrip("/")
        current_path = parsed.path.rstrip("/")
        result["route_changed"] = current_path != "/" and current_path != "" and current_path != base_path

        # 2. Homepage detection
        result["homepage_detected"] = "home" in page_title and not result["route_changed"]

        # 3. Breadcrumb verification
        try:
            for sel in CATEGORY_VERIFICATION_SELECTORS:
                breadcrumb_elements = page.query_selector_all(sel)
                for el in breadcrumb_elements[:5]:
                    text = el.inner_text().strip().lower()
                    if text and category_keyword in text:
                        result["breadcrumb_verified"] = True
                        result["breadcrumb_text"] = text[:100]
                        break
                if result["breadcrumb_verified"]:
                    break
        except Exception:
            pass

        # 4. Heading verification (H1/H2)
        try:
            headings = page.query_selector_all("h1, h2")
            for h in headings:
                text = h.inner_text().strip().lower()
                if text and category_keyword in text:
                    result["heading_verified"] = True
                    break
        except Exception:
            pass

        # 5. Product grid verification
        try:
            all_selectors = SUPERMARKET_CARD_SELECTORS + COMMON_CARD_SELECTORS
            max_count = 0
            for sel in all_selectors:
                elements = page.query_selector_all(sel)
                if len(elements) > max_count:
                    max_count = len(elements)
            result["category_item_count"] = max_count
            result["product_grid_verified"] = max_count >= 3
        except Exception:
            pass

        # 6. Composite confidence score (0-100)
        score = 0
        if result["route_changed"]:
            score += 20
        if not result["homepage_detected"]:
            score += 10
        if result["breadcrumb_verified"]:
            score += 25
        if result["heading_verified"]:
            score += 25
        if result["product_grid_verified"]:
            score += 20

        # Stricter: route must change AND at least one structural indicator must match
        result["category_verified"] = (
            result["route_changed"]
            and (result["breadcrumb_verified"] or result["heading_verified"] or result["product_grid_verified"])
            and score >= 40
        )
        result["category_confidence_score"] = score

        return result

    def _verify_extraction_quality(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate extraction quality, rejecting marketing blocks and hero content.

        Returns quality metrics and whether extraction passed quality checks.
        """
        result: Dict[str, Any] = {
            "extraction_quality_passed": False,
            "marketing_text_ratio": 0.0,
            "price_density": 0.0,
            "avg_title_length": 0.0,
            "total_records": len(records),
        }

        if not records:
            return result

        marketing_count = 0
        price_count = 0
        title_lengths = []

        for record in records:
            name = record.get("product_name", "") or ""
            lower_name = name.lower()

            # Count marketing pattern hits
            for pattern in MARKETING_TEXT_PATTERNS:
                if pattern in lower_name:
                    marketing_count += 1
                    break

            # Count prices
            if record.get("current_price") is not None:
                price_count += 1

            # Track title length
            title_lengths.append(len(name))

        total = len(records)
        result["marketing_text_ratio"] = round(marketing_count / total, 3) if total > 0 else 0.0
        result["price_density"] = round(price_count / total, 3) if total > 0 else 0.0
        result["avg_title_length"] = round(sum(title_lengths) / total, 1) if total > 0 else 0.0

        # Quality criteria:
        # - Average title length should be < 120 chars (reject marketing paragraphs)
        # - Price density should be > 10% (reject marketing-only content)
        # - Marketing text ratio should be < 30%
        quality_passed = (
            result["avg_title_length"] < 120
            and result["price_density"] > 0.1
            and result["marketing_text_ratio"] < 0.3
        )
        result["extraction_quality_passed"] = quality_passed

        return result

    def _inspect_xhr_requests(self, page: Page) -> List[str]:
        """Capture XHR/fetch API endpoints called after page interactions.

        Returns a list of discovered API endpoint URLs from the current page.
        """
        endpoints = []
        try:
            # Use page evaluate to get performance entries (XHR/fetch requests)
            entries = page.evaluate("""() => {
                try {
                    return performance.getEntriesByType('resource')
                        .filter(e => e.initiatorType === 'fetch' || e.initiatorType === 'xmlhttprequest')
                        .map(e => e.name);
                } catch(e) { return []; }
            }""")
            if entries:
                # Filter for product/category-related endpoints
                for url in entries:
                    lower = url.lower()
                    if any(kw in lower for kw in ["product", "category", "api", "graphql", "search", "soap", "detergent"]):
                        endpoints.append(url)
        except Exception:
            pass

        if endpoints:
            self.logger.info(
                "xhr_endpoints_discovered",
                event="xhr_inspection",
                endpoint_count=len(endpoints),
                endpoints=endpoints[:10],
            )
            self.metrics["xhr_endpoints_discovered"] = endpoints[:10]

        return endpoints

    def _extract_dom_links(self, page: Page) -> List[Dict[str, Any]]:
        """Extract all anchor hrefs from the DOM, including hidden/preloaded links."""
        try:
            links = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    href: a.href || '',
                    text: (a.innerText || a.getAttribute('aria-label') || a.getAttribute('title') || '').trim(),
                    rel: a.rel || '',
                    classes: a.className || '',
                }));
            }""")
        except Exception:
            return []

        candidates: List[Dict[str, Any]] = []
        for entry in links:
            href = entry.get("href", "")
            if not href:
                continue
            candidates.append({
                "href": href,
                "text": (entry.get("text") or "").strip(),
                "source": "dom",
                "rel": entry.get("rel", ""),
                "classes": entry.get("classes", ""),
            })
        return candidates

    def _extract_routes_from_json(self, payload: Any, response_url: str) -> List[Dict[str, Any]]:
        """Extract candidate category routes from JSON network responses."""
        candidates: List[Dict[str, Any]] = []

        def _walk(body: Any, context_text: str = "") -> None:
            if isinstance(body, dict):
                for key, value in body.items():
                    _walk(value, f"{context_text} {key}".strip())
            elif isinstance(body, list):
                for item in body:
                    _walk(item, context_text)
            elif isinstance(body, str):
                candidate = body.strip()
                if not candidate:
                    return
                lower = candidate.lower()
                if lower.startswith("/") or lower.startswith("http"):
                    href = urljoin(response_url, candidate)
                    candidates.append({
                        "href": href,
                        "text": context_text,
                        "source": "xhr",
                        "response_url": response_url,
                    })
                elif any(kw in lower for kw in ["soap", "detergent", "cleaning", "laundry", "household"]):
                    if "/" in lower or "-" in lower:
                        href = urljoin(response_url, candidate)
                        candidates.append({
                            "href": href,
                            "text": context_text + " " + candidate,
                            "source": "xhr",
                            "response_url": response_url,
                        })

        _walk(payload)
        return candidates

    def _save_category_debug_artifacts(self, candidates: List[Dict[str, Any]], selected: Optional[Dict[str, Any]] = None) -> None:
        """Write discovered category routes to a debug artifact file."""
        try:
            debug_dir = os.path.join(os.getcwd(), "debug", "quickmart")
            os.makedirs(debug_dir, exist_ok=True)
            artifact = {
                "selected_route": selected or {},
                "candidates": candidates,
                "timestamp": int(time.time()),
                "url": self.url,
            }
            path = os.path.join(debug_dir, "category_routes.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(artifact, handle, indent=2)
            self.logger.info("category_routes_saved", event="debug_artifact", path=path)
        except Exception as exc:
            self.logger.warning("category_routes_save_failed", event="debug_artifact", error=str(exc))

    def _discover_nested_category_links(self, page: Page, category_keyword: str = "detergent") -> List[Dict[str, Any]]:
        """Discover actual nested category routes from menus, hidden DOM links, and XHR responses."""
        candidates: List[Dict[str, Any]] = []
        json_routes: List[Dict[str, Any]] = []

        def _on_json_response(response):
            try:
                ctype = response.headers.get("content-type", "").lower()
                if "application/json" not in ctype:
                    return
                body = response.json()
                json_routes.extend(self._extract_routes_from_json(body, response.url))
            except Exception:
                return

        page.on("response", _on_json_response)

        menu_openers = [
            "button:has-text('Shop by Category')",
            "button:has-text('All Categories')",
            "button:has-text('Shop All')",
            "button:has-text('View All')",
            "button[class*='hamburger' i]",
            "button[aria-label*='menu' i]",
            "button[aria-label*='navigation' i]",
            "a[href*='/shop' i]",
            "a[href*='/category' i]",
        ]

        accordion_selectors = [
            "button[class*='accordion' i]",
            "button:has-text('Expand')",
            "button:has-text('More')",
            "button:has-text('See more')",
            "div[class*='accordion' i]",
        ]

        for selector in menu_openers:
            try:
                elements = page.query_selector_all(selector)
                for element in elements[:2]:
                    if element.is_visible(timeout=1000):
                        try:
                            element.hover(timeout=2000)
                        except Exception:
                            pass
                        try:
                            element.click(timeout=2000)
                        except Exception:
                            pass
                        page.wait_for_timeout(500)
            except Exception:
                continue

        for selector in accordion_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements[:3]:
                    if element.is_visible(timeout=1000):
                        try:
                            element.click(timeout=1500)
                        except Exception:
                            pass
                        page.wait_for_timeout(300)
            except Exception:
                continue

        try:
            page.evaluate("window.scrollBy(0, window.innerHeight)")
        except Exception:
            pass

        candidates.extend(self._extract_dom_links(page))
        candidates.extend(json_routes)

        unique = {}
        valid_candidates: List[Dict[str, Any]] = []
        for candidate in candidates:
            href = candidate.get("href", "").strip()
            text = candidate.get("text", "") or ""
            if not href:
                continue
            if href.endswith("#"):
                continue
            if href not in unique:
                unique[href] = candidate
                valid_candidates.append({
                    "href": href,
                    "text": text[:120],
                    "source": candidate.get("source", "dom"),
                    "response_url": candidate.get("response_url", ""),
                    "score": 0,
                })

        scored: List[Dict[str, Any]] = []
        for candidate in valid_candidates:
            score = score_category_route(candidate["href"], candidate["text"])
            if score > -50:
                candidate["score"] = score
                scored.append(candidate)

        scored.sort(key=lambda item: item["score"], reverse=True)
        self._save_category_debug_artifacts(scored, scored[0] if scored else None)
        return scored

    def _route_pattern_score(self, url: str) -> float:
        """Apply URL pattern intelligence for category vs product routes."""
        path = urlparse(url.lower()).path or ""
        score = 0.0
        boosts = [
            "category",
            "detergent",
            "laundry",
            "soap",
            "cleaning",
            "household",
            "products",
            "collection",
            "catalog",
            "shop",
            "browse",
        ]
        penalties = [
            r"[-\d]{3,}$",
            r"\b(\d{2,4}g|\d{1,3}kg|ml|l|litre|kg)\b",
            r"[a-z0-9]{6,}-[a-z0-9]{2,}$",
        ]
        for boost in boosts:
            if boost in path:
                score += 0.15
        for regex in penalties:
            if re.search(regex, path):
                score -= 0.35
        last_segment = path.rstrip("/").split("/")[-1] if path else ""
        if last_segment and len(last_segment) > 12 and any(ch.isdigit() for ch in last_segment) and not any(k in last_segment for k in boosts):
            score -= 0.2
        return round(score, 3)

    def _is_valid_plp_route(self, route_info: Dict[str, Any]) -> bool:
        thresholds = {
            "min_product_cards": 5,
            "min_unique_links": 4,
            "min_repeated_prices": 3,
            "min_confidence": 0.45,
        }
        if route_info.get("route_type") != "category_listing_page":
            return False
        if route_info.get("classification_confidence", 0.0) < thresholds["min_confidence"]:
            return False
        if route_info.get("product_card_count", 0) < thresholds["min_product_cards"]:
            return False
        if route_info.get("unique_product_links", 0) < thresholds["min_unique_links"]:
            return False
        if route_info.get("repeated_price_count", 0) < thresholds["min_repeated_prices"]:
            return False
        return True

    def _normalize_route_url(self, href: str) -> str:
        try:
            p = urlparse(href)
            norm = p._replace(query="", fragment="").geturl()
            # strip trailing slash
            if norm.endswith("/"):
                norm = norm.rstrip("/")
            return norm
        except Exception:
            return href


    def _evaluate_candidate_routes(self, context: BrowserContext, routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Navigate each candidate route in an isolated temp page and evaluate its page type and route validity.

        Implements prioritization, deduplication, max-cap, timeout protection, caching and convergence.
        """
        diagnostics: List[Dict[str, Any]] = []
        debug_dir = os.path.join(os.getcwd(), "debug", "quickmart")
        os.makedirs(debug_dir, exist_ok=True)
        base_url = f"{urlparse(self.url).scheme}://{urlparse(self.url).netloc}"
        # telemetry counters
        routes_discovered = len(routes or [])
        self.metrics["routes_discovered"] = routes_discovered
        route_selectors = {
            "pagination": [
                "a[rel='next']",
                "button[aria-label*='next' i]",
                ".pagination",
                ".pager",
                ".page-numbers",
                ".load-more",
                ".pagination-next",
            ],
            "sorting": [
                "select[class*='sort' i]",
                "[class*='sort' i]",
                "[aria-label*='sort' i]",
                ".sort-by",
                ".sorting",
                ".order-by",
            ],
            "filters": [
                "[class*='filter' i]",
                "[data-filter]",
                ".filter-sidebar",
                ".facets",
                ".facet",
                ".sidebar-filters",
            ],
        }
        # Deduplicate routes (normalize hrefs)
        seen_norm = set()
        unique_routes: List[Dict[str, Any]] = []
        for r in routes:
            href = (r.get("href") or r.get("url") or "").strip()
            if not href:
                continue
            if href.startswith("/"):
                href = base_url + href
            if not href.startswith("http"):
                continue
            norm = self._normalize_route_url(href)
            if norm in seen_norm:
                continue
            seen_norm.add(norm)
            r["_normalized_href"] = norm
            unique_routes.append(r)

        self.metrics["routes_deduplicated"] = len(unique_routes)

        # Prioritize routes with category keywords, deprioritize promo/blog routes
        priority_keywords = ["detergent", "soap", "cleaning", "laundry", "household"]
        deprioritize_keywords = ["promo", "offer", "deal", "banner", "blog", "recipe", "brand"]

        def route_score_fn(r: Dict[str, Any]) -> int:
            href = (r.get("href") or r.get("url") or "").lower()
            text = (r.get("text") or "").lower()
            score = 0
            for kw in priority_keywords:
                if kw in href or kw in text:
                    score += 10
            for kw in deprioritize_keywords:
                if kw in href or kw in text:
                    score -= 5
            return score

        unique_routes.sort(key=route_score_fn, reverse=True)

        # Max cap and timeout
        max_to_eval = getattr(self, "max_routes_to_evaluate", 5)
        max_total_seconds = getattr(self, "max_route_evaluation_seconds", 30)
        max_to_eval = max(1, int(max_to_eval))
        start_time = time.time()

        # Try cached validated routes first
        cache_path = os.path.join(debug_dir, "validated_routes.json")
        try:
            cached = []
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as fh:
                    cached = json.load(fh).get("validated", [])
            for entry in cached:
                # only consider routes for same base
                if not entry.get("url"):
                    continue
                if urlparse(entry["url"]).netloc != urlparse(self.url).netloc:
                    continue
                # quick validate cached route using temp page
                temp_page = context.new_page()
                try:
                    temp_page.goto(entry["url"], timeout=15000)
                    self._wait_for_stabilization(temp_page)
                    self._wait_for_dom_and_card_stabilization(temp_page)
                    classification = self._classify_page_type(temp_page, persist_debug=False)
                    signals = classification.get("signals", {})
                    if (classification.get("route_type") == "category_listing_page" and
                            classification.get("confidence", 0.0) >= 0.6 and
                            signals.get("product_card_count", 0) >= 5):
                        # accept cached route as valid
                        diagnostics.append({
                            "url": entry["url"],
                            "route_type": classification.get("route_type"),
                            "classification_confidence": classification.get("confidence", 0.0),
                            "product_card_count": signals.get("product_card_count", 0),
                            "unique_product_links": signals.get("unique_product_links", 0),
                            "repeated_price_count": signals.get("repeated_price_count", 0),
                            "final_route_score": entry.get("final_route_score", 0.0),
                            "signals": signals,
                            "cached": True,
                        })
                        self.metrics["convergence_reached"] = True
                        self.metrics["selected_route"] = entry["url"]
                        self.metrics["convergence_reason"] = "cached_validated_route"
                        try:
                            if not temp_page.is_closed():
                                temp_page.close()
                        except Exception:
                            pass
                        # persist validated routes file unchanged
                        return diagnostics
                except Exception:
                    try:
                        if not temp_page.is_closed():
                            temp_page.close()
                    except Exception:
                        pass
                    continue
        except Exception:
            pass

        temp_page = context.new_page()
        self.metrics["temp_page_created"] = self.metrics.get("temp_page_created", 0) + 1
        self.logger.info("temp_page_created", event="route_evaluation")
        try:
            routes_to_iterate = unique_routes[:max_to_eval]
            evaluated_count = 0
            rejected_count = 0
            convergence_reached = False
            selected_route = None
            convergence_reason = None

            for route in routes_to_iterate:
                # timeout guard
                if time.time() - start_time > max_total_seconds:
                    self.logger.warning("route_evaluation_timeout", event="route_evaluation", elapsed=int(time.time() - start_time))
                    break
                href = route.get("href") or route.get("url")
                if not href:
                    continue
                href = href.strip()
                if href.startswith("/"):
                    href = base_url + href
                if not href.startswith("http"):
                    continue
                try:
                    if temp_page.is_closed():
                        temp_page = context.new_page()
                        self.metrics["page_recreated"] = self.metrics.get("page_recreated", 0) + 1
                        self.logger.info("page_recreated", event="route_evaluation", reason="temp_page_closed")
                    temp_page.goto(href, timeout=60000)
                    self._wait_for_stabilization(temp_page)
                    self._wait_for_dom_and_card_stabilization(temp_page)
                    # avoid writing per-candidate debug artefacts
                    classification = self._classify_page_type(temp_page, persist_debug=False)
                    signals = classification.get("signals", {})
                    has_pagination = any(len(temp_page.query_selector_all(sel)) > 0 for sel in route_selectors["pagination"])
                    has_sorting = any(len(temp_page.query_selector_all(sel)) > 0 for sel in route_selectors["sorting"])
                    has_filters = any(len(temp_page.query_selector_all(sel)) > 0 for sel in route_selectors["filters"])
                    final_score = classification.get("confidence", 0.0)
                    final_score += min(0.15, signals.get("product_card_count", 0) / 10 * 0.15)
                    final_score += min(0.15, signals.get("unique_product_links", 0) / 10 * 0.15)
                    final_score += min(0.15, signals.get("repeated_price_count", 0) / 10 * 0.15)
                    final_score += 0.15 if has_pagination else 0.0
                    final_score += 0.15 if has_sorting else 0.0
                    final_score += 0.15 if has_filters else 0.0
                    final_score += self._route_pattern_score(href)
                    if classification.get("route_type") == "product_detail_page":
                        final_score -= 0.35
                    final_score = round(final_score, 3)
                    rejected_reason = None
                    if not self._is_valid_plp_route({
                        "route_type": classification.get("route_type"),
                        "classification_confidence": classification.get("confidence", 0.0),
                        "product_card_count": signals.get("product_card_count", 0),
                        "unique_product_links": signals.get("unique_product_links", 0),
                        "repeated_price_count": signals.get("repeated_price_count", 0),
                    }):
                        if classification.get("route_type") == "product_detail_page":
                            rejected_reason = "product_detail_page"
                        elif signals.get("url_looks_like_product"):
                            rejected_reason = "product_slug_detected"
                        elif signals.get("product_card_count", 0) < 5:
                            rejected_reason = "insufficient_repeated_product_cards"
                        elif signals.get("unique_product_links", 0) < 4:
                            rejected_reason = "insufficient_unique_product_links"
                        elif signals.get("repeated_price_count", 0) < 3:
                            rejected_reason = "insufficient_repeated_prices"
                        else:
                            rejected_reason = "low_classification_confidence"
                    diagnostics.append({
                        "url": href,
                        "route_type": classification.get("route_type"),
                        "classification_confidence": classification.get("confidence", 0.0),
                        "product_card_count": signals.get("product_card_count", 0),
                        "unique_product_links": signals.get("unique_product_links", 0),
                        "repeated_price_count": signals.get("repeated_price_count", 0),
                        "repeated_add_to_cart_count": signals.get("repeated_add_to_cart_count", 0),
                        "breadcrumb_depth": signals.get("breadcrumb_depth", 0),
                        "has_filters": has_filters,
                        "has_sorting": has_sorting,
                        "has_pagination": has_pagination,
                        "url_pattern_score": self._route_pattern_score(href),
                        "rejected_reason": rejected_reason,
                        "final_route_score": final_score,
                        "signals": signals,
                    })
                    evaluated_count += 1

                    # Check convergence conditions: strict category, high confidence, repeated cards/prices and extraction sample quality
                    try:
                        meets_basic = (
                            classification.get("route_type") == "category_listing_page" and
                            classification.get("confidence", 0.0) >= 0.75 and
                            signals.get("product_card_count", 0) >= 5 and
                            signals.get("repeated_price_count", 0) >= 3
                        )
                        sample_quality = False
                        if meets_basic:
                            # run a light extraction sample to verify extraction quality
                            try:
                                records, _ = self._extract_quickmart_products(temp_page)
                                sample = records[:12]
                                qres = self._verify_extraction_quality(sample)
                                sample_quality = qres.get("extraction_quality_passed", False)
                            except Exception:
                                sample_quality = False

                        if meets_basic and sample_quality:
                            convergence_reached = True
                            selected_route = href
                            convergence_reason = "high_confidence_and_extraction_quality"
                            self.metrics["convergence_reached"] = True
                            self.metrics["selected_route"] = selected_route
                            self.metrics["convergence_reason"] = convergence_reason
                            # persist validated route cache
                            try:
                                entry = {
                                    "url": selected_route,
                                    "final_route_score": final_score,
                                    "timestamp": int(time.time()),
                                }
                                cached_list = {"validated": [entry]}
                                with open(cache_path, "w", encoding="utf-8") as cf:
                                    json.dump(cached_list, cf, indent=2)
                                self.logger.info("validated_route_cached", event="route_evaluation", path=cache_path, route=selected_route)
                            except Exception:
                                pass
                            # write page classification only for winning route
                            try:
                                self._classify_page_type(temp_page, persist_debug=True)
                            except Exception:
                                pass
                            break
                    except Exception:
                        pass
                except Exception as exc:
                    self.metrics["route_evaluation_navigation_error"] = self.metrics.get("route_evaluation_navigation_error", 0) + 1
                    rejected_count += 1
                    self.logger.warning("route_evaluation_navigation_error", event="route_evaluation", route=href, error=str(exc))
                    diagnostics.append({
                        "url": href,
                        "route_type": "unknown",
                        "classification_confidence": 0.0,
                        "product_card_count": 0,
                        "unique_product_links": 0,
                        "repeated_price_count": 0,
                        "repeated_add_to_cart_count": 0,
                        "breadcrumb_depth": 0,
                        "has_filters": False,
                        "has_sorting": False,
                        "has_pagination": False,
                        "url_pattern_score": self._route_pattern_score(href),
                        "rejected_reason": f"navigation_failed: {str(exc)}",
                        "final_route_score": 0.0,
                        "signals": {},
                    })
                    
            # end for
        finally:
            try:
                if temp_page and not temp_page.is_closed():
                    temp_page.close()
                    self.metrics["temp_page_closed"] = self.metrics.get("temp_page_closed", 0) + 1
                    self.logger.info("temp_page_closed", event="route_evaluation")
            except Exception:
                pass
            # finalize telemetry
            self.metrics["routes_evaluated"] = evaluated_count
            self.metrics["routes_rejected"] = rejected_count
            if convergence_reached:
                self.metrics["convergence_reached"] = True
                self.metrics["selected_route"] = selected_route
                self.metrics["convergence_reason"] = convergence_reason
            else:
                self.metrics["convergence_reached"] = False
        try:
            path = os.path.join(debug_dir, "route_evaluation.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"timestamp": int(time.time()), "evaluations": diagnostics}, fh, indent=2)
            self.logger.info("route_evaluation_saved", event="debug_artifact", path=path)
        except Exception:
            pass
        self.metrics["route_evaluations"] = diagnostics
        return diagnostics
    def _detect_primary_product_container(self, page: Page) -> Dict[str, Any]:
        """Detect a dominant primary product container on a page (PDP indicators).

        Returns a dict with keys: dominant (bool), primary_price_count, primary_cta_count,
        related_products_count, confidence (0-1).
        """
        info: Dict[str, Any] = {
            "dominant": False,
            "primary_price_count": 0,
            "primary_cta_count": 0,
            "related_products_count": 0,
            "confidence": 0.0,
        }
        try:
            # Candidate selectors for main product container
            candidates = []
            selectors = ["[class*='product-detail' i]", "[id*='product' i]", "[data-product-id]", "main", "article", "section"]
            for sel in selectors:
                try:
                    els = page.query_selector_all(sel)
                    for el in els[:6]:
                        candidates.append(el)
                except Exception:
                    continue

            # Heuristic: choose candidate with h1/title and price and atc
            best = None
            best_score = 0
            for el in candidates:
                score = 0
                try:
                    # title presence (h1 preferred)
                    try:
                        title_node = el.query_selector("h1")
                        if title_node and (title_node.inner_text() or '').strip():
                            score += 30
                    except Exception:
                        pass
                    # price elements inside
                    try:
                        price_nodes = el.query_selector_all("[class*='price' i], [itemprop='price'], .price")
                        if price_nodes:
                            score += 20
                    except Exception:
                        price_nodes = []
                    # add-to-cart inside
                    try:
                        atc_nodes = el.query_selector_all("button:has-text('Add to Cart'), button:has-text('Buy Now'), a:has-text('Add to Cart')")
                        if atc_nodes:
                            score += 20
                    except Exception:
                        atc_nodes = []
                    # description length
                    try:
                        desc = el.query_selector_all("[class*='description' i], [id*='description' i], [itemprop='description']")
                        if desc:
                            score += 10
                    except Exception:
                        pass
                    # reviews/specs
                    try:
                        rev = el.query_selector_all("[id*='review' i], [class*='review' i], [data-test*='reviews' i]")
                        if rev:
                            score += 10
                    except Exception:
                        pass
                except Exception:
                    continue

                if score > best_score:
                    best_score = score
                    best = el

            if best and best_score > 30:
                # measure primary counts
                try:
                    price_nodes = best.query_selector_all("[class*='price' i], [itemprop='price'], .price")
                    atc_nodes = best.query_selector_all("button:has-text('Add to Cart'), button:has-text('Buy Now'), a:has-text('Add to Cart')")
                    related = page.query_selector_all("[class*='related' i], [class*='also-bought' i], [class*='you-may' i]")
                    info["primary_price_count"] = len(price_nodes)
                    info["primary_cta_count"] = len(atc_nodes)
                    info["related_products_count"] = len(related)
                    info["dominant"] = True
                    # confidence scaled
                    info["confidence"] = min(1.0, best_score / 80.0 + (1.0 if len(price_nodes) and len(atc_nodes) else 0.0))
                except Exception:
                    pass

        except Exception:
            pass
        return info

    def _classify_page_type(self, page: Page, persist_debug: bool = False) -> Dict[str, Any]:
        """Classify the current page into one of: homepage, category_listing_page,
        product_detail_page, search_results_page, marketing_page, unknown.

        Returns a dict with signals and classification confidence.
        """
        url = page.url or ""
        path = urlparse(url).path or ""
        lower_url = url.lower()

        signals: Dict[str, Any] = {
            "url": url,
            "breadcrumb_depth": 0,
            "product_card_count": 0,
            "unique_product_links": 0,
            "repeated_price_count": 0,
            "repeated_add_to_cart_count": 0,
            "has_product_schema": False,
            "og_type": None,
            "has_add_to_cart": False,
            "has_quantity_selector": False,
            "has_reviews_widget": False,
            "has_related_products": False,
            # structural PDP/PLP signals
            "dominant_product": False,
            "primary_price_count": 0,
            "primary_cta_count": 0,
            "related_products_count": 0,
            "grid_consistency_score": 0.0,
            "primary_product_confidence": 0.0,
        }

        try:
            # Breadcrumb depth
            bc = 0
            for sel in CATEGORY_VERIFICATION_SELECTORS:
                try:
                    els = page.query_selector_all(sel)
                    for el in els[:1]:
                        txt = (el.inner_text() or "").strip()
                        if txt:
                            # approximate depth by splitting on separators
                            bc = max(bc, len([p for p in re.split(r"[>/\\|\\-]", txt) if p.strip()]))
                except Exception:
                    continue
            signals["breadcrumb_depth"] = bc
        except Exception:
            signals["breadcrumb_depth"] = 0

        try:
            # Count repeated product-card occurrences
            card_selectors = EcommerceHeuristics.get_all_card_selectors()
            total_cards = 0
            unique_links = set()
            price_hits = 0
            add_to_cart_hits = 0
            for sel in card_selectors:
                try:
                    els = page.query_selector_all(sel)
                    for el in els[:200]:
                        total_cards += 1
                        try:
                            href = self._first_attr(el, "a[href]", "href")
                            if href:
                                unique_links.add(href)
                        except Exception:
                            pass
                        try:
                            txt = el.inner_text() or ""
                            if EcommerceHeuristics.parse_price(txt)[0] is not None:
                                price_hits += 1
                            if any(w in txt.lower() for w in ["add to cart", "buy now", "add to basket", "cart"]):
                                add_to_cart_hits += 1
                        except Exception:
                            continue
                except Exception:
                    continue

            signals["product_card_count"] = total_cards
            signals["unique_product_links"] = len(unique_links)
            signals["repeated_price_count"] = price_hits
            signals["repeated_add_to_cart_count"] = add_to_cart_hits
        except Exception:
            pass

        # Detect dominant/primary product container and related-products
        try:
            primary_info = self._detect_primary_product_container(page)
            if primary_info:
                signals["dominant_product"] = primary_info.get("dominant", False)
                signals["primary_price_count"] = primary_info.get("primary_price_count", 0)
                signals["primary_cta_count"] = primary_info.get("primary_cta_count", 0)
                signals["related_products_count"] = primary_info.get("related_products_count", 0)
                signals["primary_product_confidence"] = round(primary_info.get("confidence", 0.0), 3)
                # simple grid consistency metric: ratio of repeated card count to unique links
                try:
                    if signals.get("unique_product_links", 0) > 0:
                        signals["grid_consistency_score"] = round(min(1.0, signals.get("product_card_count", 0) / max(1, signals.get("unique_product_links", 1))), 3)
                except Exception:
                    signals["grid_consistency_score"] = 0.0
        except Exception:
            pass

        try:
            # Detect add-to-cart and quantity selectors globally
            try:
                atc = page.query_selector_all("button:has-text('Add to Cart'), button:has-text('Buy Now'), a:has-text('Add to Cart')")
                signals["has_add_to_cart"] = len(atc) > 0
            except Exception:
                signals["has_add_to_cart"] = False
            try:
                qty = page.query_selector_all("input[type='number'], select[name*='qty' i], [class*='quantity' i]")
                signals["has_quantity_selector"] = len(qty) > 0
            except Exception:
                signals["has_quantity_selector"] = False
            try:
                rev = page.query_selector_all("[id*='review' i], [class*='review' i], [data-test*='reviews' i]")
                signals["has_reviews_widget"] = len(rev) > 0
            except Exception:
                signals["has_reviews_widget"] = False
            try:
                rel = page.query_selector_all("[class*='related' i], [class*='you-may' i], [class*='also-bought' i]")
                signals["has_related_products"] = len(rel) > 0
            except Exception:
                signals["has_related_products"] = False
        except Exception:
            pass

        # JSON-LD product schema detection
        try:
            scripts = page.query_selector_all("script[type='application/ld+json']")
            has_product_schema = False
            for s in scripts[:20]:
                try:
                    txt = s.inner_text() or ""
                    if '"@type"' in txt and 'product' in txt.lower():
                        has_product_schema = True
                        break
                except Exception:
                    continue
            signals["has_product_schema"] = has_product_schema
        except Exception:
            signals["has_product_schema"] = False

        # OpenGraph metadata
        try:
            og = None
            node = page.query_selector("meta[property='og:type']")
            if node:
                og = node.get_attribute("content")
            signals["og_type"] = og
        except Exception:
            signals["og_type"] = None

        # URL heuristics for product slugs
        def url_looks_like_product(path_str: str) -> bool:
            if re.search(r"[-\d]{3,}$", path_str):
                return True
            if re.search(r"\b(\d{2,4}g|\d{1,3}kg|ml|l|litre|kg)\b", path_str):
                return True
            if re.search(r"[a-z0-9]{6,}-[a-z0-9]{2,}$", path_str):
                return True
            return False

        is_product_slug = url_looks_like_product(path)
        signals["url_looks_like_product"] = is_product_slug

        # Heuristic scoring for classification
        score = 0.0
        reasons: Dict[str, Any] = {}

        # Strong PDP signals
        if signals.get("has_product_schema"):
            score += 0.35; reasons['product_schema'] = True
        if signals.get("has_add_to_cart") and signals.get("has_quantity_selector"):
            score += 0.25; reasons['add_to_cart_with_qty'] = True
        if signals.get("has_reviews_widget"):
            score += 0.1; reasons['reviews'] = True
        if signals.get("breadcrumb_depth", 0) >= 3:
            score += 0.05; reasons['breadcrumb_depth'] = signals.get('breadcrumb_depth')
        if signals.get("unique_product_links", 0) <= 2 and signals.get("product_card_count", 0) <= 3:
            score += 0.15; reasons['single_product_dominant'] = True
        if signals.get("url_looks_like_product"):
            score += 0.25; reasons['product_slug'] = True

        # Category signals
        cat_score = 0.0
        if signals.get("product_card_count", 0) >= 6:
            cat_score += 0.4; reasons['many_cards'] = signals.get('product_card_count')
        if signals.get("unique_product_links", 0) >= 5:
            cat_score += 0.3; reasons['many_links'] = signals.get('unique_product_links')
        if signals.get("repeated_price_count", 0) >= 4:
            cat_score += 0.2; reasons['many_prices'] = signals.get('repeated_price_count')
        if signals.get("repeated_add_to_cart_count", 0) >= 3:
            cat_score += 0.1; reasons['many_add_to_cart'] = signals.get('repeated_add_to_cart_count')

        # Combine into final classification confidence
        pdp_conf = score
        plp_conf = cat_score

        classification = "unknown"
        confidence = 0.0
        if pdp_conf > plp_conf and pdp_conf >= 0.4:
            classification = "product_detail_page"
            confidence = round(min(1.0, pdp_conf), 3)
        elif plp_conf > pdp_conf and plp_conf >= 0.4:
            classification = "category_listing_page"
            confidence = round(min(1.0, plp_conf), 3)
        else:
            # Additional checks for homepage or search
            try:
                body = (page.inner_text('body') or '').lower()
            except Exception:
                body = ''
            if 'search' in lower_url or 'q=' in lower_url or 'search' in body[:200]:
                classification = 'search_results_page'
                confidence = 0.5
            else:
                # Homepage detection: prefer hero/banner/carousel presence and lack of repeated product grids
                try:
                    hero_count = 0
                    for hsel in ["[class*='hero' i]", "[class*='carousel' i]", "[class*='homepage' i]", "[id*='hero' i]", "[class*='banner' i]"]:
                        try:
                            hero_count += len(page.query_selector_all(hsel))
                        except Exception:
                            continue
                except Exception:
                    hero_count = 0

                if hero_count > 0 and signals.get("product_card_count", 0) < 3:
                    classification = 'homepage'
                    confidence = 0.6
                elif any(pattern in body for pattern in MARKETING_TEXT_PATTERNS):
                    classification = 'marketing_page'
                    confidence = 0.5
                else:
                    classification = 'unknown'
                    confidence = round(max(pdp_conf, plp_conf), 3)

        result = {
            "route_type": classification,
            "confidence": confidence,
            "signals": signals,
            "reasons": reasons,
        }

        # Persist debug artifact only when requested (winning route or final failure)
        if persist_debug:
            try:
                debug_dir = os.path.join(os.getcwd(), 'debug', 'quickmart')
                os.makedirs(debug_dir, exist_ok=True)
                path = os.path.join(debug_dir, 'page_classification.json')
                with open(path, 'w', encoding='utf-8') as fh:
                    json.dump({"timestamp": int(time.time()), "result": result}, fh, indent=2)
                self.logger.info('page_classification_saved', event='debug_artifact', path=path)
            except Exception:
                pass
            try:
                # Save a lightweight structural fingerprint
                fingerprint = {
                    "timestamp": int(time.time()),
                    "url": url,
                    "repeated_card_count": signals.get("product_card_count", 0),
                    "dominant_product_detected": signals.get("dominant_product", False),
                    "grid_consistency_score": signals.get("grid_consistency_score", 0.0),
                    "cta_distribution": {
                        "primary_cta_count": signals.get("primary_cta_count", 0),
                        "repeated_add_to_cart_count": signals.get("repeated_add_to_cart_count", 0),
                    },
                    "breadcrumb_depth": signals.get("breadcrumb_depth", 0),
                    "primary_product_confidence": signals.get("primary_product_confidence", 0.0),
                    "related_products_count": signals.get("related_products_count", 0),
                }
                fp_path = os.path.join(debug_dir, 'page_fingerprint.json')
                with open(fp_path, 'w', encoding='utf-8') as fh:
                    json.dump(fingerprint, fh, indent=2)
                self.logger.info('page_fingerprint_saved', event='debug_artifact', path=fp_path)
            except Exception:
                pass

        # Aggressive PDP override: if structural PDP signals are strong, force PDP
        try:
            strong_pdp = (
                signals.get('dominant_product') or
                (signals.get('primary_price_count', 0) >= 1 and signals.get('primary_cta_count', 0) >= 1)
            ) and (
                signals.get('has_reviews_widget') or signals.get('has_product_schema') or signals.get('url_looks_like_product') or signals.get('breadcrumb_depth', 0) >= 3
            )
            if strong_pdp:
                result['route_type'] = 'product_detail_page'
                result['confidence'] = max(result.get('confidence', 0.0), 0.85)
                reasons['structural_pdp_override'] = True
        except Exception:
            pass

        # Update metrics
        self.metrics['route_type'] = result['route_type']
        self.metrics['classification_confidence'] = result['confidence']
        self.metrics['product_card_count'] = signals.get('product_card_count')
        self.metrics['unique_product_links'] = signals.get('unique_product_links')
        self.metrics['repeated_price_count'] = signals.get('repeated_price_count')
        self.metrics['repeated_add_to_cart_count'] = signals.get('repeated_add_to_cart_count')
        # structural telemetry
        self.metrics['pdp_signals_detected'] = int(bool(signals.get('dominant_product') or signals.get('primary_price_count') > 0))
        self.metrics['plp_signals_detected'] = int(bool(signals.get('product_card_count', 0) >= 3))
        self.metrics['dominant_product_detected'] = int(bool(signals.get('dominant_product')))
        self.metrics['structural_grid_score'] = round(float(signals.get('grid_consistency_score', 0.0)), 3)
        self.metrics['related_products_detected'] = int(bool(signals.get('related_products_count', 0) > 0))
        self.metrics['primary_cta_count'] = int(signals.get('primary_cta_count', 0))

        return result

    def _discover_category_links(self, page: Page, category_keyword: str = "detergent") -> List[Dict[str, Any]]:
        """Detect clickable homepage category cards/links for the given category keyword."""
        links = []
        for selector in HOMEPAGE_CATEGORY_SELECTORS:
            try:
                elements = page.query_selector_all(selector)
                for element in elements[:5]:
                    try:
                        text = element.inner_text().strip() if element.inner_text() else ""
                        href = element.get_attribute("href") or ""
                        role = element.get_attribute("role") or element.evaluate("el => el.tagName.toLowerCase()")
                        onclick = element.get_attribute("onclick") or ""

                        if not text and not href:
                            continue

                        link_info = {
                            "selector": selector,
                            "text": text[:100],
                            "href": href,
                            "role": role,
                            "has_onclick": bool(onclick),
                        }
                        if link_info not in links:
                            links.append(link_info)
                    except Exception:
                        continue
            except Exception:
                continue

        self.logger.info(
            "category_links_discovered",
            event="category_links_discovered",
            category_keyword=category_keyword,
            total_links=len(links),
            links=links[:10],
        )
        return links

    def _navigate_via_homepage_category(self, page: Page) -> bool:
        """Navigate to the target product category by clicking from the homepage.

        Strategy:
        1. Visit homepage, accept cookies, handle location modals
        2. Discover and click a category link for the target category
        3. Apply SPA route stabilization (wait for networkidle + DOM mutations)
        4. Verify category page state via _verify_category_page()
        5. If verification fails, try direct href navigation as fallback
        """
        parsed = urlparse(self.url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        self.logger.info("homepage_category_navigation_start", event="homepage_category_navigation", base_url=base_url)

        page = self._ensure_page_alive(page.context, page)

        # Extract category name from URL for targeting
        target_path = parsed.path.lower()
        category_keywords = [kw for kw in ["soap", "detergent", "cleaning", "laundry", "household", "homecare"]
                            if kw in target_path]
        category_target = category_keywords[0] if category_keywords else "detergent"

        # Track the DOM count before click for SPA stabilization detection
        dom_before_click = 0
        try:
            dom_before_click = page.evaluate(self._JS_ELEMENT_COUNT)
        except Exception:
            pass

        try:
            # Step 1: Go to homepage
            page.goto(base_url, timeout=60000)
            self._wait_for_stabilization(page)
            self._capture_screenshot(page, "homepage_loaded")
            self._log_storage_diagnostics(page, "after_homepage_load")

            # Step 2: Dismiss cookie banner with improved strategy
            self._dismiss_cookie_banner(page)
            self._capture_screenshot(page, "after_cookie_click")
            self._log_storage_diagnostics(page, "after_cookie_accept")

            # Step 3: Handle location/branch modals on homepage
            self._handle_location_branch_modals(page)

            # Step 4: Discover nested category routes from navigation menus and API responses
            route_candidates = self._discover_nested_category_links(page, category_target)
            route_evaluations = self._evaluate_candidate_routes(page.context, route_candidates)
            validated_routes = [r for r in route_evaluations if self._is_valid_plp_route(r)]
            best_route = sorted(validated_routes, key=lambda item: item["final_route_score"], reverse=True)[0] if validated_routes else None
            self.metrics["route_evaluation_candidates"] = len(route_evaluations)
            self.metrics["route_evaluation_best_score"] = best_route["final_route_score"] if best_route else None
            clicked = False
            clicked_href = None

            if best_route:
                clicked_href = best_route.get("url") or ""
                try:
                    self.logger.info(
                        "best_valid_plp_route_selected",
                        event="route_evaluation",
                        best_category_route=clicked_href,
                        route_score=best_route.get("final_route_score"),
                        route_type=best_route.get("route_type"),
                        rejected_reason=best_route.get("rejected_reason"),
                    )
                    page = self._ensure_page_alive(page.context, page)
                    page.goto(clicked_href, timeout=60000)
                    self._wait_for_stabilization(page)
                    self._wait_for_dom_and_card_stabilization(page)
                    self.metrics["category_navigation_attempted"] = True
                    self.metrics["category_clicked"] = clicked_href[:120]
                    self.metrics["best_category_route"] = clicked_href
                    self.metrics["best_category_score"] = best_route.get("final_route_score")
                    page.wait_for_timeout(2000)
                    clicked = True
                except Exception:
                    clicked = False
            else:
                self.logger.warning(
                    "route_evaluation_no_valid_plp",
                    event="route_evaluation",
                    candidate_count=len(route_evaluations),
                    details="No high-confidence PLP route was identified from candidate routes",
                )

            if not clicked:
                links = self._discover_category_links(page, category_target)
                for link in links:
                    if category_target in link["text"].lower() or category_target in link["href"].lower():
                        try:
                            elements = page.query_selector_all(link["selector"])
                            for element in elements[:3]:
                                if element.is_visible():
                                    clicked_href = link.get("href") or ""
                                    success = self._robust_click(
                                        page, element, link["selector"],
                                        description=f"Click category: {link['text'][:50]}"
                                    )
                                    if success:
                                        clicked = True
                                        self.metrics["category_navigation_attempted"] = True
                                        self.metrics["category_clicked"] = link["text"][:80]
                                        page.wait_for_timeout(2000)
                                        break
                            if clicked:
                                break
                        except Exception:
                            continue

            # Step 5: SPA route stabilization — wait for network idle and DOM mutations
            if clicked:
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                try:
                    page.wait_for_function(
                        f"() => document.querySelectorAll('*').length !== {dom_before_click}",
                        timeout=5000,
                    )
                except Exception:
                    pass
                for heading_sel in ["h1", "h2", "[class*='page-title' i]", "[class*='category-title' i]"]:
                    try:
                        page.wait_for_selector(heading_sel, timeout=3000)
                        break
                    except Exception:
                        continue
                page.wait_for_timeout(1000)

            # Step 6: Post-click verification
            verification = self._verify_category_page(page, category_target)
            # Classify page type to avoid PDP misclassification
            classification = self._classify_page_type(page, persist_debug=False)
            self.metrics["route_type"] = classification.get("route_type")
            self.metrics["classification_confidence"] = classification.get("confidence")

            # If classifier identifies product_detail_page with high confidence, treat as navigation failure
            if classification.get("route_type") == "product_detail_page" and classification.get("confidence", 0) >= 0.5:
                self.logger.warning(
                    "navigation_hit_pdp",
                    event="category_navigation",
                    details="Clicked route classified as product_detail_page; skipping as category",
                    route=page.url,
                    confidence=classification.get("confidence"),
                    signals=classification.get("signals", {}),
                )
                self.metrics["category_navigation_attempted"] = True
                self.metrics["category_navigation_success"] = False
                return False
            self.metrics["category_verified"] = verification["category_verified"]
            self.metrics["breadcrumb_verified"] = verification["breadcrumb_verified"]
            self.metrics["product_grid_verified"] = verification["product_grid_verified"]
            self.metrics["route_changed"] = verification["route_changed"]
            self.metrics["category_confidence_score"] = verification["category_confidence_score"]
            self.metrics["category_item_count"] = verification["category_item_count"]

            # Log verification result
            self.logger.info(
                "category_page_verification",
                event="category_verification",
                **verification,
            )

            # Step 7: If verification failed but we have a href, try direct navigation
            if not verification["category_verified"] and clicked_href:
                self._capture_screenshot(page, "verification_failed")
                target_url = clicked_href
                # Make href absolute if relative
                if target_url.startswith("/"):
                    target_url = base_url + target_url
                elif not target_url.startswith("http"):
                    target_url = base_url + "/" + target_url.lstrip("/")
                else:
                    target_url = self.url

                self.logger.warning(
                    "category_verification_failed_fallback",
                    event="category_navigation",
                    details=f"Verification failed (score={verification['category_confidence_score']}), "
                            f"falling back to direct navigation: {target_url}",
                    verification=verification,
                    fallback_url=target_url,
                )
                page = self._ensure_page_alive(page.context, page)
                page.goto(target_url, timeout=60000)
                self._wait_for_stabilization(page)
                self._wait_for_dom_and_card_stabilization(page)

                # Re-verify after direct navigation
                verification = self._verify_category_page(page, category_target)
                self.metrics["category_verified"] = verification["category_verified"]
                self.metrics["category_confidence_score"] = verification["category_confidence_score"]
                self.metrics["category_item_count"] = verification["category_item_count"]

                self.logger.info(
                    "category_verification_after_fallback",
                    event="category_verification",
                    **verification,
                )
            if not verification["category_verified"]:
                page_text = ""
                try:
                    page_text = page.inner_text("body").lower()
                except Exception:
                    pass
                url_lower = page.url.lower()
                if not any(kw in url_lower for kw in VALID_CATEGORY_KEYWORDS) and not any(kw in page_text for kw in VALID_CATEGORY_KEYWORDS):
                    self.logger.error(
                        "strict_category_verification_failed",
                        event="category_navigation",
                        details="Page did not meet strict detergent/cleaning category requirements after navigation",
                        final_url=page.url,
                        page_title=page.title(),
                        category_target=category_target,
                    )
                    self.metrics["category_navigation_success"] = False
                    return False
            # Step 8: Inspect XHR requests for API telemetry
            self._inspect_xhr_requests(page)

            self._capture_debug_summary(page, "after_category_navigation")
            self._capture_screenshot(page, "after_category_click")

            # Step 9: Determine overall navigation success
            nav_success = verification["category_verified"] or verification["product_grid_verified"]
            self.metrics["category_navigation_success"] = nav_success

            self.logger.info(
                "homepage_category_navigation",
                event="homepage_category_navigation",
                clicked_category=category_target,
                navigation_success=nav_success,
                final_url=page.url,
                category_confidence_score=verification["category_confidence_score"],
                category_verified=verification["category_verified"],
                route_changed=verification["route_changed"],
            )
            return nav_success

        except Exception as exc:
            self.logger.error(
                "homepage_category_navigation_failed",
                event="homepage_category_navigation",
                error=str(exc),
            )
            return False

    def _detect_redirect(self, page: Page) -> Dict[str, Any]:
        """Detect if the page was redirected from the expected URL."""
        initial_url = self.metrics.get("initial_url", self.url)
        final_url = page.url

        redirect_detected = final_url.rstrip("/") != initial_url.rstrip("/")
        page_title = page.title().lower()

        is_homepage = any(
            final_url.rstrip("/").endswith(home)
            for home in ["/home", "", "/"]
        ) or "home" in page_title

        category_kw = ["soap", "detergent", "product", "shop", "category"]
        product_kw = ["kes", "price", "buy", "cart", "add to cart"]

        try:
            page_text = page.inner_text("body").lower()
        except Exception:
            page_text = ""

        category_keywords_found = any(kw in page_text for kw in category_kw)
        product_keywords_found = any(kw in page_text for kw in product_kw)

        result = {
            "redirect_detected": redirect_detected,
            "redirect_fallback_detected": redirect_detected and is_homepage,
            "page_title": page.title(),
            "final_url": final_url,
            "initial_url": initial_url,
            "category_keywords_found": category_keywords_found,
            "product_keywords_found": product_keywords_found,
            "is_homepage": is_homepage,
        }

        self.metrics["redirect_detected"] = redirect_detected
        self.metrics["redirect_fallback_detected"] = result["redirect_fallback_detected"]
        self.metrics["final_url"] = final_url

        return result

    def _execute_pre_actions(self, page: Page) -> None:
        """Execute configurable workflow pre-actions before navigation to target URL."""
        if not self.pre_actions:
            return

        self.logger.info("pre_actions_started", event="pre_actions", count=len(self.pre_actions))

        for idx, action in enumerate(self.pre_actions):
            action_type = action.get("type", "")
            description = action.get("description", action_type)
            try:
                if action_type == "goto":
                    target_url = action["url"]
                    page = self._ensure_page_alive(page.context, page)
                    page.goto(target_url, timeout=60000)
                    self._wait_for_stabilization(page)
                    self.logger.info("pre_action_goto", event="pre_actions", index=idx, url=target_url)

                elif action_type == "click":
                    selector = action["selector"]
                    timeout = action.get("timeout", 5000)
                    locator = page.locator(selector).first
                    if locator.count() > 0:
                        locator.click(timeout=timeout)
                        self.logger.info("pre_action_click", event="pre_actions", index=idx, selector=selector)
                        time.sleep(0.5)

                elif action_type == "wait_for_selector":
                    selector = action["selector"]
                    timeout = action.get("timeout", 5000)
                    locator = page.locator(selector).first
                    locator.wait_for(timeout=timeout)
                    self.logger.info("pre_action_wait_for_selector", event="pre_actions", index=idx, selector=selector)

                elif action_type == "wait":
                    ms = action.get("ms", 1000)
                    time.sleep(ms / 1000.0)

                elif action_type == "select_option":
                    selector = action["selector"]
                    value = action.get("value")
                    label = action.get("label")
                    page.select_option(selector, value=value, label=label)
                    self.logger.info("pre_action_select", event="pre_actions", index=idx, selector=selector, value=value or label)

            except Exception as exc:
                self.logger.warning(
                    "pre_action_failed",
                    event="pre_actions",
                    index=idx,
                    action_type=action_type,
                    error=str(exc),
                )

        self.logger.info("pre_actions_completed", event="pre_actions")

    def _handle_location_branch_modals(self, page: Page) -> None:
        """Detect and interact with branch/location selection modals."""
        location_selectors = [
            "button:has-text('Select Branch')",
            "button:has-text('Choose Location')",
            "button:has-text('Set Location')",
            "button:has-text('Continue')",
            "button:has-text('Confirm')",
            "button:has-text('Nairobi')",
            "text=Nairobi",
            "select[name*='branch' i]",
            "select[name*='location' i]",
            "div[class*='branch-list' i] > div",
            "div[class*='store-list' i] > div",
            "a[class*='branch' i]",
            "button[class*='branch' i]",
        ]

        for selector in location_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements[:3]:
                    if element.is_visible(timeout=500):
                        if element.tag_name == "select":
                            page.select_option(selector, index=1)
                        else:
                            element.click(timeout=1000)
                        self.metrics["popups_dismissed"] += 1
                        self.logger.info(
                            "location_modal_interacted",
                            event="location_modal",
                            selector=selector,
                        )
                        time.sleep(0.5)
            except Exception:
                continue

        page.wait_for_timeout(1000)

    def _log_redirect_diagnostics(self, page: Page, redirect_info: Dict[str, Any]) -> None:
        """Log detailed redirect diagnostics for observability."""
        try:
            page_text = page.inner_text("body").lower()
        except Exception:
            page_text = ""

        self.logger.info(
            "redirect_diagnostics",
            event="redirect",
            page_title=redirect_info["page_title"],
            final_url=redirect_info["final_url"],
            initial_url=redirect_info["initial_url"],
            redirect_detected=redirect_info["redirect_detected"],
            redirect_fallback_detected=redirect_info["redirect_fallback_detected"],
            is_homepage=redirect_info["is_homepage"],
            category_keywords_found=redirect_info["category_keywords_found"],
            product_keywords_found=redirect_info["product_keywords_found"],
            dom_node_count=self.metrics.get("debug_summary", {}).get("dom_node_count"),
        )

    def validate(self) -> None:
        self.validate_url()
        self.validate_selector(required=False)

    def extract(self) -> pd.DataFrame:
        records: List[Dict[str, Any]] = []
        with sync_playwright() as p:
            # --- Persistent context (always) ---
            headless = False  # Always run headed to avoid HeadlessChrome fingerprint
            slow_mo = 300 if self.debug_mode else 0
            profile_dir = os.path.join(os.getcwd(), "playwright_profiles", "quickmart")
            os.makedirs(profile_dir, exist_ok=True)

            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=headless,
                slow_mo=slow_mo,
                viewport={"width": 1440, "height": 900},
                ignore_https_errors=True,
                locale="en-KE",
                timezone_id="Africa/Nairobi",
            )

            # Collect redirect responses for diagnostics
            redirect_responses: List[Dict[str, Any]] = []
            def _on_response(response):
                if response.status in (301, 302, 307, 308):
                    redirect_responses.append({
                        "url": response.url,
                        "status": response.status,
                        "location": response.headers.get("location", ""),
                    })

            # Attach the listener to all pages in the persistent context
            for existing_page in context.pages:
                try:
                    existing_page.on("response", _on_response)
                except Exception:
                    pass

            pages = context.pages
            if not pages:
                page = context.new_page()
            else:
                page = pages[0]
            page.on("response", _on_response)

            self._start_tracing(context)
            self.logger.info(
                "browser_launched",
                event="connector_lifecycle",
                url=self.url,
                debug_mode=self.debug_mode,
                headless=headless,
                persistent_context=True,
            )

            # --- Phase 1: Homepage category navigation (establishes session state) ---
            nav_success = self._navigate_via_homepage_category(page)

            # --- Phase 2: Fallback if category navigation didn't land on a product page ---
            if not nav_success:
                self.logger.warning(
                    "direct_navigation_fallback",
                    event="navigation",
                    details="Category navigation did not succeed, navigating to target URL directly",
                )
                page = self._ensure_page_alive(page.context, page)
                page.goto(self.url, timeout=60000)
                self._wait_for_stabilization(page)
                self._wait_for_dom_and_card_stabilization(page)
                # This is a final validation of the direct URL — persist debug on failure
                classification = self._classify_page_type(page, persist_debug=True)
                if not self._is_valid_plp_route({
                    "route_type": classification.get("route_type"),
                    "classification_confidence": classification.get("confidence", 0.0),
                    "product_card_count": classification.get("signals", {}).get("product_card_count", 0),
                    "unique_product_links": classification.get("signals", {}).get("unique_product_links", 0),
                    "repeated_price_count": classification.get("signals", {}).get("repeated_price_count", 0),
                }):
                    self.logger.error(
                        "plp_validation_failed",
                        event="navigation",
                        details="Direct URL is not a high-confidence PLP route after fallback",
                        route=page.url,
                        route_type=classification.get("route_type"),
                        confidence=classification.get("confidence", 0.0),
                    )
                    raise RuntimeError("No high-confidence PLP route identified before extraction")
                nav_success = True

            # --- Phase 3: Dismiss all dialogs ---
            self._dismiss_cookie_banner(page)
            self._dismiss_dialogs(page)
            self._handle_location_branch_modals(page)

            # --- Phase 4: Capture debug summary and detect redirects ---
            self._capture_debug_summary(page, "after_page_load")
            redirect_info = self._detect_redirect(page)
            self._log_redirect_diagnostics(page, redirect_info)

            # --- Phase 5: Handle homepage fallback retry + FAIL FAST ---
            if redirect_info["redirect_fallback_detected"]:
                self.metrics["redirect_count"] += 1
                self.logger.warning(
                    "redirect_fallback_detected",
                    event="redirect",
                    details="Still redirected to homepage, retrying with homepage category navigation",
                    page_title=redirect_info["page_title"],
                    final_url=redirect_info["final_url"],
                    http_redirects=redirect_responses[:5],
                )
                # Retry with homepage category navigation
                self._navigate_via_homepage_category(page)
                self.metrics["redirect_retried"] = True

                # Check if still redirected
                redirect_info = self._detect_redirect(page)
                self._log_redirect_diagnostics(page, redirect_info)

                # FAIL FAST: if still on homepage after retry, raise immediately
                if redirect_info["is_homepage"] and redirect_info["redirect_fallback_detected"]:
                    self._capture_screenshot(page, "permanent_redirect_failure")
                    self.logger.error(
                        "category_navigation_failed_permanently",
                        event="navigation",
                        details="Category page navigation permanently failed — still on homepage after retry",
                        final_url=page.url,
                        page_title=page.title(),
                        http_redirects=redirect_responses[:10],
                        redirect_count=self.metrics["redirect_count"],
                    )
                    self.metrics["debug_summary"]["extraction_stage_failed"] = "permanent_homepage_redirect"
                    raise RuntimeError(
                        f"Cannot navigate to category page — Quickmart redirects to homepage. "
                        f"Final URL: {page.url}. "
                        f"HTTP redirects detected: {len(redirect_responses)}"
                    )

            # --- Phase 6: Extraction loop ---
            for page_index in range(self.max_pages):
                page_records = self._extract_page_with_retries(page)
                strategy = self.metrics.get("extraction_strategy", "unknown")
                self.metrics["pages_crawled"] += 1
                self.metrics["pagination_depth"] = page_index + 1
                records.extend(page_records)

                if page_index >= self.max_pages - 1:
                    break
                if not self._go_next(page):
                    break

            self._stop_tracing(context, run_id=self.run_id)
            context.close()

        # --- Post-extraction ---
        if not records:
            self._capture_screenshot(page, "extraction_failed_page")
            selector_attempts = self.metrics.get("selector_attempts", [])
            self.logger.error(
                "extraction_failed_empty",
                event="extraction_failed",
                top_selectors=selector_attempts[:5],
                candidate_counts=[s.get("candidates", 0) for s in selector_attempts[:5]],
                dom_node_count=self.metrics.get("debug_summary", {}).get("dom_node_count"),
                visible_candidates=self.metrics.get("debug_summary", {}).get("dom_node_count"),
                extraction_confidence=self.metrics.get("extraction_confidence", 0.0),
                extraction_failures=self.metrics.get("extraction_failures", [])[:5],
                debug_summary=self.metrics.get("debug_summary", {}),
                selector_fallback_used=self.metrics.get("selector_fallback_used", False),
                popups_dismissed=self.metrics.get("popups_dismissed", 0),
                cookie_banner_dismissed=self.metrics.get("cookie_banner_dismissed", 0),
                retry_attempts_used=self.metrics.get("retry_attempts_used", 0),
                redirect_detected=self.metrics.get("redirect_detected", False),
                redirect_fallback_detected=self.metrics.get("redirect_fallback_detected", False),
                redirect_retried=self.metrics.get("redirect_retried", False),
                redirect_count=self.metrics.get("redirect_count", 0),
                initial_url=self.metrics.get("initial_url"),
                final_url=self.metrics.get("final_url"),
                trace_path=self._trace_path,
            )
            raise RuntimeError("SmartPlaywrightConnector could not extract products")

        df = pd.DataFrame(records)
        before = len(df)
        df = enrich_product_identity(df, category=self.category)
        self.metrics["duplicate_collapse_count"] = before - len(df)
        self.metrics["products_extracted"] = len(df)
        self.metrics["extraction_confidence"] = round(float(df["confidence_score"].fillna(0).mean()), 3)
        df.attrs["extraction_metrics"] = self.metrics

        self.logger.info(
            "extraction_completed",
            event="connector_lifecycle",
            products_extracted=len(df),
            extraction_strategy=self.metrics.get("extraction_strategy"),
            extraction_confidence=self.metrics.get("extraction_confidence"),
            pages_crawled=self.metrics.get("pages_crawled"),
            cookie_banner_dismissed=self.metrics.get("cookie_banner_dismissed"),
            sibling_cards_detected=self.metrics.get("sibling_cards_detected"),
            sibling_card_score=self.metrics.get("sibling_card_score"),
            retry_attempts_used=self.metrics.get("retry_attempts_used"),
            redirect_detected=self.metrics.get("redirect_detected"),
            redirect_retried=self.metrics.get("redirect_retried"),
            category_navigation_success=self.metrics.get("category_navigation_success"),
            trace_path=self._trace_path,
        )
        return df

    def _wait_for_stabilization(self, page: Page) -> None:
        """Wait for DOM to stabilize after networkidle."""
        start = time.time()
        lazy_load_detected = False
        try:
            loading_count = page.evaluate(self._JS_CHECK_LOADING)
            if loading_count > 0:
                lazy_load_detected = True
                self.logger.info(
                    "dom_loading_detected",
                    event="dom_stabilization",
                    loading_indicators=loading_count,
                )
                try:
                    page.wait_for_function(
                        "() => document.querySelectorAll('[class*=\"loading\"], [class*=\"spinner\"], [class*=\"skeleton\"], [class*=\"placeholder\"], [data-loading]').length === 0",
                        timeout=self.wait_for_timeout,
                    )
                except PlaywrightTimeoutError:
                    self.logger.warning(
                        "dom_loading_timeout",
                        event="dom_stabilization",
                        details="Loading indicators did not clear within timeout",
                    )

            if self.wait_for_timeout > 0:
                page.wait_for_timeout(min(self.wait_for_timeout, 5000))
        except Exception as exc:
            self.logger.warning("dom_stabilization_error", event="dom_stabilization", error=str(exc))

        elapsed_ms = int((time.time() - start) * 1000)
        self.metrics["dom_stabilization_ms"] = elapsed_ms
        self.metrics["lazy_load_detected"] = lazy_load_detected
        self.metrics["hydration_wait_ms"] = min(self.wait_for_timeout, 5000) if self.wait_for_timeout > 0 else 0

        self.logger.info(
            "dom_stabilized",
            event="dom_stabilization",
            stabilization_ms=elapsed_ms,
            lazy_load_detected=lazy_load_detected,
            hydration_wait_ms=self.metrics["hydration_wait_ms"],
        )

    def _wait_for_dom_and_card_stabilization(self, page: Page, timeout: int = 8000) -> None:
        """Wait for the DOM and product card count to stabilize after SPA navigation."""
        start = time.time()
        stable_count = 0
        try:
            stable_count = page.evaluate(self._JS_ELEMENT_COUNT)
            tries = 0
            while tries < 4 and time.time() - start < timeout / 1000:
                page.wait_for_timeout(600)
                new_count = page.evaluate(self._JS_ELEMENT_COUNT)
                if new_count == stable_count:
                    break
                stable_count = new_count
                tries += 1
        except Exception as exc:
            self.logger.warning("dom_card_stabilization_error", event="dom_stabilization", error=str(exc))
        finally:
            elapsed_ms = int((time.time() - start) * 1000)
            self.metrics["dom_card_stabilization_ms"] = elapsed_ms
            self.logger.info(
                "dom_card_stabilized",
                event="dom_stabilization",
                stabilization_ms=elapsed_ms,
                final_element_count=stable_count,
            )

    def _ensure_page_alive(self, context: BrowserContext, page: Page) -> Page:
        """Ensure the page object is alive; recreate it if the page or context was closed."""
        if page is None or page.is_closed():
            self.logger.warning("page_recreated", event="page_liveness", reason="page_closed_or_missing")
            try:
                page = context.new_page()
                self.metrics["page_recreated"] = self.metrics.get("page_recreated", 0) + 1
            except Exception as exc:
                self.logger.error("page_recreation_failed", event="page_liveness", error=str(exc))
                raise
        return page

    def _dismiss_dialogs(self, page: Page) -> None:
        """Dismiss cookie banners, location selectors, branch dialogs, and modals."""
        all_popup_selectors = (
            POPUP_ACCEPT_BUTTONS
            + POPUP_DISMISS_BUTTONS
            + POPUP_LOCATION_BUTTONS
        )

        for selector in all_popup_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements[:3]:
                    if element.is_visible(timeout=500):
                        try:
                            element.click(timeout=1000)
                            self.metrics["popups_dismissed"] += 1
                            time.sleep(0.3)
                        except PlaywrightTimeoutError:
                            continue
                        except Exception:
                            continue
            except Exception:
                continue

        for selector in POPUP_OVERLAYS:
            try:
                overlays = page.query_selector_all(selector)
                for overlay in overlays[:2]:
                    if overlay.is_visible(timeout=500):
                        box = overlay.bounding_box()
                        if box:
                            page.mouse.click(box["x"] + 5, box["y"] + 5)
                            self.metrics["popups_dismissed"] += 1
                            time.sleep(0.3)
            except Exception:
                continue

        page.wait_for_timeout(1000)

    def _dismiss_cookie_banner(self, page: Page) -> None:
        """Robust cookie banner dismissal with scroll-into-view, force click, and retry.

        Uses multiple click strategies and retries up to 3 times per element.
        """
        all_selectors = [
            "text=Accept Cookies",
            "text=Accept",
            "text=I Agree",
            "text=Allow All",
            "text=Accept All",
        ] + COOKIE_BANNER_SELECTORS

        for selector in all_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements[:3]:
                    for attempt in range(3):
                        if not element.is_visible(timeout=500):
                            break
                        try:
                            # Strategy 1: Scroll into view + normal click
                            element.scroll_into_view_if_needed()
                            page.wait_for_timeout(200)
                            element.click(timeout=1000)
                        except Exception:
                            try:
                                # Strategy 2: Force click via locator
                                page.locator(selector).first.click(force=True, timeout=1000)
                            except Exception:
                                try:
                                    # Strategy 3: JavaScript click
                                    page.evaluate("el => el.click()", element)
                                except Exception:
                                    try:
                                        # Strategy 4: Mouse click by bounding box
                                        box = element.bounding_box()
                                        if box:
                                            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                                    except Exception:
                                        continue

                        self.metrics["cookie_banner_dismissed"] += 1
                        self.logger.info(
                            "cookie_banner_dismissed",
                            event="cookie_banner_dismissed",
                            selector=selector,
                            attempt=attempt + 1,
                            clicks=self.metrics["cookie_banner_dismissed"],
                        )
                        time.sleep(1.5)
                        break  # Success — exit retry loop
            except Exception:
                continue

    def _extract_page_with_retries(self, page: Page) -> List[Dict[str, Any]]:
        """Extract products from page with retry logic."""
        last_records: List[Dict[str, Any]] = []

        for attempt in range(self.retry_attempts + 1):
            self._adaptive_scroll(page)

            page_records, strategy = self._extract_page(page)
            self.metrics["extraction_strategy"] = strategy

            if page_records:
                if attempt > 0:
                    self.metrics["retry_attempts_used"] = attempt
                    self.logger.info(
                        "extraction_retry_success",
                        event="extraction_retry",
                        attempt=attempt,
                        records_found=len(page_records),
                        strategy=strategy,
                    )
                return page_records

            last_records = page_records

            if attempt < self.retry_attempts:
                wait_time = 3000 + (attempt * 2000)
                self.logger.warning(
                    "extraction_retry_attempt",
                    event="extraction_retry",
                    attempt=attempt + 1,
                    max_retries=self.retry_attempts,
                    wait_ms=wait_time,
                    strategy=strategy,
                )
                page.wait_for_timeout(wait_time)
                self._dismiss_dialogs(page)

        self.logger.error(
            "extraction_retry_exhausted",
            event="extraction_retry",
            details=f"All {self.retry_attempts + 1} extraction attempts failed",
            retries_used=self.retry_attempts,
        )
        return last_records

    def _adaptive_scroll(self, page: Page) -> None:
        """Adaptive scroll-until-no-change with lazy loading support."""
        initial_count = page.evaluate(self._JS_ELEMENT_COUNT)
        prev_count = initial_count
        no_change_count = 0
        max_no_change = 3
        lazy_load_detected = False

        for i in range(self.scroll_depth):
            try:
                page.evaluate(self._JS_SCROLL_AND_COUNT % self.scroll_step)
                self.metrics["scroll_iterations"] += 1

                page.wait_for_timeout(800)

                loading = page.evaluate(self._JS_CHECK_LOADING)
                if loading > 0:
                    lazy_load_detected = True
                    page.wait_for_timeout(1000)

                current_count = page.evaluate(self._JS_ELEMENT_COUNT)

                if current_count > prev_count:
                    no_change_count = 0
                    prev_count = current_count
                else:
                    no_change_count += 1
                    if no_change_count >= max_no_change:
                        break

            except Exception:
                break

        if lazy_load_detected:
            self.metrics["lazy_load_detected"] = True

    def _detect_sibling_cards(self, page: Page) -> Tuple[List[Dict[str, Any]], str]:
        """Detect repeated sibling-card div structures for product extraction."""
        sibling_selectors = [
            "div:has(img):has-text('KES')",
            "div:has(img):has-text('KSh')",
            "div[role='listitem']",
            "div[role='list'] > div",
            "div[class*='grid'] > div[class*='item' i]",
            "section > div[class*='grid' i] > div",
        ]

        best_records: List[Dict[str, Any]] = []
        best_strategy = "none"
        best_score = 0.0

        for selector in sibling_selectors:
            try:
                elements = page.query_selector_all(selector)
                if len(elements) < 2:
                    continue

                texts = []
                bounding_boxes = []
                for element in elements[:60]:
                    try:
                        text = element.inner_text()
                        texts.append(text)
                        box = element.bounding_box()
                        if box:
                            bounding_boxes.append({"width": box["width"], "height": box["height"]})
                    except Exception:
                        continue

                if len(texts) < 2:
                    continue

                score_result = EcommerceHeuristics.score_sibling_cards(selector, texts, bounding_boxes)

                if score_result.score > best_score:
                    best_score = score_result.score

                if score_result.score >= 20:
                    records = self._extract_with_selector(page, selector, "sibling_card_detection")
                    if records:
                        best_records = records
                        best_strategy = "sibling_card_detection"
                        break

            except Exception:
                continue

        self.metrics["sibling_cards_detected"] = best_score >= 20
        self.metrics["sibling_card_score"] = round(best_score, 2)

        self.logger.info(
            "sibling_card_detection",
            event="sibling_card_detection",
            score=round(best_score, 2),
            cards_detected=best_score >= 20,
            selector_used=best_strategy if best_records else None,
        )

        if best_records:
            return best_records, best_strategy

        return [], "none"

    def _extract_quickmart_products(self, page: Page) -> List[Dict[str, Any]]:
        """Dedicated Quickmart product-card extraction.

        Uses Quickmart-specific selectors and stricter validation/scoring.
        Saves a debug artifact with extracted product records.
        """
        selectors = [
            ".products .productInfoJs",
            ".productInfoJs",
            ".products",
            ".products-body",
            ".products-foot",
            ".products .products-body",
            ".products .products-foot",
            ".products-img",
        ]

        records: List[Dict[str, Any]] = []
        debug_items: List[Dict[str, Any]] = []

        seen = set()
        for sel in selectors:
            try:
                elements = page.query_selector_all(sel)
            except Exception:
                elements = []
            for el in elements[:400]:
                try:
                    # Use element's outerHTML hash as dedupe key
                    try:
                        outer = el.evaluate("el => el.outerHTML") or ""
                        key = hash(outer)
                    except Exception:
                        key = id(el)
                    if key in seen:
                        continue
                    seen.add(key)

                    raw_text = ""
                    try:
                        raw_text = el.inner_text() or ""
                    except Exception:
                        raw_text = ""

                    # Title extraction: try common semantic spots first
                    title = None
                    title_selectors = [
                        ".productInfoJs h3",
                        ".productInfoJs h4",
                        ".productInfoJs .title",
                        ".products-body h3",
                        ".products-body h4",
                        "h3",
                        "h4",
                        "[class*='title' i]",
                        "[class*='product-title' i]",
                        "span",
                    ]
                    for tsel in title_selectors:
                        try:
                            node = el.query_selector(tsel)
                            if node:
                                txt = (node.inner_text() or "").strip()
                                if txt and len(txt) >= 3:
                                    title = txt
                                    break
                        except Exception:
                            continue

                    # Fallback to heuristic name parser
                    if not title:
                        lines = EcommerceHeuristics.split_lines(raw_text)
                        title = EcommerceHeuristics.product_name(lines)

                    # Price extraction: look in products-foot and price classes
                    current_price = None
                    currency = None
                    price_selectors = [
                        ".products-foot .price",
                        ".products-foot",
                        ".price",
                        ".special-price",
                        ".old-price",
                        "span[class*='price' i]",
                    ]
                    for psel in price_selectors:
                        try:
                            node = el.query_selector(psel)
                            if node:
                                ptxt = (node.inner_text() or "").strip()
                                if ptxt:
                                    cp, curr = EcommerceHeuristics.parse_price(ptxt)
                                    if cp is not None:
                                        current_price = cp
                                        currency = curr
                                        break
                        except Exception:
                            continue

                    # Further fallback: parse from raw text
                    if current_price is None:
                        cp, curr = EcommerceHeuristics.parse_price(raw_text)
                        current_price = cp
                        currency = curr

                    # Old price and discount
                    old_price = None
                    try:
                        old_price = EcommerceHeuristics.parse_old_price(raw_text, current_price)
                    except Exception:
                        old_price = None
                    discount = EcommerceHeuristics.parse_discount(raw_text)

                    # Image
                    image_url = None
                    try:
                        img = el.query_selector("img")
                        if img:
                            image_url = img.get_attribute("src") or img.get_attribute("data-src")
                    except Exception:
                        image_url = None

                    # Add-to-cart presence
                    add_to_cart = False
                    try:
                        btns = el.query_selector_all("button, a")
                        for b in btns[:10]:
                            try:
                                bt = (b.inner_text() or "").lower()
                                if any(k in bt for k in ["add to cart", "add to basket", "buy now", "add to bag", "cart"]):
                                    add_to_cart = True
                                    break
                            except Exception:
                                continue
                    except Exception:
                        add_to_cart = False

                    # Score components
                    has_title = bool(title)
                    has_price = current_price is not None
                    has_image = bool(image_url)
                    has_discount = discount is not None
                    has_add_to_cart = add_to_cart

                    # Basic validation: at least 2 of 3 required (title, price, image)
                    required_count = sum([1 if has_title else 0, 1 if has_price else 0, 1 if has_image else 0])
                    if required_count < 2:
                        # Save debug item for low-confidence candidate
                        debug_items.append({
                            "selector": sel,
                            "raw_text": (raw_text[:1000] if raw_text else ""),
                            "title": title,
                            "current_price": current_price,
                            "image_url": image_url,
                            "reason": "missing_required_fields",
                        })
                        continue

                    # Compute a normalized confidence score
                    score = 0.0
                    score += 0.3 if has_title else 0.0
                    score += 0.3 if has_price else 0.0
                    score += 0.2 if has_image else 0.0
                    score += 0.1 if has_discount else 0.0
                    score += 0.1 if has_add_to_cart else 0.0
                    score = round(min(score, 1.0), 3)

                    record = {
                        "product_name": title,
                        "source": self.source_name or self.source_type,
                        "category": self.category,
                        "current_price": current_price,
                        "old_price": old_price,
                        "discount_percentage": discount,
                        "availability": EcommerceHeuristics.availability(raw_text),
                        "sku": EcommerceHeuristics.parse_sku(raw_text),
                        "url": EcommerceHeuristics.normalize_url(self.url, self._first_attr(el, "a[href]", "href")),
                        "image_url": EcommerceHeuristics.normalize_url(self.url, image_url),
                        "currency": currency,
                        "extraction_strategy": "quickmart_product_cards",
                        "raw_text": (raw_text[:2000] if raw_text else ""),
                        "selector_used": sel,
                        "confidence_score": score,
                        # Field telemetry
                        "title_extracted": has_title,
                        "current_price_extracted": has_price,
                        "old_price_extracted": old_price is not None,
                        "discount_extracted": has_discount,
                        "image_extracted": has_image,
                        "add_to_cart_extracted": has_add_to_cart,
                    }

                    records.append(record)
                    debug_items.append({
                        "selector": sel,
                        "raw_text": (raw_text[:2000] if raw_text else ""),
                        "parsed": {
                            "product_name": title,
                            "current_price": current_price,
                            "old_price": old_price,
                            "discount": discount,
                            "image_url": image_url,
                            "confidence_score": score,
                        },
                    })

                except Exception:
                    continue

        # Save debug artifact
        try:
            debug_dir = os.path.join(os.getcwd(), "debug", "quickmart")
            os.makedirs(debug_dir, exist_ok=True)
            path = os.path.join(debug_dir, "extracted_products.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"timestamp": int(time.time()), "items": debug_items}, fh, indent=2)
            self.logger.info("quickmart_debug_saved", event="debug_artifact", path=path)
        except Exception:
            pass

        # Update metrics
        try:
            self.metrics["price_density"] = round(sum(1 for r in records if r.get("current_price") is not None) / (len(records) or 1), 3)
            self.metrics["extraction_quality_passed"] = self._verify_extraction_quality(records)["extraction_quality_passed"]
            self.metrics["products_extracted"] = len(records)
        except Exception:
            pass

        return records

    def _extract_page(self, page: Page) -> Tuple[List[Dict[str, Any]], str]:
        """Extract products from page using heuristic selector scoring."""
        all_selectors = SUPERMARKET_CARD_SELECTORS + COMMON_CARD_SELECTORS

        # Quickmart-specific extraction strategy (site-specific refinement)
        try:
            quickmart_records = self._extract_quickmart_products(page)
            if quickmart_records:
                self.metrics["extraction_strategy"] = "quickmart_product_cards"
                return quickmart_records, "quickmart_product_cards"
        except Exception:
            pass

        if self.selector:
            fallback = self._extract_with_selector(page, self.selector, "workflow_selector_fallback")
            if fallback:
                self.metrics["selector_fallback_used"] = True
                return fallback, "workflow_selector_fallback"

        sibling_records, sibling_strategy = self._detect_sibling_cards(page)
        if sibling_records:
            return sibling_records, sibling_strategy

        best_records: List[Dict[str, Any]] = []
        best_strategy = "none"
        selector_attempts: List[Dict[str, Any]] = []

        for selector in all_selectors:
            try:
                elements = page.query_selector_all(selector)
                texts = []
                for element in elements[:120]:
                    try:
                        text = element.inner_text()
                        texts.append(text)
                    except Exception:
                        continue

                attempt = EcommerceHeuristics.score_selector_extended(selector, texts)
                selector_attempts.append({
                    "selector": attempt.selector,
                    "candidates": attempt.candidate_count,
                    "price_hits": attempt.price_hits,
                    "score": attempt.score,
                })

                if attempt.price_hits >= 2 and attempt.candidate_count >= 3:
                    records = self._extract_with_selector(page, selector, "semantic_card_auto")
                    if records:
                        best_records = records
                        best_strategy = "semantic_card_auto"
                        break

            except Exception as exc:
                selector_attempts.append({
                    "selector": selector,
                    "candidates": 0,
                    "price_hits": 0,
                    "score": 0.0,
                    "error": str(exc),
                })
                continue

        self.metrics["selector_attempts"] = selector_attempts[:20]

        if best_records:
            return best_records, best_strategy

        generic = []
        for selector in COMMON_CARD_SELECTORS:
            records = self._extract_with_selector(page, selector, "generic_ecommerce_heuristic")
            generic.extend(records)
            if len(generic) >= 3:
                return generic, "generic_ecommerce_heuristic"

        return generic, "generic_ecommerce_heuristic"

    def _extract_with_selector(self, page: Page, selector: str, strategy: str) -> List[Dict[str, Any]]:
        records = []
        try:
            elements = page.query_selector_all(selector)
        except Exception as exc:
            self.metrics["extraction_failures"].append(f"{selector}: {exc}")
            return records

        for element in elements[:250]:
            try:
                text = element.inner_text()
                if self.keyword and self.keyword.lower() not in text.lower():
                    continue
                record = self._record_from_card(element, text, strategy)
                if record and record.get("product_name") and record.get("current_price") is not None:
                    records.append(record)
            except Exception as exc:
                self.metrics["extraction_failures"].append(str(exc))
        return records

    def _record_from_card(self, element, text: str, strategy: str) -> Optional[Dict[str, Any]]:
        lines = EcommerceHeuristics.split_lines(text)
        product_name = EcommerceHeuristics.product_name(lines)
        current_price, currency = EcommerceHeuristics.parse_price(text)
        old_price = EcommerceHeuristics.parse_old_price(text, current_price)
        discount = EcommerceHeuristics.parse_discount(text)
        availability = EcommerceHeuristics.availability(text)
        sku = EcommerceHeuristics.parse_sku(text)
        href = self._first_attr(element, "a[href]", "href")
        image = self._first_attr(element, "img", "src") or self._first_attr(element, "img", "data-src")

        record = {
            "product_name": product_name,
            "source": self.source_name or self.source_type,
            "category": self.category,
            "current_price": current_price,
            "old_price": old_price,
            "discount_percentage": discount,
            "availability": availability,
            "sku": sku,
            "url": EcommerceHeuristics.normalize_url(self.url, href),
            "image_url": EcommerceHeuristics.normalize_url(self.url, image),
            "currency": currency,
            "extraction_strategy": strategy,
        }
        record["confidence_score"] = EcommerceHeuristics.confidence(record, strategy)
        return record

    def _first_attr(self, element, selector: str, attr: str) -> Optional[str]:
        try:
            child = element.query_selector(selector)
            return child.get_attribute(attr) if child else None
        except Exception:
            return None

    def _go_next(self, page: Page) -> bool:
        for selector in COMMON_NEXT_SELECTORS:
            try:
                locator = page.locator(selector).first
                if locator.count() == 0:
                    continue
                locator.click(timeout=2500)
                page.wait_for_timeout(2500)
                return True
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue
        return False