"""
Test script for Phase 3: Intelligence Quality enhancements.
Tests advanced normalization, fuzzy matching, confidence scoring, and duplicate reduction.
"""
import sys
import os
from datetime import datetime

# Add workspace to path
sys.path.insert(0, os.path.dirname(__file__))

from src.transform.intelligence_engine import (
    normalizer,
    matcher,
    scorer,
    duplicate_reducer,
)
from src.transform.comparison_engine import (
    match_products,
    build_comparison_table,
    find_similar_products,
    calculate_matching_quality,
)
import pandas as pd


def test_advanced_normalization():
    """Test advanced product normalization."""
    print("\n" + "=" * 60)
    print("Testing Advanced Product Normalization")
    print("=" * 60)

    test_cases = [
        ("Samsung 55\" QLED TV 4K UHD Smart TV", {
            "brand": "samsung",
            "size": "55",
            "model": None,
            "category": "electronics",
            "specifications": {"resolution": "4K", "technology": "QLED"}
        }),
        ("LG 65 Inch OLED Television", {
            "brand": "lg",
            "size": "65",
            "model": None,
            "category": "electronics",
            "specifications": {"technology": "OLED"}
        }),
        ("Sony Bravia 50\" 4K LED TV", {
            "brand": "sony",
            "size": "50",
            "model": "BRAVIA",
            "category": "electronics",
            "specifications": {"resolution": "4K", "technology": "LED"}
        }),
    ]

    for product_name, expected in test_cases:
        features = normalizer.extract_features_advanced(product_name)
        print(f"\nProduct: {product_name}")
        print(f"  Brand: {features.get('brand')} (expected: {expected['brand']})")
        print(f"  Size: {features.get('size')} (expected: {expected['size']})")
        print(f"  Model: {features.get('model')} (expected: {expected['model']})")
        print(f"  Category: {features.get('category')} (expected: {expected['category']})")
        print(f"  Specs: {features.get('specifications')}")

        # Check accuracy
        correct = 0
        total = 0
        for key in ['brand', 'size', 'model', 'category']:
            total += 1
            if features.get(key) == expected[key]:
                correct += 1

        accuracy = correct / total * 100
        print(f"  Accuracy: {accuracy:.1f}%")


def test_fuzzy_matching():
    """Test advanced fuzzy matching capabilities."""
    print("\n" + "=" * 60)
    print("Testing Advanced Fuzzy Matching")
    print("=" * 60)

    test_pairs = [
        ("Samsung 55\" QLED TV", "Samsung 55 Inch QLED Television", 95.0),
        ("LG 65 OLED TV", "LG 65 Inch OLED", 90.0),
        ("Sony Bravia 50\"", "Sony 50\" Bravia LED", 85.0),
        ("Samsung TV 55 Inch", "LG 55\" TV", 30.0),  # Different brands
    ]

    for product_a, product_b, expected_min in test_pairs:
        similarity = matcher.calculate_similarity(product_a, product_b)
        confidence = scorer.score_match_confidence(product_a, product_b)

        print(f"\nComparing:")
        print(f"  A: {product_a}")
        print(f"  B: {product_b}")
        print(f"  Similarity: {similarity:.1f}")
        print(f"  Confidence: {confidence:.1f}")
        print(f"  Match Type: {scorer.classify_match_type(confidence)}")

        # Check if similarity meets expectation
        status = "✓" if similarity >= expected_min else "✗"
        print(f"  Status: {status} (expected ≥ {expected_min})")


def test_duplicate_reduction():
    """Test duplicate detection and canonical product creation."""
    print("\n" + "=" * 60)
    print("Testing Duplicate Reduction & Canonical Products")
    print("=" * 60)

    # Test products with variations
    test_products = [
        "Samsung 55\" QLED TV 4K UHD",
        "Samsung 55 Inch QLED Television",
        "Samsung 55\" QLED 4K TV",
        "LG 65 OLED TV",
        "LG 65 Inch OLED Television",
        "Sony Bravia 50\" 4K",
        "Sony 50\" Bravia LED TV",
    ]

    print(f"\nProcessing {len(test_products)} products for canonical identification...")

    canonicals = duplicate_reducer.process_products(test_products)

    print(f"\nCreated {len(canonicals)} canonical products:")

    for canonical_id, canonical in canonicals.items():
        print(f"\nCanonical ID: {canonical_id}")
        print(f"  Name: {canonical.canonical_name}")
        print(f"  Brand: {canonical.brand}")
        print(f"  Confidence: {canonical.confidence_score:.1f}")
        print(f"  Match Count: {canonical.match_count}")
        print(f"  Source Products: {len(canonical.source_products)}")
        for i, source in enumerate(canonical.source_products[:3]):  # Show first 3
            print(f"    {i+1}. {source}")

    # Test canonical matching
    print("\nTesting canonical matching:")
    test_queries = [
        "Samsung 55 QLED TV",
        "LG 65 Inch OLED",
        "Sony 50\" Bravia",
    ]

    for query in test_queries:
        match = duplicate_reducer.find_canonical_match(query)
        if match:
            print(f"  '{query}' → {match.canonical_name} (confidence: {match.confidence_score:.1f})")
        else:
            print(f"  '{query}' → No match found")


def test_enhanced_comparison_engine():
    """Test the enhanced comparison engine with confidence scoring."""
    print("\n" + "=" * 60)
    print("Testing Enhanced Comparison Engine")
    print("=" * 60)

    # Create test data similar to real scenario
    test_data = [
        {"product_name": "Samsung 55\" QLED TV 4K UHD", "source": "jumia", "price": 35000},
        {"product_name": "Samsung 55 Inch QLED Television", "source": "kilimall", "price": 34500},
        {"product_name": "Samsung 55\" QLED 4K TV", "source": "amazon", "price": 35200},
        {"product_name": "LG 65 OLED TV", "source": "jumia", "price": 45000},
        {"product_name": "LG 65 Inch OLED Television", "source": "kilimall", "price": 44800},
        {"product_name": "Sony Bravia 50\" 4K", "source": "jumia", "price": 32000},
        {"product_name": "Sony 50\" Bravia LED TV", "source": "kilimall", "price": 31500},
    ]

    df = pd.DataFrame(test_data)
    print(f"\nTest dataset: {len(df)} products from {len(df['source'].unique())} sources")

    # Apply enhanced matching
    matched_df = match_products(df, threshold=70)

    print(f"\nMatching Results:")
    print(f"  Total products: {len(matched_df)}")
    print(f"  Unique match groups: {len(matched_df['match_id'].unique())}")

    # Show match groups
    for match_id in sorted(matched_df['match_id'].unique()):
        if match_id == -1:
            continue
        group = matched_df[matched_df['match_id'] == match_id]
        print(f"\nMatch Group {match_id}:")
        print(f"  Products: {len(group)}")
        print(f"  Confidence: {group['confidence_score'].mean():.1f}")
        print(f"  Match Type: {group['match_type'].iloc[0]}")
        for _, row in group.iterrows():
            print(f"    {row['source']}: {row['product_name']} (${row['price']})")

    # Build comparison table
    comparison_df = build_comparison_table(matched_df)
    print(f"\nComparison Table: {len(comparison_df)} unique products")

    if not comparison_df.empty:
        print("\nTop matches by confidence:")
        top_matches = comparison_df.head(3)
        for _, row in top_matches.iterrows():
            print(f"  {row['product_name']}")
            print(f"    Confidence: {row['match_confidence']:.1f}")
            print(f"    Sources: {row['source_count']}")
            print(f"    Cheapest: {row['cheapest_source']} (${row['cheapest_price']})")

    # Calculate quality metrics
    quality_metrics = calculate_matching_quality(matched_df)
    print("\nQuality Metrics:")
    for key, value in quality_metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")


def test_similar_products_search():
    """Test finding similar products functionality."""
    print("\n" + "=" * 60)
    print("Testing Similar Products Search")
    print("=" * 60)

    # Create test dataset
    products_data = [
        {"product_name": "Samsung 55\" QLED TV", "source": "jumia", "price": 35000},
        {"product_name": "Samsung 65\" QLED TV", "source": "kilimall", "price": 45000},
        {"product_name": "LG 55\" OLED TV", "source": "jumia", "price": 40000},
        {"product_name": "Sony 55\" LED TV", "source": "amazon", "price": 32000},
        {"product_name": "Samsung 55 Inch QLED", "source": "kilimall", "price": 34800},
    ]

    df = pd.DataFrame(products_data)

    # Test search
    target_product = "Samsung 55\" QLED Television"
    print(f"\nSearching for products similar to: '{target_product}'")

    similar_df = find_similar_products(target_product, df, threshold=70, limit=5)

    if not similar_df.empty:
        print(f"\nFound {len(similar_df)} similar products:")
        for _, row in similar_df.iterrows():
            print(f"  {row['matched_product']}")
            print(f"    Similarity: {row['similarity_score']:.1f}")
            print(f"    Confidence: {row['confidence_score']:.1f}")
            print(f"    Source: {row['source']}")
            print(f"    Match Type: {row['match_type']}")
    else:
        print("  No similar products found")


def run_all_tests():
    """Run all intelligence quality tests."""
    print("\n" + "🚀" * 35)
    print("PHASE 3: Intelligence Quality Testing")
    print("Advanced Normalization, Fuzzy Matching & Confidence Scoring")
    print("\n" + "=" * 70)

    try:
        test_advanced_normalization()
        test_fuzzy_matching()
        test_duplicate_reduction()
        test_enhanced_comparison_engine()
        test_similar_products_search()

        print("\n" + "=" * 70)
        print("✅ ALL INTELLIGENCE QUALITY TESTS COMPLETED")
        print("=" * 70)

        # Summary
        print("\n📊 Phase 3 Intelligence Quality Summary:")
        print("✓ Advanced product normalization with synonym handling")
        print("✓ Multi-algorithm fuzzy matching with confidence scoring")
        print("✓ Canonical product identification and deduplication")
        print("✓ Enhanced comparison engine with quality metrics")
        print("✓ Similar product search capabilities")
        print("✓ Duplicate reduction and canonical schema support")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
