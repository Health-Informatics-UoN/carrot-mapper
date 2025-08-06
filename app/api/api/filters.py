from django.db.models.query_utils import Q
from rest_framework import filters
from mapping.models import VisibilityChoices, ScanReportValue
from django_filters import rest_framework as django_filters


class HasConceptsFilter(django_filters.BooleanFilter):
    """
    Custom filter to check if a ScanReportValue has any concepts.
    """

    def filter(self, qs, value):
        if value is None:
            return qs

        if value:
            return qs.filter(concepts__isnull=False)
        else:
            return qs.filter(concepts__isnull=True)


class CreationTypeFilter(django_filters.CharFilter):
    """
    Custom filter to filter ScanReportValue by the creation_type of their concepts.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if not value:
            return qs

        # Split comma-separated values
        if isinstance(value, str):
            values = [v.strip() for v in value.split(",")]
        else:
            values = value

        # Handle the case where 'none' is selected
        if "none" in values:
            # Remove 'none' from the list and filter for values with no concepts
            other_values = [v for v in values if v != "none"]
            if other_values:
                # If other values are also selected, we need to use Q objects for OR logic
                from django.db.models import Q

                q_objects = Q(concepts__isnull=True)
                for creation_type in other_values:
                    q_objects |= Q(concepts__creation_type=creation_type)
                return qs.filter(q_objects).distinct()
            else:
                # Only 'none' is selected
                return qs.filter(concepts__isnull=True)
        else:
            # Only creation types are selected (no 'none')
            return qs.filter(concepts__creation_type__in=values).distinct()


class ScanReportAccessFilter(filters.BaseFilterBackend):
    """
    Filter that only allows users to see Scan Reports they are allowed to view, edit, or admin.
    """

    # Each model type needs a different relationship to get the Scan Report / Dataset permissions.
    RELATIONSHIP_MAPPING = {
        "scanreport": "",
        "scanreporttable": "scan_report__",
        "scanreportfield": "scan_report_table__scan_report__",
        "scanreportvalue": "scan_report_field__scan_report_table__scan_report__",
    }

    def filter_queryset(self, request, queryset, view):
        model = queryset.model.__name__.lower()
        relationship = self.RELATIONSHIP_MAPPING.get(model, "")
        user_id = request.user.id

        permission_conditions = self.get_permission_conditions(relationship, user_id)
        return queryset.filter(permission_conditions).distinct()

    def get_permission_conditions(self, relationship: str, user_id: str) -> Q:
        """
        Get combined visibility and permission conditions for a given relationship and user.

        Args:
            relationship (str): The relationship for which conditions are needed.
            user_id (str): The user ID for which conditions are generated.

        Returns:
            Q: Query object representing the combined conditions.
        """
        dataset_visibility = f"{relationship}parent_dataset__visibility"
        scan_report_visibility = f"{relationship}visibility"
        scan_report_viewers = f"{relationship}viewers"
        scan_report_editors = f"{relationship}editors"
        scan_report_author = f"{relationship}author"
        dataset_viewers = f"{relationship}parent_dataset__viewers"
        dataset_editors = f"{relationship}parent_dataset__editors"
        dataset_admins = f"{relationship}parent_dataset__admins"
        project_members = f"{relationship}parent_dataset__project__members"

        return Q(
            # Public dataset and public scan report
            Q(**{dataset_visibility: VisibilityChoices.PUBLIC})
            & Q(**{scan_report_visibility: VisibilityChoices.PUBLIC})
            | Q(  # Public dataset and restricted scan report
                **{dataset_visibility: VisibilityChoices.PUBLIC}
            )
            & (
                Q(**{scan_report_viewers: user_id})
                | Q(**{scan_report_editors: user_id})
                | Q(**{scan_report_author: user_id})
                | Q(**{dataset_editors: user_id})
                | Q(**{dataset_admins: user_id})
            )
            & Q(**{scan_report_visibility: VisibilityChoices.RESTRICTED})
            | Q(  # Restricted dataset and restricted scan report
                **{dataset_visibility: VisibilityChoices.RESTRICTED}
            )
            & (
                Q(**{scan_report_viewers: user_id})
                | Q(**{scan_report_editors: user_id})
                | Q(**{scan_report_author: user_id})
                | Q(**{dataset_admins: user_id})
                | Q(**{dataset_editors: user_id})
            )
            & Q(**{scan_report_visibility: VisibilityChoices.RESTRICTED})
            | Q(  # Restricted dataset and public scan report
                **{dataset_visibility: VisibilityChoices.RESTRICTED}
            )
            & (
                Q(**{dataset_editors: user_id})
                | Q(**{dataset_admins: user_id})
                | Q(**{dataset_viewers: user_id})
            )
            & Q(**{scan_report_visibility: VisibilityChoices.PUBLIC})
        ) & Q(**{project_members: user_id})


class ScanReportValueFilter(django_filters.FilterSet):
    """
    Custom filterset for ScanReportValue model.
    """

    has_concepts = HasConceptsFilter()
    creation_type = CreationTypeFilter()

    class Meta:
        model = ScanReportValue
        fields = {
            "value": ["in", "icontains"],
        }
