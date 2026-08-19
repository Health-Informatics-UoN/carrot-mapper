from api.paginations import CustomPagination
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(GenericAPIView, ListModelMixin):
    """
    Lists the authenticated user's notifications, newest first.

    Supports `?unread=true` to only return notifications that haven't been
    read yet.
    """

    serializer_class = NotificationSerializer
    pagination_class = CustomPagination
    http_method_names = ["get"]

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get("unread") == "true":
            queryset = queryset.filter(read_at__isnull=True)
        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class NotificationUnreadCountView(APIView):
    """Returns the authenticated user's unread notification count."""

    def get(self, request, *args, **kwargs):
        count = Notification.objects.filter(
            recipient=request.user, read_at__isnull=True
        ).count()
        return Response({"count": count})


class NotificationMarkReadView(APIView):
    """Marks a single notification, owned by the authenticated user, as read."""

    def patch(self, request, *args, **kwargs):
        notification = get_object_or_404(
            Notification, pk=kwargs["pk"], recipient=request.user
        )
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    """Marks every unread notification owned by the authenticated user as read."""

    def post(self, request, *args, **kwargs):
        updated = Notification.objects.filter(
            recipient=request.user, read_at__isnull=True
        ).update(read_at=timezone.now())
        return Response({"updated": updated})
