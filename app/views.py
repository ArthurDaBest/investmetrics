import logging
import tempfile
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage, send_mail
from django.db import IntegrityError, transaction
from django.http import JsonResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import ListView, DetailView

from rest_framework import generics

from .forms import (
    ContactForm,
    NewsletterForm,
    IJIRISubmissionForm,
    TrainingApplicationForm,
)

from .models import (
    NewsletterSubscriber,
    Journal,
    Contact,
    Report,
    TrainingApplication,
)

from .serializer import JournalSerializer
from ai_at_work.models import LearnerProfile
from ai_at_work.email_service import send_learning_email


logger = logging.getLogger(__name__)


# ============================================================
# JOURNAL API
# ============================================================

class JournalListCreateView(generics.ListCreateAPIView):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer


# ============================================================
# HOME
# ============================================================

def home(request):

    if request.method == "POST":

        form = ContactForm(request.POST)

        if form.is_valid():

            try:

                Contact.objects.create(
                    name=form.cleaned_data["name"],
                    email=form.cleaned_data["email"],
                    subject=form.cleaned_data["subject"],
                    message=form.cleaned_data["message"],
                )

                try:

                    send_mail(
                        subject=(
                            "New Contact Form Submission: "
                            f"{form.cleaned_data['subject']}"
                        ),
                        message=(
                            f"Name: {form.cleaned_data['name']}\n"
                            f"Email: {form.cleaned_data['email']}\n"
                            f"Subject: {form.cleaned_data['subject']}\n\n"
                            f"Message:\n{form.cleaned_data['message']}"
                        ),
                        from_email=getattr(
                            settings,
                            "DEFAULT_FROM_EMAIL",
                            "noreply@example.com",
                        ),
                        recipient_list=[
                            getattr(
                                settings,
                                "ADMIN_EMAIL",
                                "admin@example.com",
                            )
                        ],
                        fail_silently=True,
                    )

                except Exception as exc:
                    logger.error(
                        "Home contact email sending failed: %s",
                        exc,
                    )

                messages.success(
                    request,
                    "Your message has been sent successfully!",
                )

                return redirect("/#contact")

            except Exception as exc:

                logger.error(
                    "Home contact form submission failed: %s",
                    exc,
                )

                messages.error(
                    request,
                    "An error occurred. Please try again later.",
                )

    else:
        form = ContactForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "home.html",
        context,
    )


# ============================================================
# SERVICE PAGES
# ============================================================

def service(request):
    return render(
        request,
        "service-details.html",
    )


def research_and_publications(request):
    return render(
        request,
        "research-and-publications-service.html",
    )


def proj_dvt_and_management(request):
    return render(
        request,
        "proj-dvt-and-management.html",
    )


def policy_review_and_analysis(request):
    return render(
        request,
        "policy-review-and-analysis.html",
    )


# ============================================================
# ACADEMIC MENTORSHIP AND TRAINING
# ============================================================

def _training_username(email):
    """Build a unique Django username from the applicant's email address."""
    User = get_user_model()

    local_part = email.split("@", 1)[0].strip().lower()
    cleaned = "".join(
        character
        for character in local_part
        if character.isalnum() or character in "._-"
    )
    cleaned = cleaned.strip("._-") or "learner"

    base_username = cleaned[:140]
    username = base_username
    counter = 1

    while User.objects.filter(username__iexact=username).exists():
        suffix = f"-{counter}"
        username = f"{base_username[:150 - len(suffix)]}{suffix}"
        counter += 1

    return username


def _prepare_training_learner(application):
    """
    Link an application to one existing learner when the email identifies
    that learner unambiguously. Otherwise prepare a new pending learner.
    """
    User = get_user_model()
    email = application.email.strip().lower()

    if application.training_pathway == TrainingApplication.PATHWAY_PROFESSIONAL:
        requested_access_scope = LearnerProfile.ACCESS_PROFESSIONAL
    else:
        requested_access_scope = LearnerProfile.ACCESS_RESEARCH

    matching_users = list(
        User.objects.filter(email__iexact=email).order_by("id")
    )

    learner_users = [
        user
        for user in matching_users
        if hasattr(user, "aiw_profile")
    ]

    if len(learner_users) == 1:
        application.learner_user = learner_users[0]
        application.save(
            update_fields=[
                "learner_user",
                "updated_at",
            ]
        )
        return learner_users[0]

    if len(learner_users) > 1:
        logger.warning(
            "Training application %s has multiple learner accounts "
            "using email %s. Learner assignment requires Admin review.",
            application.application_reference,
            email,
        )
        return None

    eligible_existing_users = [
        user
        for user in matching_users
        if not user.is_staff and not user.is_superuser
    ]

    if len(matching_users) == 1 and len(eligible_existing_users) == 1:
        user = eligible_existing_users[0]

        profile, _ = LearnerProfile.objects.get_or_create(
            user=user,
            defaults={
                "organization": application.organisation or "",
                "access_scope": requested_access_scope,
                "professional_role": LearnerProfile.ROLE_ANY,
                "training_active": False,
                "must_change_password": True,
            },
        )

        profile.training_active = False
        profile.must_change_password = True

        if application.organisation and not profile.organization:
            profile.organization = application.organisation

        profile.save()

        application.learner_user = user
        application.save(
            update_fields=[
                "learner_user",
                "updated_at",
            ]
        )
        return user

    if matching_users:
        logger.warning(
            "Training application %s uses email %s already attached "
            "to an account that requires Admin review.",
            application.application_reference,
            email,
        )
        return None

    name_parts = application.full_name.strip().split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    user = User(
        username=_training_username(email),
        email=email,
        first_name=first_name[:150],
        last_name=last_name[:150],
        is_active=False,
    )
    user.set_unusable_password()
    user.save()

    LearnerProfile.objects.create(
        user=user,
        organization=application.organisation or "",
        access_scope=requested_access_scope,
        professional_role=LearnerProfile.ROLE_ANY,
        training_active=False,
        must_change_password=True,
    )

    application.learner_user = user
    application.save(
        update_fields=[
            "learner_user",
            "updated_at",
        ]
    )

    return user


@require_http_methods(["GET", "POST"])
def academic_mentorship_and_training(request):

    if request.method == "POST":

        training_form = TrainingApplicationForm(
            request.POST
        )

        if training_form.is_valid():

            with transaction.atomic():
                application = training_form.save()
                _prepare_training_learner(application)

            payment_subject = (
                "Investmetrics Training Application Received - "
                f"{application.application_reference}"
            )

            payment_body = (
                f"Dear {application.full_name},\n\n"
                "Thank you for applying for Investmetrics training.\n\n"
                f"Application Reference: "
                f"{application.application_reference}\n"
                f"Training Pathway: "
                f"{application.get_training_pathway_display()}\n"
                f"Training Area: "
                f"{application.get_training_area_display()}\n"
                f"Training Fee: TZS {application.training_fee:,}\n"
                f"Current Status: "
                f"{application.get_status_display()}\n\n"
                "PAYMENT DETAILS\n"
                f"Amount: TZS {application.training_fee:,}\n"
                "Payment Number: +255 689 660 000\n"
                "Account / Recipient Name: Begarving Arthur\n\n"
                "Please use your application reference when making "
                "payment or when contacting Investmetrics about your "
                "training application.\n\n"
                "After payment confirmation, you will receive secure "
                "instructions for setting your password and accessing "
                "Investmetrics Learning.\n\n"
                "Regards,\n"
                "Investmetrics Learning\n"
                "www.investmetrics.co.tz"
            )

            try:
                send_learning_email(
                    subject=payment_subject,
                    message=payment_body,
                    recipient_list=[application.email],
                )

            except Exception as exc:
                logger.error(
                    "Training application email failed for %s: %s",
                    application.application_reference,
                    exc,
                )

            return redirect(
                "training-application-success",
                reference=application.application_reference,
            )

    else:

        training_form = TrainingApplicationForm()

    return render(
        request,
        "academic-mentorship-and-training.html",
        {
            "training_form": training_form,
        },
    )

def training_application_success(request, reference):

    application = get_object_or_404(
        TrainingApplication,
        application_reference=reference,
    )

    return render(
        request,
        "training-application-success.html",
        {
            "application": application,
            "reference": application.application_reference,
        },
    )


# ============================================================
# TEAM PAGES
# ============================================================

def team_1(request):
    return render(
        request,
        "team-1.html",
    )


def team_2(request):
    return render(
        request,
        "team-2.html",
    )


def team_3(request):
    return render(
        request,
        "team-3.html",
    )


def team_4(request):
    return render(
        request,
        "team-4.html",
    )


def team_5(request):
    return render(
        request,
        "team-5.html",
    )


def team_6(request):
    return render(
        request,
        "team-6.html",
    )


# ============================================================
# REPORT PUBLICATION SYSTEM
# ============================================================

def reports(request):

    reports_list = Report.objects.filter(
        is_published=True
    ).order_by(
        "-featured",
        "-publication_date",
    )

    return render(
        request,
        "reports.html",
        {
            "reports": reports_list,
        },
    )


def report_detail(request, slug):

    report = get_object_or_404(
        Report.objects.prefetch_related("sections"),
        slug=slug,
        is_published=True,
    )

    return render(
        request,
        "report-detail.html",
        {
            "report": report,
        },
    )


# ============================================================
# PUBLISH WITH INVESTMETRICS
# ============================================================

def publish_with_investmetrics(request):

    return render(
        request,
        "publish-with-investmetrics.html",
    )


# ============================================================
# IJIRI MANUSCRIPT SUBMISSION
# ============================================================

@require_http_methods(["GET", "POST"])
def ijiri_submit(request):

    if request.method == "POST":

        form = IJIRISubmissionForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            submission = form.save()

            editorial_email = getattr(
                settings,
                "IJIRI_EDITORIAL_EMAIL",
                "ijiri@investmetrics.co.tz",
            )

            from_email = getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                getattr(
                    settings,
                    "EMAIL_HOST_USER",
                    "noreply@investmetrics.co.tz",
                ),
            )

            # ------------------------------------------------
            # EDITORIAL OFFICE NOTIFICATION
            # ------------------------------------------------

            editorial_subject = (
                f"New IJIRI Manuscript Submission - "
                f"{submission.submission_reference}"
            )

            editorial_body = (
                "A new manuscript has been submitted to IJIRI.\n\n"
                f"Submission Reference: "
                f"{submission.submission_reference}\n"
                f"Paper Title: {submission.paper_title}\n"
                f"Research Category: "
                f"{submission.get_research_category_display()}\n"
                f"Corresponding Author: "
                f"{submission.corresponding_author_name}\n"
                f"Email: "
                f"{submission.corresponding_author_email}\n"
                f"Country: {submission.country}\n"
                f"Mobile Number: "
                f"{submission.mobile_number or 'Not provided'}\n"
                f"ORCID: "
                f"{submission.orcid or 'Not provided'}\n"
                f"Keywords: {submission.keywords}\n\n"
                "Author Details:\n"
                f"{submission.author_details}\n\n"
                "Abstract:\n"
                f"{submission.abstract}\n\n"
                "AI Use Disclosure:\n"
                f"{submission.ai_use_statement or 'No statement provided.'}\n\n"
                "Declarations:\n"
                f"- Originality confirmed: "
                f"{submission.originality_confirmed}\n"
                f"- Similarity below 18% confirmed: "
                f"{submission.similarity_confirmed}\n"
                f"- AI content below 15% confirmed: "
                f"{submission.ai_threshold_confirmed}\n"
                f"- AI disclosure acknowledged: "
                f"{submission.ai_use_acknowledged}\n"
                f"- APA 7th Edition confirmed: "
                f"{submission.apa7_confirmed}\n"
                f"- Submission authority confirmed: "
                f"{submission.authorisation_confirmed}\n"
                f"- IJIRI requirements accepted: "
                f"{submission.declaration_confirmed}\n\n"
                f"Current Status: "
                f"{submission.get_status_display()}\n"
                f"Submitted At: "
                f"{submission.submitted_at}\n"
            )

            try:

                editorial_message = EmailMessage(
                    subject=editorial_subject,
                    body=editorial_body,
                    from_email=from_email,
                    to=[
                        editorial_email
                    ],
                    reply_to=[
                        submission.corresponding_author_email
                    ],
                )

                manuscript = submission.manuscript_file

                manuscript.open("rb")

                editorial_message.attach(
                    manuscript.name.split("/")[-1],
                    manuscript.read(),
                    getattr(
                        manuscript.file,
                        "content_type",
                        "application/octet-stream",
                    ),
                )

                manuscript.close()

                editorial_message.send(
                    fail_silently=False
                )

            except Exception as exc:

                logger.error(
                    "IJIRI editorial notification failed for %s: %s",
                    submission.submission_reference,
                    exc,
                )

            # ------------------------------------------------
            # AUTHOR ACKNOWLEDGEMENT
            # ------------------------------------------------

            acknowledgement_subject = (
                "IJIRI Manuscript Submission Received - "
                f"{submission.submission_reference}"
            )

            acknowledgement_body = (
                f"Dear {submission.corresponding_author_name},\n\n"
                "Thank you for submitting your manuscript to the "
                "Investmetrics Journal of Interdisciplinary Research "
                "and Intelligence (IJIRI).\n\n"
                f"Submission Reference: "
                f"{submission.submission_reference}\n"
                f"Paper Title: "
                f"{submission.paper_title}\n"
                f"Current Status: "
                f"{submission.get_status_display()}\n\n"
                "Your manuscript has been recorded in the IJIRI "
                "submission system. Please retain the submission "
                "reference for future correspondence.\n\n"
                "The manuscript will proceed through the journal's "
                "editorial screening and review process. Editorial "
                "timelines are operational targets and may vary "
                "depending on the manuscript and reviewer availability.\n\n"
                "Regards,\n"
                "IJIRI Editorial Office\n"
                "Investmetrics\n"
                "ijiri@investmetrics.co.tz"
            )

            try:

                send_mail(
                    subject=acknowledgement_subject,
                    message=acknowledgement_body,
                    from_email=from_email,
                    recipient_list=[
                        submission.corresponding_author_email
                    ],
                    fail_silently=False,
                )

            except Exception as exc:

                logger.error(
                    "IJIRI author acknowledgement failed for %s: %s",
                    submission.submission_reference,
                    exc,
                )

            return redirect(
                "ijiri-submit-success",
                reference=submission.submission_reference,
            )

    else:

        form = IJIRISubmissionForm()

    return render(
        request,
        "ijiri-submit.html",
        {
            "form": form,
        },
    )


def ijiri_submit_success(request, reference):

    return render(
        request,
        "ijiri-submit-success.html",
        {
            "reference": reference,
        },
    )


# ============================================================
# IJIRI EDITORIAL PARTNER ACCOUNT SETUP
# ============================================================

@require_http_methods(["GET", "POST"])
def ijiri_editor_set_initial_password(request, uidb64, token):
    """
    Allow an authorised AJER editorial partner to create the
    initial password using Django's signed password-reset token.
    """
    User = get_user_model()
    user = None

    try:
        user_id = force_str(
            urlsafe_base64_decode(uidb64)
        )
        user = User.objects.get(pk=user_id)

    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist,
    ):
        user = None

    user_is_authorised = bool(
        user
        and user.is_active
        and user.is_staff
        and not user.is_superuser
        and user.groups.filter(
            name="AJER Editorial Partner"
        ).exists()
    )

    token_is_valid = bool(
        user_is_authorised
        and default_token_generator.check_token(
            user,
            token,
        )
    )

    if not token_is_valid:
        return render(
            request,
            "ijiri-editor-set-password.html",
            {
                "link_invalid": True,
            },
            status=400,
        )

    if request.method == "POST":
        form = SetPasswordForm(
            user,
            request.POST,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                (
                    "Your editorial account password has been "
                    "created successfully. You can now sign in."
                ),
            )

            return redirect("/admin/")

    else:
        form = SetPasswordForm(user)

    return render(
        request,
        "ijiri-editor-set-password.html",
        {
            "form": form,
            "link_invalid": False,
            "editor_email": user.email,
        },
    )


# ============================================================
# LEGACY REPORT PAGES
# ============================================================

def report_1(request):
    return render(
        request,
        "report-1.html",
    )


def report_2(request):
    return render(
        request,
        "report-2.html",
    )


def report_3(request):
    return render(
        request,
        "report-3.html",
    )


# ============================================================
# ENROLL
# ============================================================

def enroll(request):
    return render(
        request,
        "enroll.html",
    )


# ============================================================
# COMPANY PROFILE
# ============================================================

def company_profile(request):

    return render(
        request,
        "company-profile.html",
    )


@require_POST
def download_company_profile(request):

    html_string = render_to_string(
        "company-profile.html",
        {
            "request": request,
        },
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".html",
        delete=False,
        encoding="utf-8",
    ) as temp_file:

        temp_file.write(html_string)
        temp_file_path = temp_file.name

    response = FileResponse(
        open(
            temp_file_path,
            "rb",
        ),
        content_type="text/html",
    )

    filename = (
        "Investmetrics_Company_Profile_"
        f"{datetime.now().strftime('%Y%m%d')}.html"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    return response


# ============================================================
# NEWSLETTER
# ============================================================

@require_POST
def newsletter_subscribe(request):

    form = NewsletterForm(
        request.POST
    )

    if form.is_valid():

        email = form.cleaned_data[
            "email"
        ]

        try:

            NewsletterSubscriber.objects.create(
                email=email
            )

            return JsonResponse(
                {
                    "success": True,
                }
            )

        except IntegrityError:

            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "This email is already subscribed."
                    ),
                }
            )

    return JsonResponse(
        {
            "success": False,
            "error": "Invalid email address.",
        }
    )


# ============================================================
# CONTACT PAGE
# ============================================================

@require_http_methods(["GET", "POST"])
def contact(request):

    if request.method == "POST":

        form = ContactForm(
            request.POST
        )

        logger.info(
            "Contact form data received: %s",
            request.POST,
        )

        if form.is_valid():

            name = form.cleaned_data[
                "name"
            ]

            email = form.cleaned_data[
                "email"
            ]

            subject = form.cleaned_data[
                "subject"
            ]

            message = form.cleaned_data[
                "message"
            ]

            try:

                Contact.objects.create(
                    name=name,
                    email=email,
                    subject=subject,
                    message=message,
                )

            except Exception as exc:

                logger.error(
                    "Unable to save contact submission: %s",
                    exc,
                )

                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "An error occurred while saving "
                            "your message."
                        ),
                    },
                    status=500,
                )

            email_message = (
                f"Name: {name}\n"
                f"Email: {email}\n\n"
                f"Message:\n{message}"
            )

            try:

                send_mail(
                    subject=subject,
                    message=email_message,
                    from_email=getattr(
                        settings,
                        "DEFAULT_FROM_EMAIL",
                        getattr(
                            settings,
                            "EMAIL_HOST_USER",
                            "noreply@example.com",
                        ),
                    ),
                    recipient_list=[
                        getattr(
                            settings,
                            "ADMIN_EMAIL",
                            "info@investmetrics.co.tz",
                        )
                    ],
                    fail_silently=True,
                )

            except Exception as exc:

                logger.error(
                    "Contact email sending failed: %s",
                    exc,
                )

            return JsonResponse(
                {
                    "success": True,
                    "message": (
                        "Your message has been sent. Thank you!"
                    ),
                }
            )

        logger.error(
            "Contact form errors: %s",
            form.errors,
        )

        return JsonResponse(
            {
                "success": False,
                "errors": form.errors,
            },
            status=400,
        )

    form = ContactForm()

    return render(
        request,
        "contact.html",
        {
            "form": form,
        },
    )


# ============================================================
# JOURNAL PUBLICATION VIEWS
# ============================================================

class JournalListView(ListView):

    model = Journal

    template_name = (
        "journals.html"
    )

    context_object_name = (
        "journals"
    )

    paginate_by = 2

    ordering = [
        "-published_date",
    ]


class JournalDetailView(DetailView):

    model = Journal

    template_name = (
        "journal_detail.html"
    )

    context_object_name = (
        "journal"
    )
