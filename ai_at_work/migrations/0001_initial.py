from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LearnerProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("organization", models.CharField(blank=True, max_length=180)),
                ("access_scope", models.CharField(choices=[("research", "Research & Evidence"), ("professional", "General Professional Work"), ("both", "Both pathways")], default="both", max_length=24)),
                ("professional_role", models.CharField(choices=[("client", "Client & Stakeholder Facing"), ("leadership", "Leadership & Management"), ("operations", "Operations & Delivery"), ("any", "Any professional role")], default="any", max_length=24)),
                ("access_start", models.DateField(blank=True, null=True)),
                ("access_expiry", models.DateField(blank=True, null=True)),
                ("training_active", models.BooleanField(default=True)),
                ("must_change_password", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="aiw_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Learner profile", "verbose_name_plural": "Learner profiles", "ordering": ["user__first_name", "user__last_name", "user__username"]},
        ),
        migrations.CreateModel(
            name="LearningState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("storage", models.JSONField(blank=True, default=dict)),
                ("current_pathway", models.CharField(blank=True, max_length=24)),
                ("research_progress", models.PositiveSmallIntegerField(default=0)),
                ("professional_progress", models.PositiveSmallIntegerField(default=0)),
                ("research_assessment_score", models.PositiveSmallIntegerField(default=0)),
                ("professional_assessment_score", models.PositiveSmallIntegerField(default=0)),
                ("research_completed", models.BooleanField(default=False)),
                ("professional_completed", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("profile", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="learning_state", to="ai_at_work.learnerprofile")),
            ],
            options={"verbose_name": "Learning progress", "verbose_name_plural": "Learning progress"},
        ),
        migrations.CreateModel(
            name="AssessmentSummary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pathway", models.CharField(choices=[("research", "Research & Evidence"), ("professional", "General Professional Work")], max_length=24)),
                ("professional_role", models.CharField(blank=True, max_length=24)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("best_score", models.PositiveSmallIntegerField(default=0)),
                ("passed", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assessment_summaries", to="ai_at_work.learnerprofile")),
            ],
            options={"verbose_name": "Assessment result", "verbose_name_plural": "Assessment results", "unique_together": {("profile", "pathway", "professional_role")}},
        ),
        migrations.CreateModel(
            name="SurveyResponse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pathway", models.CharField(choices=[("research", "Research & Evidence"), ("professional", "General Professional Work")], max_length=24)),
                ("professional_role", models.CharField(blank=True, max_length=24)),
                ("phase", models.CharField(choices=[("pre", "Pre-course"), ("post", "Post-course")], max_length=8)),
                ("responses", models.JSONField(blank=True, default=dict)),
                ("is_complete", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="survey_responses", to="ai_at_work.learnerprofile")),
            ],
            options={"verbose_name": "Pre/Post survey", "verbose_name_plural": "Pre/Post surveys", "unique_together": {("profile", "pathway", "professional_role", "phase")}},
        ),
        migrations.CreateModel(
            name="Certificate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pathway", models.CharField(choices=[("research", "Research & Evidence"), ("professional", "General Professional Work")], max_length=24)),
                ("professional_role", models.CharField(blank=True, max_length=24)),
                ("certificate_id", models.CharField(max_length=80, unique=True)),
                ("assessment_score", models.PositiveSmallIntegerField(default=0)),
                ("issued_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("active", models.BooleanField(default=True)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="certificates", to="ai_at_work.learnerprofile")),
            ],
            options={"ordering": ["-issued_at"]},
        ),
    ]
