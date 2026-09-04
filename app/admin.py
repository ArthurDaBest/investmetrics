from django.contrib import admin
from django.contrib.admin import register
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html

from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import (
    NewsletterSubscriber,
    Journal,
    AuthorProfile,
    Contact,
    Report,
    ReportSection,
    IJIRISubmission,
)

from ai_at_work.models import LearnerProfile


class LearnerProfileInline(admin.StackedInline):
    model = LearnerProfile
    can_delete = False
    extra = 1
    max_num = 1
    fields = (
        "organization", "access_scope", "professional_role", "access_start",
        "access_expiry", "training_active", "must_change_password", "notes",
    )


admin.site.register(NewsletterSubscriber)
admin.site.register(AuthorProfile)


admin.site.unregister(User)


@register(User)
class UserAdmin(BaseUserAdmin, UnfoldModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ("email", "username", "is_active", "is_staff", "is_superuser")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    inlines = (LearnerProfileInline,)


@admin.register(Contact)
class ContactAdmin(UnfoldModelAdmin):
    list_display = ("name", "email", "subject", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("created_at",)
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(Journal)
class JournalAdmin(UnfoldModelAdmin):
    fieldsets = (
        (
            "Publication Identity",
            {
                "fields": ("title", "slug", "header", "author"),
                "description": (
                    "Core publication information for the Investmetrics Journal of "
                    "Interdisciplinary Research and Intelligence."
                ),
            },
        ),
        ("Publication Overview", {"fields": ("excerpt", "image", "pdf_file")}),
        (
            "Citations",
            {
                "fields": ("apa_citation", "mla_citation", "chicago_citation"),
                "classes": ("collapse",),
                "description": (
                    "Optional custom citations. If left empty, the system will "
                    "generate citation text automatically."
                ),
            },
        ),
    )
    list_display = ("title", "author", "published_date", "updated_date")
    search_fields = (
        "title", "header", "excerpt", "author__username",
        "author__first_name", "author__last_name",
    )
    list_filter = ("published_date", "updated_date")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_date"
    ordering = ("-published_date",)


class ReportSectionInline(admin.StackedInline):
    model = ReportSection
    extra = 0
    min_num = 0
    validate_min = False
    can_delete = True
    fields = ("order", "heading", "content", "image", "image_caption")
    ordering = ("order",)
    verbose_name = "Optional web report section"
    verbose_name_plural = "Optional web report sections"


@admin.register(Report)
class ReportAdmin(UnfoldModelAdmin):
    fieldsets = (
        (
            "Publication Identity",
            {
                "fields": ("title", "slug", "authors", "publication_date", "report_number"),
                "description": (
                    "Enter the formal publication details exactly as they should appear to readers."
                ),
            },
        ),
        (
            "Report Classification",
            {
                "fields": ("category", "theme"),
                "description": (
                    "Classify the report for the Investmetrics publication library."
                ),
            },
        ),
        (
            "Publication Overview",
            {
                "fields": ("eyebrow", "summary", "abstract"),
                "description": (
                    "The summary appears in the Reports library. The abstract appears "
                    "within the full publication page."
                ),
            },
        ),
        (
            "Publication Files",
            {
                "fields": ("cover_image", "pdf_file", "document_file"),
                "description": (
                    "Upload the final PDF and/or an editable DOC/DOCX file."
                ),
            },
        ),
        (
            "Publishing Controls",
            {
                "fields": ("featured", "is_published"),
                "description": (
                    "Featured reports receive additional prominence in the publication library."
                ),
            },
        ),
    )
    inlines = (ReportSectionInline,)
    list_display = (
        "title", "authors", "category", "publication_date", "theme",
        "publication_format", "featured", "is_published",
    )
    list_filter = ("theme", "featured", "is_published", "publication_date", "category")
    search_fields = ("title", "authors", "category", "report_number", "summary", "abstract")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "publication_date"
    ordering = ("-publication_date", "-created_at")
    save_on_top = True

    @admin.display(description="Format")
    def publication_format(self, obj):
        has_sections = obj.sections.exists()
        has_files = bool(obj.pdf_file or obj.document_file)
        if has_sections and has_files:
            return "Hybrid"
        if has_sections:
            return "Web"
        if has_files:
            return "Document"
        return "Metadata only"


@admin.register(IJIRISubmission)
class IJIRISubmissionAdmin(UnfoldModelAdmin):
    fieldsets = (
        (
            "Submission Identity",
            {
                "fields": (
                    "submission_reference", "paper_title", "research_category",
                    "keywords", "submitted_at", "updated_at",
                ),
                "description": "Core information recorded at submission.",
            },
        ),
        (
            "Corresponding Author",
            {
                "fields": (
                    "corresponding_author_name", "corresponding_author_email",
                    "country", "mobile_number", "orcid",
                ),
            },
        ),
        ("All Author Details", {"fields": ("author_details",)}),
        (
            "Manuscript",
            {
                "fields": ("manuscript_download", "manuscript_file", "abstract"),
                "description": (
                    "Use the download link to open the submitted manuscript."
                ),
            },
        ),
        ("AI Use Disclosure", {"fields": ("ai_use_statement",)}),
        (
            "Author Declarations",
            {
                "fields": (
                    "originality_confirmed", "similarity_confirmed",
                    "ai_threshold_confirmed", "ai_use_acknowledged",
                    "apa7_confirmed", "authorisation_confirmed",
                    "declaration_confirmed",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Editorial Workflow",
            {
                "fields": ("status", "status_updated_at", "internal_notes"),
                "description": (
                    "Update the manuscript as it moves through editorial screening, "
                    "review, revision, approval, proofing and publication."
                ),
            },
        ),
    )

    list_display = (
        "submission_reference", "short_title", "corresponding_author_name",
        "corresponding_author_email", "research_category", "status",
        "submitted_at", "manuscript_link",
    )

    list_filter = (
        "status", "research_category", "country", "submitted_at",
        "originality_confirmed", "similarity_confirmed",
        "ai_threshold_confirmed", "apa7_confirmed",
    )

    search_fields = (
        "submission_reference", "paper_title", "keywords",
        "corresponding_author_name", "corresponding_author_email",
        "country", "mobile_number", "orcid", "author_details",
        "abstract", "internal_notes",
    )

    readonly_fields = (
        "submission_reference", "submitted_at", "updated_at",
        "status_updated_at", "manuscript_download",
    )

    ordering = ("-submitted_at",)
    date_hierarchy = "submitted_at"
    save_on_top = True
    list_per_page = 25

    @admin.display(description="Paper Title")
    def short_title(self, obj):
        if len(obj.paper_title) <= 70:
            return obj.paper_title
        return f"{obj.paper_title[:67]}..."

    @admin.display(description="Manuscript")
    def manuscript_link(self, obj):
        if not obj.manuscript_file:
            return "No file"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Download</a>',
            obj.manuscript_file.url,
        )

    @admin.display(description="Submitted Manuscript")
    def manuscript_download(self, obj):
        if not obj or not obj.pk or not obj.manuscript_file:
            return "No manuscript file is attached."
        filename = obj.manuscript_file.name.split("/")[-1]
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Download {}</a>',
            obj.manuscript_file.url,
            filename,
        )
