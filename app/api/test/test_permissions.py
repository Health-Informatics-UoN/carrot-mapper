import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from projects.views import ProjectDetail
from rest_framework.authtoken.models import Token
from rest_framework.generics import GenericAPIView
from rest_framework.test import APIRequestFactory, force_authenticate
from shared.mapping.models import (
    DataPartner,
    Dataset,
    Project,
    ScanReport,
    VisibilityChoices,
)
from shared.mapping.permissions import (
    CanAdmin,
    CanEdit,
    CanView,
    CanViewProject,
    has_editorship,
    has_viewership,
    is_admin,
)


class TestHasViewership(TestCase):
    def setUp(self):
        User = get_user_model()
        # Create user who can access the Project
        self.user_with_perm = User.objects.create(
            username="gandalf", password="thegrey"
        )
        # Give them a token
        Token.objects.create(user=self.user_with_perm)

        # Create user who cannot access the Project
        self.user_not_on_project = User.objects.create(
            username="balrog", password="youshallnotpass"
        )
        # Give them a token
        Token.objects.create(user=self.user_not_on_project)

        # Create user who cannot access the restricted dataset
        self.non_restricted_ds_viewer = User.objects.create(
            username="sauron", password="thedeceiver"
        )
        # Give them a token
        Token.objects.create(user=self.non_restricted_ds_viewer)

        # Create user who cannot access the restricted scan report
        self.non_restricted_sr_viewer = User.objects.create(
            username="saruman", password="thewise"
        )
        # Give them a token
        Token.objects.create(user=self.non_restricted_sr_viewer)

        # Create the project
        self.project = Project.objects.create(name="The Fellowship of the Ring")
        # Add the permitted user
        self.project.members.add(
            self.user_with_perm,
            self.non_restricted_ds_viewer,
            self.non_restricted_sr_viewer,
        )

        # Create a Data Partner
        self.data_partner = DataPartner.objects.create(name="Silvan Elves")

        # Set up datasets
        self.public_dataset = Dataset.objects.create(
            name="The Fellowship of the Ring",
            visibility=VisibilityChoices.PUBLIC,
            data_partner=self.data_partner,
        )
        self.restricted_dataset = Dataset.objects.create(
            name="The Two Towers",
            visibility=VisibilityChoices.RESTRICTED,
            data_partner=self.data_partner,
        )
        self.restricted_dataset.viewers.add(self.user_with_perm)
        self.project.datasets.add(self.public_dataset, self.restricted_dataset)

        # Set up scan reports
        self.public_scanreport = ScanReport.objects.create(
            dataset="The Shire",
            visibility=VisibilityChoices.PUBLIC,
            parent_dataset=self.public_dataset,
        )
        self.restricted_scanreport = ScanReport.objects.create(
            dataset="Moria",
            visibility=VisibilityChoices.RESTRICTED,
            parent_dataset=self.public_dataset,
        )
        self.restricted_scanreport.viewers.add(self.user_with_perm)

        # Set up request
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/paths/of/the/dead")

        # Generic test view, specific view class not required
        self.view = GenericAPIView.as_view()

    def test_dataset_perms(self):
        # Check user_with_perm can see all datasets
        self.request.user = self.user_with_perm
        self.assertTrue(has_viewership(self.public_dataset, self.request))
        self.assertTrue(has_viewership(self.restricted_dataset, self.request))

        # Check non_restricted_ds_viewer can see public dataset
        # but not restricted dataset
        self.request.user = self.non_restricted_ds_viewer
        self.assertTrue(has_viewership(self.public_dataset, self.request))
        self.assertFalse(has_viewership(self.restricted_dataset, self.request))

        # Check user_not_on_project can see nothing
        self.request.user = self.user_not_on_project
        self.assertFalse(has_viewership(self.public_dataset, self.request))
        self.assertFalse(has_viewership(self.restricted_dataset, self.request))

    def test_scan_report_perms(self):
        # Check user_with_perm can see all scan reports
        self.request.user = self.user_with_perm
        self.assertTrue(has_viewership(self.public_scanreport, self.request))
        self.assertTrue(has_viewership(self.restricted_scanreport, self.request))

        # Check non_restricted_sr_viewer can see public scan report
        # but not restricted scan report
        self.request.user = self.non_restricted_sr_viewer
        self.assertTrue(has_viewership(self.public_scanreport, self.request))
        self.assertFalse(has_viewership(self.restricted_scanreport, self.request))

        # Check user_not_on_project can see nothing
        self.request.user = self.user_not_on_project
        self.assertFalse(has_viewership(self.public_scanreport, self.request))
        self.assertFalse(has_viewership(self.restricted_scanreport, self.request))


class TestHasEditorship(TestCase):
    def setUp(self):
        User = get_user_model()
        # Create user who can access the Project
        self.user_with_perm = User.objects.create(
            username="gandalf", password="thegrey"
        )
        # Give them a token
        Token.objects.create(user=self.user_with_perm)

        # Create user who cannot access the Project
        self.user_not_on_project = User.objects.create(
            username="balrog", password="youshallnotpass"
        )
        # Give them a token
        Token.objects.create(user=self.user_not_on_project)

        # Create user who cannot access the restricted dataset
        self.non_restricted_ds_viewer = User.objects.create(
            username="sauron", password="thedeceiver"
        )
        # Give them a token
        Token.objects.create(user=self.non_restricted_ds_viewer)

        # Create user who cannot access the restricted scan report
        self.non_restricted_sr_viewer = User.objects.create(
            username="saruman", password="thewise"
        )
        # Give them a token
        Token.objects.create(user=self.non_restricted_sr_viewer)

        # Create the project
        self.project = Project.objects.create(name="The Fellowship of the Ring")
        # Add the permitted user
        self.project.members.add(
            self.user_with_perm,
            self.non_restricted_ds_viewer,
            self.non_restricted_sr_viewer,
        )

        # Create a Data Partner
        self.data_partner = DataPartner.objects.create(name="Silvan Elves")
        # Set up datasets
        self.public_dataset = Dataset.objects.create(
            name="The Fellowship of the Ring",
            visibility=VisibilityChoices.PUBLIC,
            data_partner=self.data_partner,
        )
        self.public_dataset.editors.add(self.user_with_perm)
        self.restricted_dataset = Dataset.objects.create(
            name="The Two Towers",
            visibility=VisibilityChoices.RESTRICTED,
            data_partner=self.data_partner,
        )
        self.restricted_dataset.viewers.add(self.user_with_perm)
        self.restricted_dataset.editors.add(self.user_with_perm)
        self.project.datasets.add(self.public_dataset, self.restricted_dataset)

        # Set up scan reports
        self.public_scanreport = ScanReport.objects.create(
            dataset="The Shire",
            visibility=VisibilityChoices.PUBLIC,
            parent_dataset=self.public_dataset,
        )
        self.public_scanreport.editors.add(self.user_with_perm)
        self.restricted_scanreport = ScanReport.objects.create(
            dataset="Moria",
            visibility=VisibilityChoices.RESTRICTED,
            parent_dataset=self.public_dataset,
        )
        self.restricted_scanreport.viewers.add(self.user_with_perm)
        self.restricted_scanreport.editors.add(self.user_with_perm)

        # Set up request
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/paths/of/the/dead")

        # Generic test view, specific view class not required
        self.view = GenericAPIView.as_view()

    def test_dataset_perms(self):
        # Check user_with_perm can edit all datasets
        # because they are an editor in them
        self.request.user = self.user_with_perm
        self.assertTrue(has_editorship(self.public_dataset, self.request))
        self.assertTrue(has_editorship(self.restricted_dataset, self.request))

        # Check non_restricted_ds_viewer cannot edit public or restricted dataset
        # because they are not in the editors field
        self.request.user = self.non_restricted_ds_viewer
        self.assertFalse(has_editorship(self.public_dataset, self.request))
        self.assertFalse(has_editorship(self.restricted_dataset, self.request))

        # Check user_not_on_project can edit nothing
        self.request.user = self.user_not_on_project
        self.assertFalse(has_editorship(self.public_dataset, self.request))
        self.assertFalse(has_editorship(self.restricted_dataset, self.request))

    def test_scan_report_perms(self):
        # Check user_with_perm can see edit scan reports
        # because they are an editor in them
        self.request.user = self.user_with_perm
        self.assertTrue(has_editorship(self.public_scanreport, self.request))
        self.assertTrue(has_editorship(self.restricted_scanreport, self.request))

        # Check non_restricted_ds_viewer cannot edit public or restricted scan report
        # because they are not in the editors field
        self.request.user = self.non_restricted_sr_viewer
        self.assertFalse(has_editorship(self.public_scanreport, self.request))
        self.assertFalse(has_editorship(self.restricted_scanreport, self.request))

        # Check user_not_on_project can see nothing
        self.request.user = self.user_not_on_project
        self.assertFalse(has_editorship(self.public_scanreport, self.request))
        self.assertFalse(has_editorship(self.restricted_scanreport, self.request))


class TestIsAdmin(TestCase):
    def setUp(self):
        User = get_user_model()
        # Create user who can access the Project
        self.ds_admin = User.objects.create(username="gandalf", password="thegrey")
        # Give them a token
        Token.objects.create(user=self.ds_admin)

        # Create user who cannot access the Project
        self.user_not_on_project = User.objects.create(
            username="balrog", password="youshallnotpass"
        )
        # Give them a token
        Token.objects.create(user=self.user_not_on_project)

        # Create user who cannot access the restricted dataset
        self.non_restricted_ds_viewer = User.objects.create(
            username="sauron", password="thedeceiver"
        )
        # Give them a token
        Token.objects.create(user=self.non_restricted_ds_viewer)

        # Create user who cannot access the restricted scan report
        self.sr_author = User.objects.create(username="saruman", password="thewise")
        # Give them a token
        Token.objects.create(user=self.sr_author)

        # Create the project
        self.project = Project.objects.create(name="The Fellowship of the Ring")
        # Add the permitted user
        self.project.members.add(
            self.ds_admin,
            self.non_restricted_ds_viewer,
            self.sr_author,
        )

        # Create a Data Partner
        self.data_partner = DataPartner.objects.create(name="Silvan Elves")
        # Set up datasets
        self.public_dataset = Dataset.objects.create(
            name="The Fellowship of the Ring",
            visibility=VisibilityChoices.PUBLIC,
            data_partner=self.data_partner,
        )
        self.public_dataset.admins.add(self.ds_admin)
        self.restricted_dataset = Dataset.objects.create(
            name="The Two Towers",
            visibility=VisibilityChoices.RESTRICTED,
            data_partner=self.data_partner,
        )
        self.restricted_dataset.viewers.add(self.ds_admin)
        self.restricted_dataset.admins.add(self.ds_admin)
        self.project.datasets.add(self.public_dataset, self.restricted_dataset)

        # Set up scan reports
        self.public_scanreport = ScanReport.objects.create(
            dataset="The Shire",
            visibility=VisibilityChoices.PUBLIC,
            parent_dataset=self.public_dataset,
        )
        self.restricted_scanreport = ScanReport.objects.create(
            dataset="Moria",
            visibility=VisibilityChoices.RESTRICTED,
            parent_dataset=self.restricted_dataset,
            author=self.sr_author,
        )
        self.restricted_scanreport.viewers.add(self.ds_admin)

        # Set up request
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/paths/of/the/dead")

        # Generic test view, specific view class not required
        self.view = GenericAPIView.as_view()

    def test_dataset_perms(self):
        # Check ds_admin can admin all datasets
        # because they are an admin in them
        self.request.user = self.ds_admin
        self.assertTrue(is_admin(self.public_dataset, self.request))
        self.assertTrue(is_admin(self.restricted_dataset, self.request))

        # Check non_restricted_ds_viewer cannot admin public or restricted dataset
        # because they are not in the admins field
        self.request.user = self.non_restricted_ds_viewer
        self.assertFalse(is_admin(self.public_dataset, self.request))
        self.assertFalse(is_admin(self.restricted_dataset, self.request))

        # Check user_not_on_project can edit nothing
        self.request.user = self.user_not_on_project
        self.assertFalse(is_admin(self.public_dataset, self.request))
        self.assertFalse(is_admin(self.restricted_dataset, self.request))

    def test_scan_report_perms(self):
        # Check ds_admin can see edit scan reports
        # because they are an editor in them
        self.request.user = self.ds_admin
        self.assertTrue(is_admin(self.public_scanreport, self.request))
        self.assertTrue(is_admin(self.restricted_scanreport, self.request))

        # Check sr_author cannot edit public scan report
        # but can see restricted_scanreport
        # because they are the author
        self.request.user = self.sr_author
        self.assertFalse(is_admin(self.public_scanreport, self.request))
        self.assertTrue(is_admin(self.restricted_scanreport, self.request))

        # Check user_not_on_project can see nothing
        self.request.user = self.user_not_on_project
        self.assertFalse(is_admin(self.public_scanreport, self.request))
        self.assertFalse(is_admin(self.restricted_scanreport, self.request))


class TestCanViewProject(TestCase):
    def setUp(self):
        User = get_user_model()
        # Create user who can access the Project
        self.user_with_perm = User.objects.create(
            username="gandalf", password="thegrey"
        )
        # Give them a token
        Token.objects.create(user=self.user_with_perm)

        # Create user who cannot access the Project
        self.user_without_perm = User.objects.create(
            username="balrog", password="youshallnotpass"
        )
        # Give them a token
        Token.objects.create(user=self.user_without_perm)

        # Create the project
        self.project = Project.objects.create(name="The Fellowship of the Ring")
        # Add the permitted user
        self.project.members.add(self.user_with_perm)

        # Request factory for setting up requests
        self.factory = APIRequestFactory()
        # The instance of the view required for the permission class
        self.view = ProjectDetail.as_view()

        # The permission class
        self.permission = CanViewProject()

    def test_project_member_can_view(self):
        # Make the request for the Project
        request = self.factory.get(f"/projects/{self.project.id}")
        # Add the user to the request; this is not automatic
        request.user = self.user_with_perm
        # Authenticate the user
        force_authenticate(
            request, user=self.user_with_perm, token=self.user_with_perm.auth_token
        )
        # Assert the user on the project has permission to see the view
        self.assertTrue(
            self.permission.has_object_permission(request, self.view, self.project)
        )

    def test_non_project_member_cannot_view(self):
        # Make the request for the Project
        request = self.factory.get(f"/projects/{self.project.id}")
        # Add the user to the request; this is not automatic
        request.user = self.user_without_perm
        # Authenticate the user
        force_authenticate(
            request,
            user=self.user_without_perm,
            token=self.user_without_perm.auth_token,
        )
        # Assert the user not on the project doesn't have permission to see the view
        self.assertFalse(
            self.permission.has_object_permission(request, self.view, self.project)
        )


class TestCanView(TestCase):
    def setUp(self):
        User = get_user_model()
        # Create user who can see the Dataset whether restricted or public
        self.restricted_user = User.objects.create(
            username="gandalf", password="thegrey"
        )
        # Give them a token
        Token.objects.create(user=self.restricted_user)

        # Create user who can see the Dataset when public only
        self.public_user = User.objects.create(username="aragorn", password="elissar")
        # Give them a token
        Token.objects.create(user=self.public_user)

        # Create user who cannot access the Project
        self.user_without_perm = User.objects.create(
            username="balrog", password="youshallnotpass"
        )
        # Give them a token
        Token.objects.create(user=self.user_without_perm)

        # Create the project
        self.project = Project.objects.create(name="The Fellowship of the Ring")
        # Add the permitted users
        self.project.members.add(self.public_user, self.restricted_user)

        # Create a Data Partner
        self.data_partner = DataPartner.objects.create(name="Silvan Elves")
        # Create the public dataset
        self.public_dataset = Dataset.objects.create(
            name="Hobbits of the Fellowship",
            visibility=VisibilityChoices.PUBLIC,
            data_partner=self.data_partner,
        )
        # Create the restricted dataset
        self.restricted_dataset = Dataset.objects.create(
            name="Ring bearers",
            visibility=VisibilityChoices.RESTRICTED,
            data_partner=self.data_partner,
        )
        # Add the restricted users
        self.restricted_dataset.viewers.add(self.restricted_user)
        # Add datasets to the project
        self.project.datasets.add(self.restricted_dataset, self.public_dataset)

        # Set up request
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/paths/of/the/dead")

        # Generic test view, specific view class not required
        self.view = GenericAPIView.as_view()

        # The permission class
        self.permission = CanView()

    def test_non_project_member_cannot_view(self):
        self.request.user = self.user_without_perm
        # Assert the user not on the project doesn't have permission to see the view
        self.assertFalse(
            self.permission.has_object_permission(
                self.request, self.view, self.restricted_dataset
            )
        )

        # Assert the user not on the project doesn't have permission to see the view
        self.assertFalse(
            self.permission.has_object_permission(
                self.request, self.view, self.public_dataset
            )
        )

    def test_restricted_viewership(self):
        # Add the user to the request; this is not automatic
        self.request.user = self.restricted_user
        # Assert the restricted has permission to see the view
        self.assertTrue(
            self.permission.has_object_permission(
                self.request, self.view, self.restricted_dataset
            )
        )
        # change the request user to the public user
        self.request.user = self.public_user
        # Assert the public user has no permission to see the view
        self.assertFalse(
            self.permission.has_object_permission(
                self.request, self.view, self.restricted_dataset
            )
        )

    def test_public_viewership(self):
        # Add the user to the request; this is not automatic
        self.request.user = self.restricted_user
        # Assert the restricted has permission to see the view
        self.assertTrue(
            self.permission.has_object_permission(
                self.request, self.view, self.public_dataset
            )
        )
        # change the request user to the public user
        self.request.user = self.public_user
        # Assert the public user has permission to see the view
        self.assertTrue(
            self.permission.has_object_permission(
                self.request, self.view, self.public_dataset
            )
        )

    @mock.patch.dict(os.environ, {"AZ_FUNCTION_USER": "az_functions"}, clear=True)
    def test_az_function_user_perm(self):
        User = get_user_model()
        az_user = User.objects.create(username="az_functions")

        # Add the user to the request; this is not automatic
        self.request.user = az_user
        # Assert az_user has permission on restricted view
        self.assertTrue(
            self.permission.has_object_permission(
                self.request, self.view, self.restricted_dataset
            )
        )
        # Assert az_user has permission on public view
        self.assertTrue(
            self.permission.has_object_permission(
                self.request, self.view, self.public_dataset
            )
        )


class TestCanEdit(TestCase):
    def setUp(self):
        User = get_user_model()
        # Create editor
        self.editor = User.objects.create(username="gandalf", password="thegrey")
        # Give them a token
        Token.objects.create(user=self.editor)

        # Create user who is not an editor
        self.non_editor = User.objects.create(username="aragorn", password="elissar")
        # Give them a token
        Token.objects.create(user=self.non_editor)

        # Create the project
        self.project = Project.objects.create(name="The Fellowship of the Ring")
        # Add the permitted users
        self.project.members.add(self.non_editor, self.editor)

        # Create a Data Partner
        self.data_partner = DataPartner.objects.create(name="Silvan Elves")
        # Create the public dataset
        self.dataset = Dataset.objects.create(
            name="Hobbits of the Fellowship",
            visibility=VisibilityChoices.PUBLIC,
            data_partner=self.data_partner,
        )
        # Add the restricted users
        self.dataset.admins.add(self.editor)
        # Add datasets to the project
        self.project.datasets.add(self.dataset)

        # Add the scan report
        self.scan_report = ScanReport.objects.create(
            dataset="The Rings of Power",
            visibility=VisibilityChoices.RESTRICTED,
            parent_dataset=self.dataset,
        )
        self.scan_report.viewers.add(self.non_editor, self.editor)
        self.scan_report.editors.add(self.editor)

        # Set up request
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/paths/of/the/dead")

        # Generic test view, specific view class not required
        self.view = GenericAPIView.as_view()

        # The permission class
        self.permission = CanEdit()

    def test_only_editor_has_permission(self):
        # Assert editor has permission
        self.request.user = self.editor
        self.assertTrue(
            self.permission.has_object_permission(
                self.request, self.view, self.scan_report
            )
        )
        # Assert non_editor has no permission
        self.request.user = self.non_editor
        self.assertFalse(
            self.permission.has_object_permission(
                self.request, self.view, self.scan_report
            )
        )

    def test_dataset_editor_can_edit_scanreport(self):
        User = get_user_model()
        ds_editor = User.objects.create(username="gimli", password="andmyaxe")
        Token.objects.create(user=ds_editor)

        self.dataset.editors.add(ds_editor)
        self.project.members.add(ds_editor)

        self.request.user = ds_editor

        # Assert ds_editor can edit
        self.assertTrue(
            self.permission.has_object_permission(
                self.request, self.view, self.scan_report
            )
        )

    @mock.patch.dict(os.environ, {"AZ_FUNCTION_USER": "az_functions"}, clear=True)
    def test_az_function_user_perm(self):
        User = get_user_model()
        az_user = User.objects.create(username="az_functions")

        # Add the user to the request; this is not automatic
        self.request.user = az_user

        # Assert az_user has permission on restricted view
        self.assertTrue(
            self.permission.has_object_permission(
                self.request, self.view, self.scan_report
            )
        )


class TestCanAdmin(TestCase):
    def setUp(self):
        User = get_user_model()
        # Create editor
        self.admin = User.objects.create(username="gandalf", password="thegrey")
        # Give them a token
        Token.objects.create(user=self.admin)

        # Create user who is not an editor
        self.non_admin = User.objects.create(username="aragorn", password="elissar")
        # Give them a token
        Token.objects.create(user=self.non_admin)

        # Create the project
        self.project = Project.objects.create(name="The Fellowship of the Ring")
        # Add the permitted users
        self.project.members.add(self.non_admin, self.admin)
        # Create a Data Partner
        self.data_partner = DataPartner.objects.create(name="Silvan Elves")
        # Create the public dataset
        self.dataset = Dataset.objects.create(
            name="Hobbits of the Fellowship",
            visibility=VisibilityChoices.PUBLIC,
            data_partner=self.data_partner,
        )
        # Add the restricted users
        self.dataset.admins.add(self.admin)
        # Add datasets to the project
        self.project.datasets.add(self.dataset)

        # Add the scan report
        self.scan_report = ScanReport.objects.create(
            dataset="The Rings of Power",
            visibility=VisibilityChoices.RESTRICTED,
            parent_dataset=self.dataset,
        )
        self.scan_report.viewers.add(self.non_admin, self.admin)

        # Set up request
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/paths/of/the/dead")

        # Generic test view, specific view class not required
        self.view = GenericAPIView.as_view()

        # The permission class
        self.permission = CanAdmin()

    def test_only_admin_has_permission(self):
        # Assert editor has permission
        self.request.user = self.admin
        self.assertTrue(
            self.permission.has_object_permission(
                self.request, self.view, self.scan_report
            )
        )
        # Assert non_editor has no permission
        self.request.user = self.non_admin
        self.assertFalse(
            self.permission.has_object_permission(
                self.request, self.view, self.scan_report
            )
        )

    def test_author_can_admin_scanreport(self):
        User = get_user_model()
        author = User.objects.create(username="gimli", password="andmyaxe")
        Token.objects.create(user=author)

        self.project.members.add(author)

        sr = ScanReport.objects.create(
            dataset="The Rings of Power",
            visibility=VisibilityChoices.PUBLIC,
            parent_dataset=self.dataset,
            author=author,
        )

        self.request.user = author

        # Assert ds_editor can edit
        self.assertTrue(
            self.permission.has_object_permission(self.request, self.view, sr)
        )

    @mock.patch.dict(os.environ, {"AZ_FUNCTION_USER": "az_functions"}, clear=True)
    def test_az_function_user_perm(self):
        User = get_user_model()
        az_user = User.objects.create(username="az_functions")

        # Add the user to the request; this is not automatic
        self.request.user = az_user

        # Assert az_user has permission on restricted view
        self.assertTrue(
            self.permission.has_object_permission(
                self.request, self.view, self.scan_report
            )
        )
