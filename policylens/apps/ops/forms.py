# path: policylens/apps/ops/forms.py
"""
Ops UI forms.

These forms validate input for server-rendered HTMX actions.
"""

from __future__ import annotations

from django import forms

from policylens.apps.claims.models import ReviewDecision


class AddNoteForm(forms.Form):
    """Form for adding an internal note."""

    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=True)

    def clean_body(self) -> str:
        """Trim and validate note body."""
        body = (self.cleaned_data.get("body") or "").strip()
        if not body:
            raise forms.ValidationError("Note body is required.")
        return body


class DecisionForm(forms.Form):
    """Form for recording a decision."""

    decision = forms.ChoiceField(choices=ReviewDecision.Decision.choices, required=True)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
