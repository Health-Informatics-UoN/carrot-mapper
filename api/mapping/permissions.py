import os
from rest_framework import permissions
from .models import (
    Project,
)


class CanViewProject(permissions.BasePermission):
    message = "You must be a member of this project to view its contents."

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if the User's ID is in the Project's members.
        """
        return obj.members.filter(id=request.user.id).exists()


class CanViewDataset(permissions.BasePermission):

    message = "You do not have permission to view this dataset"

    def has_object_permission(self, request, view, obj):
        """
        Return `True` in any of the following cases: 
            - the User is the `AZ_FUNCTION_USER`
            - the dataset is 'RESTRICTED' and the User's ID is in a project the User is a member of.
            - the dataset is 'PUBLIC' and the User's ID is in the Project's members,
        """
        visibility = obj.visibility

        # if the User is the `AZ_FUNCTION_USER` grant permission
        if request.user.username == os.getenv("AZ_FUNCTION_USER"):
            return True
        # if the visibility is restricted
        # check if the user is in the viewers field
        if visibility == "RESTRICTED":
            self.message = "You must be granted permission to view this dataset"
            return obj.viewers.filter(id=request.user.id).exists()
        # if the visibility is public
        # check if the user is a member in any projects the dataset is in
        elif visibility == "PUBLIC":
            # filter by projects that have dataset obj.id
            # filter by projects that have user as a member
            self.message = "You are not a member of any projects for this dataset"
            return Project.objects.filter(
                datasets__id=obj.id, members__id=request.user.id
            ).exists()
        return False


class CanViewScanReport(permissions.BasePermission):
    message = "You do not have permission to view this scan report"

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if, the scan report is 'public' and the User's ID is in the Project's members,
        or, the scan report is 'restricted' and the User's ID is in a project the User is a member of.
        """
        visibility = obj.visibility
        # if the visibility is restricted
        # check if the user is in the viewers field
        if visibility == "RESTRICTED":
            self.message = "You must be granted permission to view this scan report"
            return obj.viewers.filter(id=request.user.id).exists()
        # if the visibility is public
        # check if the user is a member in any projects the parent dataset is in
        elif visibility == "PUBLIC":
            # get projects
            # filter by projects that have dataset obj.parent_dataset
            # filter by projects that have user as a member
            self.message = "You are not a member of any projects for this scan report"
            return Project.objects.filter(
                datasets__id=obj.parent_dataset.id, members__id=request.user.id
            ).exists()

        return False
