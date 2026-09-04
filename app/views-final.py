import logging
import mimetypes
import tempfile
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage, send_mail
from django.db import IntegrityError
from django.http import JsonResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import ListView, DetailView

from rest_framework import generics

from .forms import ContactForm, NewsletterForm, IJIRISubmissionForm
from .models import (
    NewsletterSubscriber,
    Journal,
    Contact,
    Report,
)
from .serializer import JournalSerializer


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


def academic_mentorship_and_training(request):
    return render(
        request,
        "academic-mentorship-and-training.html",
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
                    "ijiri@investmetrics.co.tz",
                ),
            )

            submitted_local = timezone.localtime(
                submission.submitted_at
            )

            submitted_display = submitted_local.strftime(
                "%d %B %Y, %H:%M EAT"
            )

            status_display = submission.get_status_display()

            # ------------------------------------------------
            # EDITORIAL OFFICE NOTIFICATION
            # ------------------------------------------------
            editorial_subject = (
                f"New IJIRI Manuscript Submission - "
                f"{submission.submission_reference}"
            )

            editorial_body = (
                "A new manuscript has been submitted to the "
                "Investmetrics Journal of Interdisciplinary Research "
                "and Intelligence (IJIRI).\n\n"
                "SUBMISSION DETAILS\n"
                "------------------\n"
                f"Submission Reference: "
                f"{submission.submission_reference}\n"
                f"Paper Title: {submission.paper_title}\n"
                f"Research Category: "
                f"{submission.get_research_category_display()}\n"
                f"Current Status: {status_display}\n"
                f"Submitted: {submitted_display}\n\n"
                "CORRESPONDING AUTHOR\n"
                "--------------------\n"
                f"Name: {submission.corresponding_author_name}\n"
                f"Email: {submission.corresponding_author_email}\n"
                f"Country: {submission.country}\n"
                f"Mobile Number: "
                f"{submission.mobile_number or 'Not provided'}\n"
                f"ORCID: {submission.orcid or 'Not provided'}\n\n"
                "KEYWORDS\n"
                "--------\n"
                f"{submission.keywords}\n\n"
                "AUTHOR DETAILS\n"
                "--------------\n"
                f"{submission.author_details}\n\n"
                "ABSTRACT\n"
                "--------\n"
                f"{submission.abstract}\n\n"
                "AI USE DISCLOSURE\n"
                "-----------------\n"
                f"{submission.ai_use_statement or 'No statement provided.'}"
                "\n\n"
                "AUTHOR DECLARATIONS\n"
                "-------------------\n"
                "- Originality: Confirmed\n"
                "- Similarity below 18%: Confirmed\n"
                "- AI-generated content below 15%: Confirmed\n"
                "- AI-use disclosure requirement: Acknowledged\n"
                "- APA 7th Edition compliance: Confirmed\n"
                "- Corresponding author authority: Confirmed\n"
                "- IJIRI submission requirements: Accepted\n\n"
                "The submitted manuscript is attached to this message.\n"
            )

            try:

                editorial_message = EmailMessage(
                    subject=editorial_subject,
                    body=editorial_body,
                    from_email=from_email,
                    to=[editorial_email],
                    reply_to=[
                        submission.corresponding_author_email
                    ],
                )

                manuscript = submission.manuscript_file
                manuscript.open("rb")

                filename = manuscript.name.split("/")[-1]
                content_type = (
                    mimetypes.guess_type(filename)[0]
                    or "application/octet-stream"
                )

                editorial_message.attach(
                    filename,
                    manuscript.read(),
                    content_type,
                )

                manuscript.close()

                editorial_message.send(
                    fail_silently=False
                )

            except Exception as exc:

                logger.exception(
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
                "SUBMISSION DETAILS\n"
                "------------------\n"
                f"Submission Reference: "
                f"{submission.submission_reference}\n"
                f"Paper Title: {submission.paper_title}\n"
                f"Current Status: {status_display}\n"
                f"Submitted: {submitted_display}\n\n"
                "WHAT HAPPENS NEXT\n"
                "-----------------\n"
                "Your manuscript will first undergo an editorial check "
                "for completeness, scope and basic submission requirements. "
                "If it proceeds beyond this stage, the IJIRI Editorial "
                "Office will communicate the next applicable review step.\n\n"
                "Please retain your submission reference and include it in "
                "all future correspondence concerning this manuscript.\n\n"
                "Submission does not constitute acceptance or publication. "
                "Editorial and review timelines may vary depending on the "
                "manuscript and reviewer availability.\n\n"
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

                logger.exception(
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
        open(temp_file_path, "rb"),
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

    form = NewsletterForm(request.POST)

    if form.is_valid():

        email = form.cleaned_data["email"]

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
                    "error": "This email is already subscribed.",
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

        form = ContactForm(request.POST)

        logger.info(
            "Contact form data received: %s",
            request.POST,
        )

        if form.is_valid():

            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

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
    template_name = "journals.html"
    context_object_name = "journals"
    paginate_by = 2

    ordering = [
        "-published_date",
    ]


class JournalDetailView(DetailView):

    model = Journal
    template_name = "journal_detail.html"
    context_object_name = "journal"