from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import register
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.html import format_html

from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import (
    TrainingApplication,
    NewsletterSubscriber,
    Journal,
    AuthorProfile,
    Contact,
    Report,
    ReportSection,
    IJIRISubmission,
)

from ai_at_work.models import LearnerProfile
from ai_at_work.email_service import send_learning_email


class LearnerProfileInline(admin.StackedInline):
    model = LearnerProfile
    can_delete = False
    extra = 1
    max_num = 1
    fields = (
        "organization",
        "access_scope",
        "professional_role",
        "access_start",
        "access_expiry",
        "training_active",
        "must_change_password",
        "notes",
    )


admin.site.register(NewsletterSubscriber)
admin.site.register(AuthorProfile)


admin.site.unregister(User)


@register(User)
class UserAdmin(BaseUserAdmin, UnfoldModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        "email",
        "username",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
    )

    inlines = (LearnerProfileInline,)


@admin.register(Contact)
class ContactAdmin(UnfoldModelAdmin):
    list_display = (
        "name",
        "email",
        "subject",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "subject",
        "message",
    )

    readonly_fields = ("created_at",)
    list_filter = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(Journal)
class JournalAdmin(UnfoldModelAdmin):

    fieldsets = (
        (
            "Publication Identity",
            {
                "fields": (
                    "title",
                    "slug",
                    "header",
                    "author",
                ),
                "description": (
                    "Core publication information for the Investmetrics "
                    "Journal of Interdisciplinary Research and Intelligence."
                ),
            },
        ),
        (
            "Publication Overview",
            {
                "fields": (
                    "excerpt",
                    "image",
                    "pdf_file",
                )
            },
        ),
        (
            "Citations",
            {
                "fields": (
                    "apa_citation",
                    "mla_citation",
                    "chicago_citation",
                ),
                "classes": ("collapse",),
                "description": (
                    "Optional custom citations. If left empty, the system "
                    "will generate citation text automatically."
                ),
            },
        ),
    )

    list_display = (
        "title",
        "author",
        "published_date",
        "updated_date",
    )

    search_fields = (
        "title",
        "header",
        "excerpt",
        "author__username",
        "author__first_name",
        "author__last_name",
    )

    list_filter = (
        "published_date",
        "updated_date",
    )

    prepopulated_fields = {
        "slug": ("title",),
    }

    date_hierarchy = "published_date"
    ordering = ("-published_date",)


class ReportSectionInline(admin.StackedInline):
    model = ReportSection
    extra = 0
    min_num = 0
    validate_min = False
    can_delete = True

    fields = (
        "order",
        "heading",
        "content",
        "image",
        "image_caption",
    )

    ordering = ("order",)
    verbose_name = "Optional web report section"
    verbose_name_plural = "Optional web report sections"


@admin.register(Report)
class ReportAdmin(UnfoldModelAdmin):

    fieldsets = (
        (
            "Publication Identity",
            {
                "fields": (
                    "title",
                    "slug",
                    "authors",
                    "publication_date",
                    "report_number",
                ),
                "description": (
                    "Enter the formal publication details exactly as "
                    "they should appear to readers."
                ),
            },
        ),
        (
            "Report Classification",
            {
                "fields": (
                    "category",
                    "theme",
                ),
                "description": (
                    "Classify the report for the Investmetrics "
                    "publication library."
                ),
            },
        ),
        (
            "Publication Overview",
            {
                "fields": (
                    "eyebrow",
                    "summary",
                    "abstract",
                ),
                "description": (
                    "The summary appears in the Reports library. "
                    "The abstract appears within the full publication page."
                ),
            },
        ),
        (
            "Publication Files",
            {
                "fields": (
                    "cover_image",
                    "pdf_file",
                    "document_file",
                ),
                "description": (
                    "Upload the final PDF and/or an editable DOC/DOCX file."
                ),
            },
        ),
        (
            "Publishing Controls",
            {
                "fields": (
                    "featured",
                    "is_published",
                ),
                "description": (
                    "Featured reports receive additional prominence "
                    "in the publication library."
                ),
            },
        ),
    )

    inlines = (ReportSectionInline,)

    list_display = (
        "title",
        "authors",
        "category",
        "publication_date",
        "theme",
        "publication_format",
        "featured",
        "is_published",
    )

    list_filter = (
        "theme",
        "featured",
        "is_published",
        "publication_date",
        "category",
    )

    search_fields = (
        "title",
        "authors",
        "category",
        "report_number",
        "summary",
        "abstract",
    )

    prepopulated_fields = {
        "slug": ("title",),
    }

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

    AJER_GROUP_NAME = "AJER Editorial Partner"

    fieldsets = (
        (
            "Submission Identity",
            {
                "fields": (
                    "submission_reference",
                    "paper_title",
                    "research_category",
                    "keywords",
                    "submitted_at",
                    "updated_at",
                ),
                "description": (
                    "Core information recorded at submission."
                ),
            },
        ),
        (
            "Corresponding Author",
            {
                "fields": (
                    "corresponding_author_name",
                    "corresponding_author_email",
                    "country",
                    "mobile_number",
                    "orcid",
                ),
            },
        ),
        (
            "All Author Details",
            {
                "fields": (
                    "author_details",
                )
            },
        ),
        (
            "Manuscript",
            {
                "fields": (
                    "manuscript_download",
                    "manuscript_file",
                    "abstract",
                ),
                "description": (
                    "Use the download link to open the "
                    "submitted manuscript."
                ),
            },
        ),
        (
            "AI Use Disclosure",
            {
                "fields": (
                    "ai_use_statement",
                )
            },
        ),
        (
            "Author Declarations",
            {
                "fields": (
                    "originality_confirmed",
                    "similarity_confirmed",
                    "ai_threshold_confirmed",
                    "ai_use_acknowledged",
                    "apa7_confirmed",
                    "authorisation_confirmed",
                    "declaration_confirmed",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Editorial Workflow",
            {
                "fields": (
                    "status",
                    "status_updated_at",
                    "internal_notes",
                ),
                "description": (
                    "Update the manuscript as it moves through editorial "
                    "screening, review, revision, approval, proofing "
                    "and publication."
                ),
            },
        ),
    )

    list_display = (
        "submission_reference",
        "short_title",
        "corresponding_author_name",
        "corresponding_author_email",
        "research_category",
        "status",
        "submitted_at",
        "manuscript_link",
    )

    list_filter = (
        "status",
        "research_category",
        "country",
        "submitted_at",
        "originality_confirmed",
        "similarity_confirmed",
        "ai_threshold_confirmed",
        "apa7_confirmed",
    )

    search_fields = (
        "submission_reference",
        "paper_title",
        "keywords",
        "corresponding_author_name",
        "corresponding_author_email",
        "country",
        "mobile_number",
        "orcid",
        "author_details",
        "abstract",
        "internal_notes",
    )

    readonly_fields = (
        "submission_reference",
        "submitted_at",
        "updated_at",
        "status_updated_at",
        "manuscript_download",
    )

    ordering = ("-submitted_at",)
    date_hierarchy = "submitted_at"
    save_on_top = True
    list_per_page = 25

    def is_ajer_editorial_partner(self, request):
        if request.user.is_superuser:
            return False

        return request.user.groups.filter(
            name=self.AJER_GROUP_NAME
        ).exists()

    def get_readonly_fields(self, request, obj=None):
        if self.is_ajer_editorial_partner(request):
            return (
                "submission_reference",
                "paper_title",
                "research_category",
                "keywords",
                "submitted_at",
                "updated_at",
                "corresponding_author_name",
                "corresponding_author_email",
                "country",
                "mobile_number",
                "orcid",
                "author_details",
                "manuscript_download",
                "manuscript_file",
                "abstract",
                "ai_use_statement",
                "originality_confirmed",
                "similarity_confirmed",
                "ai_threshold_confirmed",
                "ai_use_acknowledged",
                "apa7_confirmed",
                "authorisation_confirmed",
                "declaration_confirmed",
                "status_updated_at",
            )

        return super().get_readonly_fields(request, obj)

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
            '<a href="{}" target="_blank" '
            'rel="noopener">Download</a>',
            obj.manuscript_file.url,
        )

    @admin.display(description="Submitted Manuscript")
    def manuscript_download(self, obj):
        if not obj or not obj.pk or not obj.manuscript_file:
            return "No manuscript file is attached."

        filename = obj.manuscript_file.name.split("/")[-1]

        return format_html(
            '<a href="{}" target="_blank" '
            'rel="noopener">Download {}</a>',
            obj.manuscript_file.url,
            filename,
        )


@admin.register(TrainingApplication)
class TrainingApplicationAdmin(UnfoldModelAdmin):

    fieldsets = (
        (
            "Application Identity",
            {
                "fields": (
                    "application_reference",
                    "submitted_at",
                    "updated_at",
                )
            },
        ),
        (
            "Learner Details",
            {
                "fields": (
                    "full_name",
                    "email",
                    "mobile_number",
                    "country",
                    "organisation",
                    "role_or_academic_level",
                    "learner_user",
                )
            },
        ),
        (
            "Training Selection",
            {
                "fields": (
                    "training_pathway",
                    "training_area",
                    "learning_expectation",
                    "training_fee",
                )
            },
        ),
        (
            "Payment and Access",
            {
                "fields": (
                    "status",
                    "payment_confirmed_at",
                    "training_access_link",
                    "access_email_sent",
                )
            },
        ),
        (
            "Internal Notes",
            {
                "fields": (
                    "internal_notes",
                )
            },
        ),
    )

    list_display = (
        "application_reference",
        "full_name",
        "email",
        "training_pathway",
        "training_area",
        "status",
        "training_fee",
        "submitted_at",
    )

    list_filter = (
        "status",
        "training_pathway",
        "training_area",
        "country",
        "submitted_at",
    )

    search_fields = (
        "application_reference",
        "full_name",
        "email",
        "mobile_number",
        "country",
        "organisation",
        "role_or_academic_level",
        "learner_user__username",
        "learner_user__email",
    )

    readonly_fields = (
        "application_reference",
        "training_fee",
        "submitted_at",
        "updated_at",
        "access_email_sent",
    )

    ordering = ("-submitted_at",)
    date_hierarchy = "submitted_at"
    save_on_top = True
    list_per_page = 25

    actions = (
        "confirm_payment_and_send_access",
    )

    @admin.action(
        description="Confirm payment and send training access"
    )
    def confirm_payment_and_send_access(self, request, queryset):

        sent_count = 0
        skipped_count = 0
        failed_count = 0

        for application in queryset:

            # Never send the access message twice.
            if application.access_email_sent:
                skipped_count += 1
                continue

            # Every approved application must be linked to a learner.
            if not application.learner_user:
                skipped_count += 1
                continue

            user = application.learner_user

            try:
                profile = user.aiw_profile
            except LearnerProfile.DoesNotExist:
                skipped_count += 1
                continue

            learner_email = (
                application.email.strip()
                or user.email.strip()
            )

            if not learner_email:
                skipped_count += 1
                continue

            # Keep the learner entitlement aligned with the pathway
            # selected in the approved training application.
            if (
                application.training_pathway
                == TrainingApplication.PATHWAY_PROFESSIONAL
            ):
                profile.access_scope = LearnerProfile.ACCESS_PROFESSIONAL
            else:
                profile.access_scope = LearnerProfile.ACCESS_RESEARCH

            access_link = ""

            if application.training_access_link:
                access_link = application.training_access_link.strip()

            if not access_link:
                access_link = request.build_absolute_uri("/learn/")

            needs_password_setup = not user.has_usable_password()
            password_setup_link = ""

            if needs_password_setup:
                uid = urlsafe_base64_encode(
                    force_bytes(user.pk)
                )
                token = default_token_generator.make_token(user)

                password_setup_link = request.build_absolute_uri(
                    f"/learn/set-password/{uid}/{token}/"
                )

            # Activate the account and learning entitlement only after
            # Investmetrics has confirmed payment.
            today = timezone.localdate()

            if not user.is_active:
                user.is_active = True
                user.save(
                    update_fields=[
                        "is_active",
                    ]
                )

            profile.training_active = True

            if not profile.access_start:
                profile.access_start = today

            # New learners must complete the secure password setup.
            # Existing learners continue using their current password.
            profile.must_change_password = needs_password_setup

            profile.save(
                update_fields=[
                    "access_scope",
                    "training_active",
                    "access_start",
                    "must_change_password",
                    "updated_at",
                ]
            )

            if not application.payment_confirmed_at:
                application.payment_confirmed_at = timezone.now()

            application.status = "payment_confirmed"

            application.save(
                update_fields=[
                    "payment_confirmed_at",
                    "status",
                    "updated_at",
                ]
            )

            access_subject = (
                "Investmetrics Training Access - "
                f"{application.application_reference}"
            )

            if needs_password_setup:
                account_instructions = (
                    "ACCOUNT SETUP\n"
                    "Your Investmetrics Learning access is ready. "
                    "Set your password using the secure one-time "
                    "link below:\n"
                    f"{password_setup_link}\n\n"
                    "After setting your password, use the training "
                    "access link below:\n"
                    f"{access_link}\n\n"
                    f"Account Email: {user.email}\n"
                    f"Username: {user.username}\n\n"
                    "For security, do not share the password setup "
                    "link or your learning account credentials.\n\n"
                )
            else:
                account_instructions = (
                    "TRAINING ACCESS\n"
                    f"{access_link}\n\n"
                    "Your existing Investmetrics Learning account "
                    "remains your login account. Use your current "
                    "password to sign in.\n\n"
                    f"Account Email: {user.email}\n"
                    f"Username: {user.username}\n\n"
                    "Please keep your learning account private. "
                    "It is intended only for the approved learner "
                    "named in this application.\n\n"
                )

            access_body = (
                f"Dear {application.full_name},\n\n"
                "Your payment has been confirmed and your "
                "Investmetrics Learning access is now active.\n\n"
                f"Application Reference: "
                f"{application.application_reference}\n"
                f"Training Pathway: "
                f"{application.get_training_pathway_display()}\n"
                f"Training Area: "
                f"{application.get_training_area_display()}\n"
                f"Training Fee: TZS {application.training_fee:,}\n"
                "Payment Status: Confirmed\n\n"
                f"{account_instructions}"
                "Regards,\n"
                "Investmetrics Learning\n"
                "www.investmetrics.co.tz"
            )

            try:
                send_learning_email(
                    subject=access_subject,
                    message=access_body,
                    recipient_list=[learner_email],
                )

            except Exception as exc:
                failed_count += 1

                # Payment remains confirmed so Admin can retry
                # the access email without reconfirming payment.
                self.message_user(
                    request,
                    (
                        "Access email failed for "
                        f"{application.application_reference}: {exc}"
                    ),
                    level=messages.ERROR,
                )
                continue

            application.status = "access_sent"
            application.access_email_sent = True

            application.save(
                update_fields=[
                    "status",
                    "access_email_sent",
                    "updated_at",
                ]
            )

            sent_count += 1

        if sent_count:
            self.message_user(
                request,
                (
                    f"{sent_count} training access email(s) sent "
                    "successfully."
                ),
                level=messages.SUCCESS,
            )

        if skipped_count:
            self.message_user(
                request,
                (
                    f"{skipped_count} application(s) skipped because "
                    "access had already been sent or learner account "
                    "information was incomplete."
                ),
                level=messages.WARNING,
            )

        if failed_count:
            self.message_user(
                request,
                (
                    f"{failed_count} access email(s) could not be sent. "
                    "Payment confirmation was retained for retry."
                ),
                level=messages.ERROR,
            )
