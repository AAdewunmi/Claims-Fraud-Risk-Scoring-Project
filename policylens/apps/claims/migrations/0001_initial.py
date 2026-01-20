# path: policylens/apps/claims/migrations/0001_initial.py
# Generated manually for deterministic bootstrapping in this lab.
# Django will treat this like any other migration file.

from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PolicyHolder",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("full_name", models.CharField(max_length=255)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Policy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "policy_number",
                    models.CharField(max_length=64, unique=True),
                ),
                (
                    "product_type",
                    models.CharField(max_length=128),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("LAPSED", "Lapsed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                ("effective_date", models.DateField(blank=True, null=True)),
                ("expiry_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "holder",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="policies",
                        to="claims.policyholder",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Claim",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "claim_type",
                    models.CharField(
                        choices=[
                            ("CLAIM", "Claim"),
                            ("POLICY_CHANGE", "Policy change"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("NEW", "New"),
                            ("IN_REVIEW", "In review"),
                            ("DECIDED", "Decided"),
                        ],
                        default="NEW",
                        max_length=16,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("LOW", "Low"),
                            ("NORMAL", "Normal"),
                            ("HIGH", "High"),
                        ],
                        default="NORMAL",
                        max_length=16,
                    ),
                ),
                ("summary", models.TextField(blank=True)),
                ("created_by", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="claims",
                        to="claims.policy",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ClaimDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("original_filename", models.CharField(max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=128)),
                ("size_bytes", models.PositiveIntegerField(default=0)),
                ("storage_key", models.CharField(blank=True, max_length=255)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "claim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="claims.claim",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ChecklistItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(max_length=64)),
                ("label", models.CharField(max_length=255)),
                ("is_required", models.BooleanField(default=True)),
                ("is_satisfied", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "claim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checklist_items",
                        to="claims.claim",
                    ),
                ),
            ],
            options={"unique_together": {("claim", "key")}},
        ),
        migrations.CreateModel(
            name="ReviewDecision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "decision",
                    models.CharField(
                        choices=[
                            ("APPROVE", "Approve"),
                            ("REJECT", "Reject"),
                            ("REQUEST_INFO", "Request info"),
                        ],
                        max_length=32,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("decided_by", models.CharField(blank=True, max_length=128)),
                ("decided_at", models.DateTimeField(auto_now_add=True)),
                (
                    "claim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="decisions",
                        to="claims.claim",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SlaClock",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("breached_at", models.DateTimeField(blank=True, null=True)),
                (
                    "claim",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sla_clock",
                        to="claims.claim",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("event_type", models.CharField(max_length=64)),
                ("actor", models.CharField(blank=True, max_length=128)),
                ("payload", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "claim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_events",
                        to="claims.claim",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="MlScore",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("score", models.FloatField(default=0.0)),
                ("label", models.CharField(blank=True, max_length=32)),
                ("reason_codes", models.JSONField(default=list)),
                ("scored_at", models.DateTimeField(auto_now=True)),
                (
                    "claim",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ml_score",
                        to="claims.claim",
                    ),
                ),
            ],
        ),
    ]
