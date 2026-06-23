import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0007_delete_viewingstat"),
    ]

    operations = [
        migrations.CreateModel(
            name="YearlyRecap",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("year", models.CharField(max_length=16)),
                ("data", models.JSONField(default=dict)),
                ("event_count", models.PositiveIntegerField(default=0)),
                ("latest_event_at", models.DateTimeField(blank=True, null=True)),
                ("generated_at", models.DateTimeField(auto_now=True)),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="yearly_recaps",
                        to="api.netflixprofile",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="yearly_recaps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="yearlyrecap",
            constraint=models.UniqueConstraint(fields=("user", "profile", "year"), name="unique_yearly_recap"),
        ),
        migrations.AddIndex(
            model_name="yearlyrecap",
            index=models.Index(fields=["user", "profile", "year"], name="api_yearlyr_user_id_fd17df_idx"),
        ),
        migrations.AddIndex(
            model_name="yearlyrecap",
            index=models.Index(fields=["generated_at"], name="api_yearlyr_generat_0cb304_idx"),
        ),
    ]
