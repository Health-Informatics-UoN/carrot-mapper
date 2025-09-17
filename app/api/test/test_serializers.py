from api.serializers import (
    MappingRecommendationSerializerV3,
    ScanReportEditSerializer,
    ScanReportValueViewSerializerV3,
)
from data.models import Concept
from datasets.serializers import DatasetEditSerializer
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from mapping.models import (
    DataPartner,
    Dataset,
    MappingRecommendation,
    Project,
    ScanReport,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
    VisibilityChoices,
)
from rest_framework.serializers import ValidationError
from rest_framework.test import APIRequestFactory


class TestScanReportEditSerializer(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create(
            username="gandalf", password="onfwojeijfe"
        )
        self.author_user = User.objects.create(
            username="frodo", password="owdjqwojdowjjwf"
        )
        self.non_viewer_user = User.objects.create(
            username="saruman", password="pjwjfefjefew"
        )
        self.viewer_user = User.objects.create(
            username="thewatcher", password="oidoijewfoj"
        )
        self.editor_user = User.objects.create(username="sauron", password="oijfowfjef")
        self.project = Project.objects.create(name="The Fellowship of The Ring")
        self.project.members.add(
            self.admin_user,
            self.author_user,
            self.non_viewer_user,
            self.viewer_user,
            self.editor_user,
        )
        self.data_partner = DataPartner.objects.create(name="Silvan Elves")
        self.public_dataset = Dataset.objects.create(
            name="Places in Middle Earth",
            visibility=VisibilityChoices.PUBLIC,
            data_partner=self.data_partner,
        )
        self.restricted_dataset = Dataset.objects.create(
            name="Forbidden Places in Middle Earth",
            visibility=VisibilityChoices.RESTRICTED,
            data_partner=self.data_partner,
        )
        self.public_dataset.admins.add(self.admin_user)
        self.project.datasets.add(self.public_dataset, self.restricted_dataset)
        self.public_scanreport = ScanReport.objects.create(
            dataset="The Shire",
            visibility=VisibilityChoices.PUBLIC,
            parent_dataset=self.public_dataset,
            author=self.author_user,
        )
        self.restricted_scanreport = ScanReport.objects.create(
            dataset="Cirith Ungol",
            visibility=VisibilityChoices.RESTRICTED,
            parent_dataset=self.restricted_dataset,
            author=self.author_user,
        )

    def test_validate_editors(self):
        User = get_user_model()
        new_editor = User.objects.create(username="samwise", password="ejojwejfefe")
        request = APIRequestFactory().patch(
            "/the/path/to/isengard", data={"editors": [new_editor]}
        )
        serializer = ScanReportEditSerializer(
            self.public_scanreport,
            data={"editors": [new_editor]},
            context={"request": request},
        )
        # check non admin can't alter editors
        request.user = self.non_viewer_user
        self.assertRaises(
            ValidationError, serializer.validate_editors, editors=[new_editor]
        )

        # check viewer can't alter editors on restricted SRs
        request.user = self.viewer_user
        self.restricted_dataset.viewers.add(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_editors, editors=[new_editor]
        )
        self.restricted_dataset.viewers.remove(self.viewer_user)
        self.restricted_scanreport.viewers.add(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_editors, editors=[new_editor]
        )

        # check editor can't alter editors on restricted SRs
        request.user = self.editor_user
        self.restricted_dataset.viewers.add(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_editors, editors=[new_editor]
        )
        self.restricted_dataset.viewers.remove(self.editor_user)
        self.restricted_scanreport.viewers.add(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_editors, editors=[new_editor]
        )

        # check author can alter editors
        request.user = self.author_user
        self.assertListEqual(serializer.validate_editors([new_editor]), [new_editor])

        # check admin can alter editors
        request.user = self.admin_user
        self.assertListEqual(serializer.validate_editors([new_editor]), [new_editor])

    def test_validate_viewers(self):
        User = get_user_model()
        new_viewer = User.objects.create(username="samwise", password="ejojwejfefe")
        request = APIRequestFactory().patch(
            "/the/path/to/isengard", data={"viewers": [new_viewer]}
        )
        serializer = ScanReportEditSerializer(
            self.public_scanreport,
            data={"viewers": [new_viewer]},
            context={"request": request},
        )
        # check non admin can't alter viewers
        request.user = self.non_viewer_user
        self.assertRaises(
            ValidationError, serializer.validate_viewers, viewers=[new_viewer]
        )

        # check viewer can't alter viewers on restricted SRs
        request.user = self.viewer_user
        self.restricted_dataset.viewers.add(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_viewers, viewers=[new_viewer]
        )
        self.restricted_dataset.viewers.remove(self.viewer_user)
        self.restricted_scanreport.viewers.add(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_viewers, viewers=[new_viewer]
        )

        # check editor can't alter viewers on restricted SRs
        request.user = self.editor_user
        self.restricted_dataset.viewers.add(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_viewers, viewers=[new_viewer]
        )
        self.restricted_dataset.viewers.remove(self.editor_user)
        self.restricted_scanreport.viewers.add(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_viewers, viewers=[new_viewer]
        )

        # check author can alter viewers
        request.user = self.author_user
        self.assertListEqual(serializer.validate_viewers([new_viewer]), [new_viewer])

        # check admin can alter viewers
        request.user = self.admin_user
        self.assertListEqual(serializer.validate_viewers([new_viewer]), [new_viewer])

    def test_validate_author(self):
        User = get_user_model()
        new_author = User.objects.create(username="samwise", password="ejojwejfefe")
        request = APIRequestFactory().patch(
            "/the/path/to/isengard", data={"author": new_author}
        )
        serializer = ScanReportEditSerializer(
            self.public_scanreport,
            data={"author": new_author},
            context={"request": request},
        )

        # check non admin can't alter author
        request.user = self.non_viewer_user
        self.assertRaises(
            ValidationError, serializer.validate_author, author=new_author
        )

        # check viewer can't alter author on restricted SRs
        request.user = self.viewer_user
        self.restricted_dataset.viewers.add(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_author, author=new_author
        )
        self.restricted_dataset.viewers.remove(self.viewer_user)
        self.restricted_scanreport.viewers.add(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_author, author=new_author
        )

        # check editor can't alter author on restricted SRs
        request.user = self.editor_user
        self.restricted_dataset.viewers.add(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_author, author=new_author
        )
        self.restricted_dataset.viewers.remove(self.editor_user)
        self.restricted_scanreport.viewers.add(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_author, author=new_author
        )

        # check author can alter author
        request.user = self.author_user
        self.assertEqual(serializer.validate_author(new_author), new_author)

        # check admin can alter author
        request.user = self.admin_user
        self.assertEqual(serializer.validate_author(new_author), new_author)


class TestDatasetEditSerializer(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create(
            username="gandalf", password="onfwojeijfe"
        )
        self.non_viewer_user = User.objects.create(
            username="saruman", password="pjwjfefjefew"
        )
        self.viewer_user = User.objects.create(
            username="thewatcher", password="oidoijewfoj"
        )
        self.editor_user = User.objects.create(username="sauron", password="oijfowfjef")
        self.project = Project.objects.create(name="The Fellowship of The Ring")
        self.project.members.add(
            self.admin_user,
            self.non_viewer_user,
            self.viewer_user,
            self.editor_user,
        )
        self.data_partner = DataPartner.objects.create(name="Silvan Elves")
        self.dataset = Dataset.objects.create(
            name="Forbidden Places in Middle Earth",
            visibility=VisibilityChoices.RESTRICTED,
            data_partner=self.data_partner,
        )
        self.dataset.admins.add(self.admin_user)
        self.project.datasets.add(self.dataset)

    def test_validate_editors(self):
        User = get_user_model()
        new_editor = User.objects.create(username="samwise", password="ejojwejfefe")
        request = APIRequestFactory().patch(
            "/the/path/to/isengard", data={"editors": [new_editor]}
        )
        serializer = DatasetEditSerializer(
            self.dataset,
            data={"editors": [new_editor]},
            context={"request": request},
        )
        # check non admin can't alter editors
        request.user = self.non_viewer_user
        self.assertRaises(
            ValidationError, serializer.validate_editors, editors=[new_editor]
        )

        # check viewer can't alter editors on restricted SRs
        request.user = self.viewer_user
        self.dataset.viewers.add(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_editors, editors=[new_editor]
        )
        self.dataset.viewers.remove(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_editors, editors=[new_editor]
        )

        # check editor can't alter editors on restricted SRs
        request.user = self.editor_user
        self.dataset.viewers.add(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_editors, editors=[new_editor]
        )
        self.dataset.viewers.remove(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_editors, editors=[new_editor]
        )

        # check admin can alter editors
        request.user = self.admin_user
        self.assertListEqual(serializer.validate_editors([new_editor]), [new_editor])

    def test_validate_viewers(self):
        User = get_user_model()
        new_viewer = User.objects.create(username="samwise", password="ejojwejfefe")
        request = APIRequestFactory().patch(
            "/the/path/to/isengard", data={"viewers": [new_viewer]}
        )
        serializer = DatasetEditSerializer(
            self.dataset,
            data={"viewers": [new_viewer]},
            context={"request": request},
        )
        # check non admin can't alter viewers
        request.user = self.non_viewer_user
        self.assertRaises(
            ValidationError, serializer.validate_viewers, viewers=[new_viewer]
        )

        # check viewer can't alter viewers on restricted SRs
        request.user = self.viewer_user
        self.dataset.viewers.add(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_viewers, viewers=[new_viewer]
        )
        self.dataset.viewers.remove(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_viewers, viewers=[new_viewer]
        )

        # check editor can't alter viewers on restricted SRs
        request.user = self.editor_user
        self.dataset.viewers.add(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_viewers, viewers=[new_viewer]
        )
        self.dataset.viewers.remove(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_viewers, viewers=[new_viewer]
        )

        # check admin can alter viewers
        request.user = self.admin_user
        self.assertListEqual(serializer.validate_viewers([new_viewer]), [new_viewer])

    def test_validate_admin(self):
        User = get_user_model()
        new_admin = User.objects.create(username="samwise", password="ejojwejfefe")
        request = APIRequestFactory().patch(
            "/the/path/to/isengard", data={"admin": new_admin}
        )
        serializer = DatasetEditSerializer(
            self.dataset,
            data={"admin": new_admin},
            context={"request": request},
        )

        # check non admin can't alter author
        request.user = self.non_viewer_user
        self.assertRaises(
            ValidationError, serializer.validate_admins, admins=[new_admin]
        )

        # check viewer can't alter author on restricted SRs
        request.user = self.viewer_user
        self.dataset.viewers.add(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_admins, admins=[new_admin]
        )
        self.dataset.viewers.remove(self.viewer_user)
        self.assertRaises(
            ValidationError, serializer.validate_admins, admins=[new_admin]
        )

        # check editor can't alter admins on restricted SRs
        request.user = self.editor_user
        self.dataset.viewers.add(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_admins, admins=[new_admin]
        )
        self.dataset.viewers.remove(self.editor_user)
        self.assertRaises(
            ValidationError, serializer.validate_admins, admins=[new_admin]
        )

        # check admin can alter admins
        request.user = self.admin_user
        self.assertEqual(serializer.validate_admins(new_admin), new_admin)


class TestMappingRecommendationSerializerV3(TestCase):
    def setUp(self):
        # Create test data
        self.scan_report = ScanReport.objects.create(
            dataset="Test Dataset",
            visibility="PUBLIC",
        )

        self.table = ScanReportTable.objects.create(
            scan_report=self.scan_report,
            name="Test Table",
        )

        self.field = ScanReportField.objects.create(
            scan_report_table=self.table,
            name="Test Field",
            description_column="Test Description",
            type_column="string",
        )

        self.value = ScanReportValue.objects.create(
            scan_report_field=self.field,
            value="test_value",
            frequency=5,
        )

        # Create a concept for the recommendation
        self.concept = Concept.objects.create(
            concept_id=12345,
            concept_name="Test Concept",
            concept_code="TEST123",
            domain_id="Test",
            vocabulary_id="Test",
            concept_class_id="Test",
            standard_concept="S",
            valid_start_date="2020-01-01",
            valid_end_date="2099-12-31",
        )

        # Create a mapping recommendation
        content_type = ContentType.objects.get_for_model(ScanReportValue)
        self.recommendation = MappingRecommendation.objects.create(
            content_type=content_type,
            object_id=self.value.id,
            concept=self.concept,
            score=0.85,
            tool_name="test-tool",
            tool_version="1.0.0",
        )

    def test_mapping_recommendation_serializer(self):
        """Test that MappingRecommendationSerializerV3 serializes correctly."""
        serializer = MappingRecommendationSerializerV3(self.recommendation)
        data = serializer.data

        self.assertEqual(data["id"], self.recommendation.id)
        self.assertEqual(data["score"], 0.85)
        self.assertEqual(data["tool_name"], "test-tool")
        self.assertEqual(data["tool_version"], "1.0.0")
        self.assertEqual(data["concept"]["concept_id"], self.concept.concept_id)
        self.assertEqual(data["concept"]["concept_name"], self.concept.concept_name)

    def test_scan_report_value_v3_serializer_includes_recommendations(self):
        """Test that ScanReportValueViewSerializerV3 includes mapping recommendations."""
        serializer = ScanReportValueViewSerializerV3(self.value)
        data = serializer.data

        # Check that mapping recommendations are included
        self.assertIn("mapping_recommendations", data)
        self.assertEqual(len(data["mapping_recommendations"]), 1)

        recommendation_data = data["mapping_recommendations"][0]
        self.assertEqual(recommendation_data["id"], self.recommendation.id)
        self.assertEqual(recommendation_data["score"], 0.85)
        self.assertEqual(recommendation_data["tool_name"], "test-tool")
        self.assertEqual(recommendation_data["tool_version"], "1.0.0")
        self.assertEqual(
            recommendation_data["concept"]["concept_id"], self.concept.concept_id
        )
        self.assertEqual(
            recommendation_data["concept"]["concept_name"], self.concept.concept_name
        )
