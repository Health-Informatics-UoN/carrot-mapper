from typing import Type

from django.core.cache import cache
from django.db.models import Model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from shared.mapping.models import Dataset, Project, ScanReport, ScanReportConcept


@receiver(post_save, sender=Project)
@receiver(post_delete, sender=Project)
@receiver(post_save, sender=Dataset)
@receiver(post_delete, sender=Dataset)
@receiver(post_save, sender=ScanReport)
@receiver(post_delete, sender=ScanReport)
@receiver(post_save, sender=ScanReportConcept)
@receiver(post_delete, sender=ScanReportConcept)
def clear_cache(sender: Type[Model], **kwargs):
    """
    Clears the cache when a Project, Dataset, or Scan Report is saved or deleted.

    Args:
        sender: The sender of the signal.

    Returns:
        None
    """
    cache.clear()
