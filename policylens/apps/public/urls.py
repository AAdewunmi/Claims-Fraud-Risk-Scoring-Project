"""
URL routes for public site surfaces.
"""

from django.urls import path

from policylens.apps.public.views import LandingPageView

app_name = "public"

urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
]
