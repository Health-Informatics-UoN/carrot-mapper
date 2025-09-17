# gunicorn.conf.py
import os

from azure.monitor.opentelemetry import configure_azure_monitor
from dotenv import load_dotenv


def on_starting(server):
    load_dotenv()

    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        configure_azure_monitor()
