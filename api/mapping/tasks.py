# Create your tasks here

from celery import shared_task
from .models import ScanReport
from .services import process_scan_report


@shared_task
def add(x, y):
    return x + y


@shared_task
def mul(x, y):
    return x * y


@shared_task
def xsum(numbers):
    return sum(numbers)


@shared_task
def count_scanreports():
    return ScanReport.objects.count()


@shared_task
def rename_scanreport(scanreport_id, name):
    w = ScanReport.objects.get(id=scanreport_id)
    w.name = name
    w.save()


@shared_task
def process_scan_report_task(scan_report_id):
    process_scan_report(scan_report_id)

