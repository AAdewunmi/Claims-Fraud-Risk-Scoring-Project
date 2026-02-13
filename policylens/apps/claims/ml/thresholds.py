# path: policylens/apps/claims/ml/thresholds.py
"""
Threshold governance utilities.

Monotonicity requirement:
If score_a >= score_b then flagged(score_a) must be >= flagged(score_b) for a fixed threshold.
"""

from __future__ import annotations


def is_flagged(*, score: float, threshold: float) -> bool:
    """Return True if score is flagged as likely incomplete.

    Args:
        score: Probability score.
        threshold: Threshold used for flagging.

    Returns:
        True if score >= threshold.
    """
    return float(score) >= float(threshold)
