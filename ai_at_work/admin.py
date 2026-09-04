from django.contrib import admin
from django.http import HttpResponse
import csv
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from .models import (
    LearnerProfile,
    LearningState,
    AssessmentSummary,
    SurveyResponse,
    Certificate,
)


@admin.register(LearnerProfile)
class LearnerProfileAdmin(UnfoldModelAdmin):
    list_display = (
        "display_name_admin",
        "email_admin",
        "organization",
        "access_scope",
        "professional_role",
        "training_active",
        "access_expiry",
        "must_change_password",
        "research_progress_admin",
        "professional_progress_admin",
    )
    list_filter = ("access_scope", "professional_role", "training_active", "must_change_password")
    search_fields = ("user__first_name", "user__last_name", "user__username", "user__email", "organization")
    autocomplete_fields = ("user",)


    actions = ("export_learner_register",)

    @admin.display(description="Research")
    def research_progress_admin(self, obj):
        try:
            return f"{obj.learning_state.research_progress}%"
        except Exception:
            return "0%"

    @admin.display(description="Professional")
    def professional_progress_admin(self, obj):
        try:
            return f"{obj.learning_state.professional_progress}%"
        except Exception:
            return "0%"

    @admin.action(description="Export selected learner register (CSV)")
    def export_learner_register(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="ai_at_work_learner_register.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Full name", "Email", "Organization", "Access", "Professional role",
            "Active", "Access start", "Access expiry", "Research progress",
            "Research score", "Professional progress", "Professional score",
        ])
        for obj in queryset.select_related("user"):
            try:
                state = obj.learning_state
            except Exception:
                state = None
            writer.writerow([
                obj.display_name,
                obj.user.email,
                obj.organization,
                obj.get_access_scope_display(),
                obj.get_professional_role_display(),
                obj.training_active,
                obj.access_start or "",
                obj.access_expiry or "",
                getattr(state, "research_progress", 0),
                getattr(state, "research_assessment_score", 0),
                getattr(state, "professional_progress", 0),
                getattr(state, "professional_assessment_score", 0),
            ])
        return response

    @admin.display(description="Learner")
    def display_name_admin(self, obj):
        return obj.display_name

    @admin.display(description="Email")
    def email_admin(self, obj):
        return obj.user.email


@admin.register(LearningState)
class LearningStateAdmin(UnfoldModelAdmin):
    list_display = (
        "profile",
        "current_pathway",
        "research_progress",
        "research_assessment_score",
        "professional_progress",
        "professional_assessment_score",
        "updated_at",
    )
    list_filter = ("current_pathway", "research_completed", "professional_completed")
    search_fields = ("profile__user__first_name", "profile__user__last_name", "profile__user__email")
    readonly_fields = (
        "profile",
        "storage",
        "current_pathway",
        "research_progress",
        "professional_progress",
        "research_assessment_score",
        "professional_assessment_score",
        "research_completed",
        "professional_completed",
        "updated_at",
    )


@admin.register(AssessmentSummary)
class AssessmentSummaryAdmin(UnfoldModelAdmin):
    list_display = ("profile", "pathway", "professional_role", "best_score", "attempts", "passed", "updated_at")
    list_filter = ("pathway", "professional_role", "passed")
    search_fields = ("profile__user__first_name", "profile__user__last_name", "profile__user__email")


@admin.register(SurveyResponse)
class SurveyResponseAdmin(UnfoldModelAdmin):
    list_display = ("profile", "phase", "pathway", "professional_role", "is_complete", "updated_at")
    list_filter = ("phase", "pathway", "professional_role", "is_complete")
    search_fields = ("profile__user__first_name", "profile__user__last_name", "profile__user__email")
    readonly_fields = ("responses", "updated_at")


@admin.register(Certificate)
class CertificateAdmin(UnfoldModelAdmin):
    list_display = ("certificate_id", "profile", "pathway", "professional_role", "assessment_score", "issued_at", "active")
    list_filter = ("pathway", "professional_role", "active")
    search_fields = ("certificate_id", "profile__user__first_name", "profile__user__last_name", "profile__user__email")
    readonly_fields = ("issued_at",)
