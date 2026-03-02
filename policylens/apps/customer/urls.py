"""
URL routes for the customer console.

Routes are scoped under /customer and require authenticated customer access.
"""

from django.urls import path

from policylens.apps.customer.views import (
    customer_claim_detail,
    customer_claim_list,
    customer_document_upload,
)

app_name = "customer"

urlpatterns = [
    path("customer/", customer_claim_list, name="claim_list"),
    path("customer/claims/<int:claim_id>/", customer_claim_detail, name="claim_detail"),
    path(
        "customer/claims/<int:claim_id>/documents/upload/",
        customer_document_upload,
        name="document_upload",
    ),
]
