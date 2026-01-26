# path: policylens/apps/claims/migrations/0002_documents_and_notes.py
from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion
import apps.claims.models


class Migration(migrations.Migration):
    dependencies = [
        ("claims", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="claimdocument",
            name="file",
            field=models.FileField(default="", upload_to=apps.claims.models.claim_document_upload_to),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="claimdocument",
            name="uploaded_by",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.RemoveField(
            model_name="claimdocument",
            name="storage_key",
        ),
        migrations.CreateModel(
            name="InternalNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField()),
                ("created_by", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("claim", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notes", to="claims.claim")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
