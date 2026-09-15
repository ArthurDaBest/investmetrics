from django.urls import path

from . import views


app_name = "ai_at_work"


urlpatterns = [
    path(
        "",
        views.home,
        name="home",
    ),
    path(
        "change-password/",
        views.change_password,
        name="change_password",
    ),
    path(
        "set-password/<uidb64>/<token>/",
        views.set_initial_password,
        name="set_initial_password",
    ),
    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),
    path(
        "api/sync/",
        views.sync_progress,
        name="sync_progress",
    ),
    path(
        "verify/<str:certificate_id>/",
        views.verify_certificate,
        name="verify_certificate",
    ),
]