import json

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LearnerLoginForm
from .models import (
    AssessmentSummary,
    Certificate,
    LearnerProfile,
    LearningState,
    SurveyResponse,
)


# =============================================================================
# COURSE STORAGE KEYS
# =============================================================================

RESEARCH_KEY = "ai_at_work_investmetrics_gold_v1"
MODE_KEY = "ai_at_work_investmetrics_pathway_choice_v1"
ROLE_KEY = "ai_at_work_investmetrics_professional_role_v1"
PRO_KEY_PREFIX = "ai_at_work_investmetrics_professional_"
COURSE_PREFIX = "ai_at_work_investmetrics_"


# =============================================================================
# COURSE STRUCTURE
# =============================================================================

RESEARCH_LESSONS = [
    "welcome",
    "simple",
    "works",
    "classify",
    "reality",
    "core",
    "task",
    "prompt",
    "game1",
    "loop",
    "proof",
    "game2",
    "approve",
    "recall",
    "apply",
    "action",
    "game3",
    "toolkit",
    "exam",
    "finish",
]

PRO_LESSONS = [
    "welcome",
    "simple",
    "works",
    "reality",
    "core",
    "task",
    "prompt",
    "game1",
    "loop",
    "check",
    "game2",
    "approve",
    "recall",
    "game3",
    "functions",
    "toolkit",
    "workflows",
    "action",
    "assessment",
    "certificate",
]


# The first 18 sections are required learning sections.
# Assessment and completion/certificate come afterwards.

RESEARCH_REQUIRED_LESSONS = RESEARCH_LESSONS[:18]
PRO_REQUIRED_LESSONS = PRO_LESSONS[:18]

PROFESSIONAL_ROLES = (
    LearnerProfile.ROLE_CLIENT,
    LearnerProfile.ROLE_LEADERSHIP,
    LearnerProfile.ROLE_OPERATIONS,
)


# =============================================================================
# LEARNER / ACCESS HELPERS
# =============================================================================

def _profile_for(user):
    """
    Return the learner profile attached to the authenticated user.

    IMPORTANT:
    Staff/admin users are NOT automatically enrolled as learners.
    An administrator must deliberately have a LearnerProfile if they
    also need to participate in the course.
    """
    try:
        profile = user.aiw_profile
    except LearnerProfile.DoesNotExist:
        return None

    LearningState.objects.get_or_create(profile=profile)
    return profile


def _find_user(identifier):
    """
    Allow learners to sign in using either email address or username.
    """
    return (
        User.objects.filter(
            Q(email__iexact=identifier)
            | Q(username__iexact=identifier)
        )
        .first()
    )


def _valid_access_message(profile):
    """
    Return an explanatory message if learner access is not currently valid.
    Otherwise return an empty string.
    """
    today = timezone.localdate()

    if not profile.training_active or not profile.user.is_active:
        return "This learner account is not active."

    if profile.access_start and today < profile.access_start:
        return (
            f"Your training access begins on "
            f"{profile.access_start:%d %B %Y}."
        )

    if profile.access_expiry and today > profile.access_expiry:
        return (
            "Your training access period has expired. "
            "Contact Investmetrics Learning Support."
        )

    return ""


def _can_access_research(profile):
    """
    Whether Research & Evidence is assigned to this learner.
    """
    return profile.access_scope in {
        LearnerProfile.ACCESS_RESEARCH,
        LearnerProfile.ACCESS_BOTH,
    }


def _can_access_professional(profile):
    """
    Whether General Professional Work is assigned to this learner.
    """
    return profile.access_scope in {
        LearnerProfile.ACCESS_PROFESSIONAL,
        LearnerProfile.ACCESS_BOTH,
    }


def _allowed_professional_roles(profile):
    """
    Return the professional role(s) that this learner may access.
    """
    if not _can_access_professional(profile):
        return ()

    if profile.professional_role == LearnerProfile.ROLE_ANY:
        return PROFESSIONAL_ROLES

    if profile.professional_role in PROFESSIONAL_ROLES:
        return (profile.professional_role,)

    return ()


def _normalise_pathway(profile, pathway):
    """
    Prevent an unassigned pathway from becoming the learner's current pathway.
    """
    pathway = str(pathway or "").strip().lower()

    if pathway == AssessmentSummary.PATH_RESEARCH:
        if _can_access_research(profile):
            return AssessmentSummary.PATH_RESEARCH

    if pathway == AssessmentSummary.PATH_PROFESSIONAL:
        if _can_access_professional(profile):
            return AssessmentSummary.PATH_PROFESSIONAL

    # For single-pathway learners, default to the assigned pathway.
    if profile.access_scope == LearnerProfile.ACCESS_RESEARCH:
        return AssessmentSummary.PATH_RESEARCH

    if profile.access_scope == LearnerProfile.ACCESS_PROFESSIONAL:
        return AssessmentSummary.PATH_PROFESSIONAL

    return ""


def _overall_progress(profile, learning):
    """
    Calculate progress only from pathways actually assigned to the learner.
    """
    if profile.access_scope == LearnerProfile.ACCESS_RESEARCH:
        return learning.research_progress

    if profile.access_scope == LearnerProfile.ACCESS_PROFESSIONAL:
        return learning.professional_progress

    if profile.access_scope == LearnerProfile.ACCESS_BOTH:
        return round(
            (
                learning.research_progress
                + learning.professional_progress
            )
            / 2
        )

    return 0


def _overall_best_score(profile, learning):
    """
    Show the best assessment only from pathways assigned to the learner.
    """
    if profile.access_scope == LearnerProfile.ACCESS_RESEARCH:
        return learning.research_assessment_score

    if profile.access_scope == LearnerProfile.ACCESS_PROFESSIONAL:
        return learning.professional_assessment_score

    if profile.access_scope == LearnerProfile.ACCESS_BOTH:
        return max(
            learning.research_assessment_score,
            learning.professional_assessment_score,
        )

    return 0


# =============================================================================
# STORAGE HELPERS
# =============================================================================

def _decode(value):
    """
    Decode JSON stored in browser-style storage values.
    """
    if isinstance(value, (dict, list)):
        return value

    if not isinstance(value, str) or not value:
        return {}

    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _encode(value):
    """
    Encode course state back to a compact JSON string.
    """
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _score(value):
    """
    Safely normalise an assessment score to 0-100.
    """
    try:
        return max(0, min(100, int(value or 0)))
    except (TypeError, ValueError):
        return 0


def _nonnegative_int(value):
    """
    Safely normalise attempt counts.
    """
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _sequential_reviewed(reviewed, lesson_ids):
    """
    Accept only a continuous sequence of completed lessons.

    Example:

    Submitted:
        welcome
        simple
        works
        prompt
        game2

    If 'classify' is the next required lesson after 'works',
    only the first three are accepted.

    This prevents later sections from counting as completed while
    an earlier required session remains incomplete.
    """
    if not isinstance(reviewed, list):
        return []

    reviewed_set = {
        item
        for item in reviewed
        if isinstance(item, str)
    }

    accepted = []

    for lesson_id in lesson_ids:
        if lesson_id not in reviewed_set:
            break

        accepted.append(lesson_id)

    return accepted


def _percent(reviewed, lesson_ids):
    """
    Calculate pathway completion percentage.
    """
    if not lesson_ids:
        return 0

    if not isinstance(reviewed, list):
        return 0

    count = len(
        set(reviewed).intersection(set(lesson_ids))
    )

    return max(
        0,
        min(
            100,
            round(count / len(lesson_ids) * 100),
        ),
    )


def _professional_role_from_storage_key(key):
    """
    Extract client / leadership / operations from professional storage keys.
    """
    if not isinstance(key, str):
        return None

    if not key.startswith(PRO_KEY_PREFIX):
        return None

    suffix = key[len(PRO_KEY_PREFIX):]

    if suffix.endswith("_v1"):
        suffix = suffix[:-3]

    if suffix in PROFESSIONAL_ROLES:
        return suffix

    return None


def _clean_storage_for_profile(profile, incoming):
    """
    Keep only valid Investmetrics course storage and enforce learner entitlement.

    This prevents:
    - Research-only learners from submitting Professional pathway state.
    - Professional-only learners from submitting Research pathway state.
    - Role-specific learners from submitting progress for other roles.
    """
    if not isinstance(incoming, dict):
        return {}

    clean = {}

    allowed_roles = _allowed_professional_roles(profile)

    for key, value in incoming.items():

        if not isinstance(key, str):
            continue

        if not key.startswith(COURSE_PREFIX):
            continue

        if not isinstance(value, str):
            continue

        if len(value) > 500_000:
            continue

        # ---------------------------------------------------------
        # Current pathway
        # ---------------------------------------------------------
        if key == MODE_KEY:
            pathway = _normalise_pathway(profile, value)

            if pathway:
                clean[key] = pathway

            continue

        # ---------------------------------------------------------
        # Current professional role
        # ---------------------------------------------------------
        if key == ROLE_KEY:

            if not _can_access_professional(profile):
                continue

            selected_role = str(value or "").strip()

            if selected_role in allowed_roles:
                clean[key] = selected_role

            elif (
                profile.professional_role
                != LearnerProfile.ROLE_ANY
                and allowed_roles
            ):
                clean[key] = allowed_roles[0]

            continue

        # ---------------------------------------------------------
        # Research pathway
        # ---------------------------------------------------------
        if key == RESEARCH_KEY:

            if _can_access_research(profile):
                clean[key] = value

            continue

        # ---------------------------------------------------------
        # Professional role pathway storage
        # ---------------------------------------------------------
        if key.startswith(PRO_KEY_PREFIX):

            if not _can_access_professional(profile):
                continue

            role = _professional_role_from_storage_key(key)

            if role and role in allowed_roles:
                clean[key] = value

            continue

        # ---------------------------------------------------------
        # Other Investmetrics course-level keys
        # ---------------------------------------------------------
        clean[key] = value

    return clean


# =============================================================================
# LOGIN / LEARNER HOME
# =============================================================================

def home(request):
    login_form = LearnerLoginForm()
    login_error = ""

    # -------------------------------------------------------------------------
    # LOGIN
    # -------------------------------------------------------------------------
    if (
        request.method == "POST"
        and request.POST.get("action") == "login"
    ):
        login_form = LearnerLoginForm(request.POST)

        if login_form.is_valid():

            identifier = (
                login_form.cleaned_data["identifier"]
                .strip()
            )

            candidate = _find_user(identifier)
            user = None

            if candidate:
                user = authenticate(
                    request,
                    username=candidate.username,
                    password=login_form.cleaned_data["password"],
                )

            if user is None:
                login_error = (
                    "The email/username or password is incorrect."
                )

            else:
                profile = _profile_for(user)

                if profile is None:
                    login_error = (
                        "This account is valid but is not enrolled "
                        "in AI at Work."
                    )

                else:
                    access_message = _valid_access_message(profile)

                    if access_message:
                        login_error = access_message

                    else:
                        login(request, user)
                        return redirect("ai_at_work:home")

    # -------------------------------------------------------------------------
    # NOT AUTHENTICATED
    # -------------------------------------------------------------------------
    if not request.user.is_authenticated:

        return render(
            request,
            "ai_at_work/index.html",
            {
                "stage": "login",
                "login_form": login_form,
                "login_error": login_error,
            },
        )

    # -------------------------------------------------------------------------
    # AUTHENTICATED BUT NOT ENROLLED
    # -------------------------------------------------------------------------
    profile = _profile_for(request.user)

    if profile is None:

        logout(request)

        return render(
            request,
            "ai_at_work/index.html",
            {
                "stage": "login",
                "login_form": LearnerLoginForm(),
                "login_error": (
                    "This account is not enrolled in AI at Work."
                ),
            },
        )

    # -------------------------------------------------------------------------
    # ACCESS VALIDITY
    # -------------------------------------------------------------------------
    access_message = _valid_access_message(profile)

    if access_message:

        logout(request)

        return render(
            request,
            "ai_at_work/index.html",
            {
                "stage": "login",
                "login_form": LearnerLoginForm(),
                "login_error": access_message,
            },
        )

    # -------------------------------------------------------------------------
    # FORCED PASSWORD CHANGE
    # -------------------------------------------------------------------------
    if profile.must_change_password:

        password_form = SetPasswordForm(request.user)

        return render(
            request,
            "ai_at_work/index.html",
            {
                "stage": "password_change",
                "password_form": password_form,
                "profile": profile,
            },
        )

    # -------------------------------------------------------------------------
    # COURSE
    # -------------------------------------------------------------------------
    state, _ = LearningState.objects.get_or_create(
        profile=profile
    )

    display_name = profile.display_name

    account_config = {
        "userId": request.user.pk,
        "name": display_name,
        "email": request.user.email,
        "organization": profile.organization,
        "accessScope": profile.access_scope,
        "professionalRole": profile.professional_role,
        "isStaff": request.user.is_staff,

        # Additional entitlement information for the learner UI.
        "canAccessResearch": _can_access_research(profile),
        "canAccessProfessional": _can_access_professional(profile),
        "allowedProfessionalRoles": list(
            _allowed_professional_roles(profile)
        ),

        "syncUrl": reverse("ai_at_work:sync_progress"),
        "logoutUrl": reverse("ai_at_work:logout"),
    }

    progress = _overall_progress(
        profile,
        state,
    )

    best_score = _overall_best_score(
        profile,
        state,
    )

    # Do not expose an unassigned pathway's browser state
    # back to the learner.
    storage_data = _clean_storage_for_profile(
        profile,
        state.storage or {},
    )

    return render(
        request,
        "ai_at_work/index.html",
        {
            "stage": "course",
            "profile": profile,
            "learning_state": state,
            "account_config": account_config,
            "storage_data": storage_data,
            "display_name": display_name,
            "progress": progress,
            "best_score": best_score,
        },
    )


# =============================================================================
# PASSWORD CHANGE
# =============================================================================

@login_required
@require_POST
def change_password(request):

    profile = _profile_for(request.user)

    if profile is None:
        logout(request)
        return redirect("ai_at_work:home")

    form = SetPasswordForm(
        request.user,
        request.POST,
    )

    if form.is_valid():

        user = form.save()

        update_session_auth_hash(
            request,
            user,
        )

        profile.must_change_password = False

        profile.save(
            update_fields=[
                "must_change_password",
                "updated_at",
            ]
        )

        messages.success(
            request,
            (
                "Password updated. "
                "You can now start AI at Work."
            ),
        )

        return redirect("ai_at_work:home")

    return render(
        request,
        "ai_at_work/index.html",
        {
            "stage": "password_change",
            "password_form": form,
            "profile": profile,
        },
    )


# =============================================================================
# LOGOUT
# =============================================================================

@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("ai_at_work:home")


# =============================================================================
# SURVEY STORAGE
# =============================================================================

def _save_survey(
    profile,
    pathway,
    role,
    phase,
    responses,
):
    """
    Create or update a learner's pre/post survey response.
    """

    complete = (
        all(
            str(value).strip()
            for value in responses.values()
        )
        if responses
        else False
    )

    SurveyResponse.objects.update_or_create(
        profile=profile,
        pathway=pathway,
        professional_role=role,
        phase=phase,
        defaults={
            "responses": responses,
            "is_complete": complete,
        },
    )


# =============================================================================
# RESEARCH PATHWAY SYNCHRONISATION
# =============================================================================

def _sync_research(
    profile,
    storage,
    learning,
):
    """
    Synchronise Research & Evidence progress.

    Sequential enforcement:
    A later section cannot count until every previous section has been completed.

    Assessment enforcement:
    Assessment results do not count until all required learning sections
    are complete.

    Completion enforcement:
    Research completion requires:
        - all required learning sections
        - assessment pass >= 80%
        - capstone completion
    """

    if not _can_access_research(profile):
        return

    data = _decode(
        storage.get(RESEARCH_KEY)
    )

    if not data:
        return

    raw_reviewed = data.get(
        "reviewed",
        [],
    )

    sequential = _sequential_reviewed(
        raw_reviewed,
        RESEARCH_LESSONS,
    )

    # -------------------------------------------------------------------------
    # REQUIRED LEARNING
    # -------------------------------------------------------------------------
    required_learning = (
        len(sequential)
        >= len(RESEARCH_REQUIRED_LESSONS)
    )

    # Keep only the completed required sequence first.
    canonical_reviewed = [
        lesson
        for lesson in RESEARCH_REQUIRED_LESSONS
        if lesson in sequential
    ]

    # -------------------------------------------------------------------------
    # ASSESSMENT
    # -------------------------------------------------------------------------
    if required_learning:

        score = _score(
            data.get("examBestScore")
        )

        attempts = _nonnegative_int(
            data.get("examAttempts")
        )

        passed = (
            bool(data.get("examPassed"))
            and score >= 80
        )

    else:
        score = 0
        attempts = 0
        passed = False

    # Assessment is considered completed only after passing.
    if passed:
        canonical_reviewed.append("exam")

    # -------------------------------------------------------------------------
    # FINAL COMPLETION
    # -------------------------------------------------------------------------
    capstone_passed = bool(
        data.get("capstonePassed")
    )

    eligible = (
        required_learning
        and passed
        and capstone_passed
    )

    if eligible:
        canonical_reviewed.append("finish")

    # Replace browser-submitted sequence with server-approved sequence.
    data["reviewed"] = canonical_reviewed

    # Prevent locked assessment data from surviving server sanitisation.
    if not required_learning:
        data["examBestScore"] = 0
        data["examAttempts"] = 0
        data["examPassed"] = False

    # Store the sanitised Research state.
    storage[RESEARCH_KEY] = _encode(data)

    # -------------------------------------------------------------------------
    # PROGRESS
    # -------------------------------------------------------------------------
    progress = _percent(
        canonical_reviewed,
        RESEARCH_LESSONS,
    )

    learning.research_progress = progress
    learning.research_assessment_score = score
    learning.research_completed = bool(eligible)

    # -------------------------------------------------------------------------
    # ASSESSMENT SUMMARY
    # -------------------------------------------------------------------------
    AssessmentSummary.objects.update_or_create(
        profile=profile,
        pathway=AssessmentSummary.PATH_RESEARCH,
        professional_role="",
        defaults={
            "attempts": attempts,
            "best_score": score,
            "passed": passed,
        },
    )

    # -------------------------------------------------------------------------
    # PRE-COURSE SURVEY
    # -------------------------------------------------------------------------
    pre = {
        "prompt": data.get(
            "field_prePrompt",
            "",
        ),
        "verify": data.get(
            "field_preVerify",
            "",
        ),
        "evidence": data.get(
            "field_preEvidence",
            "",
        ),
        "boundary": data.get(
            "field_preBoundary",
            "",
        ),
        "workflow": data.get(
            "field_preWorkflow",
            "",
        ),
    }

    # -------------------------------------------------------------------------
    # POST-COURSE SURVEY
    # -------------------------------------------------------------------------
    post = {
        "prompt": data.get(
            "field_postPrompt",
            "",
        ),
        "verify": data.get(
            "field_postVerify",
            "",
        ),
        "evidence": data.get(
            "field_postEvidence",
            "",
        ),
        "boundary": data.get(
            "field_postBoundary",
            "",
        ),
        "workflow": data.get(
            "field_postWorkflow",
            "",
        ),
        "reflection_start": data.get(
            "field_refStart",
            "",
        ),
        "reflection_never": data.get(
            "field_refNever",
            "",
        ),
        "reflection_rule": data.get(
            "field_refRule",
            "",
        ),
        "reflection_workflow": data.get(
            "field_refWorkflow",
            "",
        ),
        "reflection_risk": data.get(
            "field_refRisk",
            "",
        ),
    }

    if any(pre.values()):
        _save_survey(
            profile,
            AssessmentSummary.PATH_RESEARCH,
            "",
            SurveyResponse.PHASE_PRE,
            pre,
        )

    if any(post.values()):
        _save_survey(
            profile,
            AssessmentSummary.PATH_RESEARCH,
            "",
            SurveyResponse.PHASE_POST,
            post,
        )

    # -------------------------------------------------------------------------
    # CERTIFICATE
    # -------------------------------------------------------------------------
    cert_id = str(
        data.get("certificateId")
        or ""
    ).strip()

    if eligible and cert_id:

        Certificate.objects.update_or_create(
            certificate_id=cert_id,
            defaults={
                "profile": profile,
                "pathway": AssessmentSummary.PATH_RESEARCH,
                "professional_role": "",
                "assessment_score": score,
                "active": True,
            },
        )


# =============================================================================
# PROFESSIONAL PATHWAY SYNCHRONISATION
# =============================================================================

def _sync_professional(
    profile,
    storage,
    learning,
):
    """
    Synchronise General Professional Work.

    The learner may submit progress only for role(s) assigned in LearnerProfile.

    Sequential enforcement:
    A later professional section cannot count until every preceding required
    section has been completed.

    Assessment enforcement:
    Assessment results count only after all required learning is complete.
    """

    if not _can_access_professional(profile):
        return

    roles = _allowed_professional_roles(
        profile
    )

    best_progress = 0
    best_score = 0
    completed = False

    found_any = False

    for role in roles:

        storage_key = (
            f"{PRO_KEY_PREFIX}{role}_v1"
        )

        data = _decode(
            storage.get(storage_key)
        )

        if not data:
            continue

        found_any = True

        raw_reviewed = data.get(
            "reviewed",
            [],
        )

        sequential = _sequential_reviewed(
            raw_reviewed,
            PRO_LESSONS,
        )

        # ---------------------------------------------------------------------
        # REQUIRED LEARNING
        # ---------------------------------------------------------------------
        required_learning = (
            len(sequential)
            >= len(PRO_REQUIRED_LESSONS)
        )

        canonical_reviewed = [
            lesson
            for lesson in PRO_REQUIRED_LESSONS
            if lesson in sequential
        ]

        # ---------------------------------------------------------------------
        # ASSESSMENT
        # ---------------------------------------------------------------------
        if required_learning:

            score = _score(
                data.get("examBestScore")
            )

            attempts = _nonnegative_int(
                data.get("examAttempts")
            )

            passed = (
                bool(data.get("examPassed"))
                and score >= 80
            )

        else:
            score = 0
            attempts = 0
            passed = False

        # Assessment becomes complete only after a passing score.
        if passed:
            canonical_reviewed.append(
                "assessment"
            )

        eligible = (
            required_learning
            and passed
        )

        # Completion & Certificate becomes available only after passing.
        if eligible:
            canonical_reviewed.append(
                "certificate"
            )

        # Replace submitted sequence with server-approved sequence.
        data["reviewed"] = canonical_reviewed

        if not required_learning:
            data["examBestScore"] = 0
            data["examAttempts"] = 0
            data["examPassed"] = False

        storage[storage_key] = _encode(
            data
        )

        # ---------------------------------------------------------------------
        # PROGRESS
        # ---------------------------------------------------------------------
        progress = _percent(
            canonical_reviewed,
            PRO_LESSONS,
        )

        best_progress = max(
            best_progress,
            progress,
        )

        best_score = max(
            best_score,
            score,
        )

        completed = (
            completed
            or eligible
        )

        # ---------------------------------------------------------------------
        # ASSESSMENT SUMMARY
        # ---------------------------------------------------------------------
        AssessmentSummary.objects.update_or_create(
            profile=profile,
            pathway=AssessmentSummary.PATH_PROFESSIONAL,
            professional_role=role,
            defaults={
                "attempts": attempts,
                "best_score": score,
                "passed": passed,
            },
        )

        # ---------------------------------------------------------------------
        # SURVEYS
        # ---------------------------------------------------------------------
        fields = data.get(
            "fields"
        ) or {}

        pre = {
            "prompt": fields.get(
                "proPrePrompt",
                "",
            ),
            "verify": fields.get(
                "proPreVerify",
                "",
            ),
            "evidence": fields.get(
                "proPreEvidence",
                "",
            ),
            "boundary": fields.get(
                "proPreBoundary",
                "",
            ),
            "workflow": fields.get(
                "proPreWorkflow",
                "",
            ),
        }

        post = {
            "prompt": fields.get(
                "proPostPrompt",
                "",
            ),
            "verify": fields.get(
                "proPostVerify",
                "",
            ),
            "evidence": fields.get(
                "proPostEvidence",
                "",
            ),
            "boundary": fields.get(
                "proPostBoundary",
                "",
            ),
            "workflow": fields.get(
                "proPostWorkflow",
                "",
            ),
            "reflection_start": fields.get(
                "proRefStart",
                "",
            ),
            "reflection_human": fields.get(
                "proRefHuman",
                "",
            ),
            "reflection_rule": fields.get(
                "proRefRule",
                "",
            ),
        }

        if any(pre.values()):
            _save_survey(
                profile,
                AssessmentSummary.PATH_PROFESSIONAL,
                role,
                SurveyResponse.PHASE_PRE,
                pre,
            )

        if any(post.values()):
            _save_survey(
                profile,
                AssessmentSummary.PATH_PROFESSIONAL,
                role,
                SurveyResponse.PHASE_POST,
                post,
            )

        # ---------------------------------------------------------------------
        # CERTIFICATE
        # ---------------------------------------------------------------------
        cert_id = str(
            data.get("certificateId")
            or ""
        ).strip()

        if eligible and cert_id:

            Certificate.objects.update_or_create(
                certificate_id=cert_id,
                defaults={
                    "profile": profile,
                    "pathway": AssessmentSummary.PATH_PROFESSIONAL,
                    "professional_role": role,
                    "assessment_score": score,
                    "active": True,
                },
            )

    # Only modify professional progress when valid professional
    # pathway data was actually submitted.
    if found_any:
        learning.professional_progress = best_progress
        learning.professional_assessment_score = best_score
        learning.professional_completed = completed


# =============================================================================
# PROGRESS SYNCHRONISATION ENDPOINT
# =============================================================================

@login_required
@require_POST
def sync_progress(request):
    """
    Receive course browser state and synchronise it with the authenticated
    learner's Django LearningState.

    The authenticated request.user determines which LearnerProfile receives
    the progress record.
    """

    profile = _profile_for(
        request.user
    )

    if profile is None:
        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "This account is not enrolled."
                ),
            },
            status=403,
        )

    if not profile.access_is_valid:
        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "Access is not active."
                ),
            },
            status=403,
        )

    # Prevent unexpectedly large browser-state submissions.
    if len(request.body) > 2_000_000:
        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "Progress payload is too large."
                ),
            },
            status=413,
        )

    try:
        payload = json.loads(
            request.body.decode("utf-8")
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "Invalid progress payload."
                ),
            },
            status=400,
        )

    incoming = payload.get(
        "storage"
    ) or {}

    if not isinstance(incoming, dict):
        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "Invalid storage data."
                ),
            },
            status=400,
        )

    # -------------------------------------------------------------------------
    # ACCESS-AWARE STORAGE FILTER
    # -------------------------------------------------------------------------
    clean = _clean_storage_for_profile(
        profile,
        incoming,
    )

    learning, _ = LearningState.objects.get_or_create(
        profile=profile
    )

    # -------------------------------------------------------------------------
    # CURRENT PATHWAY
    # -------------------------------------------------------------------------
    mode = str(
        clean.get(MODE_KEY)
        or ""
    )

    learning.current_pathway = (
        _normalise_pathway(
            profile,
            mode,
        )
    )

    # -------------------------------------------------------------------------
    # RESEARCH
    # -------------------------------------------------------------------------
    if _can_access_research(profile):
        _sync_research(
            profile,
            clean,
            learning,
        )

    # -------------------------------------------------------------------------
    # PROFESSIONAL
    # -------------------------------------------------------------------------
    if _can_access_professional(profile):
        _sync_professional(
            profile,
            clean,
            learning,
        )

    # Store only the server-approved course state.
    learning.storage = clean

    learning.save()

    return JsonResponse(
        {
            "ok": True,
            "progress": _overall_progress(
                profile,
                learning,
            ),
            "researchProgress": (
                learning.research_progress
                if _can_access_research(profile)
                else None
            ),
            "professionalProgress": (
                learning.professional_progress
                if _can_access_professional(profile)
                else None
            ),
            "researchScore": (
                learning.research_assessment_score
                if _can_access_research(profile)
                else None
            ),
            "professionalScore": (
                learning.professional_assessment_score
                if _can_access_professional(profile)
                else None
            ),
            "researchCompleted": (
                learning.research_completed
                if _can_access_research(profile)
                else None
            ),
            "professionalCompleted": (
                learning.professional_completed
                if _can_access_professional(profile)
                else None
            ),
            "currentPathway": (
                learning.current_pathway
            ),
            "updatedAt": (
                learning.updated_at.isoformat()
            ),
        }
    )


# =============================================================================
# CERTIFICATE VERIFICATION
# =============================================================================

def verify_certificate(
    request,
    certificate_id,
):
    """
    Public certificate verification endpoint.
    """

    cert = (
        Certificate.objects
        .select_related(
            "profile__user"
        )
        .filter(
            certificate_id=certificate_id,
            active=True,
        )
        .first()
    )

    if not cert:
        raise Http404(
            "Certificate not found"
        )

    return render(
        request,
        "ai_at_work/verify.html",
        {
            "certificate": cert,
        },
    )
