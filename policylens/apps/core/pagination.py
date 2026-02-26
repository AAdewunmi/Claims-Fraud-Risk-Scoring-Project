"""
Pagination helpers for server-rendered surfaces.

Contract:
- Request `page` query param is 1-indexed.
- Invalid page values resolve to page 1.
- Out-of-range pages resolve to the last page.
- Existing filters are preserved in generated query strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.paginator import EmptyPage, Page, Paginator
from django.http import HttpRequest


@dataclass
class RequestPagination:
    """Template-friendly pagination payload for request-bound list views."""

    paginator: Paginator
    page_obj: Page
    page_number: int
    querystring: str

    def page_query(self, page_number: int) -> str:
        """
        Return a `?` query string for a target page.

        Existing non-page filters are retained.
        """
        if self.querystring:
            return f"?{self.querystring}&page={page_number}"
        return f"?page={page_number}"


def _filtered_querystring(request: HttpRequest) -> str:
    """Return current query params excluding the `page` parameter."""
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def paginate_request_queryset(
    request: HttpRequest,
    queryset: Any,
    *,
    page_size: int = 15,
) -> RequestPagination:
    """
    Paginate a queryset/list from request query params with deterministic fallback.
    """
    paginator = Paginator(queryset, page_size)
    raw_page = request.GET.get("page", "1")

    try:
        page_number = int(raw_page)
    except (TypeError, ValueError):
        page_number = 1

    if page_number < 1:
        page_number = 1

    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
        page_number = page_obj.number

    return RequestPagination(
        paginator=paginator,
        page_obj=page_obj,
        page_number=page_number,
        querystring=_filtered_querystring(request),
    )
