"""
Customer portal views for PolicyLens.

Week 6 Day 4 contract
- Customer claim list is paginated at 15 per page.
- Claims are scoped to authenticated customer ownership.
- Customer can upload documents only for owned claims.
- Customer surface is role gated (customer or admin).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.core.files.uploadedfile import UploadedFile
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

# Import Claim model.
# If your repo structure differs, update this import to the canonical Claim model.
from policylens.apps.claims.models import Claim  # type: ignore
from policylens.apps.core.authz import user_is_customer
from policylens.apps.core.pagination import paginate_request_queryset


@dataclass(frozen=True)
class DocumentModelSpec:
    """
    Resolved document model fields needed for upload.

    This keeps the view logic stable even if the underlying document model evolves.
    """

    model: Any
    claim_fk_field: str
    file_field: str
    uploaded_by_field: str | None = None
    original_name_field: str | None = None


def _model_has_field(model: Any, field_name: str) -> bool:
    """Return True if a Django model has a given field name."""
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


def _owned_claims_queryset_for_user(user: Any):
    """
    Return a queryset of claims owned by the given user.

    Ownership resolution tries the strongest first:
    - FK fields on Claim that reference the user (customer_user/customer/owner)
    - created_by string matching username (if Claim.created_by exists)
    - policy holder email matching user.email (if Claim.policy -> holder -> email exists)

    If no ownership strategy is available, returns Claim.objects.none().
    """
    qs = Claim.objects.all()
    model = qs.model

    # Direct FK ownership patterns (update list if your model uses a different name).
    for candidate in ["customer_user", "customer", "owner", "owner_user", "submitted_by"]:
        if _model_has_field(model, candidate):
            try:
                return qs.filter(**{candidate: user})
            except Exception:
                # Field exists but type may not match user model; keep searching.
                pass

    # created_by string ownership pattern.
    if _model_has_field(model, "created_by"):
        try:
            return qs.filter(created_by=getattr(user, "username", ""))
        except Exception:
            pass

    # Policy-holder email ownership pattern.
    user_email = getattr(user, "email", "") or ""
    if user_email:
        # This assumes Claim has `policy` FK, Policy has `holder` FK, and PolicyHolder has `email`.
        # If any link in the chain does not exist, this will raise FieldError; treat as unavailable.
        try:
            return qs.filter(policy__holder__email=user_email)
        except Exception:
            pass

    return qs.none()


def _apply_stable_ordering(qs: Any) -> Any:
    """
    Apply stable ordering for customer claim list.

    Preferred
    - newest first when created_at exists
    - always include id as a deterministic tiebreaker
    """
    model = getattr(qs, "model", None)
    if model is None:
        return qs

    fields = []
    if _model_has_field(model, "created_at"):
        fields.append("-created_at")
    if _model_has_field(model, "id"):
        fields.append("id")

    return qs.order_by(*fields) if fields else qs


def _get_owned_claim_or_404(user: Any, claim_id: int) -> Claim:
    """
    Fetch an owned claim or raise 404.

    404 is used (not 403) to avoid leaking whether a claim id exists.
    """
    qs = _owned_claims_queryset_for_user(user)
    try:
        return qs.get(pk=claim_id)
    except Claim.DoesNotExist:
        raise Http404("Claim not found.") from None


def _resolve_document_model_spec() -> DocumentModelSpec:
    """
    Resolve the document model and its required fields.

    Expected: a model in policylens.apps.claims.models that has:
    - a ForeignKey to Claim
    - a FileField

    This function attempts common names first, then falls back to introspection.
    """
    from django.db import models  # imported lazily to keep module import clean

    claims_models = __import__("policylens.apps.claims.models", fromlist=["*"])

    # Common explicit names first.
    for name in ["ClaimDocument", "Document", "ClaimAttachment", "Attachment"]:
        if hasattr(claims_models, name):
            model = getattr(claims_models, name)
            spec = _spec_from_model(model)
            if spec is not None:
                return spec

    # Fallback: scan module for model classes.
    for attr_name in dir(claims_models):
        attr = getattr(claims_models, attr_name)
        try:
            if isinstance(attr, type) and issubclass(attr, models.Model):
                spec = _spec_from_model(attr)
                if spec is not None:
                    return spec
        except Exception:
            continue

    raise RuntimeError(
        "No claim document model found. Expected a model with FK to Claim and a FileField in policylens.apps.claims.models."
    )


def _spec_from_model(model: Any) -> DocumentModelSpec | None:
    """
    Build a DocumentModelSpec from a candidate model if it looks like a claim document model.
    """
    from django.db import models  # local import

    claim_fk_field = None
    file_field = None

    for field in model._meta.fields:
        if field.get_internal_type() == "ForeignKey":
            try:
                if field.remote_field.model == Claim:
                    claim_fk_field = field.name
            except Exception:
                pass
        if isinstance(field, models.FileField):
            file_field = field.name

    if not claim_fk_field or not file_field:
        return None

    uploaded_by_field = None
    for candidate in ["uploaded_by", "created_by_user", "user", "actor"]:
        if _model_has_field(model, candidate):
            uploaded_by_field = candidate
            break

    original_name_field = None
    for candidate in ["original_filename", "filename", "name"]:
        if _model_has_field(model, candidate):
            original_name_field = candidate
            break

    return DocumentModelSpec(
        model=model,
        claim_fk_field=claim_fk_field,
        file_field=file_field,
        uploaded_by_field=uploaded_by_field,
        original_name_field=original_name_field,
    )


@require_GET
def customer_claim_list(request: HttpRequest) -> HttpResponse:
    """
    Customer portal claim list.

    Access
    - Requires customer or admin role.
    - Anonymous users should reach this through customer login entry point.

    Pagination
    - Uses shared PolicyLens contract.
    - Page size fixed at settings.UI_PAGE_SIZE (Week 6: 15).
    - Stable ordering with id tiebreaker.
    """
    if not user_is_customer(request.user):
        return render(request, "site/forbidden.html", status=403)

    qs = _owned_claims_queryset_for_user(request.user)
    qs = _apply_stable_ordering(qs)

    pagination = paginate_request_queryset(
        request,
        qs,
        page_size=getattr(settings, "UI_PAGE_SIZE", 15),
    )

    return render(
        request,
        "customer/claim_list.html",
        {
            "pagination": pagination,
            "claims": pagination.page_obj.object_list,
        },
    )


@require_GET
def customer_claim_detail(request: HttpRequest, claim_id: int) -> HttpResponse:
    """
    Customer portal claim detail.

    Access
    - Requires customer or admin role.
    - Claim must be owned by the authenticated customer.
    """
    if not user_is_customer(request.user):
        return render(request, "site/forbidden.html", status=403)

    claim = _get_owned_claim_or_404(request.user, claim_id)

    # If a document model exists, show documents related to this claim.
    documents = []
    try:
        spec = _resolve_document_model_spec()
        documents = list(spec.model.objects.filter(**{spec.claim_fk_field: claim}).order_by("-id"))
    except Exception:
        # If document model cannot be resolved, detail still renders.
        documents = []

    return render(
        request,
        "customer/claim_detail.html",
        {
            "claim": claim,
            "documents": documents,
        },
    )


@require_http_methods(["GET", "POST"])
def customer_document_upload(request: HttpRequest, claim_id: int) -> HttpResponse:
    """
    Upload a document for a customer-owned claim.

    Access
    - Requires customer or admin role.
    - Claim must be owned by the authenticated customer.
    - Upload is rejected for non-owned claims via 404.
    """
    if not user_is_customer(request.user):
        return render(request, "site/forbidden.html", status=403)

    claim = _get_owned_claim_or_404(request.user, claim_id)

    if request.method == "GET":
        return render(request, "customer/document_upload.html", {"claim": claim})

    upload: UploadedFile | None = request.FILES.get("file")
    if upload is None:
        # Keep behaviour explicit: re-render with a clear error.
        return render(
            request,
            "customer/document_upload.html",
            {"claim": claim, "error": "Please choose a file to upload."},
            status=400,
        )

    spec = _resolve_document_model_spec()
    instance = spec.model()

    # Attach to claim.
    setattr(instance, spec.claim_fk_field, claim)

    # Store file.
    setattr(instance, spec.file_field, upload)

    # Optional metadata.
    if spec.uploaded_by_field:
        try:
            setattr(instance, spec.uploaded_by_field, request.user)
        except Exception:
            # If field is not a FK to user, fall back to a string when possible.
            try:
                setattr(
                    instance, spec.uploaded_by_field, getattr(request.user, "username", "customer")
                )
            except Exception:
                pass

    if spec.original_name_field:
        try:
            setattr(instance, spec.original_name_field, upload.name)
        except Exception:
            pass

    instance.save()

    return redirect("customer:claim_detail", claim_id=claim.id)
