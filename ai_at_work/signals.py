from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LearnerProfile, LearningState


@receiver(post_save, sender=LearnerProfile)
def ensure_learning_state(sender, instance, created, **kwargs):
    if created:
        LearningState.objects.get_or_create(profile=instance)
