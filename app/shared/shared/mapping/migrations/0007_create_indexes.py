from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "mapping",
            "0006_scanreporttable_trigger_reuse",
        ),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Core value and field indexes for concept reuse queries
            CREATE INDEX IF NOT EXISTS idx_scanreportvalue_value ON mapping_scanreportvalue(value);
            CREATE INDEX IF NOT EXISTS idx_scanreportvalue_value_description ON mapping_scanreportvalue(value_description);
            CREATE INDEX IF NOT EXISTS idx_scanreportfield_name ON mapping_scanreportfield(name);
            CREATE INDEX IF NOT EXISTS idx_scanreporttable_name ON mapping_scanreporttable(name);
            
            -- Concept creation type filtering
            CREATE INDEX IF NOT EXISTS idx_scanreportconcept_creation_type ON mapping_scanreportconcept(creation_type);
            
            -- Composite indexes for complex queries
            CREATE INDEX IF NOT EXISTS idx_scanreportvalue_field_value ON mapping_scanreportvalue(scan_report_field_id, value);
            CREATE INDEX IF NOT EXISTS idx_scanreportconcept_object_content_type ON mapping_scanreportconcept(object_id, content_type_id);
            CREATE INDEX IF NOT EXISTS idx_scanreportconcept_object_content_concept ON mapping_scanreportconcept(object_id, content_type_id, concept_id);
            CREATE INDEX IF NOT EXISTS idx_scanreportconcept_creation_content_type ON mapping_scanreportconcept(creation_type, content_type_id);
            
            -- Scan report hierarchy indexes
            CREATE INDEX IF NOT EXISTS idx_scanreporttable_scanreport_id ON mapping_scanreporttable(scan_report_id);
            CREATE INDEX IF NOT EXISTS idx_scanreportfield_table_id ON mapping_scanreportfield(scan_report_table_id);
            CREATE INDEX IF NOT EXISTS idx_scanreportvalue_field_id ON mapping_scanreportvalue(scan_report_field_id);
            
            -- Dataset and scan report filtering
            CREATE INDEX IF NOT EXISTS idx_scanreport_dataset_hidden ON mapping_scanreport(parent_dataset_id, hidden);
            CREATE INDEX IF NOT EXISTS idx_scanreport_dataset_status ON mapping_scanreport(parent_dataset_id, hidden, mapping_status_id);
            CREATE INDEX IF NOT EXISTS idx_dataset_hidden ON mapping_dataset(hidden);
            CREATE INDEX IF NOT EXISTS idx_mappingstatus_value ON mapping_mappingstatus(value);
            
            -- OMOP field and table mapping
            CREATE INDEX IF NOT EXISTS idx_omopfield_table_field ON mapping_omopfield(table_id, field);
            CREATE INDEX IF NOT EXISTS idx_omoptable_table_name ON mapping_omoptable("table");
            
            -- Mapping rules export
            CREATE INDEX IF NOT EXISTS idx_mappingrule_scanreport_concept ON mapping_mappingrule(scan_report_id, concept_id);
            CREATE INDEX IF NOT EXISTS idx_mappingrule_omop_source_fields ON mapping_mappingrule(omop_field_id, source_field_id);
            
            -- Content type lookups (used everywhere)
            CREATE INDEX IF NOT EXISTS idx_django_content_type_app_model ON django_content_type(app_label, model);
            """,
            reverse_sql="""
            -- Drop indexes in reverse order
            DROP INDEX IF EXISTS idx_django_content_type_app_model;
            DROP INDEX IF EXISTS idx_mappingrule_omop_source_fields;
            DROP INDEX IF EXISTS idx_mappingrule_scanreport_concept;
            DROP INDEX IF EXISTS idx_omoptable_table_name;
            DROP INDEX IF EXISTS idx_omopfield_table_field;
            DROP INDEX IF EXISTS idx_mappingstatus_value;
            DROP INDEX IF EXISTS idx_dataset_hidden;
            DROP INDEX IF EXISTS idx_scanreport_dataset_status;
            DROP INDEX IF EXISTS idx_scanreport_dataset_hidden;
            DROP INDEX IF EXISTS idx_scanreportvalue_field_id;
            DROP INDEX IF EXISTS idx_scanreportfield_table_id;
            DROP INDEX IF EXISTS idx_scanreporttable_scanreport_id;
            DROP INDEX IF EXISTS idx_scanreportconcept_creation_content_type;
            DROP INDEX IF EXISTS idx_scanreportconcept_object_content_concept;
            DROP INDEX IF EXISTS idx_scanreportconcept_object_content_type;
            DROP INDEX IF EXISTS idx_scanreportvalue_field_value;
            DROP INDEX IF EXISTS idx_scanreportconcept_creation_type;
            DROP INDEX IF EXISTS idx_scanreporttable_name;
            DROP INDEX IF EXISTS idx_scanreportfield_name;
            DROP INDEX IF EXISTS idx_scanreportvalue_value_description;
            DROP INDEX IF EXISTS idx_scanreportvalue_value;
            """,
        ),
        # OMOP SCHEMA concept indexes
        migrations.RunSQL(
            sql="""
            -- OMOP concept indexes
            CREATE INDEX IF NOT EXISTS idx_concept_code_vocabulary ON omop.concept(concept_code, vocabulary_id);
            CREATE INDEX IF NOT EXISTS idx_concept_standard_domain ON omop.concept(standard_concept, domain_id);
            CREATE INDEX IF NOT EXISTS idx_concept_code_vocabulary_standard ON omop.concept(concept_code, vocabulary_id, standard_concept, domain_id);
            
            -- OMOP concept relationship index
            CREATE INDEX IF NOT EXISTS idx_concept_relationship_maps_to ON omop.concept_relationship(concept_id_1, relationship_id) WHERE relationship_id = 'Maps to';
            """,
            reverse_sql="""
            -- Drop OMOP indexes
            DROP INDEX IF EXISTS omop.idx_concept_relationship_maps_to;
            DROP INDEX IF EXISTS omop.idx_concept_code_vocabulary_standard;
            DROP INDEX IF EXISTS omop.idx_concept_standard_domain;
            DROP INDEX IF EXISTS omop.idx_concept_code_vocabulary;
            """,
        ),
    ]
