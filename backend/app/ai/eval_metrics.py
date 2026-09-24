"""Binary classification metrics — implemented from definitions, zero dependencies.

The repo refuses invented numbers, so these are computed from a labeled
evaluation run (app/ai/evaluation.py). Every metric here is a textbook
definition so the artifact can be audited line by line:

- ROC-AUC via the rank (Mann–Whitney U) formulation.
- PR-AUC via average precision: sum of precision increments over recall steps.
- Brier score: mean squared error of the positive-class probability.
- Precision / Recall / F1 at the operating threshold (0.5 by default).
- Wilson 95% interval for accuracy — honest uncertainty, not a point boast.
"""

from __future__ import annotations

import math
from typing import Optional


def roc_auc(scores: list[float], labels: list[int]) -> Optional[float]:
    """Mann–Whitney U: P(score_pos > score_neg) + ½·P(equal), over all pairs."""
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return None
    wins = ties = 0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1
            elif p == n:
                ties += 1
    return (wins + 0.5 * ties) / (len(pos) * len(neg))


def pr_auc(scores: list[float], labels: list[int]) -> Optional[float]:
    """Average precision: precision summed over recall increments."""
    if not any(labels) or not scores:
        return None
    ranked = sorted(zip(scores, labels), key=lambda x: -x[0])
    tp = fp = 0
    total_pos = sum(labels)
    ap = 0.0
    prev_recall = 0.0
    for _, y in ranked:
        if y == 1:
            tp += 1
        else:
            fp += 1
        recall = tp / total_pos
        precision = tp / (tp + fp)
        ap += precision * (recall - prev_recall)
        prev_recall = recall
    return ap


def brier(scores: list[float], labels: list[int]) -> Optional[float]:
    """Mean (p − y)² over the labeled examples."""
    if not scores:
        return None
    return sum((p - y) ** 2 for p, y in zip(scores, labels)) / len(scores)


def confusion(scores: list[float], labels: list[int], threshold: float = 0.5) -> dict:
    tp = sum(1 for p, y in zip(scores, labels) if p >= threshold and y == 1)
    fp = sum(1 for p, y in zip(scores, labels) if p >= threshold and y == 0)
    fn = sum(1 for p, y in zip(scores, labels) if p < threshold and y == 1)
    tn = sum(1 for p, y in zip(scores, labels) if p < threshold and y == 0)
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and (precision + recall) else None
    accuracy = (tp + tn) / len(scores) if scores else None
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": _r(precision), "recall": _r(recall), "f1": _r(f1),
        "accuracy": _r(accuracy), "threshold": threshold,
    }


def wilson_interval(successes: int, n: int, z: float = 1.96) -> Optional[tuple[float, float]]:
    """Wilson score 95% interval — the honest way to state accuracy."""
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (round(center - spread, 4), round(center + spread, 4))


def _r(v: Optional[float]) -> Optional[float]:
    return round(v, 4) if v is not None else None
