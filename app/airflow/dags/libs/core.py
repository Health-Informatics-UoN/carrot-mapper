import logging
from typing import Dict, Any, Optional
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.exceptions import AirflowException
import psycopg2

# Set up logger
logger = logging.getLogger(__name__)

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="1-conn-db")


def test_add_scan_report_values(
    concept_id: Optional[int] = None, **kwargs
) -> Dict[str, Any]:
    """
    Test function that inserts a scan report concept.

    Args:
        concept_id: The concept ID to use, passed from the DAG run configuration
        **kwargs: Additional arguments from Airflow

    Returns:
        Dict with status information about the operation
    """
    logger.info(f"Starting test_add_scan_report_values with concept_id: {concept_id}")

    # If concept_id wasn't provided directly, try to get it from dag_run.conf
    if concept_id is None:
        # Check if we have it in dag_run.conf (passed by template)
        dag_run = kwargs.get("dag_run")
        if dag_run and hasattr(dag_run, "conf"):
            concept_id = dag_run.conf.get("concept_id")
            logger.info(f"Got concept_id {concept_id} from dag_run.conf")

    # Use default if still None
    #  TODO: remove or improve this
    if concept_id is None:
        concept_id = 8507  # Default value
        logger.info(f"Using default concept_id: {concept_id}")

    try:
        # Use proper SQL syntax with quotes around string values
        # Use the passed concept_id in the query
        update_query = f"""
        INSERT INTO mapping_scanreportconcept (created_at, updated_at, object_id, creation_type, concept_id, content_type_id)
        VALUES (
            NOW(),
            NOW(),
            72766,
            'V',
            {concept_id},
            23
        )
        """

        # Execute the query
        pg_hook.run(update_query)

        logger.info(
            f"Successfully inserted scan report concept with concept_id: {concept_id}"
        )
        return {
            "status": "success",
            "message": f"Successfully inserted scan report concept with concept_id: {concept_id}",
            "concept_id": concept_id,
        }

    except psycopg2.errors.UndefinedColumn as e:
        error_msg = f"SQL syntax error: {str(e)}"
        logger.error(error_msg)
        raise AirflowException(error_msg) from e

    except psycopg2.Error as e:
        error_msg = f"Database error: {str(e)}"
        logger.error(error_msg)
        raise AirflowException(error_msg) from e

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        raise AirflowException(error_msg) from e
