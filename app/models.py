from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.text import slugify
from ckeditor.fields import RichTextField
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
import io


# ============================================================
# IJIRI SUBMISSION VALIDATORS
# ============================================================

def validate_max_6mb(file):
    """Restrict uploaded IJIRI manuscript files to a maximum of 6 MB."""
    max_size = 6 * 1024 * 1024
    if file and file.size > max_size:
        raise ValidationError(
            "The manuscript file must not exceed 6 MB."
        )


def validate_title_15_words(value):
    """IJIRI paper title must not exceed 15 words."""
    if value:
        word_count = len(value.split())
        if word_count > 15:
            raise ValidationError(
                f"Paper title must not exceed 15 words. "
                f"Current title contains {word_count} words."
            )


def validate_subtitle_10_words(value):
    """IJIRI subtitle must not exceed 10 words."""
    if value:
        word_count = len(value.split())
        if word_count > 10:
            raise ValidationError(
                f"Paper subtitle must not exceed 10 words. "
                f"Current subtitle contains {word_count} words."
            )


def validate_abstract_300_words(value):
    """IJIRI abstract must not exceed 300 words."""
    if value:
        word_count = len(value.split())
        if word_count > 300:
            raise ValidationError(
                f"Abstract must not exceed 300 words. "
                f"Current abstract contains {word_count} words."
            )


def validate_keywords_3_to_5(value):
    """Require 3 to 5 comma-separated keywords."""
    if not value:
        return

    keywords = [
        keyword.strip()
        for keyword in value.split(",")
        if keyword.strip()
    ]

    if len(keywords) < 3 or len(keywords) > 5:
        raise ValidationError(
            "Provide between 3 and 5 keywords, separated by commas."
        )


# ============================================================
# NEWSLETTER
# ============================================================

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.email


# ============================================================
# JOURNAL PUBLICATION SYSTEM
# ============================================================

class Journal(models.Model):
    title = models.CharField(max_length=200)

    slug = models.SlugField(
        unique=True,
        max_length=200,
        blank=True
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="journals"
    )

    header = models.TextField(blank=True)

    excerpt = RichTextField(
        blank=True,
        config_name="default",
        help_text="You can format this text using the editor tools"
    )

    image = models.ImageField(
        upload_to="journal_images/",
        blank=True,
        null=True
    )

    pdf_file = models.FileField(
        upload_to="journal_pdfs/",
        null=True,
        blank=True
    )

    published_date = models.DateTimeField(
        auto_now_add=True
    )

    updated_date = models.DateTimeField(
        auto_now=True
    )

    apa_citation = models.TextField(
        blank=True,
        help_text="APA format citation"
    )

    mla_citation = models.TextField(
        blank=True,
        help_text="MLA format citation"
    )

    chicago_citation = models.TextField(
        blank=True,
        help_text="Chicago format citation"
    )

    def save(self, *args, **kwargs):

        # ----------------------------------------------------
        # GENERATE SLUG
        # ----------------------------------------------------
        if not self.slug:
            base_slug = slugify(self.title or self.header)
            slug = base_slug
            counter = 2

            while Journal.objects.filter(
                slug=slug
            ).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        # ----------------------------------------------------
        # PROCESS IMAGE
        # ----------------------------------------------------
        if self.image:
            try:
                img = Image.open(self.image)

                target_width = 1200
                aspect_ratio = img.height / img.width
                target_height = int(target_width * aspect_ratio)

                img = img.resize(
                    (target_width, target_height),
                    Image.Resampling.LANCZOS
                )

                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                output = io.BytesIO()
                img.save(
                    output,
                    format="JPEG",
                    quality=85
                )
                output.seek(0)

                original_name = self.image.name.rsplit(".", 1)[0]

                self.image = InMemoryUploadedFile(
                    output,
                    "ImageField",
                    f"{original_name}.jpg",
                    "image/jpeg",
                    output.getbuffer().nbytes,
                    None
                )

            except Exception:
                # Keep the original image if processing fails.
                pass

        # ----------------------------------------------------
        # EXCERPT FALLBACK
        # ----------------------------------------------------
        if not self.excerpt and self.header:
            self.excerpt = self.header[:500]

        # Save first so published_date exists for new records.
        super().save(*args, **kwargs)

        # ----------------------------------------------------
        # AUTO-GENERATE CITATIONS
        # ----------------------------------------------------
        year = (
            self.published_date.year
            if self.published_date
            else timezone.now().year
        )

        author_name = (
            self.author.get_full_name().strip()
            or self.author.username
        )

        journal_name = (
            "Investmetrics Journal of Interdisciplinary "
            "Research and Intelligence"
        )

        citation_changed = False

        if not self.apa_citation:
            self.apa_citation = (
                f"{author_name}. ({year}). "
                f"{self.header}. {journal_name}."
            )
            citation_changed = True

        if not self.mla_citation:
            self.mla_citation = (
                f'{author_name}. "{self.header}." '
                f"{journal_name}, {year}."
            )
            citation_changed = True

        if not self.chicago_citation:
            self.chicago_citation = (
                f'{author_name}. "{self.header}." '
                f"{journal_name} ({year})."
            )
            citation_changed = True

        if citation_changed:
            Journal.objects.filter(pk=self.pk).update(
                apa_citation=self.apa_citation,
                mla_citation=self.mla_citation,
                chicago_citation=self.chicago_citation,
            )

    def __str__(self):
        return self.title or self.header

    def get_pdf_url(self):
        if self.pdf_file:
            return self.pdf_file.url
        return None


# ============================================================
# AUTHOR PROFILE
# ============================================================

class AuthorProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    image = models.ImageField(
        upload_to="author_images/",
        default="author_images/default.jpg"
    )

    def __str__(self):
        return self.user.username


# ============================================================
# CONTACT
# ============================================================

class Contact(models.Model):
    name = models.CharField(max_length=100)

    email = models.EmailField()

    subject = models.CharField(max_length=200)

    message = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.name} - {self.subject}"

    class Meta:
        ordering = ["-created_at"]


# ============================================================
# ENROLL
# ============================================================

class Enroll(models.Model):
    pass


# ============================================================
# INVESTMETRICS REPORT PUBLICATION SYSTEM
# ============================================================

class Report(models.Model):

    THEME_CHOICES = (
        ("standard", "Standard Intelligence"),
        ("agriculture", "Agriculture & Trade"),
        ("economics", "Economics & Markets"),
        ("policy", "Policy & Governance"),
        ("public_affairs", "Public Affairs"),
        ("humanitarian", "Humanitarian Research"),
        ("market_research", "Market Research"),
        ("statistics", "Statistics & Data"),
        ("development", "Development"),
        ("technology", "Technology & Innovation"),
    )

    title = models.CharField(
        max_length=300
    )

    slug = models.SlugField(
        unique=True,
        max_length=320,
        blank=True
    )

    authors = models.CharField(
        max_length=500,
        help_text=(
            "Enter author names as they should appear "
            "in the publication."
        )
    )

    publication_date = models.DateField(
        default=timezone.now
    )

    category = models.CharField(
        max_length=120,
        blank=True
    )

    report_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional publication/report number."
    )

    eyebrow = models.CharField(
        max_length=150,
        blank=True,
        help_text="Short label displayed above the report title."
    )

    summary = models.TextField(
        blank=True,
        help_text=(
            "Short description used on the Reports library page."
        )
    )

    abstract = RichTextField(
        blank=True,
        config_name="default"
    )

    cover_image = models.ImageField(
        upload_to="report_covers/",
        blank=True,
        null=True
    )

    pdf_file = models.FileField(
        upload_to="report_pdfs/",
        blank=True,
        null=True,
        help_text=(
            "Optional final report in PDF format."
        )
    )

    document_file = models.FileField(
        upload_to="report_documents/",
        blank=True,
        null=True,
        help_text=(
            "Optional editable publication file such as DOC or DOCX."
        )
    )

    theme = models.CharField(
        max_length=30,
        choices=THEME_CHOICES,
        default="standard"
    )

    featured = models.BooleanField(
        default=False
    )

    is_published = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "-publication_date",
            "-created_at",
        ]

    def save(self, *args, **kwargs):

        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 2

            while Report.objects.filter(
                slug=slug
            ).exclude(pk=self.pk).exists():

                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def has_uploaded_document(self):
        return bool(
            self.pdf_file or self.document_file
        )


# ============================================================
# REPORT SECTIONS
# ============================================================

class ReportSection(models.Model):

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="sections"
    )

    order = models.PositiveIntegerField(
        default=1
    )

    heading = models.CharField(
        max_length=250
    )

    content = RichTextField(
        blank=True,
        config_name="default"
    )

    image = models.ImageField(
        upload_to="report_section_images/",
        blank=True,
        null=True
    )

    image_caption = models.CharField(
        max_length=300,
        blank=True
    )

    class Meta:
        ordering = [
            "order",
            "id",
        ]

    def __str__(self):
        return f"{self.report.title} â€” {self.heading}"

# ============================================================
# IJIRI MANUSCRIPT SUBMISSION SYSTEM
# ============================================================

class IJIRISubmission(models.Model):

    CATEGORY_CHOICES = (
        ("business_management", "Business & Management"),
        ("economics_development", "Economics & Development"),
        ("public_policy_governance", "Public Policy & Governance"),
        ("social_sciences", "Social Sciences"),
        ("education", "Education"),
        ("health", "Health & Wellbeing"),
        ("environment_climate", "Environment & Climate Change"),
        ("agriculture_food", "Agriculture & Food Systems"),
        ("technology_data", "Technology, Data & Innovation"),
        ("market_research", "Market Research & Consumer Insights"),
        ("interdisciplinary", "Interdisciplinary Research"),
        ("other", "Other"),
    )

    STATUS_CHOICES = (
        ("submitted", "Submitted"),
        ("editorial_check", "Editorial Check"),
        ("deep_review", "Deep Review"),
        ("editorial_decision", "Editorial Decision"),
        ("peer_review", "Peer Review"),
        ("revision", "Revision Required"),
        ("revision_review", "Revision Review"),
        ("approved", "Approved"),
        ("galley_proof", "Galley Proof"),
        ("published", "Published"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    )

    submission_reference = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        editable=False
    )

    paper_title = models.CharField(
        max_length=300,
        validators=[validate_title_15_words],
        help_text="Maximum 15 words."
    )

    subtitle = models.CharField(
        max_length=300,
        blank=True,
        validators=[validate_subtitle_10_words],
        help_text=(
            "Optional subtitle or case context. Maximum 10 words."
        )
    )

    abstract = models.TextField(
        validators=[validate_abstract_300_words],
        help_text="Maximum 300 words."
    )

    research_category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )

    keywords = models.CharField(
        max_length=500,
        validators=[validate_keywords_3_to_5],
        help_text="Provide 3–5 relevant keywords separated by commas."
    )

    author_details = models.TextField(
        help_text=(
            "Provide all author names, affiliations, countries "
            "and email addresses."
        )
    )

    corresponding_author_name = models.CharField(
        max_length=200
    )

    corresponding_author_email = models.EmailField()

    country = models.CharField(
        max_length=120
    )

    mobile_number = models.CharField(
        max_length=40,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\+?[0-9\s\-\(\)]{7,30}$",
                message=(
                    "Enter a valid mobile number including "
                    "the international country code."
                )
            )
        ],
        help_text=(
            "Optional. Include international country code, "
            "for example +255..."
        )
    )

    orcid = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional ORCID identifier."
    )

    manuscript_file = models.FileField(
        upload_to="ijiri_submissions/%Y/%m/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["doc", "docx"]
            ),
            validate_max_6mb
        ],
        help_text=(
            "Accepted formats: DOC or DOCX. "
            "Maximum file size: 6 MB."
        )
    )

    originality_confirmed = models.BooleanField(
        default=False,
        verbose_name="Originality declaration confirmed"
    )

    similarity_confirmed = models.BooleanField(
        default=False,
        verbose_name="Similarity below 18% confirmed"
    )

    ai_threshold_confirmed = models.BooleanField(
        default=False,
        verbose_name="AI content below 15% confirmed"
    )

    ai_use_acknowledged = models.BooleanField(
        default=False,
        verbose_name="AI use disclosure acknowledged"
    )

    apa7_confirmed = models.BooleanField(
        default=False,
        verbose_name="APA 7th Edition compliance confirmed"
    )

    authorisation_confirmed = models.BooleanField(
        default=False,
        verbose_name=(
            "Corresponding author submission authority confirmed"
        )
    )

    declaration_confirmed = models.BooleanField(
        default=False,
        verbose_name="General submission declaration confirmed"
    )

    ai_use_statement = models.TextField(
        blank=True,
        help_text=(
            "Describe any use of generative AI in preparing "
            "the manuscript, if applicable."
        )
    )

    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default="submitted"
    )

    internal_notes = models.TextField(
        blank=True
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    status_updated_at = models.DateTimeField(
        default=timezone.now
    )

    class Meta:
        verbose_name = "IJIRI Manuscript Submission"
        verbose_name_plural = "IJIRI Manuscript Submissions"
        ordering = ["-submitted_at"]

    def __str__(self):
        if self.submission_reference:
            return (
                f"{self.submission_reference} - "
                f"{self.paper_title}"
            )
        return self.paper_title

    def save(self, *args, **kwargs):
        previous_status = None

        if self.pk:
            try:
                previous_status = (
                    IJIRISubmission.objects
                    .get(pk=self.pk)
                    .status
                )
            except IJIRISubmission.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Generate a stable reference after the first database save.
        if not self.submission_reference:
            reference = (
                f"IJIRI-{self.submitted_at.year}-{self.pk:05d}"
            )

            IJIRISubmission.objects.filter(
                pk=self.pk
            ).update(
                submission_reference=reference
            )

            self.submission_reference = reference

        # Record when editorial status changes.
        if (
            previous_status is not None
            and previous_status != self.status
        ):
            new_time = timezone.now()

            IJIRISubmission.objects.filter(
                pk=self.pk
            ).update(
                status_updated_at=new_time
            )

            self.status_updated_at = new_time

    @property
    def full_title(self):
        if self.subtitle:
            return f"{self.paper_title}: {self.subtitle}"
        return self.paper_title

    @property
    def subtitle_word_count(self):
        return len(self.subtitle.split()) if self.subtitle else 0

    @property
    def title_word_count(self):
        return len(self.paper_title.split())

    @property
    def abstract_word_count(self):
        return len(self.abstract.split())

    @property
    def keyword_list(self):
        return [
            keyword.strip()
            for keyword in self.keywords.split(",")
            if keyword.strip()
        ]

# ============================================================
# TRAINING APPLICATION SYSTEM
# ============================================================



class TrainingApplication(models.Model):
    """
    Public application for Investmetrics training.

    The training pathway records the broad learning stream requested by
    the applicant. The training area records the specific subject selected.

    Final Investmetrics Learning access remains controlled through
    LearnerProfile and is not granted merely by submitting this application.
    """

    PATHWAY_RESEARCH = "research"
    PATHWAY_PROFESSIONAL = "professional"

    PATHWAY_CHOICES = (
        (
            PATHWAY_RESEARCH,
            "Research & Evidence",
        ),
        (
            PATHWAY_PROFESSIONAL,
            "General Professional Work",
        ),
    )

    TRAINING_RESEARCH_FUNDAMENTALS = "research_fundamentals"
    TRAINING_RESEARCH_DESIGN = "research_design_methods"
    TRAINING_PROPOSAL = "proposal_development"
    TRAINING_DATA_COLLECTION = "data_collection_techniques"
    TRAINING_QUANTITATIVE = "quantitative_analysis"
    TRAINING_QUALITATIVE = "qualitative_analysis"

    TRAINING_PROFESSIONAL_CLIENT = "ai_client_stakeholder"
    TRAINING_PROFESSIONAL_LEADERSHIP = "ai_leadership_management"
    TRAINING_PROFESSIONAL_OPERATIONS = "ai_operations_delivery"

    RESEARCH_TRAINING_CHOICES = (
        (
            TRAINING_RESEARCH_FUNDAMENTALS,
            "Research Fundamentals",
        ),
        (
            TRAINING_RESEARCH_DESIGN,
            "Research Design & Methods",
        ),
        (
            TRAINING_PROPOSAL,
            "Proposal Development",
        ),
        (
            TRAINING_DATA_COLLECTION,
            "Data Collection Techniques",
        ),
        (
            TRAINING_QUANTITATIVE,
            "Quantitative Analysis",
        ),
        (
            TRAINING_QUALITATIVE,
            "Qualitative Analysis",
        ),
    )

    PROFESSIONAL_TRAINING_CHOICES = (
        (
            TRAINING_PROFESSIONAL_CLIENT,
            "AI for Client & Stakeholder Facing Work",
        ),
        (
            TRAINING_PROFESSIONAL_LEADERSHIP,
            "AI for Leadership & Management",
        ),
        (
            TRAINING_PROFESSIONAL_OPERATIONS,
            "AI for Operations & Delivery",
        ),
    )

    TRAINING_CHOICES = (
        *RESEARCH_TRAINING_CHOICES,
        *PROFESSIONAL_TRAINING_CHOICES,
    )

    STATUS_CHOICES = (
        ("pending_payment", "Pending Payment"),
        ("payment_confirmed", "Payment Confirmed"),
        ("access_sent", "Access Sent"),
        ("cancelled", "Cancelled"),
    )

    learner_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_applications",
        help_text=(
            "Investmetrics Learning account assigned to this "
            "training application."
        ),
    )

    application_reference = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        editable=False,
    )

    full_name = models.CharField(
        max_length=200
    )

    email = models.EmailField()

    mobile_number = models.CharField(
        max_length=40
    )

    country = models.CharField(
        max_length=100
    )

    organisation = models.CharField(
        max_length=200,
        blank=True
    )

    role_or_academic_level = models.CharField(
        max_length=200
    )

    training_pathway = models.CharField(
        max_length=30,
        choices=PATHWAY_CHOICES,
        default=PATHWAY_RESEARCH,
    )

    training_area = models.CharField(
        max_length=50,
        choices=TRAINING_CHOICES
    )

    learning_expectation = models.TextField(
        blank=True
    )

    training_fee = models.PositiveIntegerField(
        default=280000,
        editable=False
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending_payment"
    )

    payment_confirmed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    training_access_link = models.URLField(
        max_length=500,
        blank=True
    )

    access_email_sent = models.BooleanField(
        default=False
    )

    internal_notes = models.TextField(
        blank=True
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Training Application"
        verbose_name_plural = "Training Applications"
        ordering = ["-submitted_at"]

    def __str__(self):
        if self.application_reference:
            return (
                f"{self.application_reference} - "
                f"{self.full_name}"
            )
        return self.full_name

    @classmethod
    def research_training_values(cls):
        return {
            value
            for value, label in cls.RESEARCH_TRAINING_CHOICES
        }

    @classmethod
    def professional_training_values(cls):
        return {
            value
            for value, label in cls.PROFESSIONAL_TRAINING_CHOICES
        }

    def expected_pathway_for_training_area(self):
        if self.training_area in self.research_training_values():
            return self.PATHWAY_RESEARCH

        if self.training_area in self.professional_training_values():
            return self.PATHWAY_PROFESSIONAL

        return ""

    def clean(self):
        super().clean()

        expected_pathway = self.expected_pathway_for_training_area()

        if (
            expected_pathway
            and self.training_pathway != expected_pathway
        ):
            raise ValidationError(
                {
                    "training_area": (
                        "The selected training area does not belong "
                        "to the selected training pathway."
                    )
                }
            )

    def save(self, *args, **kwargs):
        expected_pathway = self.expected_pathway_for_training_area()

        if expected_pathway:
            self.training_pathway = expected_pathway

        super().save(*args, **kwargs)

        if not self.application_reference:
            reference = (
                f"TRN-{self.submitted_at.year}-{self.pk:05d}"
            )

            TrainingApplication.objects.filter(
                pk=self.pk
            ).update(
                application_reference=reference
            )

            self.application_reference = reference