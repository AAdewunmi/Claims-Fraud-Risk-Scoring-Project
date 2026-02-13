# path: policylens/tests/test_ml_threshold_monotonicity.py
"""
Tests for threshold monotonicity.
"""

from __future__ import annotations

from policylens.apps.claims.ml.thresholds import is_flagged


def test_threshold_monotonicity_holds_for_increasing_scores():
    """If score increases, flagged status must not flip from True to False."""
    threshold = 0.6
    scores = [0.0, 0.2, 0.59, 0.6, 0.61, 0.9, 1.0]

    flagged = [is_flagged(score=s, threshold=threshold) for s in scores]

    # Once flagged becomes True, it must stay True for higher scores.
    seen_true = False
    for f in flagged:
        if f:
            seen_true = True
        if seen_true:
            assert f is True
