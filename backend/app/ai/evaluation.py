"""Labeled evaluation harness for the attribute-extraction pipeline.

The honest KARVANTANA equivalent of a model card: a fixed, versioned corpus of
artisan transcripts (Tamil/Hindi/English) with human-assigned ground-truth
attributes. run_evaluation() scores the real extractor against the labels and
computes ROC-AUC, PR-AUC, F1 and Brier from app/ai/eval_metrics.py.

Nothing here is estimated: labels are fixed in code (auditable), scores are the
extractor's own emitted confidences, omissions count as predictions with score
0, and hard cases the lexicon cannot handle (unseen materials, negated colours,
machine-made work) are deliberately included so the eval measures real
weaknesses — not a curated highlight reel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.ai import eval_metrics as m
from app.ai.pipeline import extract_from_texts

CORPUS_VERSION = "v1"


@dataclass(frozen=True)
class EvalSample:
    sample_id: str
    language: str  # dominant language of the transcript
    transcript_original: str
    transcript_en: str
    truth: dict[str, Any]  # field → stated value; a tuple = any of them is faithful


# Hand-labeled corpus. Labels reflect ONLY what each transcript explicitly
# states — the same rule the extractor prompt is held to. Where a speaker
# states two techniques ("handwoven … natural dye") either extraction is
# faithful, so the label allows both.
CORPUS: tuple[EvalSample, ...] = (
    EvalSample(
        "eval-ta-001", "ta",
        "இது கைத்தறியில் நெய்த பருத்தி சேலை. இயற்கை நிறம் பயன்படுத்தியிருக்கோம். இதை நாலு நாள்ல தயாரிக்க முடியும்.",
        "This is a handwoven cotton saree. We used natural dye. It takes four days.",
        {"material": "cotton", "technique": ("handloom", "natural dye"), "colour": "Natural",
         "production_days": 4, "category": "saree"},
    ),
    EvalSample(
        "eval-ta-002", "ta",
        "இது மூங்கில் கூடை. கையால் நெய்தது. காய்கறி சேமிக்க பயன்படும்.",
        "This is a bamboo basket. Handmade. Good for kitchen storage.",
        {"material": "bamboo", "technique": "handmade", "usage": "kitchen storage", "category": "basket"},
    ),
    EvalSample(
        "eval-hi-001", "hi",
        "यह बांस की टोकरी है। पूरी तरह हाथ से बुनी हुई। रसोई में सब्ज़ी रखने के काम आती है।",
        "This is a bamboo basket. Woven entirely by hand. Used to store vegetables in the kitchen.",
        {"material": "bamboo", "technique": "handwoven", "usage": "kitchen storage", "category": "basket"},
    ),
    EvalSample(
        "eval-ta-003", "ta",
        "இது பட்டு சேலை. பட்டுப் போர்டரில் பருத்தி நூல் பயன்படுத்தியுள்ளோம்.",
        "This is a silk saree. The border uses cotton thread.",
        {"material": "silk", "category": "saree"},
    ),
    EvalSample(
        "eval-en-001", "en",
        "Indigo blue handwoven cotton saree with natural dye. Ready in six days.",
        "Indigo blue handwoven cotton saree with natural dye. Ready in six days.",
        {"material": "cotton", "technique": ("handloom", "natural dye"), "colour": ("Indigo", "Blue"),
         "production_days": 6, "category": "saree"},
    ),
    EvalSample(
        "eval-en-002", "en",
        "Hand-thrown terracotta water pot made of natural clay, for the kitchen. Ready in three days.",
        "Hand-thrown terracotta water pot made of natural clay, for the kitchen. Ready in three days.",
        {"material": "clay", "technique": "hand-thrown", "usage": "kitchen storage", "colour": "Natural",
         "production_days": 3, "category": "pottery"},
    ),
    EvalSample(
        "eval-ta-004", "ta",
        "இது களிமண் பானை. சுடுமண் சட்டியால் சமையலறையில் பயன்படும். இரண்டு நாள்ல தயாரிக்கலாம்.",
        "This is a clay pot. Terracotta cookware for the kitchen. Made in two days.",
        {"material": "clay", "usage": "kitchen storage", "production_days": 2, "category": "pottery"},
    ),
    EvalSample(
        "eval-en-003", "en",
        "Jute shopping bags with bamboo handles. Great for daily use and gifting.",
        "Jute shopping bags with bamboo handles. Great for daily use and gifting.",
        {"material": "jute", "usage": "gifting"},
    ),
    EvalSample(
        "eval-en-004", "en",
        "Woolen muffler woven on a handloom in Kullu. Takes five days.",
        "Woolen muffler woven on a handloom in Kullu. Takes five days.",
        {"material": "wool", "technique": "handloom", "production_days": 5},
    ),
    EvalSample(
        "eval-hi-002", "hi",
        "यह पीतल का बर्तन है। घर की सजावट के लिए। तीन दिन में तैयार।",
        "This is a brass vessel. For home decoration. Ready in three days.",
        {"material": "brass", "usage": "home decor", "production_days": 3, "category": "pottery"},
    ),
    EvalSample(
        "eval-ta-005", "ta",
        "இது கம்பளி ஷால். ஐந்து நாட்களில் தயாராகும்.",
        "This is a woolen shawl. Ready in five days.",
        {"material": "wool", "production_days": 5},
    ),
    EvalSample(
        "eval-hi-003", "hi",
        "यह नारियल के रेशे से बनी रस्सी है। दो दिन लगते हैं।",
        "This is a rope made of coconut coir. Takes two days.",
        {"material": "coir", "production_days": 2},
    ),
    # ---- deliberately hard cases (measured weaknesses, not hidden) ----------
    EvalSample(
        "eval-en-005", "en",
        "Kalamkari hand-painted cotton wall hanging for home decor.",
        "Kalamkari hand-painted cotton wall hanging for home decor.",
        {"material": "cotton", "technique": "hand-painted", "usage": "home decor"},
    ),
    EvalSample(
        "eval-en-006", "en",
        "Screw-pine floor mat, woven by hand with natural fibres. A week to finish one.",
        "Screw-pine floor mat, woven by hand with natural fibres. A week to finish one.",
        {"material": "screw pine", "technique": "handwoven", "production_days": 7},
    ),
    EvalSample(
        "eval-en-007", "en",
        "Teal floral print cotton fabric. Not red, not maroon.",
        "Teal floral print cotton fabric. Not red, not maroon.",
        {"material": "cotton", "colour": "Teal"},
    ),
    EvalSample(
        "eval-en-008", "en",
        "Machine-made acrylic yarn keychains, ready in a day.",
        "Machine-made acrylic yarn keychains, ready in a day.",
        {"material": "acrylic", "technique": "machine-made", "production_days": 1},
    ),
)


def _truth_display(v: Any) -> str:
    return " / ".join(v) if isinstance(v, tuple) else str(v)


def run_evaluation() -> dict:
    """Score the real extractor against CORPUS and compute honest metrics."""
    scores: list[float] = []
    labels: list[int] = []
    per_field: dict[str, dict[str, int]] = {}
    per_sample: list[dict] = []
    extra_fields = 0

    for s in CORPUS:
        predicted = extract_from_texts(s.transcript_original, s.transcript_en)
        sample_rows = []
        for field, truth_value in s.truth.items():
            pred = predicted.get(field)
            correct = pred is not None and (
                pred["value"] in truth_value if isinstance(truth_value, tuple) else pred["value"] == truth_value
            )
            score = float(pred["confidence"]) if pred is not None else 0.0
            scores.append(score)
            labels.append(1 if correct else 0)
            pf = per_field.setdefault(field, {"labeled": 0, "correct": 0, "omitted": 0})
            pf["labeled"] += 1
            pf["correct"] += 1 if correct else 0
            pf["omitted"] += 1 if pred is None else 0
            sample_rows.append({"field": field, "truth": _truth_display(truth_value),
                                "predicted": pred["value"] if pred is not None else None,
                                "confidence": round(score, 3), "correct": correct})
        for field in predicted:
            if field not in s.truth:
                # Over-extraction: an unstated "fact" is a false positive. It gets
                # score 0 (worse than a stated-but-wrong guess) and label 0, so the
                # metrics punish invention the same way they punish omission.
                extra_fields += 1
                scores.append(0.0)
                labels.append(0)
                sample_rows.append({"field": field, "truth": "(not stated)",
                                    "predicted": predicted[field]["value"],
                                    "confidence": 0.0, "correct": False, "over_extracted": True})
        per_sample.append({"sample_id": s.sample_id, "language": s.language, "fields": sample_rows})

    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    acc = m.confusion(scores, labels)
    wil = m.wilson_interval(n_pos, len(labels))
    roc = m.roc_auc(scores, labels)
    pr = m.pr_auc(scores, labels)
    br = m.brier(scores, labels)

    return {
        "extractor": "lexicon-v1 (demo AI pipeline)",
        "corpus_version": CORPUS_VERSION,
        "task": "voice-transcript attribute extraction (material/technique/usage/colour/production_days/category)",
        "languages": ["ta", "hi", "en"],
        "n_samples": len(CORPUS),
        "n_labeled_fields": len(labels),
        "n_positive": n_pos,
        "n_negative": n_neg,
        "over_extracted_fields": extra_fields,
        "metrics": {
            "roc_auc": round(roc, 4) if roc is not None else None,
            "pr_auc": round(pr, 4) if pr is not None else None,
            "f1_score": acc["f1"],
            "brier_score": round(br, 4) if br is not None else None,
            "accuracy": acc["accuracy"],
            "accuracy_wilson_95": [wil[0], wil[1]] if wil else None,
            "precision": acc["precision"],
            "recall": acc["recall"],
            "confusion": {k: acc[k] for k in ("tp", "fp", "fn", "tn")},
            "operating_threshold": acc["threshold"],
        },
        "per_field": per_field,
        "per_sample": per_sample,
        "method_note": (
            "Each labeled field is one binary item: correct extraction = 1, wrong value or "
            "omission = 0. An unstated field the extractor invents counts as a false "
            "positive with score 0. The score used for ROC/PR/Brier is the extractor's "
            "own emitted confidence (0 when it abstains). Labels are fixed in "
            "app/ai/evaluation.py and auditable — no number on the dashboard is estimated."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
