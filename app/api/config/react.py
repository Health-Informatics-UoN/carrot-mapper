from mapping.models import UploadStatus


def react(request):
    return {
        "upload_status": [
            {"id": status.id, "label": status.display_name}
            for status in UploadStatus.objects.all()
        ],
    }
