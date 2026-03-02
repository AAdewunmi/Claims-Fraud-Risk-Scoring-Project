"""
Tests for customer console views and helper logic.

These tests focus on branch coverage for ownership resolution and upload flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.http import Http404, HttpResponse
from django.test import RequestFactory

from policylens.apps.claims.models import Claim, ClaimDocument, Policy
from policylens.apps.customer import views
from tests.factories import ClaimFactory, PolicyFactory

pytestmark = pytest.mark.django_db


@dataclass
class RenderCapture:
    response: HttpResponse
    template_name: str
    context: dict[str, Any] | None
    status: int | None


def _capture_render(monkeypatch: pytest.MonkeyPatch) -> list[RenderCapture]:
    captures: list[RenderCapture] = []

    def fake_render(
        _request: Any,
        template_name: str,
        context: dict[str, Any] | None = None,
        status: int | None = None,
    ) -> HttpResponse:
        response = HttpResponse("ok", status=status or 200)
        captures.append(
            RenderCapture(
                response=response,
                template_name=template_name,
                context=context,
                status=status,
            )
        )
        return response

    monkeypatch.setattr(views, "render", fake_render)
    return captures


def test_model_has_field_true_and_false():
    assert views._model_has_field(Claim, "created_by") is True
    assert views._model_has_field(Claim, "does_not_exist") is False


def test_owned_claims_queryset_uses_created_by_username():
    c1 = ClaimFactory(created_by="owned_user")
    ClaimFactory(created_by="someone_else")

    user = SimpleNamespace(username="owned_user", email="")
    qs = views._owned_claims_queryset_for_user(user)

    assert list(qs.values_list("id", flat=True)) == [c1.id]


def test_owned_claims_queryset_falls_back_to_policy_holder_email(monkeypatch: pytest.MonkeyPatch):
    owned_policy = PolicyFactory(holder__email="owner@example.com")
    other_policy = PolicyFactory(holder__email="other@example.com")
    owned_claim = ClaimFactory(policy=owned_policy, created_by="")
    ClaimFactory(policy=other_policy, created_by="")

    monkeypatch.setattr(views, "_model_has_field", lambda _model, _field_name: False)

    user = SimpleNamespace(username="", email="owner@example.com")
    qs = views._owned_claims_queryset_for_user(user)

    assert list(qs.values_list("id", flat=True)) == [owned_claim.id]


def test_owned_claims_queryset_returns_none_when_no_strategy(monkeypatch: pytest.MonkeyPatch):
    ClaimFactory(created_by="anyone")
    monkeypatch.setattr(views, "_model_has_field", lambda _model, _field_name: False)

    user = SimpleNamespace(username="", email="")
    qs = views._owned_claims_queryset_for_user(user)

    assert list(qs) == []


def test_owned_claims_queryset_handles_filter_exceptions_and_returns_none(
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeQS:
        model = object()

        def filter(self, **_kwargs):
            raise RuntimeError("filter failed")

        def none(self):
            return "NONE_QS"

    class FakeManager:
        def all(self):
            return FakeQS()

    monkeypatch.setattr(views.Claim, "objects", FakeManager())

    def fake_has_field(_model: Any, field_name: str) -> bool:
        return field_name in {"customer_user", "created_by"}

    monkeypatch.setattr(views, "_model_has_field", fake_has_field)
    result = views._owned_claims_queryset_for_user(
        SimpleNamespace(username="u", email="u@example.com")
    )
    assert result == "NONE_QS"


def test_apply_stable_ordering_orders_by_created_at_then_id():
    qs = Claim.objects.all()
    ordered = views._apply_stable_ordering(qs)
    assert ordered.query.order_by == ("-created_at", "id")


def test_apply_stable_ordering_no_model_returns_input():
    class NoModel:
        model = None

    sentinel = NoModel()
    assert views._apply_stable_ordering(sentinel) is sentinel


def test_get_owned_claim_or_404_success(monkeypatch: pytest.MonkeyPatch):
    claim = ClaimFactory()

    class FakeOwnedQS:
        def get(self, pk: int) -> Claim:
            assert pk == claim.id
            return claim

    monkeypatch.setattr(views, "_owned_claims_queryset_for_user", lambda _user: FakeOwnedQS())
    found = views._get_owned_claim_or_404(SimpleNamespace(), claim.id)
    assert found.id == claim.id


def test_get_owned_claim_or_404_raises_http404(monkeypatch: pytest.MonkeyPatch):
    class FakeOwnedQS:
        def get(self, pk: int) -> Claim:
            raise Claim.DoesNotExist

    monkeypatch.setattr(views, "_owned_claims_queryset_for_user", lambda _user: FakeOwnedQS())
    with pytest.raises(Http404):
        views._get_owned_claim_or_404(SimpleNamespace(), 99999)


def test_spec_from_model_for_claim_document():
    spec = views._spec_from_model(ClaimDocument)
    assert spec is not None
    assert spec.claim_fk_field == "claim"
    assert spec.file_field == "file"
    assert spec.uploaded_by_field == "uploaded_by"
    assert spec.original_name_field == "original_filename"


def test_spec_from_model_returns_none_for_non_document_model():
    assert views._spec_from_model(Policy) is None


def test_resolve_document_model_spec_finds_claim_document():
    spec = views._resolve_document_model_spec()
    assert spec.model is ClaimDocument
    assert spec.claim_fk_field == "claim"
    assert spec.file_field == "file"


def test_resolve_document_model_spec_returns_from_fallback_scan(
    monkeypatch: pytest.MonkeyPatch,
):
    real_import = __import__

    class CandidateModel(models.Model):
        class Meta:
            app_label = "tests"

    class FakeClaimsModels:
        def __dir__(self):
            return ["CandidateModel"]

    fake_claims_models = FakeClaimsModels()
    fake_claims_models.CandidateModel = CandidateModel

    def fake_import(name: str, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "policylens.apps.claims.models":
            return fake_claims_models
        return real_import(name, globals, locals, fromlist, level)

    expected = views.DocumentModelSpec(
        model=CandidateModel,
        claim_fk_field="claim",
        file_field="file",
    )

    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(
        views,
        "_spec_from_model",
        lambda model: expected if model is CandidateModel else None,
    )

    assert views._resolve_document_model_spec() is expected


def test_resolve_document_model_spec_raises_when_no_candidate_model(
    monkeypatch: pytest.MonkeyPatch,
):
    real_import = __import__

    class CandidateModelNoSpec(models.Model):
        class Meta:
            app_label = "tests"

    class FakeClaimsModels:
        def __dir__(self):
            return ["CandidateModelNoSpec"]

    fake_claims_models = FakeClaimsModels()
    fake_claims_models.CandidateModelNoSpec = CandidateModelNoSpec

    def fake_import(name: str, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "policylens.apps.claims.models":
            return fake_claims_models
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(views, "_spec_from_model", lambda _model: (_ for _ in ()).throw(ValueError))

    with pytest.raises(RuntimeError, match="No claim document model found"):
        views._resolve_document_model_spec()


def test_customer_claim_list_forbidden(monkeypatch: pytest.MonkeyPatch):
    captures = _capture_render(monkeypatch)
    monkeypatch.setattr(views, "user_is_customer", lambda _user: False)

    request = RequestFactory().get("/customer/")
    request.user = SimpleNamespace()
    response = views.customer_claim_list(request)

    assert response.status_code == 403
    assert captures[-1].template_name == "site/forbidden.html"


def test_customer_claim_list_success(monkeypatch: pytest.MonkeyPatch):
    captures = _capture_render(monkeypatch)
    monkeypatch.setattr(views, "user_is_customer", lambda _user: True)
    owned_qs = object()
    ordered_qs = object()
    page_items = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    pagination = SimpleNamespace(page_obj=SimpleNamespace(object_list=page_items))

    monkeypatch.setattr(views, "_owned_claims_queryset_for_user", lambda _user: owned_qs)
    monkeypatch.setattr(
        views, "_apply_stable_ordering", lambda qs: ordered_qs if qs is owned_qs else qs
    )
    monkeypatch.setattr(
        views,
        "paginate_request_queryset",
        lambda _request, qs, page_size: (
            pagination
            if (qs is ordered_qs and page_size == 15)
            else SimpleNamespace(page_obj=SimpleNamespace(object_list=[]))
        ),
    )

    request = RequestFactory().get("/customer/")
    request.user = SimpleNamespace()
    response = views.customer_claim_list(request)

    assert response.status_code == 200
    assert captures[-1].template_name == "customer/claim_list.html"
    assert captures[-1].context is not None
    assert captures[-1].context["pagination"] is pagination
    assert captures[-1].context["claims"] == page_items


def test_customer_claim_detail_forbidden(monkeypatch: pytest.MonkeyPatch):
    captures = _capture_render(monkeypatch)
    monkeypatch.setattr(views, "user_is_customer", lambda _user: False)

    request = RequestFactory().get("/customer/claims/1/")
    request.user = SimpleNamespace()
    response = views.customer_claim_detail(request, claim_id=1)

    assert response.status_code == 403
    assert captures[-1].template_name == "site/forbidden.html"


def test_customer_claim_detail_with_documents(monkeypatch: pytest.MonkeyPatch):
    captures = _capture_render(monkeypatch)
    monkeypatch.setattr(views, "user_is_customer", lambda _user: True)
    claim = ClaimFactory()
    docs = [SimpleNamespace(id=7), SimpleNamespace(id=4)]

    class FakeManager:
        def filter(self, **kwargs):
            assert kwargs == {"claim": claim}
            return self

        def order_by(self, *args):
            assert args == ("-id",)
            return docs

    fake_model = SimpleNamespace(objects=FakeManager())
    spec = views.DocumentModelSpec(model=fake_model, claim_fk_field="claim", file_field="file")

    monkeypatch.setattr(views, "_get_owned_claim_or_404", lambda _user, _claim_id: claim)
    monkeypatch.setattr(views, "_resolve_document_model_spec", lambda: spec)

    request = RequestFactory().get(f"/customer/claims/{claim.id}/")
    request.user = SimpleNamespace()
    response = views.customer_claim_detail(request, claim_id=claim.id)

    assert response.status_code == 200
    assert captures[-1].template_name == "customer/claim_detail.html"
    assert captures[-1].context is not None
    assert captures[-1].context["claim"].id == claim.id
    assert captures[-1].context["documents"] == docs


def test_customer_claim_detail_without_documents_if_resolution_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    captures = _capture_render(monkeypatch)
    monkeypatch.setattr(views, "user_is_customer", lambda _user: True)
    claim = ClaimFactory()

    monkeypatch.setattr(views, "_get_owned_claim_or_404", lambda _user, _claim_id: claim)
    monkeypatch.setattr(
        views,
        "_resolve_document_model_spec",
        lambda: (_ for _ in ()).throw(RuntimeError("no model")),
    )

    request = RequestFactory().get(f"/customer/claims/{claim.id}/")
    request.user = SimpleNamespace()
    response = views.customer_claim_detail(request, claim_id=claim.id)

    assert response.status_code == 200
    assert captures[-1].template_name == "customer/claim_detail.html"
    assert captures[-1].context is not None
    assert captures[-1].context["documents"] == []


def test_customer_document_upload_forbidden(monkeypatch: pytest.MonkeyPatch):
    captures = _capture_render(monkeypatch)
    monkeypatch.setattr(views, "user_is_customer", lambda _user: False)

    request = RequestFactory().get("/customer/claims/1/documents/upload/")
    request.user = SimpleNamespace()
    response = views.customer_document_upload(request, claim_id=1)

    assert response.status_code == 403
    assert captures[-1].template_name == "site/forbidden.html"


def test_customer_document_upload_get_renders_form(monkeypatch: pytest.MonkeyPatch):
    captures = _capture_render(monkeypatch)
    monkeypatch.setattr(views, "user_is_customer", lambda _user: True)
    claim = ClaimFactory()
    monkeypatch.setattr(views, "_get_owned_claim_or_404", lambda _user, _claim_id: claim)

    request = RequestFactory().get(f"/customer/claims/{claim.id}/documents/upload/")
    request.user = SimpleNamespace()
    response = views.customer_document_upload(request, claim_id=claim.id)

    assert response.status_code == 200
    assert captures[-1].template_name == "customer/document_upload.html"
    assert captures[-1].context == {"claim": claim}


def test_customer_document_upload_post_missing_file_returns_400(monkeypatch: pytest.MonkeyPatch):
    captures = _capture_render(monkeypatch)
    monkeypatch.setattr(views, "user_is_customer", lambda _user: True)
    claim = ClaimFactory()
    monkeypatch.setattr(views, "_get_owned_claim_or_404", lambda _user, _claim_id: claim)

    request = RequestFactory().post(f"/customer/claims/{claim.id}/documents/upload/", data={})
    request.user = SimpleNamespace()
    response = views.customer_document_upload(request, claim_id=claim.id)

    assert response.status_code == 400
    assert captures[-1].template_name == "customer/document_upload.html"
    assert captures[-1].context is not None
    assert captures[-1].context["error"] == "Please choose a file to upload."


def test_customer_document_upload_post_success_with_uploaded_by_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(views, "user_is_customer", lambda _user: True)
    claim = ClaimFactory()
    monkeypatch.setattr(views, "_get_owned_claim_or_404", lambda _user, _claim_id: claim)

    created_instances: list[Any] = []

    class FakeDoc:
        def __init__(self):
            self.saved = False

        def __setattr__(self, key: str, value: Any) -> None:
            # Force fallback path: user object assignment fails, username string succeeds.
            if key == "uploaded_by" and not isinstance(value, str):
                raise TypeError("uploaded_by expects string")
            super().__setattr__(key, value)

        def save(self) -> None:
            self.saved = True
            created_instances.append(self)

    spec = views.DocumentModelSpec(
        model=FakeDoc,
        claim_fk_field="claim",
        file_field="file",
        uploaded_by_field="uploaded_by",
        original_name_field="original_filename",
    )
    monkeypatch.setattr(views, "_resolve_document_model_spec", lambda: spec)

    uploaded = SimpleUploadedFile("evidence.txt", b"hello", content_type="text/plain")
    request = RequestFactory().post(
        f"/customer/claims/{claim.id}/documents/upload/",
        data={"file": uploaded},
    )
    request.user = SimpleNamespace(username="customer_1")
    response = views.customer_document_upload(request, claim_id=claim.id)

    assert response.status_code == 302
    assert response["Location"] == f"/customer/claims/{claim.id}/"
    assert len(created_instances) == 1
    instance = created_instances[0]
    assert instance.claim.id == claim.id
    assert instance.uploaded_by == "customer_1"
    assert instance.original_filename == "evidence.txt"
    assert instance.saved is True


def test_spec_from_model_handles_broken_foreign_key_field():
    class BrokenRemote:
        @property
        def model(self):
            raise RuntimeError("broken remote model")

    class BrokenForeignKeyField:
        name = "claim_fk"
        remote_field = BrokenRemote()

        @staticmethod
        def get_internal_type() -> str:
            return "ForeignKey"

    fake_model = SimpleNamespace(_meta=SimpleNamespace(fields=[BrokenForeignKeyField()]))
    assert views._spec_from_model(fake_model) is None


def test_customer_document_upload_ignores_metadata_setattr_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(views, "user_is_customer", lambda _user: True)
    claim = ClaimFactory()
    monkeypatch.setattr(views, "_get_owned_claim_or_404", lambda _user, _claim_id: claim)

    created_instances: list[Any] = []

    class FakeDoc:
        def __init__(self):
            self.saved = False

        def __setattr__(self, key: str, value: Any) -> None:
            if key in {"uploaded_by", "original_filename"}:
                raise TypeError(f"{key} rejected")
            super().__setattr__(key, value)

        def save(self) -> None:
            self.saved = True
            created_instances.append(self)

    spec = views.DocumentModelSpec(
        model=FakeDoc,
        claim_fk_field="claim",
        file_field="file",
        uploaded_by_field="uploaded_by",
        original_name_field="original_filename",
    )
    monkeypatch.setattr(views, "_resolve_document_model_spec", lambda: spec)

    uploaded = SimpleUploadedFile("evidence.txt", b"hello", content_type="text/plain")
    request = RequestFactory().post(
        f"/customer/claims/{claim.id}/documents/upload/",
        data={"file": uploaded},
    )
    request.user = SimpleNamespace(username="customer_2")
    response = views.customer_document_upload(request, claim_id=claim.id)

    assert response.status_code == 302
    assert response["Location"] == f"/customer/claims/{claim.id}/"
    assert len(created_instances) == 1
    assert created_instances[0].saved is True
