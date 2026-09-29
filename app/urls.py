from django.urls import path

from . import views
from .views import (
    JournalListView,
    JournalDetailView,
    JournalListCreateView,
)


urlpatterns = [

    # ========================================================
    # HOME
    # ========================================================

    path(
        "",
        views.home,
        name="home",
    ),


    # ========================================================
    # SERVICES
    # ========================================================

    path(
        "service/",
        views.service,
        name="service-details.html",
    ),

    path(
        "research-and-publications/",
        views.research_and_publications,
        name="research-and-publications-service.html",
    ),

    path(
        "project-development-and-management/",
        views.proj_dvt_and_management,
        name="proj-dvt-and-management.html",
    ),

    path(
        "policy-review-and-analysis/",
        views.policy_review_and_analysis,
        name="policy-review-and-analysis.html",
    ),

    path(
        "academic-mentorship-and-training/",
        views.academic_mentorship_and_training,
        name="academic-mentorship-and-training.html",
    ),
path(
    "academic-mentorship-and-training/success/<str:reference>/",
    views.training_application_success,
    name="training-application-success",
),

    # ========================================================
    # PUBLISH WITH INVESTMETRICS
    # ========================================================

    path(
        "publish-with-investmetrics/",
        views.publish_with_investmetrics,
        name="publish-with-investmetrics",
    ),


    # ========================================================
    # IJIRI MANUSCRIPT SUBMISSION
    # ========================================================

    path(
        "ijiri/submit/",
        views.ijiri_submit,
        name="ijiri-submit",
    ),

    path(
        "ijiri/submit/success/<str:reference>/",
        views.ijiri_submit_success,
        name="ijiri-submit-success",
    ),


    # Secure initial account setup for authorised IJIRI editorial partners.
    path(
        "ijiri/editor/setup/<uidb64>/<token>/",
        views.ijiri_editor_set_initial_password,
        name="ijiri-editor-set-initial-password",
    ),


    # ========================================================
    # NEWSLETTER & CONTACT
    # ========================================================

    path(
        "newsletter-subscribe/",
        views.newsletter_subscribe,
        name="newsletter_subscribe",
    ),

    path(
        "contact/",
        views.contact,
        name="contact",
    ),


    # ========================================================
    # TEAM
    # ========================================================

    path(
        "team-1/",
        views.team_1,
        name="team-1.html",
    ),

    path(
        "team-2/",
        views.team_2,
        name="team-2.html",
    ),

    path(
        "team-3/",
        views.team_3,
        name="team-3.html",
    ),

    path(
        "team-4/",
        views.team_4,
        name="team-4.html",
    ),

    path(
        "team-5/",
        views.team_5,
        name="team-5.html",
    ),

    path(
        "team-6/",
        views.team_6,
        name="team-6.html",
    ),


    # ========================================================
    # REPORT PUBLICATION SYSTEM
    # ========================================================

    path(
        "reports/",
        views.reports,
        name="reports",
    ),

    path(
        "reports/<slug:slug>/",
        views.report_detail,
        name="report-detail",
    ),


    # ========================================================
    # LEGACY REPORT ROUTES
    # Retained while older publications remain in use
    # ========================================================

    path(
        "report-1/",
        views.report_1,
        name="report-1",
    ),

    path(
        "report-2/",
        views.report_2,
        name="report-2",
    ),

    path(
        "report-3/",
        views.report_3,
        name="report-3",
    ),


    # ========================================================
    # JOURNAL PUBLICATION SYSTEM
    # ========================================================

    path(
        "journals/",
        JournalListView.as_view(),
        name="journal_list",
    ),

    path(
        "journals/<slug:slug>/",
        JournalDetailView.as_view(),
        name="journal_detail",
    ),


    # ========================================================
    # ENROLLMENT
    # ========================================================

    path(
        "enroll/",
        views.enroll,
        name="enroll",
    ),


    # ========================================================
    # COMPANY PROFILE
    # ========================================================

    path(
        "company-profile/",
        views.company_profile,
        name="company-profile",
    ),

    path(
        "download-company-profile/",
        views.download_company_profile,
        name="download_company_profile",
    ),


    # ========================================================
    # APIs
    # ========================================================

    path(
        "api/journals/",
        JournalListCreateView.as_view(),
        name="journal-list-create",
    ),
]
