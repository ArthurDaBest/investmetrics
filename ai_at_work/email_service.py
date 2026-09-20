from django.conf import settings
from django.core.mail import get_connection, send_mail


def get_learning_email_connection():
    """
    Return the dedicated SMTP connection used by Investmetrics Learning.
    This keeps Learning email separate from IJIRI and other website email.
    """
    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=settings.LEARNING_EMAIL_HOST,
        port=settings.LEARNING_EMAIL_PORT,
        username=settings.LEARNING_EMAIL_HOST_USER,
        password=settings.LEARNING_EMAIL_HOST_PASSWORD,
        use_tls=settings.LEARNING_EMAIL_USE_TLS,
        use_ssl=settings.LEARNING_EMAIL_USE_SSL,
        fail_silently=False,
    )


def send_learning_email(subject, message, recipient_list):
    """
    Send learner-facing email from the dedicated Investmetrics Learning mailbox.
    """
    connection = get_learning_email_connection()

    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.LEARNING_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
        connection=connection,
    )