from rest_framework import serializers

from .models import Job, JobStage, StageStatus


class StageStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = StageStatus
        fields = ["value"]


class JobStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobStage
        fields = ["value"]


class JobSerializer(serializers.ModelSerializer):
    stage = JobStageSerializer()
    status = StageStatusSerializer()

    class Meta:
        model = Job
        fields = "__all__"
