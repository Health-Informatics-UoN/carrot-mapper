from django.db import transaction
from mapping.models import (
    ScanReport,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
)


@transaction.atomic
def bulk_create_tables(
    scan_report: ScanReport, tables_data: list[dict]
) -> list[ScanReportTable]:
    tables = [ScanReportTable(scan_report=scan_report, **data) for data in tables_data]
    return ScanReportTable.objects.bulk_create(tables)


@transaction.atomic
def bulk_create_fields(
    table: ScanReportTable, fields_data: list[dict]
) -> list[ScanReportField]:
    fields = [ScanReportField(scan_report_table=table, **data) for data in fields_data]
    return ScanReportField.objects.bulk_create(fields)


@transaction.atomic
def bulk_create_values(
    field: ScanReportField, values_data: list[dict]
) -> list[ScanReportValue]:
    values = [
        ScanReportValue(
            scan_report_field=field,
            frequency=data.pop("frequency", 1),
            **data,
        )
        for data in values_data
    ]
    return ScanReportValue.objects.bulk_create(values)
