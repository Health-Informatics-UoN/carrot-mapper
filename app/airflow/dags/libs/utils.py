import logging
import ast
import json

# Set up logger
logger = logging.getLogger(__name__)


# TODO: more error handling and comments for this function
def process_field_vocab_pairs(field_vocab_pairs: str):
    """Extract and validate parameters from DAG run configuration"""

    # Check if field_vocab_pairs is a string and try to parse it as JSON
    if isinstance(field_vocab_pairs, str):
        try:
            field_vocab_pairs = ast.literal_eval(field_vocab_pairs)
            print("Parsed field_vocab_pairs from string: ", field_vocab_pairs)
        except json.JSONDecodeError:
            print("Failed to parse field_vocab_pairs as JSON")

    return field_vocab_pairs


def update_job_status(job_id: int, status: str):
    """Update the status of a job in the database"""
    pass
