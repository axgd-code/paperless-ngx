# Generated migration for DocumentIntegrationMetadata model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_integration"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentIntegrationMetadata",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "remote_id",
                    models.CharField(
                        help_text="Identifier of the document on the external platform",
                        max_length=512,
                        verbose_name="remote ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        default="pending",
                        help_text="Current status of the document on the external platform",
                        max_length=50,
                        verbose_name="status",
                    ),
                ),
                (
                    "remote_url",
                    models.URLField(
                        blank=True,
                        help_text="Direct URL to access the document on the external platform",
                        max_length=1024,
                        null=True,
                        verbose_name="remote URL",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Provider-specific metadata (recipients, signatures, etc.)",
                        null=True,
                        verbose_name="metadata",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "updated",
                    models.DateTimeField(auto_now=True, verbose_name="updated"),
                ),
                (
                    "last_synced",
                    models.DateTimeField(
                        blank=True,
                        help_text="Last time status was synced from the external platform",
                        null=True,
                        verbose_name="last synced",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="integration_metadata",
                        to="documents.document",
                        verbose_name="document",
                    ),
                ),
                (
                    "integration",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_metadata",
                        to="documents.integration",
                        verbose_name="integration",
                    ),
                ),
            ],
            options={
                "verbose_name": "document integration metadata",
                "verbose_name_plural": "document integration metadata",
            },
        ),
        migrations.AddIndex(
            model_name="documentintegrationmetadata",
            index=models.Index(fields=["remote_id"], name="documents_do_remote__a1b2c3_idx"),
        ),
        migrations.AddIndex(
            model_name="documentintegrationmetadata",
            index=models.Index(fields=["status"], name="documents_do_status_d4e5f6_idx"),
        ),
        migrations.AddIndex(
            model_name="documentintegrationmetadata",
            index=models.Index(
                fields=["document", "integration"],
                name="documents_do_documen_g7h8i9_idx",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="documentintegrationmetadata",
            unique_together={("document", "integration")},
        ),
    ]
