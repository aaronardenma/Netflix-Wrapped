from rest_framework import serializers

class UploadCSVSerializer(serializers.Serializer):
    file = serializers.FileField()
    user = serializers.CharField()
    year = serializers.IntegerField()
