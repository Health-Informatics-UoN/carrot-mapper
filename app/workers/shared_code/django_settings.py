import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "shared.data",
    "shared.mapping",
    "shared",
    "shared.files",
    "shared.jobs",
]

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "TEST": {
            "NAME": "throwawaydb",
        },
    }
}

# Storage Configuration (Azure or MinIO)
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "azure")
if not STORAGE_TYPE:
    raise ValueError(
        "STORAGE_TYPE environment variable must be set (e.g., 'azure' or 'minio')."
    )


# Azure Storage Connection String
STORAGE_CONN_STRING = os.getenv("STORAGE_CONN_STRING")
