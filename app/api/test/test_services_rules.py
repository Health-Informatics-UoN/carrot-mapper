from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.authtoken.models import Token
from shared.data.models import Concept
from shared.mapping.models import (
    DataPartner,
    Dataset,
    MappingRule,
    OmopField,
    OmopTable,
    Project,
    ScanReport,
    ScanReportConcept,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
)


class TestMisalignedMappings(TestCase):
    def setUp(self):
        # Create User
        User = get_user_model()
        self.user1 = User.objects.create(username="oliver", password="uhafcvbsyrgf")
        # Generate Token for the user
        Token.objects.create(user=self.user1)
        # Create Dataset
        self.data_partner = DataPartner.objects.create(name="Data Partner")
        self.dataset1 = Dataset.objects.create(
            name="Dataset", visibility="PUBLIC", data_partner=self.data_partner
        )
        # Create Project
        self.project1 = Project.objects.create(name="Project")
        # Add user to project
        self.project1.members.add(self.user1)
        # Add dataset to project
        self.project1.datasets.add(
            self.dataset1,
        )
        # Create Scan Report
        self.scan_report1 = ScanReport.objects.create(
            author=self.user1,
            name="Scan Report",
            dataset="Dataset Name",
            parent_dataset=self.dataset1,
        )
        self.scan_report2 = ScanReport.objects.create(
            author=self.user1,
            name="Scan Report 2",
            dataset="Dataset Name 2",
            parent_dataset=self.dataset1,
        )
        # Allow user to view scan reports
        self.scan_report1.viewers.add(self.user1)
        self.scan_report2.viewers.add(self.user1)
        # Create Scan Report Tables
        self.scan_report_table = ScanReportTable.objects.create(
            scan_report=self.scan_report1, name="Table 1"
        )
        self.scan_report_table_2 = ScanReportTable.objects.create(
            scan_report=self.scan_report2, name="Table 2"
        )
        # Create Scan Report ID fields
        self.scan_report_field_ID = ScanReportField.objects.create(
            scan_report_table=self.scan_report_table,
            name="ID",
            description_column="",
            type_column="INT",
            max_length=10,
            nrows=-1,
            nrows_checked=557,
            fraction_empty=0.0,
            nunique_values=55,
            fraction_unique=100,
            ignore_column=None,
        )
        self.scan_report_field_ID2 = ScanReportField.objects.create(
            scan_report_table=self.scan_report_table_2,
            name="ID",
            description_column="",
            type_column="INT",
            max_length=10,
            nrows=-1,
            nrows_checked=557,
            fraction_empty=0.0,
            nunique_values=55,
            fraction_unique=100,
            ignore_column=None,
        )
        # Create Date fields
        self.scan_report_field_date = ScanReportField.objects.create(
            scan_report_table=self.scan_report_table,
            name="Date",
            description_column="",
            type_column="VARCHAR",
            max_length=10,
            nrows=-1,
            nrows_checked=557,
            fraction_empty=0.0,
            nunique_values=21,
            fraction_unique=3.8,
            ignore_column=None,
        )
        self.scan_report_field_date2 = ScanReportField.objects.create(
            scan_report_table=self.scan_report_table_2,
            name="Date",
            description_column="",
            type_column="VARCHAR",
            max_length=10,
            nrows=-1,
            nrows_checked=557,
            fraction_empty=0.0,
            nunique_values=21,
            fraction_unique=3.8,
            ignore_column=None,
        )
        # Create Productive Cough field
        self.scan_report_field_prod_cough = ScanReportField.objects.create(
            scan_report_table=self.scan_report_table,
            name="Productive Cough",
            description_column="",
            type_column="VARCHAR",
            max_length=4,
            nrows=-1,
            nrows_checked=557,
            fraction_empty=0.0,
            nunique_values=3,
            fraction_unique=0.5,
            ignore_column=None,
        )
        # Create Cough field
        self.scan_report_field_cough = ScanReportField.objects.create(
            scan_report_table=self.scan_report_table_2,
            name="Cough",
            description_column="",
            type_column="VARCHAR",
            max_length=4,
            nrows=-1,
            nrows_checked=557,
            fraction_empty=0.0,
            nunique_values=3,
            fraction_unique=0.5,
            ignore_column=None,
        )
        # Create Productive cough -clear sputum field
        self.scan_report_field_desc = ScanReportField.objects.create(
            scan_report_table=self.scan_report_table_2,
            name="Productive cough -clear sputum",
            description_column="",
            type_column="VARCHAR",
            max_length=4,
            nrows=-1,
            nrows_checked=557,
            fraction_empty=0.0,
            nunique_values=3,
            fraction_unique=0.5,
            ignore_column=None,
        )

        # Create Cough field values, Y & N
        self.scan_report_value_Y = ScanReportValue.objects.create(
            value="Y",
            frequency=34,
            value_description="",
            scan_report_field=self.scan_report_field_prod_cough,
        )
        self.scan_report_value_N = ScanReportValue.objects.create(
            value="N",
            frequency=25,
            value_description="",
            scan_report_field=self.scan_report_field_prod_cough,
        )
        # Create Ancestor and Descendant values, Y & N
        self.scan_report_value_Y2 = ScanReportValue.objects.create(
            value="Y",
            frequency=34,
            value_description="",
            scan_report_field=self.scan_report_field_cough,
        )
        self.scan_report_value_N2 = ScanReportValue.objects.create(
            value="N",
            frequency=25,
            value_description="",
            scan_report_field=self.scan_report_field_cough,
        )

        self.scan_report_value_Y3 = ScanReportValue.objects.create(
            value="Y",
            frequency=34,
            value_description="",
            scan_report_field=self.scan_report_field_desc,
        )
        self.scan_report_value_N3 = ScanReportValue.objects.create(
            value="N",
            frequency=25,
            value_description="",
            scan_report_field=self.scan_report_field_desc,
        )
        # Set table person_id and date_event to create mapping rules
        self.scan_report_table.person_id = self.scan_report_field_ID
        self.scan_report_table.date_event = self.scan_report_field_date

        self.scan_report_table_2.person_id = self.scan_report_field_ID2
        self.scan_report_table_2.date_event = self.scan_report_field_date2

        self.omop_table1 = OmopTable.objects.create(table="condition")
        self.omop_field1 = OmopField.objects.create(
            table=self.omop_table1, field="condition_concept_id"
        )
        # Get "Productive Cough" Concept ID
        self.concept_prod_cough = Concept.objects.get(concept_id=4102774)
        # Get Productive Cough ancestor, "Cough" Concept ID
        self.concept_cough = Concept.objects.get(concept_id=254761)
        # Get Productive Cough descendant, "Productive cough -clear sputum" Concept ID
        self.concept_cough_desc = Concept.objects.get(concept_id=4060224)

        # Get the Content Type
        self.content_type = ContentType.objects.get(
            app_label="mapping", model="scanreportvalue"
        )
        # Mapping Rule for Scan Report 1, "Productive Cough"
        self.scan_report_concept_prod_cough = ScanReportConcept.objects.create(
            concept=self.concept_prod_cough,
            content_type=self.content_type,
            object_id=self.scan_report_value_Y.id,
            creation_type="M",
        )
        self.mapping_rule1 = MappingRule.objects.create(
            scan_report=self.scan_report1,
            omop_field=self.omop_field1,
            source_table=self.scan_report_table,
            source_field=self.scan_report_field_prod_cough,
            concept=self.scan_report_concept_prod_cough,
        )

        # Mapping Rules for Scan Report 2, "Cough", "Productive cough -clear sputum"
        self.scan_report_concept_cough = ScanReportConcept.objects.create(
            concept=self.concept_cough,
            content_type=self.content_type,
            object_id=self.scan_report_value_Y2.id,
            creation_type="M",
        )
        self.mapping_rule2 = MappingRule.objects.create(
            scan_report=self.scan_report2,
            omop_field=self.omop_field1,
            source_table=self.scan_report_table_2,
            source_field=self.scan_report_field_cough,
            concept=self.scan_report_concept_cough,
        )

        self.scan_report_concept_cough_desc = ScanReportConcept.objects.create(
            concept=self.concept_cough_desc,
            content_type=self.content_type,
            object_id=self.scan_report_value_Y3.id,
            creation_type="M",
        )
        self.mapping_rule1 = MappingRule.objects.create(
            scan_report=self.scan_report2,
            omop_field=self.omop_field1,
            source_table=self.scan_report_table_2,
            source_field=self.scan_report_field_desc,
            concept=self.scan_report_concept_cough_desc,
        )
