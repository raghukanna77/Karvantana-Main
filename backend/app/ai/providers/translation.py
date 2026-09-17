"""Demo TranslationProvider.

Craft-aware demo implementation: a curated lexicon of common craft terms
across supported languages, applied longest-match-first, preserving unknown
words verbatim (never inventing content — blueprint §48, §78). IndicTrans2 or
a cloud provider implements the same interface in production.
"""

from __future__ import annotations

# EN -> language term maps (both directions used for translation)
_LEXICON: dict[str, dict[str, str]] = {
    "ta": {
        "handwoven": "கைத்தறியில் நெய்த", "handloom": "கைத்தறி", "cotton": "பருத்தி",
        "saree": "சேலை", "natural dye": "இயற்கை நிறம்", "natural": "இயற்கை",
        "bamboo": "மூங்கில்", "basket": "கூடை", "handmade": "கையால் நெய்த",
        "pottery": "களிமண் பானை", "terracotta": "டெரகோட்டா", "storage": "சேமிப்பு",
        "four days": "நாலு நாள்", "days": "நாட்கள்", "kitchen": "சமையலறை",
    },
    "hi": {
        "handwoven": "हाथ से बुना हुआ", "handloom": "हैंडलूम", "cotton": "कपास",
        "saree": "साड़ी", "natural dye": "प्राकृतिक रंग", "natural": "प्राकृतिक",
        "bamboo": "बांस", "basket": "टोकरी", "handmade": "हाथ से बना",
        "pottery": "मिट्टी के बर्तन", "terracotta": "टेराकोटा", "storage": "भंडारण",
        "four days": "चार दिन", "days": "दिन", "kitchen": "रसोई",
    },
    "te": {
        "handwoven": "చేతితో నేసిన", "cotton": "పట్టి", "saree": "చీర",
        "bamboo": "వెదురు", "basket": "బుట్ట", "handmade": "చేతిపని",
    },
    "kn": {
        "handwoven": "ಕೈಯಿಂದ ನೇಯ್ದ", "cotton": "ಹತ್ತಿ", "saree": "ಸೀರೆ",
        "bamboo": "ಬಿದಿರು", "basket": "ಬುಟ್ಟಿ", "handmade": "ಕೈ ಕೆಲಸ",
    },
    "ml": {
        "handwoven": "കൈകൊണ്ട് നെയ്ത", "cotton": "പഞ്ഞി", "saree": "സാരി",
        "bamboo": "മുള", "basket": "കൊട്ട", "handmade": "കൈകൊണ്ടുള്ള",
    },
    "bn": {
        "handwoven": "হাতে বোনা", "cotton": "সুতি", "saree": "শাড়ি",
        "bamboo": "বাঁশ", "basket": "ঝুড়ি", "handmade": "হাতে তৈরি",
    },
    "mr": {
        "handwoven": "हाताने विणलेले", "cotton": "सुती", "saree": "साडी",
        "bamboo": "बांबू", "basket": "टोपली", "handmade": "हस्तनिर्मित",
    },
    "gu": {
        "handwoven": "હાથથી વણેલું", "cotton": "કપાસ", "saree": "સાડી",
        "bamboo": "બાંસ", "basket": "ટોપલી", "handmade": "હાથે બનાવેલું",
    },
    "pa": {
        "handwoven": "ਹੱਥ ਨਾਲ ਬੁਣਿਆ", "cotton": "ਸੂਤੀ", "saree": "ਸਾੜ੍ਹੀ",
        "bamboo": "ਬਾਂਸ", "basket": "ਟੋਕਰੀ", "handmade": "ਹੱਥ ਨਾਲ ਬਣਿਆ",
    },
}

_REVERSE: dict[str, list[tuple[str, str]]] = {}
for _lang, _terms in _LEXICON.items():
    _REVERSE[_lang] = sorted(((v, k) for k, v in _terms.items()), key=lambda t: -len(t[0]))

_EN_TERMS = sorted(_LEXICON["en"].keys(), key=lambda t: -len(t)) if False else sorted(
    {t for terms in _LEXICON.values() for t in terms}, key=lambda t: -len(t)
)


class DemoTranslationProvider:
    name = "demo-translation"

    def detect_language(self, text: str) -> str:
        from app.ai.providers.speech import detect_language_by_script

        return detect_language_by_script(text)

    def translate(self, text: str, source_lang: str, target_lang: str = "en") -> str:
        if source_lang == target_lang:
            return text
        if source_lang == "en":
            # English -> regional: demo-quality phrase mapping
            table = _LEXICON.get(target_lang)
            if not table:
                return text
            out = text
            for en, tr in sorted(table.items(), key=lambda kv: -len(kv[0])):
                out = out.replace(en, tr)
            return out
        if target_lang == "en":
            # regional -> English: longest-match craft lexicon, keep unknowns verbatim
            pairs = _REVERSE.get(source_lang, [])
            out = text
            for src, en in pairs:
                out = out.replace(src, f" {en} ")
            return _tidy(out)
        # regional -> regional goes through English pivot (demo fidelity)
        en = self.translate(text, source_lang, "en")
        return self.translate(en, "en", target_lang)


def _tidy(text: str) -> str:
    out = text
    out = out.replace("  ", " ").replace(" .", ".").replace(" ,", ",")
    out = out.replace("நாலு நாள்", "four days").replace("नालू", "four days")
    return out.strip()
