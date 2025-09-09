import logging
from django.conf import settings
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiRecommendationService:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key='AIzaSyBolxV9MsOG3hG7iTznN2lto1T3oOjxhgI')
            # Try different model names that are currently available
            model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
            self.model = None
            
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    # Test the model with a simple prompt
                    test_response = self.model.generate_content("Hello")
                    logger.info(f"✅ Gemini API configured successfully with model: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"⚠️ Model {model_name} not available: {e}")
                    continue
            
            if not self.model:
                logger.error("❌ No working Gemini model found. Using fallback recommendations.")
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
                
                # Try to parse JSON response
                try:
                    import json
                    # Clean the response text to extract JSON
                    response_text = response.text.strip()
                    if response_text.startswith('```json'):
                        response_text = response_text.replace('```json', '').replace('```', '').strip()
                    elif response_text.startswith('```'):
                        response_text = response_text.replace('```', '').strip()
                    
                    parsed_response = json.loads(response_text)
                    return parsed_response
                except json.JSONDecodeError as json_error:
                    logger.warning(f"⚠️ Failed to parse JSON response: {json_error}")
                    logger.warning(f"Raw response: {response.text[:200]}...")
                    return self._fallback_recommendation(crop_type, disease, severity, confidence, location)
            else:
                logger.info(f"🎭 Using fallback recommendation for {crop_type} - {disease}")
                return self._fallback_recommendation(crop_type, disease, severity, confidence, location)
        except Exception as e:
            logger.error(f"❌ Error generating Gemini recommendation: {e}")
            return self._fallback_recommendation(crop_type, disease, severity, confidence, location)
    
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

Please provide your response in the following JSON format ONLY. Do not include any text outside of this JSON structure:

{{
  "crop_type": "{crop_type}",
  "disease_detected": "{disease}",
  "severity_level": "{severity}",
  "confidence": {confidence:.3f},
  "location": "{location if location else 'Not specified'}",
  "summary": "Brief 2-3 sentence summary of the situation and overall recommendation",
  "immediate_actions": [
    {{
      "step": 1,
      "title": "Action Title",
      "description": "Detailed description of what to do"
    }},
    {{
      "step": 2,
      "title": "Action Title",
      "description": "Detailed description of what to do"
    }},
    {{
      "step": 3,
      "title": "Action Title",
      "description": "Detailed description of what to do"
    }}
  ],
  "treatment_recommendations": {{
    "organic_options": [
      {{
        "treatment": "Treatment name",
        "description": "How to apply and what it does",
        "safety_notes": "Any safety considerations"
      }}
    ],
    "chemical_options": [
      {{
        "treatment": "Chemical name",
        "description": "How to apply and what it does",
        "safety_warnings": "Important safety warnings and PPE requirements"
      }}
    ]
  }},
  "prevention_measures": [
    {{
      "measure": "Prevention method",
      "description": "How to implement this prevention measure"
    }}
  ],
  "expert_help_indicators": [
    "When to seek expert help - condition 1",
    "When to seek expert help - condition 2"
  ],
  "recovery_timeline": {{
    "expected_duration": "Time estimate",
    "factors_affecting_recovery": "What affects the timeline",
    "monitoring_frequency": "How often to check progress"
  }},
  "additional_notes": "Any additional important information"
}}

Keep recommendations practical, safe, and suitable for small to medium-scale farmers.
"""
        return prompt
    
    def _fallback_recommendation(self, crop_type, disease, severity, confidence=0.0, location=None):
        """Fallback recommendations when Gemini is unavailable - returns JSON format"""
        import json
        
        # Base recommendation structure
        base_recommendation = {
            "crop_type": crop_type,
            "disease_detected": disease,
            "severity_level": severity,
            "confidence": confidence,
            "location": location or "Not specified",
            "summary": "",
            "immediate_actions": [],
            "treatment_recommendations": {
                "organic_options": [],
                "chemical_options": []
            },
            "prevention_measures": [],
            "expert_help_indicators": [
                "Symptoms worsen or spread rapidly",
                "Multiple plants are affected",
                "Unusual symptoms not covered in basic recommendations"
            ],
            "recovery_timeline": {
                "expected_duration": "1-2 weeks with proper treatment",
                "factors_affecting_recovery": "Weather conditions, treatment timing, and plant health",
                "monitoring_frequency": "Check daily for the first week, then every 2-3 days"
            },
            "additional_notes": "These are general recommendations. For specific conditions, consult local agricultural experts."
        }
        
        if disease.lower() == 'healthy':
            base_recommendation.update({
                "summary": f"Your {crop_type} appears healthy. Continue with regular maintenance and monitoring to keep it in good condition.",
                "immediate_actions": [
                    {
                        "step": 1,
                        "title": "Regular Monitoring",
                        "description": "Continue daily visual inspections for any changes in plant health, leaf color, or growth patterns."
                    },
                    {
                        "step": 2,
                        "title": "Maintain Watering Schedule",
                        "description": "Keep consistent watering schedule, ensuring soil moisture without waterlogging."
                    },
                    {
                        "step": 3,
                        "title": "Nutrient Check",
                        "description": "Monitor plant growth and consider soil testing if growth seems slower than expected."
                    }
                ],
                "treatment_recommendations": {
                    "organic_options": [
                        {
                            "treatment": "Compost Application",
                            "description": "Apply well-aged compost around the base to improve soil health",
                            "safety_notes": "Ensure compost is fully decomposed to avoid burning plants"
                        }
                    ],
                    "chemical_options": [
                        {
                            "treatment": "Balanced Fertilizer",
                            "description": "Apply balanced NPK fertilizer according to package directions",
                            "safety_warnings": "Wear gloves when handling fertilizer and avoid over-application"
                        }
                    ]
                },
                "prevention_measures": [
                    {
                        "measure": "Regular Inspection",
                        "description": "Inspect plants weekly for early signs of disease or pest issues"
                    },
                    {
                        "measure": "Proper Spacing",
                        "description": "Ensure adequate spacing between plants for good air circulation"
                    }
                ]
            })
        else:
            # Generic disease recommendations
            base_recommendation.update({
                "summary": f"{disease} detected in {crop_type} with {severity} severity. Immediate treatment recommended to prevent spread.",
                "immediate_actions": [
                    {
                        "step": 1,
                        "title": "Isolate Affected Plants",
                        "description": "Remove or isolate affected plant parts to prevent disease spread"
                    },
                    {
                        "step": 2,
                        "title": "Improve Air Circulation",
                        "description": "Prune surrounding vegetation and ensure proper plant spacing"
                    },
                    {
                        "step": 3,
                        "title": "Apply Treatment",
                        "description": "Apply appropriate fungicide or treatment based on disease type"
                    }
                ],
                "treatment_recommendations": {
                    "organic_options": [
                        {
                            "treatment": "Neem Oil Spray",
                            "description": "Apply neem oil solution every 7-14 days in early morning or evening",
                            "safety_notes": "Test on small area first; avoid application in direct sunlight"
                        }
                    ],
                    "chemical_options": [
                        {
                            "treatment": "Copper-based Fungicide",
                            "description": "Apply according to label directions, typically every 7-10 days",
                            "safety_warnings": "Wear protective equipment including gloves, mask, and eye protection"
                        }
                    ]
                },
                "prevention_measures": [
                    {
                        "measure": "Crop Rotation",
                        "description": "Rotate crops annually to break disease cycles"
                    },
                    {
                        "measure": "Sanitation",
                        "description": "Remove and dispose of infected plant debris properly"
                    }
                ]
            })
        
        return base_recommendation

# Global instance
gemini_service = GeminiRecommendationService()
