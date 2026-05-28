from src.extract.heuristics.ecommerce import EcommerceHeuristics


def test_price_parser_ignores_units_and_discount_percentages():
    text = "Ariel Touch Of Downy Detergent 1Kg KES 289 KES 359 20% off"

    price, currency = EcommerceHeuristics.parse_price(text)

    assert price == 289
    assert currency == "KES"
    assert EcommerceHeuristics.parse_old_price(text, price) == 359
    assert EcommerceHeuristics.parse_discount(text) == 20


def test_product_name_ignores_price_and_action_lines():
    lines = ["20% off", "Ariel Original Perfume Detergent 1Kg", "KES 289", "ADD TO CART"]

    assert EcommerceHeuristics.product_name(lines) == "Ariel Original Perfume Detergent 1Kg"


def test_product_name_detergent_with_weight():
    """Detergent product with Kg unit should be identified correctly."""
    lines = ["Omo Active Detergent 2Kg", "KES 450", "ADD TO CART"]
    assert EcommerceHeuristics.product_name(lines) == "Omo Active Detergent 2Kg"


def test_product_name_supermarket_with_mixed_units():
    """Supermarket products with various unit types should be preserved."""
    lines = ["Sunlight Dishwashing Liquid 500ml", "KES 320", "20% off", "BUY NOW"]
    assert EcommerceHeuristics.product_name(lines) == "Sunlight Dishwashing Liquid 500ml"


def test_product_name_with_brand_keywords():
    """Brand names should not cause false rejection."""
    lines = ["Ariel Matic Front Load Detergent 1Kg", "KES 550", "VIEW DETAILS"]
    assert EcommerceHeuristics.product_name(lines) == "Ariel Matic Front Load Detergent 1Kg"


def test_product_name_with_mixed_casing():
    """Mixed casing product names should be preserved."""
    lines = ["Geisha Bar Soap 150g", "KSh 120", "QUICK VIEW"]
    assert EcommerceHeuristics.product_name(lines) == "Geisha Bar Soap 150g"


def test_product_name_with_gram_unit():
    """Products with gram units should be preserved."""
    lines = ["Toss Detergent 500g", "KES 250", "WISHLIST"]
    assert EcommerceHeuristics.product_name(lines) == "Toss Detergent 500g"


def test_product_name_with_litre_unit():
    """Products with litre units should be preserved."""
    lines = ["Cooking Oil 3L", "KES 650", "ADD TO CART"]
    assert EcommerceHeuristics.product_name(lines) == "Cooking Oil 3L"


def test_product_name_rejects_discount_only_lines():
    """Discount-only lines should still be rejected."""
    lines = ["20% off", "Ariel Detergent 1Kg", "KES 289", "ADD TO CART"]
    assert EcommerceHeuristics.product_name(lines) == "Ariel Detergent 1Kg"


def test_product_name_rejects_price_only_lines():
    """Price-only lines should still be rejected."""
    lines = ["KES 289", "Ariel Detergent 1Kg", "ADD TO CART"]
    assert EcommerceHeuristics.product_name(lines) == "Ariel Detergent 1Kg"


def test_product_name_rejects_cta_lines():
    """CTA lines should still be rejected."""
    lines = ["ADD TO CART", "Ariel Detergent 1Kg", "KES 289"]
    assert EcommerceHeuristics.product_name(lines) == "Ariel Detergent 1Kg"


def test_product_name_with_multiple_products():
    """Multiple valid product lines should pick the longest most descriptive one."""
    lines = [
        "Ariel Original Perfume Detergent 1Kg",
        "Ariel Original Detergent 1Kg",
        "KES 359",
        "20% off",
        "ADD TO CART",
    ]
    assert EcommerceHeuristics.product_name(lines) == "Ariel Original Perfume Detergent 1Kg"


def test_product_name_with_pcs_unit():
    """Products with pcs/pieces unit should be preserved."""
    lines = ["Soap Bar 3pcs", "KES 150", "BUY NOW"]
    assert EcommerceHeuristics.product_name(lines) == "Soap Bar 3pcs"


def test_is_price_or_discount_line_discount():
    """_is_price_or_discount_line should identify discount lines."""
    assert EcommerceHeuristics._is_price_or_discount_line("20% off")
    assert EcommerceHeuristics._is_price_or_discount_line("10% discount")
    assert EcommerceHeuristics._is_price_or_discount_line("50%")
    assert not EcommerceHeuristics._is_price_or_discount_line("Ariel Original 1Kg")


def test_is_price_or_discount_line_price():
    """_is_price_or_discount_line should identify price lines."""
    assert EcommerceHeuristics._is_price_or_discount_line("KES 289")
    assert EcommerceHeuristics._is_price_or_discount_line("KSh 450")
    assert EcommerceHeuristics._is_price_or_discount_line("$10.99")
    assert not EcommerceHeuristics._is_price_or_discount_line("Ariel Original Perfume Detergent 1Kg")


def test_is_price_or_discount_line_price_text_mixed():
    """_is_price_or_discount_line should NOT reject text with numbers that are units."""
    assert not EcommerceHeuristics._is_price_or_discount_line("Ariel 1Kg")
    assert not EcommerceHeuristics._is_price_or_discount_line("Omo 500g")
    assert not EcommerceHeuristics._is_price_or_discount_line("Geisha 150g")