"""Unit tests: attribute extraction + language detection."""

from __future__ import annotations

from app.ai.providers.speech import detect_language_by_script
from app.ai.pipeline import extract_from_texts


def test_language_detection_by_script():
    assert detect_language_by_script("இது ஒரு சோதனை") == "ta"
    assert detect_language_by_script("यह एक परीक्षण है") == "hi"
    assert detect_language_by_script("this is a test") == "en"


def test_extraction_pulls_material_technique_days_from_tamil():
    original = "இது கைத்தறியில் நெய்த பருத்தி சேலை. இயற்கை நிறம் பயன்படுத்தியிருக்கோம். இதை நாலு நாள்ல தயாரிக்க முடியும்."
    fields = extract_from_texts(original, "This is a handwoven cotton saree. We used natural dye. It takes four days.")
    assert fields["material"]["value"] == "cotton"
    assert fields["material"]["source"] == "VOICE"
    # both techniques are stated; either is a faithful extraction
    assert fields["technique"]["value"] in ("handloom", "natural dye")
    assert fields["category"]["value"] == "saree"
    assert 0.5 <= fields["material"]["confidence"] <= 1.0


def test_extraction_omits_unstated_fields():
    fields = extract_from_texts("a nice thing", "a nice thing")
    assert "material" not in fields
    assert "category" not in fields
