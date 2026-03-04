"""
Tests for request pagination helpers.
"""

from __future__ import annotations

from django.test import RequestFactory

from policylens.apps.core.pagination import _page_window, paginate_request_queryset


def test_paginate_invalid_page_defaults_to_first_and_keeps_filters():
    """Invalid page values should resolve to page 1 and keep non-page filters."""
    request = RequestFactory().get("/ops/queue/", data={"status": "NEW", "page": "abc"})

    pagination = paginate_request_queryset(request, list(range(6)), page_size=2)

    assert pagination.page_obj.number == 1
    assert pagination.total_count == 6
    assert pagination.showing_from == 1
    assert pagination.showing_to == 2
    assert pagination.next_url == "/ops/queue/?status=NEW&page=2"
    assert pagination.last_url == "/ops/queue/?status=NEW&page=3"
    assert pagination.prev_url == ""
    assert pagination.first_url == ""
    assert [link.number for link in pagination.page_links] == [1, 2, 3]
    assert pagination.page_links[0].is_current is True
    assert pagination.page_links[1].url == "/ops/queue/?status=NEW&page=2"


def test_paginate_negative_page_defaults_to_first_and_out_of_range_uses_last():
    """Negative page goes to first; out-of-range page goes to last."""
    request_neg = RequestFactory().get("/ops/queue/", data={"page": "-3"})
    negative = paginate_request_queryset(request_neg, list(range(4)), page_size=2)

    assert negative.page_obj.number == 1
    assert negative.first_url == ""
    assert negative.prev_url == ""
    assert negative.next_url == "/ops/queue/?page=2"
    assert negative.last_url == "/ops/queue/?page=2"

    request_oor = RequestFactory().get("/ops/queue/", data={"priority": "HIGH", "page": "999"})
    out_of_range = paginate_request_queryset(request_oor, list(range(5)), page_size=2)

    assert out_of_range.page_obj.number == 3
    assert out_of_range.first_url == "/ops/queue/?priority=HIGH&page=1"
    assert out_of_range.prev_url == "/ops/queue/?priority=HIGH&page=2"
    assert out_of_range.next_url == ""
    assert out_of_range.last_url == ""


def test_paginate_empty_queryset_sets_showing_range_to_zero():
    """Empty result sets should expose a 0-0 showing range."""
    request = RequestFactory().get("/ops/queue/")
    pagination = paginate_request_queryset(request, [], page_size=15)

    assert pagination.total_count == 0
    assert pagination.showing_from == 0
    assert pagination.showing_to == 0
    assert pagination.page_obj.number == 1


def test_page_window_handles_non_positive_total_pages():
    """Window helper should still return a safe page list when total_pages <= 0."""
    assert _page_window(current=1, total_pages=0) == [1]


def test_paginate_supports_custom_page_param_for_links():
    """Custom page params should be used in generated URLs."""
    request = RequestFactory().get("/console/admin/", data={"q": "ops", "users_page": "2"})
    pagination = paginate_request_queryset(
        request,
        list(range(12)),
        page_size=5,
        page_param="users_page",
    )

    assert pagination.page_obj.number == 2
    assert pagination.prev_url == "/console/admin/?q=ops&users_page=1"
    assert pagination.next_url == "/console/admin/?q=ops&users_page=3"
