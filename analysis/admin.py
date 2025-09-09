from django.contrib import admin
from .models import Analysis, ImageResult, Recommendation

@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'crop_type', 'average_confidence', 'average_severity', 'status', 'created_at']
    list_filter = ['crop_type', 'average_severity', 'status', 'created_at']
    search_fields = ['user__username', 'crop_type']
    readonly_fields = ['id', 'created_at']

@admin.register(ImageResult)
class ImageResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'analysis', 'disease_detected', 'confidence_score', 'severity', 'created_at']
    list_filter = ['disease_detected', 'severity', 'created_at']
    search_fields = ['disease_detected', 'analysis__crop_type']

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['id', 'analysis', 'generated_by', 'status', 'created_at']
    list_filter = ['generated_by', 'status', 'created_at']
    search_fields = ['analysis__crop_type', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at']
