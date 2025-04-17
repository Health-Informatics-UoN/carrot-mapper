# TODO: we may use this when we have the source_concept_id in the model SCANREPORTCONCEPT
def create_source_concept_rules(**kwargs):
    """
    Create mapping rules in the mapping_mappingrule table for source concept fields.
    Uses source_concept_id instead of standard_concept_id for the concept mapping.
    """
    try:
        table_id, field_vocab_pairs = extract_params(**kwargs)
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")

        if not field_vocab_pairs:
            logging.error("No field-vocabulary pairs provided")
            raise ValueError("No field-vocabulary pairs provided")

        for pair in field_vocab_pairs:
            sr_field_id = pair.get("sr_field_id")

            if not scan_report_id:
                logging.warning(
                    "No scan_report_id provided in create_source_concept_rules"
                )
                raise AirflowException(
                    "scan_report_id is required for creating mapping rules"
                )

            if not sr_field_id:
                logging.warning(
                    "No sr_field_id provided in create_source_concept_rules"
                )
                raise AirflowException(
                    "sr_field_id is required for creating mapping rules"
                )

            # Create mapping rules for source concept fields using source_concept_id
            source_concept_query = f"""
            INSERT INTO temp_mapping_rules (
                created_at, updated_at, omop_field_id, source_field_id, concept_id, scan_report_id, approved
            )
            SELECT
                NOW(), NOW(), tsc.source_concept_field_id, {sr_field_id}, src.id, {scan_report_id}, TRUE
            FROM temp_standard_concepts tsc
            -- TODO: when we have the source_concept_id in the model SCANREPORTCONCEPT, we have to use it here instead of standard_concept_id
            JOIN mapping_scanreportconcept src ON 
                src.object_id = tsc.sr_value_id AND
                src.source_concept_id = tsc.source_concept_id AND  -- Using source_concept_id here instead of standard_concept_id
                src.content_type_id = 23
            WHERE tsc.source_concept_field_id IS NOT NULL
            AND NOT EXISTS (
                -- Check if the mapping rule already exists
                SELECT 1 FROM mapping_mappingrule mr
                WHERE mr.omop_field_id = tsc.source_concept_field_id
                AND mr.source_field_id = {sr_field_id}
                AND mr.concept_id = src.id
                AND mr.scan_report_id = {scan_report_id}
            );
            """

            try:
                result = pg_hook.run(source_concept_query)
                logging.info(
                    "Successfully created mapping rules for source concept fields"
                )
                return result
            except Exception as e:
                logging.error(
                    f"Database error in create_source_concept_rules: {str(e)}"
                )
                raise AirflowException(
                    f"Database error in create_source_concept_rules: {str(e)}"
                )

    except Exception as e:
        logging.error(f"Error in create_source_concept_rules: {str(e)}")
        raise AirflowException(f"Error in create_source_concept_rules: {str(e)}")
