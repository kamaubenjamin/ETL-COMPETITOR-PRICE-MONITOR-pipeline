"""
Enhanced Intelligence Layer for Product Matching and Normalization.
Phase 3: Intelligence Quality - Advanced product normalization, fuzzy matching,
confidence scoring, and duplicate reduction.
"""
import re
import json
import os
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
import pandas as pd
from rapidfuzz import fuzz, process
import numpy as np


@dataclass
class ProductCanonical:
    """Canonical representation of a product."""
    canonical_id: str
    canonical_name: str
    brand: str
    category: str
    model: str
    size: str
    specifications: Dict[str, str]
    confidence_score: float
    match_count: int
    last_updated: str
    source_products: List[str]  # List of original product names that match this canonical

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "ProductCanonical":
        return ProductCanonical(**data)


@dataclass
class MatchResult:
    """Result of product matching with confidence scoring."""
    product_a: str
    product_b: str
    confidence_score: float
    match_type: str  # 'exact', 'fuzzy', 'brand_model', 'size_match', 'no_match'
    similarity_score: float
    feature_matches: Dict[str, bool]
    canonical_id: Optional[str] = None


class AdvancedProductNormalizer:
    """Enhanced product normalization with synonym handling and canonical forms."""

    def __init__(self):
        self.synonym_map = self._load_synonyms()
        self.brand_variants = self._load_brand_variants()
        self.canonical_forms = self._load_canonical_forms()

    def _load_synonyms(self) -> Dict[str, str]:
        """Load product synonym mappings."""
        return {
            # TV synonyms
            "television": "tv",
            "smart tv": "tv",
            "led tv": "tv",
            "qled tv": "tv",
            "oled tv": "tv",
            "4k tv": "tv",
            "uhd tv": "tv",
            "smart television": "tv",

            # Size synonyms
            "inch": '"',
            "inches": '"',
            "\"": '"',

            # Brand variants
            "samsung electronics": "samsung",
            "lg electronics": "lg",
            "sony corporation": "sony",

            # Quality terms
            "premium": "",
            "deluxe": "",
            "professional": "",
            "commercial": "",
        }

    def _load_brand_variants(self) -> Dict[str, str]:
        """Load brand name variants."""
        return {
            "samsung": ["samsung", "samsung electronics", "samsung elec"],
            "lg": ["lg", "lg electronics", "lg elec", "life's good"],
            "sony": ["sony", "sony corporation", "sony corp"],
            "hisense": ["hisense", "hisense group"],
            "tcl": ["tcl", "tcl corporation"],
            "vitron": ["vitron", "vitron electronics"],
            "amtec": ["amtec", "amtec electronics"],
        }

    def _load_canonical_forms(self) -> Dict[str, str]:
        """Load canonical product name templates."""
        return {
            "tv": "{brand} {size}\" {model} {technology} TV",
            "monitor": "{brand} {size}\" {model} Monitor",
            "phone": "{brand} {model} {storage}GB",
            "laptop": "{brand} {model} {ram}GB RAM {storage}GB SSD",
        }

    def normalize_text(self, text: str) -> str:
        """Advanced text normalization with synonym replacement."""
        if not text:
            return ""

        # Convert to lowercase and strip
        text = str(text).lower().strip()

        # Apply synonym replacements
        for synonym, replacement in self.synonym_map.items():
            text = text.replace(synonym, replacement)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but keep numbers and letters
        text = re.sub(r'[^a-z0-9\s\"\-]', '', text)

        return text.strip()

    def extract_brand_advanced(self, text: str) -> Optional[str]:
        """Advanced brand extraction with variant handling."""
        if not text:
            return None

        normalized = self.normalize_text(text)

        # Check for exact brand matches first
        for canonical_brand, variants in self.brand_variants.items():
            for variant in variants:
                if variant in normalized:
                    return canonical_brand

        # Fallback to first word if it looks like a brand
        words = normalized.split()
        if words:
            first_word = words[0]
            # Check if it matches brand patterns
            if re.match(r'^[a-z]{2,15}$', first_word) and len(first_word) > 2:
                return first_word

        return None

    def extract_model_advanced(self, text: str) -> Optional[str]:
        """Advanced model number extraction."""
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

    def extract_size_advanced(self, text: str) -> Optional[str]:
        """Advanced size extraction for TVs/monitors."""
        if not text:
            return None

        # Look for size patterns
        patterns = [
            r'(\d{2,3})\s*(?:inch|inches|"|'')',  # 55 inch, 55"
            r'(\d{2,3})\s*inch',                      # 55inch (no space)
            r"(\d{2,3})[\"']",                      # 55 inch quotes
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                size = int(match.group(1))
                # Validate reasonable TV/monitor sizes
                if 10 <= size <= 100:
                    return str(size)

        return None

    def normalize_text_advanced(self, text: str) -> str:
        """Normalize text using synonym map and canonical replacements."""
        normalized = self.normalize_text(text)
        # Remove duplicate spaces and standardize quote marks
        normalized = normalized.replace("''", '"').replace('""', '"')
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def detect_category(self, text: str) -> str:
        """Detect product category from text."""
        normalized = self.normalize_text(text)
        if any(keyword in normalized for keyword in ['tv', 'television', 'smart tv', 'qled', 'oled', 'led']):
            return 'tv'
        if any(keyword in normalized for keyword in ['monitor', 'display', 'screen']):
            return 'monitor'
        if any(keyword in normalized for keyword in ['phone', 'smartphone', 'mobile']):
            return 'phone'
        if any(keyword in normalized for keyword in ['laptop', 'notebook', 'ultrabook']):
            return 'laptop'
        return 'other'

    def extract_specifications(self, text: str) -> Dict[str, str]:
        """Extract technical specifications from product name."""
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

    def create_canonical_name(self, features: Dict[str, str]) -> str:
        """Create canonical product name from extracted features."""
        brand = features.get('brand', 'Unknown')
        size = features.get('size', '')
        model = features.get('model', '')
        category = features.get('category', 'other')

        # Use template if available
        if category in self.canonical_forms:
            template = self.canonical_forms[category]
            return template.format(
                brand=brand,
                size=size,
                model=model,
                **features.get('specifications', {})
            )

        # Fallback canonical format
        parts = [brand]
        if size:
            parts.append(f'{size}"')
        if model:
            parts.append(model)

        return ' '.join(parts).strip()

    def extract_features_advanced(self, text: str) -> dict:
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
        normalized = self.normalize_text_advanced(text)

        # Extract components with advanced methods
        brand = self.extract_brand_advanced(text)
        size = self.extract_size_advanced(text)
        model = self.extract_model_advanced(text)
        category = self.detect_category(text)
        specifications = self.extract_specifications(text)

        return {
            "brand": brand,
            "size": size,
            "model": model,
            "category": category,
            "specifications": specifications,
            "normalized_name": normalized,
        }


class AdvancedFuzzyMatcher:
    """Advanced fuzzy matching with multiple algorithms and confidence scoring."""

    def __init__(self):
        self.normalizer = AdvancedProductNormalizer()

    def calculate_similarity_matrix(self, names: List[str]) -> np.ndarray:
        """Calculate similarity matrix for all name pairs."""
        n = len(names)
        similarity_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                score = self.calculate_similarity(names[i], names[j])
                similarity_matrix[i, j] = score
                similarity_matrix[j, i] = score

        return similarity_matrix

    def calculate_similarity(self, name_a: str, name_b: str) -> float:
        """Calculate comprehensive similarity score between two product names."""
        if not name_a or not name_b:
            return 0.0

        # Normalize both names
        norm_a = self.normalizer.normalize_text(name_a)
        norm_b = self.normalizer.normalize_text(name_b)

        if norm_a == norm_b:
            return 100.0

        # Extract features
        features_a = self.normalizer.extract_features_advanced(name_a)
        features_b = self.normalizer.extract_features_advanced(name_b)

        # Calculate different similarity scores
        scores = {
            'token_set': fuzz.token_set_ratio(norm_a, norm_b),
            'token_sort': fuzz.token_sort_ratio(norm_a, norm_b),
            'partial': fuzz.partial_ratio(norm_a, norm_b),
            'wratio': fuzz.WRatio(norm_a, norm_b),
        }

        # Feature-based scoring
        feature_score = self._calculate_feature_similarity(features_a, features_b)

        # Weighted combination
        weights = {
            'token_set': 0.3,
            'token_sort': 0.2,
            'partial': 0.2,
            'wratio': 0.2,
            'features': 0.1,
        }

        final_score = sum(scores[alg] * weights[alg] for alg in ['token_set', 'token_sort', 'partial', 'wratio'])
        final_score += feature_score * weights['features']

        return min(final_score, 100.0)

    def _calculate_feature_similarity(self, features_a: Dict, features_b: Dict) -> float:
        """Calculate similarity based on extracted features."""
        score = 0.0

        # Brand match (high weight)
        if features_a.get('brand') and features_b.get('brand'):
            if features_a['brand'] == features_b['brand']:
                score += 40.0

        # Size match (high weight for TVs/monitors)
        if features_a.get('size') and features_b.get('size'):
            if features_a['size'] == features_b['size']:
                score += 30.0

        # Model match (very high weight)
        if features_a.get('model') and features_b.get('model'):
            if features_a['model'] == features_b['model']:
                score += 30.0

        # Category match
        if features_a.get('category') == features_b.get('category'):
            score += 10.0

        return score

    def find_best_matches(
        self,
        target: str,
        candidates: List[str],
        threshold: float = 70.0,
        limit: int = 5
    ) -> List[Tuple[str, float]]:
        """Find best matches for a target string from candidates."""
        if not target or not candidates:
            return []

        # Use rapidfuzz process for efficient matching
        results = process.extract(
            target,
            candidates,
            scorer=fuzz.WRatio,
            limit=limit,
            score_cutoff=threshold
        )

        return [(match, score) for match, score, _ in results]


class ConfidenceScorer:
    """Calculate confidence scores for product matches."""

    def __init__(self):
        self.matcher = AdvancedFuzzyMatcher()

    def score_match_confidence(
        self,
        product_a: str,
        product_b: str,
        context: Optional[Dict] = None
    ) -> float:
        """Calculate confidence score for a product match."""
        base_similarity = self.matcher.calculate_similarity(product_a, product_b)

        # Extract features for both products
        features_a = self.matcher.normalizer.extract_features_advanced(product_a)
        features_b = self.matcher.normalizer.extract_features_advanced(product_b)

        # Feature matching boosts confidence
        feature_matches = 0
        total_features = 0

        for feature in ['brand', 'model', 'size', 'category']:
            if features_a.get(feature) and features_b.get(feature):
                total_features += 1
                if features_a[feature] == features_b[feature]:
                    feature_matches += 1

        feature_confidence = (feature_matches / max(total_features, 1)) * 30.0

        # Length similarity (similar length products are more likely matches)
        len_ratio = min(len(product_a), len(product_b)) / max(len(product_a), len(product_b))
        length_confidence = len_ratio * 10.0

        # Context-based adjustments
        context_boost = 0.0
        if context:
            # Same source boost
            if context.get('same_source'):
                context_boost += 5.0
            # Recent data boost
            if context.get('recent_data'):
                context_boost += 5.0

        total_confidence = base_similarity + feature_confidence + length_confidence + context_boost

        return min(total_confidence, 100.0)

    def classify_match_type(self, confidence: float) -> str:
        """Classify match confidence into categories."""
        if confidence >= 95.0:
            return 'exact_match'
        elif confidence >= 85.0:
            return 'high_confidence'
        elif confidence >= 70.0:
            return 'medium_confidence'
        elif confidence >= 50.0:
            return 'low_confidence'
        else:
            return 'no_match'


class DuplicateReducer:
    """Handle duplicate product detection and canonical product creation."""

    def __init__(self):
        self.normalizer = AdvancedProductNormalizer()
        self.matcher = AdvancedFuzzyMatcher()
        self.scorer = ConfidenceScorer()
        self.canonical_products: Dict[str, ProductCanonical] = {}
        self._load_canonicals()

    def _load_canonicals(self):
        """Load canonical products from storage."""
        canonical_file = "src/canonical_products.json"
        if os.path.exists(canonical_file):
            try:
                with open(canonical_file, 'r') as f:
                    data = json.load(f)
                self.canonical_products = {
                    cid: ProductCanonical.from_dict(cp)
                    for cid, cp in data.items()
                }
            except Exception:
                self.canonical_products = {}

    def _save_canonicals(self):
        """Save canonical products to storage."""
        canonical_file = "src/canonical_products.json"
        os.makedirs(os.path.dirname(canonical_file), exist_ok=True)

        data = {
            cid: cp.to_dict()
            for cid, cp in self.canonical_products.items()
        }

        with open(canonical_file, 'w') as f:
            json.dump(data, f, indent=2)

    def process_products(self, products: List[str]) -> Dict[str, ProductCanonical]:
        """Process list of products and create/update canonical representations."""
        # Group similar products
        clusters = self._cluster_similar_products(products)

        # Create/update canonicals for each cluster
        for cluster in clusters:
            if len(cluster) >= 2:  # Only create canonicals for groups of 2+ products
                canonical = self._create_canonical_from_cluster(cluster)
                self.canonical_products[canonical.canonical_id] = canonical

        self._save_canonicals()
        return self.canonical_products

    def _cluster_similar_products(self, products: List[str]) -> List[List[str]]:
        """Cluster similar products together."""
        clusters = []
        processed = set()

        for i, product in enumerate(products):
            if i in processed:
                continue

            cluster = [product]
            processed.add(i)

            # Find similar products
            for j, other in enumerate(products):
                if j in processed or i == j:
                    continue

                similarity = self.matcher.calculate_similarity(product, other)
                if similarity >= 75.0:  # High similarity threshold for clustering
                    cluster.append(other)
                    processed.add(j)

            if len(cluster) > 1:
                clusters.append(cluster)

        return clusters

    def _create_canonical_from_cluster(self, cluster: List[str]) -> ProductCanonical:
        """Create canonical product from a cluster of similar products."""
        # Use the most common/most detailed product as base
        base_product = max(cluster, key=lambda x: (len(x), sum(1 for c in x if c.isalnum())))

        # Extract features from base product
        features = self.normalizer.extract_features_advanced(base_product)

        # Create canonical name
        canonical_name = self.normalizer.create_canonical_name(features)

        # Generate canonical ID
        canonical_id = self._generate_canonical_id(canonical_name, features)

        # Calculate average confidence
        confidence_scores = []
        for product in cluster:
            confidence = self.scorer.score_match_confidence(base_product, product)
            confidence_scores.append(confidence)

        avg_confidence = sum(confidence_scores) / len(confidence_scores)

        return ProductCanonical(
            canonical_id=canonical_id,
            canonical_name=canonical_name,
            brand=features.get('brand', 'Unknown'),
            category=features.get('category', 'other'),
            model=features.get('model', ''),
            size=features.get('size', ''),
            specifications=features.get('specifications', {}),
            confidence_score=avg_confidence,
            match_count=len(cluster),
            last_updated=pd.Timestamp.now().isoformat(),
            source_products=cluster
        )

    def _generate_canonical_id(self, canonical_name: str, features: Dict) -> str:
        """Generate unique canonical ID."""
        # Create ID from brand, model, and size
        parts = [
            (features.get('brand') or 'unknown').lower(),
            (features.get('model') or '').lower(),
            features.get('size') or '',
        ]

        id_string = '_'.join(str(p) for p in parts if p)
        # Add hash for uniqueness
        import hashlib
        hash_suffix = hashlib.md5(canonical_name.encode()).hexdigest()[:8]

        return f"{id_string}_{hash_suffix}"

    def find_canonical_match(self, product_name: str) -> Optional[ProductCanonical]:
        """Find the best canonical match for a product name."""
        best_match = None
        best_score = 0.0

        for canonical in self.canonical_products.values():
            # Check against canonical name
            score = self.matcher.calculate_similarity(product_name, canonical.canonical_name)
            if score > best_score and score >= 70.0:
                best_score = score
                best_match = canonical

            # Check against source products
            for source_product in canonical.source_products:
                score = self.matcher.calculate_similarity(product_name, source_product)
                if score > best_score and score >= 70.0:
                    best_score = score
                    best_match = canonical

        return best_match


# Global instances
normalizer = AdvancedProductNormalizer()
matcher = AdvancedFuzzyMatcher()
scorer = ConfidenceScorer()
duplicate_reducer = DuplicateReducer()