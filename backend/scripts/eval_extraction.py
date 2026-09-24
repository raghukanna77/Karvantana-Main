"""CLI: run the labeled AI evaluation and persist a real measurement artifact.

    python3 scripts/eval_extraction.py [out.json]

Writes eval-results.json (KARVANTANA_EVAL_REPORT can override the path) — the
honest counterpart of a model card. The artifact contains no numbers we did not
just measure: per-field accuracy with sample sizes, ROC-AUC / PR-AUC from the
extractor's own confidences, Brier calibration error, F1 at threshold 0.5,
and the full per-sample breakdown for auditing.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.evaluation import run_evaluation  # noqa: E402


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        "KARVANTANA_EVAL_REPORT", "eval-results.json")
    report = run_evaluation()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    m = report["metrics"]
    print("=== CURRENT PROTOTYPE PERFORMANCE — measured, not estimated ===")
    print(f"extractor          : {report['extractor']}")
    print(f"corpus             : {report['corpus_version']} — {report['n_samples']} transcripts "
          f"(ta/hi/en), {report['n_labeled_fields']} labeled fields "
          f"({report['n_positive']} correct / {report['n_negative']} wrong)")
    print(f"ROC-AUC            : {m['roc_auc']}")
    print(f"PR-AUC             : {m['pr_auc']}")
    print(f"F1-Score (τ=0.5)   : {m['f1_score']}")
    print(f"Brier Score        : {m['brier_score']}")
    print(f"Accuracy           : {m['accuracy']}  (Wilson 95% CI {m['accuracy_wilson_95'][0]}–{m['accuracy_wilson_95'][1]})")
    print(f"Confusion @0.5     : TP={m['confusion']['tp']} FP={m['confusion']['fp']} "
          f"FN={m['confusion']['fn']} TN={m['confusion']['tn']}")
    print(f"over-extractions   : {report['over_extracted_fields']} (fields invented not stated)")
    print()
    print(f"{'field':<17}{'acc':<8}{'n':<6}{'omitted'}")
    for field in sorted(report["per_field"]):
        pf = report["per_field"][field]
        acc = pf["correct"] / pf["labeled"] if pf["labeled"] else 0.0
        print(f"{field:<17}{acc:<8.2f}{pf['labeled']:<6}{pf['omitted']}")
    print()
    misses = [(s["sample_id"], f["field"], f["truth"], f["predicted"])
              for s in report["per_sample"] for f in s["fields"] if not f["correct"]]
    if misses:
        print("MISSES (auditable):")
        for sid, field, truth, pred in misses:
            print(f"  {sid:<12} {field:<16} truth={truth!r:<24} predicted={pred!r}")
    print(f"\nArtifact written → {out_path}")
    print("Method note:", report["method_note"])


if __name__ == "__main__":
    main()
