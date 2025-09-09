import logging
from django.conf import settings
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiRecommendationService:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("✅ Gemini API configured successfully")
        else:
            self.model = None
            logger.warning("⚠️ Gemini API key not configured. Using fallback recommendations.")
    
    def generate_recommendation(self, crop_type, disease, severity, confidence, location=None):
        """Generate AI-powered recommendations using Gemini"""
        try:
            if self.model and settings.GEMINI_API_KEY:
                prompt = self._build_prompt(crop_type, disease, severity, confidence, location)
                response = self.model.generate_content(prompt)
                logger.info(f"🤖 Gemini recommendation generated for {crop_type} - {disease}")
                return response.text
            else:
                logger.info(f"🎭 Using fallback recommendation for {crop_type} - {disease}")
                return self._fallback_recommendation(crop_type, disease, severity)
        except Exception as e:
            logger.error(f"❌ Error generating Gemini recommendation: {e}")
            return self._fallback_recommendation(crop_type, disease, severity)
    
    def _build_prompt(self, crop_type, disease, severity, confidence, location):
        """Build structured prompt for Gemini"""
        prompt = f"""
You are an expert agricultural advisor. Provide practical, actionable recommendations for a farmer.

Crop Analysis:
- Crop Type: {crop_type}
- Disease Detected: {disease}
- Severity Level: {severity}
- Detection Confidence: {confidence:.2%}
{f"- Location: {location}" if location else ""}

Please provide:
1. Immediate actions to take (2-3 steps)
2. Treatment recommendations (organic and chemical options)
3. Prevention measures for future crops
4. When to seek expert help
5. Expected recovery timeline

Keep recommendations practical, safe, and suitable for small to medium-scale farmers.
Include safety warnings for any chemical treatments.
Format as clear, numbered steps.
"""
        return prompt
    
    def _fallback_recommendation(self, crop_type, disease, severity):
        """Fallback recommendations when Gemini is unavailable"""
        recommendations = {
            'healthy': {
                'low': f"Your {crop_type} appears healthy! Continue with regular care including proper watering, fertilization, and monitoring for any changes.",
                'medium': f"Your {crop_type} shows good health. Maintain current care practices and monitor regularly.",
                'high': f"Excellent! Your {crop_type} is in great condition. Keep up the good work with your current care routine."
            },
            'blight': {
                'low': f"Early signs of blight detected in {crop_type}. Remove affected leaves immediately and improve air circulation. Consider copper-based fungicide application.",
                'medium': f"Moderate blight infection in {crop_type}. Apply fungicide treatment immediately, remove infected plant parts, and ensure proper spacing for air circulation.",
                'high': f"Severe blight infection in {crop_type}. Immediate action required: apply systemic fungicide, remove heavily infected plants, and implement strict sanitation measures."
            },
            'spot': {
                'low': f"Leaf spot detected in {crop_type}. Remove affected leaves, avoid overhead watering, and apply preventive fungicide spray.",
                'medium': f"Moderate leaf spot in {crop_type}. Apply fungicide treatment, improve air circulation, and water at soil level to prevent spread.",
                'high': f"Severe leaf spot in {crop_type}. Immediate fungicide treatment needed, remove infected foliage, and consider crop rotation for next season."
            },
            'rust': {
                'low': f"Early rust symptoms in {crop_type}. Apply preventive fungicide, ensure good air circulation, and monitor closely.",
                'medium': f"Rust infection spreading in {crop_type}. Apply systemic fungicide, remove infected leaves, and avoid overhead irrigation.",
                'high': f"Severe rust infection in {crop_type}. Immediate treatment with systemic fungicide required, remove heavily infected plants, and implement sanitation measures."
            }
        }
        
        # Find matching recommendation
        disease_lower = disease.lower()
        for key in recommendations:
            if key in disease_lower:
                return recommendations[key].get(severity, recommendations[key]['medium'])
        
        # Default recommendation
        if severity == 'high':
            return f"Severe disease detected in {crop_type}. Consult with a local agricultural extension officer immediately for proper diagnosis and treatment."
        elif severity == 'medium':
            return f"Disease symptoms detected in {crop_type}. Monitor closely, improve plant care conditions, and consider preventive treatments."
        else:
            return f"Minor issues detected in {crop_type}. Continue monitoring and maintain good agricultural practices."

# Global instance
gemini_service = GeminiRecommendationService()
