from django.urls import path
from . import views

urlpatterns = [
    # Analysis endpoints
    path('analysis/upload/', views.upload_analysis, name='upload_analysis'),
    path('analysis/history/', views.analysis_history, name='analysis_history'),
    path('analysis/<uuid:analysis_id>/', views.analysis_detail, name='analysis_detail'),
    path('analysis/request-recommendation/', views.request_recommendation, name='request_recommendation'),
    path('analysis/request-opinion/', views.request_opinion, name='request_opinion'),
    
    # Admin endpoints
    path('admin/pending/', views.admin_pending, name='admin_pending'),
    path('admin/review/<uuid:recommendation_id>/', views.admin_review, name='admin_review'),
    path('admin/stats/', views.admin_stats, name='admin_stats'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/<uuid:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('admin/recommendations/', views.admin_recommendations, name='admin_recommendations'),
    path('admin/recommendations/<uuid:recommendation_id>/', views.admin_recommendation_detail, name='admin_recommendation_detail'),
    path('admin/opinions/', views.admin_opinions, name='admin_opinions'),
    path('admin/opinions/<uuid:opinion_id>/', views.admin_opinion_detail, name='admin_opinion_detail'),
    path('admin/opinions/<uuid:opinion_id>/respond/', views.admin_opinion_respond, name='admin_opinion_respond'),
]
