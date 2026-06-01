import pytest

from src.transform.intelligence_engine import AdvancedProductNormalizer


def test_create_canonical_name_handles_missing_spec_fields():
    normalizer = AdvancedProductNormalizer()
    features = {
        'brand': 'Samsung',
        'size': '55',
        'model': 'UN55ABC',
        'category': 'tv',
        'specifications': {},
    }

    # Should not raise and should return a string (technology may be missing)
    cname = normalizer.create_canonical_name(features)
    assert isinstance(cname, str)
    assert 'Samsung' in cname or 'samsung' in cname


def test_comparison_engine_exports_normalize_name():
    # Import via the compatibility path used by tests/callers
    from src.transform.comparison_engine import normalize_name

    res = normalize_name('Samsung 55" TV')
    assert isinstance(res, str)
    assert res == res.lower()
