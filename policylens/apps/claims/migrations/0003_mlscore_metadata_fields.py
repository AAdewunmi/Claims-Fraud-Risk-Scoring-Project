# path: policylens/apps/claims/migrations/0003_mlscore_metadata_fields.py
from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("claims", "0002_documents_and_notes"),
    ]

    operations = [
        migrations.AddField(
            model_name="mlscore",
            name="feature_contract_hash",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="mlscore",
            name="model_version",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="mlscore",
            name="threshold",
            field=models.FloatField(default=0.0),
        ),
    ]
