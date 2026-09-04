from django import forms

from .models import IJIRISubmission


# ============================================================
# CONTACT FORM
# ============================================================

class ContactForm(forms.Form):

    name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Your Name",
            }
        )
    )

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Your Email",
            }
        )
    )

    subject = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Subject",
            }
        )
    )

    message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Message",
                "style": "height: 100px",
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update(
                {"class": "form-control"}
            )


# ============================================================
# NEWSLETTER FORM
# ============================================================

class NewsletterForm(forms.Form):

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your email",
            }
        )
    )


# ============================================================
# IJIRI MANUSCRIPT SUBMISSION FORM
# ============================================================

class IJIRISubmissionForm(forms.ModelForm):

    paper_title = forms.CharField(
        label="Paper Title",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter the research paper title",
                "maxlength": "300",
                "autocomplete": "off",
            }
        ),
        help_text="Maximum 15 words.",
    )

    subtitle = forms.CharField(
        label="Subtitle",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": (
                    "Optional. Example: A Case of Dar es Salaam Port Authority"
                ),
                "maxlength": "300",
                "autocomplete": "off",
            }
        ),
        help_text=(
            "Optional case, location or study context. Maximum 10 words."
        ),
    )

    abstract = forms.CharField(
        label="Abstract",
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": (
                    "Provide the abstract covering purpose, methodology, "
                    "findings, conclusion and contribution."
                ),
                "rows": 8,
            }
        ),
        help_text="Maximum 300 words.",
    )

    research_category = forms.ChoiceField(
        label="Research Paper Category",
        required=True,
        choices=[
            ("", "Select research category"),
            *IJIRISubmission.CATEGORY_CHOICES,
        ],
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    keywords = forms.CharField(
        label="Keywords",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": (
                    "Example: Climate change, Governance, Public policy"
                ),
            }
        ),
        help_text=(
            "Provide 3–5 distinct, relevant keywords separated by commas."
        ),
    )

    author_details = forms.CharField(
        label="Author Details",
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": (
                    "Provide each author's full name, affiliation, "
                    "country and email address."
                ),
            }
        ),
        help_text=(
            "Include all authors in the order they should appear "
            "in the publication."
        ),
    )

    corresponding_author_name = forms.CharField(
        label="Corresponding Author",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Full name of corresponding author",
            }
        ),
    )

    corresponding_author_email = forms.EmailField(
        label="Corresponding Author Email",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "author@example.com",
                "autocomplete": "email",
            }
        ),
    )

    country = forms.CharField(
        label="Country",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Country",
                "autocomplete": "country-name",
            }
        ),
    )

    mobile_number = forms.CharField(
        label="Mobile Number",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: +255 7XX XXX XXX",
                "autocomplete": "tel",
            }
        ),
        help_text=(
            "Optional. Include the international country code."
        ),
    )

    orcid = forms.CharField(
        label="ORCID",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: 0000-0002-1825-0097",
            }
        ),
        help_text="Optional.",
    )

    manuscript_file = forms.FileField(
        label="Attach Research Paper",
        required=True,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".doc,.docx",
            }
        ),
        help_text=(
            "Accepted format: Microsoft Word (.doc or .docx). "
            "Maximum file size: 6 MB."
        ),
    )

    ai_use_statement = forms.CharField(
        label="AI Use Disclosure",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "If generative AI was used, briefly describe how it was "
                    "used. If none was used, this field may be left blank."
                ),
            }
        ),
    )

    originality_confirmed = forms.BooleanField(
        required=True,
        label=(
            "I confirm that this manuscript represents original work and "
            "has not been submitted using false authorship or fabricated "
            "information."
        ),
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input"}
        ),
    )

    similarity_confirmed = forms.BooleanField(
        required=True,
        label=(
            "I confirm that the manuscript's overall similarity level is "
            "below 18%."
        ),
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input"}
        ),
    )

    ai_threshold_confirmed = forms.BooleanField(
        required=True,
        label=(
            "I confirm that AI-generated content does not exceed 15% of "
            "the manuscript."
        ),
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input"}
        ),
    )

    ai_use_acknowledged = forms.BooleanField(
        required=True,
        label=(
            "I understand that any use of generative AI must be "
            "acknowledged and disclosed."
        ),
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input"}
        ),
    )

    apa7_confirmed = forms.BooleanField(
        required=True,
        label=(
            "I confirm that citations and references have been prepared "
            "using APA 7th Edition."
        ),
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input"}
        ),
    )

    authorisation_confirmed = forms.BooleanField(
        required=True,
        label=(
            "I confirm that I am authorised to submit this manuscript on "
            "behalf of all listed authors."
        ),
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input"}
        ),
    )

    declaration_confirmed = forms.BooleanField(
        required=True,
        label=(
            "I have read the IJIRI Author Guidelines and agree to the "
            "journal's submission requirements."
        ),
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input"}
        ),
    )

    class Meta:
        model = IJIRISubmission
        fields = [
            "paper_title",
            "subtitle",
            "abstract",
            "research_category",
            "keywords",
            "author_details",
            "corresponding_author_name",
            "corresponding_author_email",
            "country",
            "mobile_number",
            "orcid",
            "manuscript_file",
            "ai_use_statement",
            "originality_confirmed",
            "similarity_confirmed",
            "ai_threshold_confirmed",
            "ai_use_acknowledged",
            "apa7_confirmed",
            "authorisation_confirmed",
            "declaration_confirmed",
        ]

    def clean_paper_title(self):
        title = self.cleaned_data.get("paper_title", "").strip()
        word_count = len(title.split())

        if word_count > 15:
            raise forms.ValidationError(
                f"Paper title must not exceed 15 words. Your title "
                f"currently contains {word_count} words."
            )

        return title

    def clean_subtitle(self):
        subtitle = self.cleaned_data.get(
            "subtitle",
            ""
        ).strip()

        if not subtitle:
            return ""

        word_count = len(
            subtitle.split()
        )

        if word_count > 10:
            raise forms.ValidationError(
                f"Paper subtitle must not exceed 10 words. "
                f"Your subtitle currently contains {word_count} words."
            )

        return subtitle

    def clean_abstract(self):
        abstract = self.cleaned_data.get("abstract", "").strip()
        word_count = len(abstract.split())

        if word_count > 300:
            raise forms.ValidationError(
                f"Abstract must not exceed 300 words. Your abstract "
                f"currently contains {word_count} words."
            )

        return abstract

    def clean_keywords(self):
        value = self.cleaned_data.get("keywords", "")
        keywords = [
            keyword.strip()
            for keyword in value.split(",")
            if keyword.strip()
        ]

        if len(keywords) < 3:
            raise forms.ValidationError(
                "Please provide at least 3 keywords."
            )

        if len(keywords) > 5:
            raise forms.ValidationError(
                "Please provide no more than 5 keywords."
            )

        normalized = [
            keyword.casefold()
            for keyword in keywords
        ]

        if len(normalized) != len(set(normalized)):
            raise forms.ValidationError(
                "Keywords must be distinct. Please remove duplicate keywords."
            )

        return ", ".join(keywords)

    def clean_manuscript_file(self):
        manuscript = self.cleaned_data.get("manuscript_file")

        if not manuscript:
            return manuscript

        filename = manuscript.name.lower()

        if not (
            filename.endswith(".doc")
            or filename.endswith(".docx")
        ):
            raise forms.ValidationError(
                "Only Microsoft Word files (.doc or .docx) are accepted."
            )

        max_size = 6 * 1024 * 1024

        if manuscript.size > max_size:
            raise forms.ValidationError(
                "The manuscript file must not exceed 6 MB."
            )

        return manuscript

    def clean_orcid(self):
        orcid = self.cleaned_data.get("orcid", "").strip()

        if not orcid:
            return ""

        orcid = orcid.replace(
            "https://orcid.org/", ""
        ).replace(
            "http://orcid.org/", ""
        ).strip()

        parts = orcid.split("-")

        if (
            len(parts) != 4
            or not all(len(part) == 4 for part in parts)
        ):
            raise forms.ValidationError(
                "Enter ORCID in the format 0000-0000-0000-0000."
            )

        first_three = "".join(parts[:3])
        last_part = parts[3]

        if (
            not first_three.isdigit()
            or not last_part[:3].isdigit()
            or not (
                last_part[3].isdigit()
                or last_part[3].upper() == "X"
            )
        ):
            raise forms.ValidationError(
                "Enter a valid ORCID in the format 0000-0000-0000-0000."
            )

        return (
            f"{parts[0]}-{parts[1]}-{parts[2]}-"
            f"{last_part[:3]}{last_part[3].upper()}"
        )

    def clean(self):
        cleaned_data = super().clean()

        required_declarations = {
            "originality_confirmed": (
                "You must confirm the originality declaration."
            ),
            "similarity_confirmed": (
                "You must confirm the similarity requirement."
            ),
            "ai_threshold_confirmed": (
                "You must confirm the AI-content requirement."
            ),
            "ai_use_acknowledged": (
                "You must acknowledge the AI-use disclosure policy."
            ),
            "apa7_confirmed": (
                "You must confirm APA 7th Edition compliance."
            ),
            "authorisation_confirmed": (
                "You must confirm that you are authorised to submit on "
                "behalf of the authors."
            ),
            "declaration_confirmed": (
                "You must accept the IJIRI submission requirements."
            ),
        }

        for field_name, error_message in required_declarations.items():
            if not cleaned_data.get(field_name):
                self.add_error(field_name, error_message)

        return cleaned_data
