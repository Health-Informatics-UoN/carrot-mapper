import logging
from datetime import datetime
from airflow.exceptions import AirflowFailException
from sqlalchemy import (
    cast,
    String,
    between,
)
from sqlalchemy.sql.schema import Column, Table
from typing import Any, Dict, List


def cast_value(column: Column, value: Any):
    """Helper function to cast values based on column type"""
    # Get the type in Python of the column in the DB
    python_type = column.type.python_type
    # Checking mismatch
    if not isinstance(value, python_type):
        logging.warning(
            f"There is a type mismatch between column type declared in DB (column: {column.name} - type: {python_type.__name__}) and value type (value: {value} - type: {type(value).__name__}) in JSON config. Trying to cast the value..."
        )
    try:
        if python_type is str:
            return str(value)
        elif python_type is int:
            return int(value)
        elif python_type is float:
            return float(value)
        elif python_type is bool:
            return bool(value)
        elif python_type is datetime.date:
            return datetime(value)
        # TODO: do we need to handle datetime ("%Y-%m-%d %H:%M:%S") cast as well?
        logging.info("Casting successfully!")
        return value
    except Exception as e:
        logging.error(f"Error casting value for column {column.name}: {e}")
        raise AirflowFailException(f"Error casting value for column {column.name}: {e}")


def handle_between_condition(column: Column, value: List[Any]) -> Any:
    """Handle BETWEEN condition"""
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("BETWEEN operator requires a list of [start, end] values")
    start_value = cast_value(column, value[0])
    end_value = cast_value(column, value[1])
    return between(column, start_value, end_value)


def building_conditions(table: Table, conditions: List[Dict[str, Any]]) -> List[Any]:
    """Build conditions using SQLAlchemy"""
    operator_map = {
        "=": lambda col, val: col == val,
        "!=": lambda col, val: col != val,
        ">": lambda col, val: col > val,
        "<": lambda col, val: col < val,
        ">=": lambda col, val: col >= val,
        "<=": lambda col, val: col <= val,
        "like": lambda col, val: cast(col, String).like(val),
    }

    built_conditions = []
    for col in conditions:
        # Get the column as SQL structure, value and the operator for each condition
        column: Column = getattr(table.c, col["column_name"])
        operator = col["operator"].strip().lower()
        value = col["value"]

        if operator == "between":
            built_conditions.append(handle_between_condition(column, value))
        elif operator in operator_map:
            casted_value = cast_value(column, value)
            built_conditions.append(operator_map[operator](column, casted_value))
        else:
            raise ValueError(f"Unsupported operator: {operator}")

    return built_conditions


def process_headers(raw_headers):
    """Process the tables' headers pulled from XCom"""
    try:
        headers_list = []
        for i, headers in enumerate(raw_headers):
            flat_headers = [row[0] for row in headers]
            headers_list.append(flat_headers)

        return headers_list

    except Exception as e:
        logging.error(f"Error processing table headers: {e}")
        raise AirflowFailException(f"Task failed due to: {e}")


def save_sql(file_name: str, query):
    path = f"/opt/airflow/dags/sql/{file_name}"
    with open(path, "w") as f:
        f.write(str(query))
    logging.info(f"SQL query saved to {path}")
