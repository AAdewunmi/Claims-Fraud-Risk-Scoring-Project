"""
Views for public site surfaces.
"""

from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    """
    Public landing page.

    Provides entry points to the three surface-specific login pages.
    """

    template_name = "public/landing.html"
