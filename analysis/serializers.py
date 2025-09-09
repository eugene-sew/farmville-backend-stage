from rest_framework import serializers
from .models import Analysis, ImageResult, Recommendation

class ImageResultSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ImageResult
        fields = ['id', 'image_url', 'disease_detected', 'confidence_score', 'severity', 'created_at']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None

class RecommendationSerializer(serializers.ModelSerializer):
    structured_data = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()
    
    class Meta:
        model = Recommendation
        fields = ['id', 'generated_by', 'content', 'text', 'structured_data', 'status', 'admin_feedback', 'created_at', 'updated_at']
    
    def get_text(self, obj):
        """Extract the plain text part of the content"""
        if "--- STRUCTURED_DATA ---" in obj.content:
            parts = obj.content.split("--- STRUCTURED_DATA ---")
            return parts[0].strip()
        return obj.content
    
    def get_structured_data(self, obj):
        """Extract structured data from content if it exists"""
        if "--- STRUCTURED_DATA ---" in obj.content:
            try:
                import json
                parts = obj.content.split("--- STRUCTURED_DATA ---")
                if len(parts) > 1:
                    json_str = parts[1].strip()
                    return json.loads(json_str)
            except (json.JSONDecodeError, IndexError):
                pass
        return None

class AnalysisSerializer(serializers.ModelSerializer):
    results = ImageResultSerializer(many=True, read_only=True)
    recommendations = RecommendationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Analysis
        fields = ['id', 'crop_type', 'average_confidence', 'average_severity', 'status', 'created_at', 'results', 'recommendations']

class AnalysisCreateSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        min_length=1,
        max_length=5
    )
    crop_type = serializers.CharField(max_length=50, required=False)
    
    def validate_images(self, value):
        from django.conf import settings
        max_size = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
        
        for image in value:
            if image.size > max_size:
                raise serializers.ValidationError(f"Image {image.name} is too large. Maximum size is {settings.MAX_IMAGE_SIZE_MB}MB.")
            
            # Validate image format
            if not image.content_type.startswith('image/'):
                raise serializers.ValidationError(f"File {image.name} is not a valid image.")
        
        return value

class AdminReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    feedback = serializers.CharField(required=False, allow_blank=True)
