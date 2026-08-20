from django.contrib import admin

from .models import Profile


class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "data_partner",
        "orcid",
    )


admin.site.register(Profile, ProfileAdmin)
