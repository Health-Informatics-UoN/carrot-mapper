from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from mapping.models import BaseModel, DataPartner

orcid_validator = RegexValidator(
    regex=r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$",
    message="ORCID iD must be in the format 0000-0000-0000-0000.",
)


class Profile(BaseModel):
    """
    Model for a User's profile, holding optional details not on the
    built-in `User` model: their Data Partner affiliation and ORCID iD.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    data_partner = models.ForeignKey(
        DataPartner,
        on_delete=models.SET_NULL,
        related_name="profiles",
        related_query_name="profile",
        null=True,
        blank=True,
    )
    orcid = models.CharField(
        max_length=19,
        null=True,
        blank=True,
        validators=[orcid_validator],
    )

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self) -> str:
        return str(self.id)
