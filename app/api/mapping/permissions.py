import os
from typing import Any

from django.contrib.auth.models import User
from django.db.models.query_utils import Q
from rest_framework import permissions
from rest_framework.request import Request

from mapping.models import (
    Dataset,
    ScanReport,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
    VisibilityChoices,
)

# Get scan report for the table|field|value
SCAN_REPORT_QUERIES = {
    ScanReportTable: lambda x: ScanReport.objects.get(id=x.scan_report.id),
    ScanReportField: lambda x: ScanReport.objects.get(
        id=x.scan_report_table.scan_report.id
    ),
    ScanReportValue: lambda x: ScanReport.objects.get(
        id=x.scan_report_field.scan_report_table.scan_report.id
    ),
}


def is_az_function_user(user: User) -> bool:
    """Check of the user is the `AZ_FUNCTION_USER`

    Args:
        user (User): The user to check

    Returns:
        bool: `True` if `user` is the `AZ_FUNCTION_USER` else `False`
    """

    return user.username == os.getenv("AZ_FUNCTION_USER")


def is_scan_report_author(obj: Any, request: Request) -> bool:
    """Check if the user is the author of a scan report.

    Args:
        obj (Any): The object to check (should be a ScanReport or related object).
        request (Request): The request with the User instance.

    Returns:
        bool: `True` if the request's user is the author of the scan report, else `False`.
    """
    try:
        # If `obj` is a scan report table|field|value, get the scan report
        # it belongs to and check the user has permission to view it.
        if sub_scan_report_query := SCAN_REPORT_QUERIES.get(type(obj)):
            sub_scan_report = sub_scan_report_query(obj)
        else:
            sub_scan_report = obj

        # Check if the user is the author
        if isinstance(sub_scan_report, ScanReport):
            return sub_scan_report.author.id == request.user.id
        else:
            return False
    except Exception:
        return False


def has_viewership(obj: Any, request: Request) -> bool:
    """Check the viewership permission on an object.

    Args:
        obj (Any): The object to check the permissions on.
        request (Request): The request with the User instance.

    Returns:
        bool: `True` if the request's user has permission, else `False`.
    """
    # Permission checks to perform
    checks = {
        Dataset: lambda x: Dataset.objects.filter(
            Q(visibility=VisibilityChoices.PUBLIC)
            | Q(viewers__id=request.user.id, visibility=VisibilityChoices.RESTRICTED)
            | Q(editors__id=request.user.id, visibility=VisibilityChoices.RESTRICTED)
            | Q(admins__id=request.user.id, visibility=VisibilityChoices.RESTRICTED),
            project__members__id=request.user.id,
            id=x.id,
        ).exists(),
        ScanReport: lambda x: ScanReport.objects.filter(
            # parent dataset and SR are public checks
            Q(
                # parent dataset and SR are public
                parent_dataset__visibility=VisibilityChoices.PUBLIC,
                visibility=VisibilityChoices.PUBLIC,
            )
            # parent dataset is public but SR restricted checks
            | Q(
                # parent dataset is public
                # SR is restricted and user is in SR viewers
                parent_dataset__visibility=VisibilityChoices.PUBLIC,
                viewers=request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            | Q(
                # parent dataset is public
                # SR is restricted and user is in SR editors
                parent_dataset__visibility=VisibilityChoices.PUBLIC,
                editors=request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            | Q(
                # parent dataset is public
                # SR is restricted and user is SR author
                parent_dataset__visibility=VisibilityChoices.PUBLIC,
                author=request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            | Q(
                # parent dataset is public
                # SR is restricted and user is in parent dataset editors
                parent_dataset__visibility=VisibilityChoices.PUBLIC,
                parent_dataset__editors=request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            | Q(
                # parent dataset is public
                # SR is restricted and user is in parent dataset admins
                parent_dataset__visibility=VisibilityChoices.PUBLIC,
                parent_dataset__admins=request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            # parent dataset and SR are restricted checks
            | Q(
                # parent dataset and SR are restricted
                # user is in SR viewers
                parent_dataset__visibility=VisibilityChoices.RESTRICTED,
                viewers=request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            | Q(
                # parent dataset and SR are restricted
                # user is in SR editors
                parent_dataset__visibility=VisibilityChoices.RESTRICTED,
                editors=request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            | Q(
                # parent dataset and SR are restricted
                # user is SR author
                parent_dataset__visibility=VisibilityChoices.RESTRICTED,
                author=request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            | Q(
                # parent dataset and SR are restricted
                # user is in parent dataset admins
                parent_dataset__visibility=VisibilityChoices.RESTRICTED,
                parent_dataset__admins=request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            | Q(
                # parent dataset and SR are restricted
                # user is in parent dataset editors
                parent_dataset__visibility=VisibilityChoices.RESTRICTED,
                parent_dataset__editors=request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            # parent dataset is restricted but SR is public checks
            | Q(
                # parent dataset is restricted and SR public
                # user is in parent dataset editors
                parent_dataset__visibility=VisibilityChoices.RESTRICTED,
                parent_dataset__editors=request.user.id,
                visibility=VisibilityChoices.PUBLIC,
            )
            | Q(
                # parent dataset is restricted and SR public
                # user is in parent dataset admins
                parent_dataset__visibility=VisibilityChoices.RESTRICTED,
                parent_dataset__admins=request.user.id,
                visibility=VisibilityChoices.PUBLIC,
            )
            | Q(
                # parent dataset is restricted and SR public
                # user is in parent dataset viewers
                parent_dataset__visibility=VisibilityChoices.RESTRICTED,
                parent_dataset__viewers=request.user.id,
                visibility=VisibilityChoices.PUBLIC,
            ),
            parent_dataset__project__members=request.user.id,
            id=x.id,
        ).exists(),
    }

    # If `obj` is a scan report table|field|value, get the scan report
    # it belongs to and check the user has permission to view it.
    if sub_scan_report := SCAN_REPORT_QUERIES.get(type(obj)):
        sub_scan_report = sub_scan_report(obj)
        return checks.get(type(sub_scan_report))(sub_scan_report)

    # If `obj` is a dataset or scan report, check the user can view it.
    if permission_check := checks.get(type(obj)):
        return permission_check(obj)

    return False


def has_editorship(obj: Any, request: Request) -> bool:
    """Check the editorship permission on an object.

    Args:
        obj (Any): The object to check the permissions on.
        request (Request): The request with the User instance.

    Returns:
        bool: `True` if the request's user has permission, else `False`.
    """
    # Permission checks to perform
    checks = {
        Dataset: lambda x: Dataset.objects.filter(
            project__members__id=request.user.id, editors__id=request.user.id, id=x.id
        ).exists(),
        ScanReport: lambda x: ScanReport.objects.filter(
            Q(parent_dataset__editors__id=request.user.id)
            | Q(editors__id=request.user.id),
            parent_dataset__project__members__id=request.user.id,
            id=x.id,
        ).exists(),
    }

    # If `obj` is a scan report table|field|value, get the scan report
    # it belongs to and check the user has permission to edit it.
    if sub_scan_report := SCAN_REPORT_QUERIES.get(type(obj)):
        sub_scan_report = sub_scan_report(obj)
        return checks.get(type(sub_scan_report))(sub_scan_report)

    # If `obj` is a dataset or scan report, check the user can edit it.
    if permission_check := checks.get(type(obj)):
        return permission_check(obj)

    return False


def can_edit(obj: Any, user: User) -> bool:
    """Check the editorship permission on an object.

    Args:
        obj (Any): The object to check the permissions on.
        user (User): User instance.

    Returns:
        bool: `True` if the request's user has permission, else `False`.
    """
    # Permission checks to perform
    checks = {
        ScanReport: lambda x: ScanReport.objects.filter(
            Q(parent_dataset__editors__id=user.id)
            | Q(parent_dataset__admins__id=user.id)
            | Q(editors__id=user.id)
            | Q(author__id=user.id),
            parent_dataset__project__members__id=user.id,
            id=x.id,
        ).exists(),
    }

    # If `obj` is a scan report table|field|value, get the scan report
    # it belongs to and check the user has permission to edit it.
    if sub_scan_report := SCAN_REPORT_QUERIES.get(type(obj)):
        sub_scan_report = sub_scan_report(obj)
        return checks.get(type(sub_scan_report))(sub_scan_report)

    # If `obj` is a dataset or scan report, check the user can edit it.
    if permission_check := checks.get(type(obj)):
        return permission_check(obj)

    return False


def is_admin(obj: Any, request: Request) -> bool:
    """Check the admin permission on an object.

    Args:
        obj (Any): The object to check the permissions on.
        request (Request): The request with the User instance.

    Returns:
        bool: `True` if the request's user has permission, else `False`.
    """
    # Permission checks to perform
    checks = {
        Dataset: lambda x: Dataset.objects.filter(
            project__members__id=request.user.id, admins__id=request.user.id, id=x.id
        ).exists(),
        ScanReport: lambda x: ScanReport.objects.filter(
            Q(parent_dataset__admins__id=request.user.id)
            | Q(author__id=request.user.id),
            parent_dataset__project__members__id=request.user.id,
            id=x.id,
        ).exists(),
    }

    # If `obj` is a scan report table|field|value, get the scan report
    # it belongs to and check the user has permission to edit it.
    if sub_scan_report := SCAN_REPORT_QUERIES.get(type(obj)):
        sub_scan_report = sub_scan_report(obj)
        return checks.get(type(sub_scan_report))(sub_scan_report)

    # If `obj` is a dataset or scan report, check the user can edit it.
    if permission_check := checks.get(type(obj)):
        return permission_check(obj)

    return False


class IsAuthor(permissions.BasePermission):
    message = "You are not the author of this scan report."

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if the User is the author of the scan report.
        """
        return is_scan_report_author(obj, request)


class CanViewProject(permissions.BasePermission):
    message = "You must be a member of this project to view its contents."

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if the User's ID is in the Project's members.
        """
        return obj.members.filter(id=request.user.id).exists()


class CanView(permissions.BasePermission):
    message = "You do not have permission to view this."

    def has_object_permission(self, request, view, obj):
        """
        Return `True` in any of the following cases:
            - the User is the `AZ_FUNCTION_USER`
            - the Object is 'RESTRICTED' and the User is an Object viewer
            - the Object is 'PUBLIC' and the User is a member of a Project
            that the Object is in.
        """

        if is_az_function_user(request.user):
            return True
        return has_viewership(obj, request)


class CanEditOrAdmin(permissions.BasePermission):
    message = "You do not have permission to edit this."

    def has_object_permission(self, request: Request, view, obj):
        """
        Return `True` in any of the following cases:
            - the User is an Object editor or Admin.
        """
        return can_edit(obj, request.user)


class CanEdit(permissions.BasePermission):
    message = "You do not have permission to edit this."

    def has_object_permission(self, request, view, obj):
        """
        Return `True` in any of the following cases:
            - the User is the `AZ_FUNCTION_USER`
            - the User is an Object editor.
        """

        if is_az_function_user(request.user):
            return True
        return has_editorship(obj, request)


class CanAdmin(permissions.BasePermission):
    message = "You are not an admin of this."

    def has_object_permission(self, request, view, obj):
        """
        Return `True` in any of the following cases:
            - the User is the `AZ_FUNCTION_USER`
            - the User is an Object admin.
        """

        if is_az_function_user(request.user):
            return True
        return is_admin(obj, request)


def get_user_permissions_on_dataset(request, dataset_id):
    """
    Retrieve the list of permissions a user has on a specific dataset.

    Args:
        request (HttpRequest): The HTTP request object containing the authenticated user.
        dataset_id (int): The primary key of the dataset.

    Returns:
        list: A list of permission strings the user has on the dataset.
              Returns an empty list if the datset does not exist or if the user has no permissions.
    """
    try:
        dataset = Dataset.objects.get(id=dataset_id)
        permissions = []

        if CanView().has_object_permission(request, None, dataset):
            permissions.append("CanView")
        if CanEdit().has_object_permission(request, None, dataset):
            permissions.append("CanEdit")
        if CanAdmin().has_object_permission(request, None, dataset):
            permissions.append("CanAdmin")

        return permissions
    except Dataset.DoesNotExist:
        return []


def get_user_permissions_on_scan_report(request, scan_report_id):
    """
    Retrieve the list of permissions a user has on a specific scan report.

    Args:
        request (HttpRequest): The HTTP request object containing the authenticated user.
        scan_report_id (int): The primary key of the scan report.

    Returns:
        list: A list of permission strings the user has on the scan report.
              Returns an empty list if the scan report does not exist or if the user has no permissions.
    """
    try:
        scan_report = ScanReport.objects.get(id=scan_report_id)
        permissions = []

        if CanView().has_object_permission(request, None, scan_report):
            permissions.append("CanView")
        if CanEdit().has_object_permission(request, None, scan_report):
            permissions.append("CanEdit")
        if CanAdmin().has_object_permission(request, None, scan_report):
            permissions.append("CanAdmin")
        if IsAuthor().has_object_permission(request, None, scan_report):
            permissions.append("IsAuthor")

        return permissions
    except ScanReport.DoesNotExist:
        return []
