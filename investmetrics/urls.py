"""URL configuration for Investmetrics."""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.generic import RedirectView


def healthz(request):
    return HttpResponse("OK", content_type="text/plain")


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("admin/", admin.site.urls),

    # Investmetrics Learning: final public location.
    path("learn/", include("ai_at_work.urls")),

    # Temporary compatibility route for earlier AI at Work test links.
    path(
        "ai-at-work/",
        RedirectView.as_view(url="/learn/", permanent=False),
        name="ai_at_work_legacy_redirect",
    ),

    # Existing corporate website remains the root application.
    path("", include("app.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
