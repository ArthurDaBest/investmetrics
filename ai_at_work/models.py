from django.conf import settings
from django.db import models
from django.utils import timezone


class LearnerProfile(models.Model):
    ACCESS_RESEARCH = "research"
    ACCESS_PROFESSIONAL = "professional"
    ACCESS_BOTH = "both"
    ACCESS_CHOICES = [
        (ACCESS_RESEARCH, "Research & Evidence"),
        (ACCESS_PROFESSIONAL, "General Professional Work"),
        (ACCESS_BOTH, "Both pathways"),
    ]

    ROLE_CLIENT = "client"
    ROLE_LEADERSHIP = "leadership"
    ROLE_OPERATIONS = "operations"
    ROLE_ANY = "any"
    ROLE_CHOICES = [
        (ROLE_CLIENT, "Client & Stakeholder Facing"),
        (ROLE_LEADERSHIP, "Leadership & Management"),
        (ROLE_OPERATIONS, "Operations & Delivery"),
        (ROLE_ANY, "Any professional role"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="aiw_profile",
    )
    organization = models.CharField(max_length=180, blank=True)
    access_scope = models.CharField(max_length=24, choices=ACCESS_CHOICES, default=ACCESS_BOTH)
    professional_role = models.CharField(max_length=24, choices=ROLE_CHOICES, default=ROLE_ANY)
    access_start = models.DateField(blank=True, null=True)
    access_expiry = models.DateField(blank=True, null=True)
    training_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Learner profile"
        verbose_name_plural = "Learner profiles"
        ordering = ["user__first_name", "user__last_name", "user__username"]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        full = self.user.get_full_name().strip()
        return full or self.user.username

    @property
    def access_is_valid(self):
        today = timezone.localdate()
        if not self.training_active or not self.user.is_active:
            return False
        if self.access_start and today < self.access_start:
            return False
        if self.access_expiry and today > self.access_expiry:
            return False
        return True


class LearningState(models.Model):
    profile = models.OneToOneField(
        LearnerProfile,
        on_delete=models.CASCADE,
        related_name="learning_state",
    )
    storage = models.JSONField(default=dict, blank=True)
    current_pathway = models.CharField(max_length=24, blank=True)
    research_progress = models.PositiveSmallIntegerField(default=0)
    professional_progress = models.PositiveSmallIntegerField(default=0)
    research_assessment_score = models.PositiveSmallIntegerField(default=0)
    professional_assessment_score = models.PositiveSmallIntegerField(default=0)
    research_completed = models.BooleanField(default=False)
    professional_completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Learning progress"
        verbose_name_plural = "Learning progress"

    def __str__(self):
        return f"{self.profile.display_name} — progress"


class AssessmentSummary(models.Model):
    PATH_RESEARCH = "research"
    PATH_PROFESSIONAL = "professional"
    PATH_CHOICES = [
        (PATH_RESEARCH, "Research & Evidence"),
        (PATH_PROFESSIONAL, "General Professional Work"),
    ]
    profile = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="assessment_summaries")
    pathway = models.CharField(max_length=24, choices=PATH_CHOICES)
    professional_role = models.CharField(max_length=24, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    best_score = models.PositiveSmallIntegerField(default=0)
    passed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("profile", "pathway", "professional_role")
        verbose_name = "Assessment result"
        verbose_name_plural = "Assessment results"

    def __str__(self):
        return f"{self.profile.display_name} — {self.get_pathway_display()} — {self.best_score}%"


class SurveyResponse(models.Model):
    PHASE_PRE = "pre"
    PHASE_POST = "post"
    PHASE_CHOICES = [(PHASE_PRE, "Pre-course"), (PHASE_POST, "Post-course")]
    PATH_CHOICES = AssessmentSummary.PATH_CHOICES

    profile = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="survey_responses")
    pathway = models.CharField(max_length=24, choices=PATH_CHOICES)
    professional_role = models.CharField(max_length=24, blank=True)
    phase = models.CharField(max_length=8, choices=PHASE_CHOICES)
    responses = models.JSONField(default=dict, blank=True)
    is_complete = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("profile", "pathway", "professional_role", "phase")
        verbose_name = "Pre/Post survey"
        verbose_name_plural = "Pre/Post surveys"

    def __str__(self):
        return f"{self.profile.display_name} — {self.get_phase_display()} — {self.get_pathway_display()}"


class Certificate(models.Model):
    profile = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="certificates")
    pathway = models.CharField(max_length=24, choices=AssessmentSummary.PATH_CHOICES)
    professional_role = models.CharField(max_length=24, blank=True)
    certificate_id = models.CharField(max_length=80, unique=True)
    assessment_score = models.PositiveSmallIntegerField(default=0)
    issued_at = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.certificate_id} — {self.profile.display_name}"
