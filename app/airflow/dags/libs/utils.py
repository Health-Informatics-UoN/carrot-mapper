import logging
import ast
import json

# Set up logger
logger = logging.getLogger(__name__)


# TODO: more error handling and comments for this function
def extract_params(**kwargs):
    """Extract and validate parameters from DAG run configuration"""
    table_id = kwargs["dag_run"].conf.get("table_id")

    field_vocab_pairs = kwargs["dag_run"].conf.get("field_vocab_pairs")

    # Check if field_vocab_pairs is a string and try to parse it as JSON
    if isinstance(field_vocab_pairs, str):
        try:
            field_vocab_pairs = ast.literal_eval(field_vocab_pairs)
            print("Parsed field_vocab_pairs from string: ", field_vocab_pairs)
        except json.JSONDecodeError:
            print("Failed to parse field_vocab_pairs as JSON")

    if not table_id or not field_vocab_pairs or not isinstance(field_vocab_pairs, list):
        raise ValueError(
            f"Invalid parameters: requires table_id and field_vocab_pairs (as list). Got table_id={table_id}, field_vocab_pairs={field_vocab_pairs} of type {type(field_vocab_pairs)}"
        )
    return table_id, field_vocab_pairs
