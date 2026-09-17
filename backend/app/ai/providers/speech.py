"""Demo SpeechProvider.

Whisper-compatible interface. The demo implementation uses scripted regional
language samples so the voice journey is fully demonstrable without cloud STT;
`language` detection is real Unicode-block heuristics. A cloud provider drops in
by implementing transcribe() (blueprint §47).
"""

from __future__ import annotations

import re
from typing import Optional

from app.ai.providers.base import SpeechResult

# Scripted samples (clearly the DEMO corpus — not live STT)
_DEMO_SCRIPTS: dict[str, list[str]] = {
    "ta": [
        "இது கைத்தறியில் நெய்த பருத்தி சேலை. இயற்கை நிறம் பயன்படுத்தியிருக்கோம். இதை நாலு நாள்ல தயாரிக்க முடியும்.",
        "இது மூங்கில் கூடை. கையால் நெய்தது. காய்கறி சேமிக்க பயன்படும்.",
    ],
    "hi": [
        "यह हाथ से बुना हुआ कपास की साड़ी है। हमने प्राकृतिक रंग का उपयोग किया है। इसे बनाने में चार दिन लगते हैं।",
        "यह बांस की टोकरी है। पूरी तरह हाथ से बुनी हुई। रसोई में सब्ज़ी रखने के काम आती है।",
    ],
    "en": [
        "This is a handwoven cotton saree. We used natural dyes. It takes about four days to weave one.",
        "This is a handmade bamboo basket, woven entirely by hand. Good for kitchen storage.",
    ],
}

# Unicode block ranges per language code — genuine detection heuristic
_RANGE_TESTS = [
    ("ta", re.compile(r"[\u0B80-\u0BFF]")),
    ("hi", re.compile(r"[\u0900-\u097F]")),
    ("te", re.compile(r"[\u0C00-\u0C7F]")),
    ("kn", re.compile(r"[\u0C80-\u0CFF]")),
    ("ml", re.compile(r"[\u0D00-\u0D7F]")),
    ("bn", re.compile(r"[\u0980-\u09FF]")),
    ("gu", re.compile(r"[\u0A80-\u0AFF]")),
    ("pa", re.compile(r"[\u0A00-\u0A7F]")),
]


def detect_language_by_script(text: str) -> str:
    for code, rx in _RANGE_TESTS:
        if rx.search(text):
            return code
    return "en"


class DemoSpeechProvider:
    name = "demo-speech"

    def transcribe(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> SpeechResult:
        # The demo provider maps audio duration → nearest scripted sample so the
        # pipeline (and UI) behave exactly like a real STT integration.
        lang = language_hint or "ta"
        corpus = _DEMO_SCRIPTS.get(lang) or _DEMO_SCRIPTS["en"]
        duration = max(1.0, len(audio_bytes) / 8000.0)
        text = corpus[0] if duration < 8 else corpus[-1]
        confidence = 0.93
        return SpeechResult(
            language=lang if lang in _DEMO_SCRIPTS else "en",
            transcript=text,
            confidence=confidence,
            duration_seconds=round(duration, 1),
        )


def transcribe_text_payload(text: str) -> SpeechResult:
    """Shared helper: detect script + confidence for text already captured client-side."""
    lang = detect_language_by_script(text)
    # confidence: real scripts give high confidence; ASCII fallback lower
    conf = 0.95 if lang != "en" else 0.88
    return SpeechResult(language=lang, transcript=text, confidence=conf)
