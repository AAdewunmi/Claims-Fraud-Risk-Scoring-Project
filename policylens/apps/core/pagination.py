"""
Pagination helpers for PolicyLens UI surfaces.

Contract
- Query param `page`, 1-indexed.
- Page size fixed per surface (Week 6 uses UI_PAGE_SIZE = 15).
- Missing or invalid `page` falls back to page 1.
- Negative/zero `page` is treated as invalid and falls back to page 1.
- Page out of range returns the last page.
- Filters are applied before pagination.
- Pagination links preserve current filters in the querystring.
- UI needs First, Previous, a page window, Next, Last, and "Showing X-Y of Z".

This module produces template-friendly structures so templates remain simple.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.paginator import Page, Paginator
from django.http import HttpRequest
from django.utils.http import urlencode


@dataclass(frozen=True)
class PageLink:
    """A single pagination link rendered in the UI."""

    number: int
    url: str
    is_current: bool


@dataclass(frozen=True)
class PaginationContext:
    """
    Template-friendly pagination context.

    Notes
    - `page_links` is the window of page links to render.
    - `first_url`, `prev_url`, `next_url`, `last_url` are empty strings when disabled.
    """

    page_obj: Page
    paginator: Paginator
    page_links: list[PageLink]
    first_url: str
    prev_url: str
    next_url: str
    last_url: str
    showing_from: int
    showing_to: int
    total_count: int


def _parse_page_number(raw: str | None) -> int:
    """
    Parse the `page` query parameter.

    Rules
    - Missing or non-integer is invalid and returns 1.
    - Zero or negative is invalid and returns 1.
    """

    if raw is None or raw == "":
        return 1
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1
    if value < 1:
        return 1
    return value


def _build_url(request: HttpRequest, *, page_number: int) -> str:
    """
    Build a URL querystring preserving existing query params while overriding `page`.

    This preserves filters by copying request.GET and replacing only the page.
    """

    params = request.GET.copy()
    params["page"] = str(page_number)
    query = urlencode(params, doseq=True)
    return f"{request.path}?{query}" if query else request.path


def _page_window(current: int, total_pages: int, *, radius: int = 2) -> list[int]:
    """
    Compute a simple page window around the current page.

    Example
    - current=6, total_pages=10, radius=2 -> [4, 5, 6, 7, 8]
    """

    if total_pages <= 0:
        return [1]
    start = max(1, current - radius)
    end = min(total_pages, current + radius)
    return list(range(start, end + 1))


def paginate_request_queryset(
    request: HttpRequest,
    queryset: Any,
    *,
    page_size: int,
    page_param: str = "page",
    window_radius: int = 2,
) -> PaginationContext:
    """
    Paginate a queryset using the PolicyLens UI contract.

    Parameters
    - request: Django request holding querystring parameters.
    - queryset: Django QuerySet-like object.
    - page_size: fixed page size for the surface.
    - page_param: query parameter name, defaults to 'page'.
    - window_radius: how many pages either side of current to render.

    Returns
    A PaginationContext suitable for templates.

    Behaviour
    - Invalid or missing page -> 1.
    - Out of range -> last page.
    - Links preserve all existing querystring params.
    """

    requested = _parse_page_number(request.GET.get(page_param))
    paginator = Paginator(queryset, page_size)

    # Django's Paginator.get_page returns:
    # - first page for non-integer
    # - last page for out-of-range
    # We pre-normalise negatives/zero to enforce "invalid -> page 1".
    page_obj = paginator.get_page(requested)

    # Compute navigation URLs (empty when disabled).
    first_url = (
        _build_url(request, page_number=1)
        if paginator.num_pages > 1 and page_obj.number != 1
        else ""
    )
    prev_url = _build_url(request, page_number=page_obj.previous_page_number()) if page_obj.has_previous() else ""
    next_url = _build_url(request, page_number=page_obj.next_page_number()) if page_obj.has_next() else ""
    last_url = (
        _build_url(request, page_number=paginator.num_pages)
        if paginator.num_pages > 1 and page_obj.number != paginator.num_pages
        else ""
    )

    window_numbers = _page_window(page_obj.number, paginator.num_pages, radius=window_radius)
    links = [
        PageLink(number=n, url=_build_url(request, page_number=n), is_current=(n == page_obj.number))
        for n in window_numbers
    ]

    # Showing X-Y of Z: Django Page has start_index/end_index but they raise on empty.
    total = paginator.count
    if total == 0:
        showing_from = 0
        showing_to = 0
    else:
        showing_from = page_obj.start_index()
        showing_to = page_obj.end_index()

    return PaginationContext(
        page_obj=page_obj,
        paginator=paginator,
        page_links=links,
        first_url=first_url,
        prev_url=prev_url,
        next_url=next_url,
        last_url=last_url,
        showing_from=showing_from,
        showing_to=showing_to,
        total_count=total,
    )
