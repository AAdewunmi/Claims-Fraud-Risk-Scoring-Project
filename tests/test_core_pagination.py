"""
Tests for request pagination helpers.
"""

from __future__ import annotations

from django.test import RequestFactory

from policylens.apps.core.pagination import paginate_request_queryset


def test_paginate_invalid_page_defaults_to_first_and_keeps_filters():
    """Invalid page values should resolve to page 1 and keep non-page filters."""
    request = RequestFactory().get("/ops/queue/", data={"status": "NEW", "page": "abc"})

    pagination = paginate_request_queryset(request, list(range(6)), page_size=2)

    assert pagination.page_number == 1
    assert pagination.page_obj.number == 1
    assert pagination.querystring == "status=NEW"
    assert pagination.page_query(2) == "?status=NEW&page=2"


def test_paginate_negative_page_defaults_to_first_and_out_of_range_uses_last():
    """Negative page goes to first; out-of-range page goes to last."""
    request_neg = RequestFactory().get("/ops/queue/", data={"page": "-3"})
    negative = paginate_request_queryset(request_neg, list(range(4)), page_size=2)

    assert negative.page_number == 1
    assert negative.page_obj.number == 1
    assert negative.querystring == ""
    assert negative.page_query(2) == "?page=2"

    request_oor = RequestFactory().get("/ops/queue/", data={"priority": "HIGH", "page": "999"})
    out_of_range = paginate_request_queryset(request_oor, list(range(5)), page_size=2)

    assert out_of_range.page_number == 3
    assert out_of_range.page_obj.number == 3
    assert out_of_range.querystring == "priority=HIGH"
