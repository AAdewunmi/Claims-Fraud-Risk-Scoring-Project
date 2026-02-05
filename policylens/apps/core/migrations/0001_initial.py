# path: policylens/apps/core/migrations/0001_initial.py
from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IdempotencyRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=128)),
                ("method", models.CharField(max_length=16)),
                ("path", models.CharField(max_length=255)),
                ("request_hash", models.CharField(max_length=64)),
                ("response_status", models.PositiveIntegerField()),
                ("response_body", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="idempotency_records", to=settings.AUTH_USER_MODEL)),
            ],
            options={},
        ),
        migrations.AddConstraint(
            model_name="idempotencyrecord",
            constraint=models.UniqueConstraint(fields=("key", "user", "method", "path"), name="uniq_idempotency_key_user_method_path"),
        ),
        migrations.AddIndex(
            model_name="idempotencyrecord",
            index=models.Index(fields=["user", "created_at"], name="core_idempo_user_cr_7bfeae_idx"),
        ),
        migrations.AddIndex(
            model_name="idempotencyrecord",
            index=models.Index(fields=["key"], name="core_idempo_key_0d2b10_idx"),
        ),
    ]
