import logging
from django.db.models import Q, Count, Avg
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta

from .models import Analysis, ImageResult, Recommendation
from .serializers import (
    AnalysisSerializer, AnalysisCreateSerializer, 
    AdminReviewSerializer, RecommendationSerializer
)
# from .ml_service import disease_detection_service
# from .gemini_service import gemini_service

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_analysis(request):
    """Upload images for disease analysis"""
    serializer = AnalysisCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    images = serializer.validated_data['images']
    crop_type_override = serializer.validated_data.get('crop_type')
    
    try:
        # Run ML prediction
        predictions = disease_detection_service.predict_disease(images)
        
        # Check if any images were invalid
        invalid_results = [r for r in predictions if r.get('severity') == 'invalid']
        if invalid_results:
            return Response({
                'error': 'Invalid images detected',
                'message': 'The uploaded images do not appear to be plant or crop images.',
                'invalid_images': [r['image_name'] for r in invalid_results],
                'details': [r.get('error', 'Not a plant image') for r in invalid_results]
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if all results are errors
        error_results = [r for r in predictions if r.get('disease') == 'Error']
        if len(error_results) == len(predictions):
            return Response({
                'error': 'Analysis failed',
                'message': 'Could not analyze the uploaded images. Please try again with clear plant images.',
                'details': [r.get('error', 'Processing error') for r in error_results]
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not predictions:
            return Response({'error': 'Failed to process images'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Calculate averages
        confidences = [p['confidence'] for p in predictions]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Determine crop type (use override or most common prediction)
        if crop_type_override:
            crop_type = crop_type_override
        else:
            crop_types = [p['crop_type'] for p in predictions]
            crop_type = max(set(crop_types), key=crop_types.count)
        
        # Determine average severity
        severity_weights = {'low': 1, 'medium': 2, 'high': 3}
        avg_severity_weight = sum(severity_weights[p['severity']] for p in predictions) / len(predictions)
        
        if avg_severity_weight >= 2.5:
            avg_severity = 'high'
        elif avg_severity_weight >= 1.5:
            avg_severity = 'medium'
        else:
            avg_severity = 'low'
        
        # Create analysis record
        analysis = Analysis.objects.create(
            user=request.user,
            crop_type=crop_type,
            average_confidence=avg_confidence,
            average_severity=avg_severity,
            status='completed'
        )
        
        # Create image results
        image_results = []
        for i, (image, prediction) in enumerate(zip(images, predictions)):
            image_result = ImageResult.objects.create(
                analysis=analysis,
                image=image,
                disease_detected=prediction['disease'],
                confidence_score=prediction['confidence'],
                severity=prediction['severity']
            )
            image_results.append(image_result)
        
        # Generate AI recommendation
        diseases = [p['disease'] for p in predictions]
        primary_disease = max(set(diseases), key=diseases.count)
        
        recommendation_data = gemini_service.generate_recommendation(
            crop_type=crop_type,
            disease=primary_disease,
            severity=avg_severity,
            confidence=avg_confidence
        )
        
        # Handle both string and JSON responses
        if isinstance(recommendation_data, dict):
            # Store JSON as content and extract text summary
            import json
            recommendation_text = recommendation_data.get('summary', 'AI recommendation generated')
            # Store the structured data as JSON string in content for now
            full_content = f"{recommendation_text}\n\n--- STRUCTURED_DATA ---\n{json.dumps(recommendation_data, indent=2)}"
        else:
            # Fallback for string responses
            full_content = str(recommendation_data)
        
        recommendation = Recommendation.objects.create(
            analysis=analysis,
            generated_by='ai',
            content=full_content,
            status='pending'
        )
        
        # Prepare response matching frontend expectations
        response_data = {
            'analysis_id': str(analysis.id),
            'id': str(analysis.id),  # Frontend expects 'id' field
            'crop_type': crop_type,
            'disease': primary_disease,
            'confidence': f"{avg_confidence * 100:.0f}%",
            'severity': avg_severity,
            'affectedAreas': [],  # Can be enhanced based on ML model output
            'results': [
                {
                    'image_name': pred['image_name'],
                    'disease': pred['disease'],
                    'severity': pred['severity'],
                    'confidence': pred['confidence']
                }
                for pred in predictions
            ],
            'recommendations': [
                {
                    'id': str(recommendation.id),
                    'generated_by': 'AI',
                    'content': recommendation_text,
                    'status': 'pending'
                }
            ],
            'average_confidence': avg_confidence,
            'average_severity': avg_severity
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error in upload_analysis: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analysis_history(request):
    """Get user's analysis history with filtering"""
    queryset = Analysis.objects.filter(user=request.user)
    
    # Filtering
    crop_type = request.GET.get('crop_type')
    if crop_type:
        queryset = queryset.filter(crop_type__icontains=crop_type)
    
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)
    
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(crop_type__icontains=search) |
            Q(results__disease_detected__icontains=search)
        ).distinct()
    
    # Pagination
    paginator = PageNumberPagination()
    paginator.page_size = 20
    page = paginator.paginate_queryset(queryset, request)
    
    serializer = AnalysisSerializer(page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analysis_detail(request, analysis_id):
    """Get detailed analysis results with images, recommendations, and expert responses"""
    try:
        analysis = Analysis.objects.select_related('user').prefetch_related(
            'results', 'recommendations'
        ).get(id=analysis_id, user=request.user)
        
        # Get image results
        results_data = []
        for result in analysis.results.all():
            image_url = None
            if result.image:
                try:
                    image_url = request.build_absolute_uri(result.image.url)
                except Exception as e:
                    logger.error(f"Error building image URL: {e}")
                    image_url = None
            
            results_data.append({
                'id': str(result.id),
                'image': image_url,
                'disease_detected': result.disease_detected,
                'confidence_score': result.confidence_score,
                'severity': result.severity
            })
        
        # Get recommendations (AI generated)
        recommendations_data = []
        ai_recommendations = analysis.recommendations.filter(generated_by='AI')
        for rec in ai_recommendations:
            # Extract expert response if it exists in content
            content = rec.content
            expert_response = None
            if "--- Admin Comment ---" in content:
                parts = content.split("--- Admin Comment ---")
                content = parts[0].strip()
                expert_response = parts[1].strip() if len(parts) > 1 else None
            
            recommendations_data.append({
                'id': str(rec.id),
                'content': content,
                'expert_response': expert_response,
                'generated_by': rec.generated_by,
                'status': rec.status,
                'created_at': rec.created_at.isoformat()
            })
        
        # Get opinion requests (Human generated)
        opinion_requests_data = []
        opinion_requests = analysis.recommendations.filter(generated_by='Human')
        for opinion in opinion_requests:
            # Extract question and expert response
            content = opinion.content
            question = content
            expert_response = None
            
            if content.startswith("Opinion Request: "):
                question = content.replace("Opinion Request: ", "")
            
            if "--- Expert Response ---" in content:
                parts = content.split("--- Expert Response ---")
                question = parts[0].replace("Opinion Request: ", "").strip()
                expert_response = parts[1].strip() if len(parts) > 1 else None
            
            opinion_requests_data.append({
                'id': str(opinion.id),
                'question': question,
                'expert_response': expert_response,
                'status': opinion.status,
                'created_at': opinion.created_at.isoformat()
            })
        
        response_data = {
            'id': str(analysis.id),
            'crop_type': analysis.crop_type,
            'average_confidence': analysis.average_confidence,
            'average_severity': analysis.average_severity,
            'status': analysis.status,
            'created_at': analysis.created_at.isoformat(),
            'results': results_data,
            'recommendations': recommendations_data,
            'opinion_requests': opinion_requests_data
        }
        
        return Response({
            'success': True,
            'data': response_data
        })
        
    except Analysis.DoesNotExist:
        return Response({'error': 'Analysis not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Analysis detail error: {e}")
        return Response({'error': 'Failed to fetch analysis details'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_pending(request):
    """Get pending recommendations for admin review"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    recommendations = Recommendation.objects.filter(status='pending').select_related('analysis')
    serializer = RecommendationSerializer(recommendations, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_review(request, recommendation_id):
    """Admin review of recommendations"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        recommendation = Recommendation.objects.get(id=recommendation_id)
    except Recommendation.DoesNotExist:
        return Response({'error': 'Recommendation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = AdminReviewSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    action = serializer.validated_data['action']
    feedback = serializer.validated_data.get('feedback', '')
    
    if action == 'approve':
        recommendation.status = 'approved'
    else:
        recommendation.status = 'rejected'
    
    recommendation.admin_feedback = feedback
    recommendation.save()
    
    return Response({
        'message': f'Recommendation {action}d successfully',
        'recommendation': RecommendationSerializer(recommendation).data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_stats(request):
    """Admin dashboard statistics"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    # Import User model
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Basic counts
    total_analyses = Analysis.objects.count()
    total_farmers = User.objects.count()  # Count all registered users
    active_farmers = Analysis.objects.values('user').distinct().count()  # Users who have done analyses
    recent_analyses = Analysis.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=1)
    ).count()
    
    # Recommendation statistics
    total_recommendations = Recommendation.objects.count()
    pending_recommendations = Recommendation.objects.filter(status='pending').count()
    approved_recommendations = Recommendation.objects.filter(status='approved').count()
    rejected_recommendations = Recommendation.objects.filter(status='rejected').count()
    
    # AI vs Human recommendations
    ai_recommendations = Recommendation.objects.filter(generated_by='AI').count()
    human_recommendations = Recommendation.objects.filter(generated_by='Human').count()
    
    # Confidence distribution
    confidence_stats = Analysis.objects.aggregate(
        avg_confidence=Avg('average_confidence'),
        high_confidence=Count('id', filter=Q(average_confidence__gte=0.8)),
        medium_confidence=Count('id', filter=Q(average_confidence__gte=0.6, average_confidence__lt=0.8)),
        low_confidence=Count('id', filter=Q(average_confidence__lt=0.6))
    )
    
    # Crop type distribution
    crop_distribution = Analysis.objects.values('crop_type').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Disease distribution from image results
    disease_distribution = ImageResult.objects.values('disease_detected').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    return Response({
        'total_analyses': total_analyses,
        'total_farmers': total_farmers,
        'active_farmers': active_farmers,
        'recent_analyses': recent_analyses,
        'total_recommendations': total_recommendations,
        'pending_recommendations': pending_recommendations,
        'approved_recommendations': approved_recommendations,
        'rejected_recommendations': rejected_recommendations,
        'ai_recommendations': ai_recommendations,
        'human_recommendations': human_recommendations,
        'confidence_distribution': {
            'high': confidence_stats['high_confidence'],
            'medium': confidence_stats['medium_confidence'],
            'low': confidence_stats['low_confidence']
        },
        'average_confidence': confidence_stats['avg_confidence'] or 0,
        'crop_distribution': list(crop_distribution),
        'disease_distribution': list(disease_distribution)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_recommendation(request):
    """Generate AI recommendation for existing analysis"""
    try:
        analysis_id = request.data.get('analysis_id')
        
        if not analysis_id:
            return Response({'error': 'Analysis ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            analysis = Analysis.objects.get(id=analysis_id, user=request.user)
        except Analysis.DoesNotExist:
            return Response({'error': 'Analysis not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get the most common disease from image results
        image_results = analysis.results.all()
        if image_results.exists():
            # Get the disease with highest confidence
            best_result = image_results.order_by('-confidence_score').first()
            disease = best_result.disease_detected
            severity = best_result.severity
        else:
            disease = "Unknown"
            severity = analysis.average_severity
        
        # Generate AI recommendation using Gemini
        recommendation_data = gemini_service.generate_recommendation(
            crop_type=analysis.crop_type,
            disease=disease,
            severity=severity,
            confidence=analysis.average_confidence
        )
        
        # Handle both string and JSON responses
        if isinstance(recommendation_data, dict):
            import json
            recommendation_text = recommendation_data.get('summary', 'AI recommendation generated')
            full_content = f"{recommendation_text}\n\n--- STRUCTURED_DATA ---\n{json.dumps(recommendation_data, indent=2)}"
        else:
            full_content = str(recommendation_data)
        
        # Create recommendation
        recommendation = Recommendation.objects.create(
            analysis=analysis,
            content=full_content,
            generated_by='AI',
            status='pending'
        )
        
        return Response({
            'success': True,
            'recommendation': RecommendationSerializer(recommendation).data,
            'message': 'AI recommendation generated successfully'
        })
        
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        return Response({'error': 'Failed to generate recommendation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_opinion(request):
    """Request expert opinion for analysis"""
    try:
        analysis_id = request.data.get('analysis_id')
        question = request.data.get('question', 'Please provide expert advice for this crop analysis.')
        
        if not analysis_id:
            return Response({'error': 'Analysis ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            analysis = Analysis.objects.get(id=analysis_id, user=request.user)
        except Analysis.DoesNotExist:
            return Response({'error': 'Analysis not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Create opinion request (you might want to create a separate model for this)
        # For now, we'll create a recommendation with type 'opinion_request'
        opinion_request = Recommendation.objects.create(
            analysis=analysis,
            content=f"Opinion Request: {question}",
            generated_by='Human',
            status='pending'
        )
        
        return Response({
            'success': True,
            'opinion_request': RecommendationSerializer(opinion_request).data,
            'message': 'Expert opinion request submitted successfully'
        })
        
    except Exception as e:
        logger.error(f"Opinion request error: {e}")
        return Response({'error': 'Failed to submit opinion request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_recommendations(request):
    """Get all recommendations for admin review"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        recommendations = Recommendation.objects.select_related(
            'analysis__user'
        ).prefetch_related('analysis__results').order_by('-created_at')
        
        # Serialize with related data
        recommendations_data = []
        for rec in recommendations:
            rec_data = RecommendationSerializer(rec).data
            
            # Get image results
            results_data = []
            for result in rec.analysis.results.all():
                image_url = None
                if result.image:
                    try:
                        image_url = request.build_absolute_uri(result.image.url)
                        logger.info(f"Generated image URL: {image_url}")
                    except Exception as e:
                        logger.error(f"Error building image URL: {e}")
                        image_url = None
                
                results_data.append({
                    'id': str(result.id),
                    'image': image_url,
                    'disease_detected': result.disease_detected,
                    'confidence_score': result.confidence_score,
                    'severity': result.severity
                })
            
            logger.info(f"Results data for analysis {rec.analysis.id}: {len(results_data)} results")
            
            rec_data['analysis'] = {
                'id': str(rec.analysis.id),
                'crop_type': rec.analysis.crop_type,
                'average_confidence': rec.analysis.average_confidence,
                'average_severity': rec.analysis.average_severity,
                'status': rec.analysis.status,
                'created_at': rec.analysis.created_at.isoformat(),
                'user': {
                    'username': rec.analysis.user.username,
                    'email': rec.analysis.user.email
                },
                'results': results_data
            }
            recommendations_data.append(rec_data)
        
        return Response({
            'success': True,
            'results': recommendations_data
        })
        
    except Exception as e:
        logger.error(f"Admin recommendations error: {e}")
        return Response({'error': 'Failed to fetch recommendations'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def admin_recommendation_detail(request, recommendation_id):
    """CRUD operations for individual recommendations"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        recommendation = Recommendation.objects.get(id=recommendation_id)
    except Recommendation.DoesNotExist:
        return Response({'error': 'Recommendation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        # Get recommendation details
        return Response({
            'success': True,
            'data': RecommendationSerializer(recommendation).data
        })
    
    elif request.method == 'PUT':
        # Update recommendation content
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        recommendation.content = content
        recommendation.save()
        
        return Response({
            'success': True,
            'data': RecommendationSerializer(recommendation).data,
            'message': 'Recommendation updated successfully'
        })
    
    elif request.method == 'DELETE':
        # Delete recommendation
        recommendation.delete()
        return Response({
            'success': True,
            'message': 'Recommendation deleted successfully'
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_review(request, recommendation_id):
    """Update recommendation status (approve/reject) with optional admin comment"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        recommendation = Recommendation.objects.get(id=recommendation_id)
    except Recommendation.DoesNotExist:
        return Response({'error': 'Recommendation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    new_status = request.data.get('status')
    admin_comment = request.data.get('admin_comment', '')
    
    if new_status not in ['approved', 'rejected']:
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    recommendation.status = new_status
    
    # Add admin comment to content if provided
    if admin_comment:
        recommendation.content += f"\n\n--- Admin Comment ---\n{admin_comment}"
    
    recommendation.save()
    
    return Response({
        'success': True,
        'data': RecommendationSerializer(recommendation).data,
        'message': f'Recommendation {new_status} successfully'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_opinions(request):
    """Get all opinion requests for admin management"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Get opinion requests (recommendations with generated_by='Human')
        opinion_requests = Recommendation.objects.filter(
            generated_by='Human'
        ).select_related('analysis__user').prefetch_related('analysis__results').order_by('-created_at')
        
        # Serialize with related data
        opinions_data = []
        for opinion in opinion_requests:
            # Extract question from content
            question = opinion.content
            if question.startswith("Opinion Request: "):
                question = question.replace("Opinion Request: ", "")
            
            # Get image results
            results_data = []
            for result in opinion.analysis.results.all():
                image_url = None
                if result.image:
                    try:
                        image_url = request.build_absolute_uri(result.image.url)
                    except Exception as e:
                        logger.error(f"Error building image URL: {e}")
                        image_url = None
                
                results_data.append({
                    'id': str(result.id),
                    'image': image_url,
                    'disease_detected': result.disease_detected,
                    'confidence_score': result.confidence_score,
                    'severity': result.severity
                })
            
            opinion_data = {
                'id': str(opinion.id),
                'question': question,
                'content': opinion.content,
                'expert_response': getattr(opinion, 'expert_response', None),
                'status': opinion.status,
                'created_at': opinion.created_at.isoformat(),
                'updated_at': opinion.updated_at.isoformat(),
                'analysis': {
                    'id': str(opinion.analysis.id),
                    'crop_type': opinion.analysis.crop_type,
                    'average_confidence': opinion.analysis.average_confidence,
                    'average_severity': opinion.analysis.average_severity,
                    'created_at': opinion.analysis.created_at.isoformat(),
                    'user': {
                        'username': opinion.analysis.user.username,
                        'email': opinion.analysis.user.email
                    },
                    'results': results_data
                }
            }
            opinions_data.append(opinion_data)
        
        return Response({
            'success': True,
            'results': opinions_data
        })
        
    except Exception as e:
        logger.error(f"Admin opinions error: {e}")
        return Response({'error': 'Failed to fetch opinion requests'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def admin_opinion_detail(request, opinion_id):
    """CRUD operations for individual opinion requests"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        opinion = Recommendation.objects.get(id=opinion_id, generated_by='Human')
    except Recommendation.DoesNotExist:
        return Response({'error': 'Opinion request not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        # Get opinion details
        return Response({
            'success': True,
            'data': RecommendationSerializer(opinion).data
        })
    
    elif request.method == 'PATCH':
        # Update opinion status
        new_status = request.data.get('status')
        if new_status not in ['pending', 'responded', 'closed']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        opinion.status = new_status
        opinion.save()
        
        return Response({
            'success': True,
            'data': RecommendationSerializer(opinion).data,
            'message': f'Opinion status updated to {new_status}'
        })
    
    elif request.method == 'DELETE':
        # Delete opinion request
        opinion.delete()
        return Response({
            'success': True,
            'message': 'Opinion request deleted successfully'
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_opinion_respond(request, opinion_id):
    """Respond to an opinion request"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        opinion = Recommendation.objects.get(id=opinion_id, generated_by='Human')
    except Recommendation.DoesNotExist:
        return Response({'error': 'Opinion request not found'}, status=status.HTTP_404_NOT_FOUND)
    
    expert_response = request.data.get('expert_response')
    if not expert_response:
        return Response({'error': 'Expert response is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Update the recommendation with expert response
    opinion.content += f"\n\n--- Expert Response ---\n{expert_response}"
    opinion.status = 'responded'
    opinion.save()
    
    # You might want to add an expert_response field to the model in the future
    # For now, we append it to the content
    
    return Response({
        'success': True,
        'data': RecommendationSerializer(opinion).data,
        'message': 'Expert response sent successfully'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_analytics(request):
    """Get comprehensive analytics data"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from datetime import timedelta
        
        User = get_user_model()
        
        # Time periods
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Basic counts
        total_analyses = Analysis.objects.count()
        total_farmers = User.objects.count()
        total_recommendations = Recommendation.objects.count()
        pending_recommendations = Recommendation.objects.filter(status='pending').count()
        
        # Time-based analytics
        analyses_this_week = Analysis.objects.filter(created_at__gte=week_ago).count()
        analyses_this_month = Analysis.objects.filter(created_at__gte=month_ago).count()
        new_users_this_week = User.objects.filter(date_joined__gte=week_ago).count()
        new_users_this_month = User.objects.filter(date_joined__gte=month_ago).count()
        
        # Crop distribution
        crop_stats = Analysis.objects.values('crop_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        total_crop_analyses = sum(stat['count'] for stat in crop_stats)
        crop_distribution = []
        for stat in crop_stats:
            crop_distribution.append({
                'crop_type': stat['crop_type'],
                'count': stat['count'],
                'percentage': (stat['count'] / total_crop_analyses * 100) if total_crop_analyses > 0 else 0
            })
        
        # Disease distribution
        disease_stats = ImageResult.objects.values('disease_detected').annotate(
            count=Count('id')
        ).order_by('-count')
        
        total_disease_detections = sum(stat['count'] for stat in disease_stats)
        disease_distribution = []
        for stat in disease_stats:
            disease_distribution.append({
                'disease_detected': stat['disease_detected'],
                'count': stat['count'],
                'percentage': (stat['count'] / total_disease_detections * 100) if total_disease_detections > 0 else 0
            })
        
        # Confidence distribution
        confidence_stats = Analysis.objects.aggregate(
            avg_confidence=Avg('average_confidence'),
            high_confidence=Count('id', filter=Q(average_confidence__gte=0.8)),
            medium_confidence=Count('id', filter=Q(average_confidence__gte=0.6, average_confidence__lt=0.8)),
            low_confidence=Count('id', filter=Q(average_confidence__lt=0.6))
        )
        
        # User engagement
        active_users_this_week = Analysis.objects.filter(
            created_at__gte=week_ago
        ).values('user').distinct().count()
        
        repeat_users = User.objects.annotate(
            analysis_count=Count('analysis')
        ).filter(analysis_count__gt=1).count()
        
        # Recommendation analytics
        ai_recommendations = Recommendation.objects.filter(generated_by='AI').count()
        human_requests = Recommendation.objects.filter(generated_by='Human').count()
        approved_recommendations = Recommendation.objects.filter(status='approved').count()
        rejected_recommendations = Recommendation.objects.filter(status='rejected').count()
        
        return Response({
            'success': True,
            'data': {
                'total_analyses': total_analyses,
                'total_farmers': total_farmers,
                'total_recommendations': total_recommendations,
                'pending_recommendations': pending_recommendations,
                'analyses_this_week': analyses_this_week,
                'analyses_this_month': analyses_this_month,
                'new_users_this_week': new_users_this_week,
                'new_users_this_month': new_users_this_month,
                'crop_distribution': crop_distribution,
                'disease_distribution': disease_distribution,
                'confidence_distribution': {
                    'high': confidence_stats['high_confidence'],
                    'medium': confidence_stats['medium_confidence'],
                    'low': confidence_stats['low_confidence']
                },
                'average_confidence': confidence_stats['avg_confidence'] or 0,
                'active_users_this_week': active_users_this_week,
                'repeat_users': repeat_users,
                'ai_recommendations': ai_recommendations,
                'human_requests': human_requests,
                'approved_recommendations': approved_recommendations,
                'rejected_recommendations': rejected_recommendations
            }
        })
        
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return Response({'error': 'Failed to fetch analytics'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_users(request):
    """Get all users with their activity statistics"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        users = User.objects.all().order_by('-date_joined')
        
        users_data = []
        for user in users:
            # Get user activity stats
            analysis_count = Analysis.objects.filter(user=user).count()
            recommendation_count = Recommendation.objects.filter(analysis__user=user, generated_by='AI').count()
            opinion_request_count = Recommendation.objects.filter(analysis__user=user, generated_by='Human').count()
            
            user_data = {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'role': getattr(user, 'role', 'farmer'),
                'is_active': user.is_active,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'analysis_count': analysis_count,
                'recommendation_count': recommendation_count,
                'opinion_request_count': opinion_request_count
            }
            users_data.append(user_data)
        
        return Response({
            'success': True,
            'results': users_data
        })
        
    except Exception as e:
        logger.error(f"Users error: {e}")
        return Response({'error': 'Failed to fetch users'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def admin_user_detail(request, user_id):
    """Get or update user details"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        # Get user details
        analysis_count = Analysis.objects.filter(user=user).count()
        recommendation_count = Recommendation.objects.filter(analysis__user=user, generated_by='AI').count()
        opinion_request_count = Recommendation.objects.filter(analysis__user=user, generated_by='Human').count()
        
        user_data = {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'role': getattr(user, 'role', 'farmer'),
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'analysis_count': analysis_count,
            'recommendation_count': recommendation_count,
            'opinion_request_count': opinion_request_count
        }
        
        return Response({
            'success': True,
            'data': user_data
        })
    
    elif request.method == 'PATCH':
        # Update user status
        is_active = request.data.get('is_active')
        if is_active is not None:
            user.is_active = is_active
            user.save()
        
        return Response({
            'success': True,
            'message': f'User {"activated" if is_active else "deactivated"} successfully'
        })
