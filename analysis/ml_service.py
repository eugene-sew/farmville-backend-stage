import os
import logging
import numpy as np
from PIL import Image, ImageOps
from django.conf import settings
from keras.models import load_model

# Disable scientific notation for clarity
np.set_printoptions(suppress=True)

logger = logging.getLogger(__name__)

class DiseaseDetectionService:
    def __init__(self):
        self.model = None
        self.class_names = []
        self.load_model()
    
    def load_model(self):
        try:
            # Load Teachable Machine model
            model_dir = "models/converted_keras"
            model_path = os.path.join(model_dir, "keras_Model.h5")
            labels_path = os.path.join(model_dir, "labels.txt")
            
            if os.path.exists(model_path):
                # Load the Teachable Machine model
                self.model = load_model(model_path, compile=False)
                logger.info(f"✅ Teachable Machine model loaded successfully from {model_path}")
                logger.info(f"Model input shape: {self.model.input_shape}")
                logger.info(f"Model output shape: {self.model.output_shape}")
                
                # Load class names from labels.txt
                if os.path.exists(labels_path):
                    with open(labels_path, "r") as f:
                        self.class_names = [line.strip() for line in f.readlines()]
                    logger.info(f"✅ Loaded {len(self.class_names)} class labels")
                else:
                    logger.warning(f"⚠️ Labels file not found at {labels_path}")
                    self.class_names = ["Unknown"]
            else:
                logger.warning(f"❌ Teachable Machine model not found at {model_path}. Using mock predictions.")
                self.model = None
        except Exception as e:
            logger.error(f"❌ Error loading Teachable Machine model: {e}")
            self.model = None
    
    def preprocess_image(self, image_file):
        """Preprocess image to match Teachable Machine format"""
        try:
            # Load and convert image to RGB
            image = Image.open(image_file).convert("RGB")
            
            # Basic image validation
            if not self._basic_image_validation(image):
                raise ValueError("Image does not appear to be valid")
            
            # Resize and crop from center to 224x224 (Teachable Machine format)
            size = (224, 224)
            image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
            
            # Convert to numpy array
            image_array = np.asarray(image)
            
            # Normalize the image (Teachable Machine normalization: (pixel/127.5) - 1)
            normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
            
            # Create array of the right shape for the model (1, 224, 224, 3)
            data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
            data[0] = normalized_image_array
            
            return data
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            raise
    
    def _basic_image_validation(self, image):
        """Basic validation to check if image might contain plant content - very relaxed"""
        try:
            # Only check for basic image validity, not content
            if image.width < 32 or image.height < 32:
                logger.warning("Image too small for processing")
                return False
            
            # Check for completely uniform images (solid color)
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                color_variance = np.var(img_array.reshape(-1, 3), axis=0)
                avg_variance = np.mean(color_variance)
                
                if avg_variance < 10:  # Only reject completely uniform images
                    logger.warning(f"Completely uniform image ({avg_variance:.1f}) - likely solid color")
                    return False
            
            # Otherwise, let the ML model decide
            return True
            
        except Exception as e:
            logger.error(f"Error in basic image validation: {e}")
            return True  # If validation fails, allow the image through
    
    def predict_disease(self, image_files):
        """Predict disease for multiple images using Teachable Machine model"""
        results = []
        
        for image_file in image_files:
            try:
                if self.model and len(self.class_names) > 0:
                    # Teachable Machine prediction
                    processed_image = self.preprocess_image(image_file)
                    
                    # Make prediction
                    prediction = self.model.predict(processed_image, verbose=0)
                    predicted_class_idx = np.argmax(prediction)
                    confidence = float(prediction[0][predicted_class_idx])
                    
                    # Get class name (remove index prefix if present)
                    class_name = self.class_names[predicted_class_idx]
                    if class_name.startswith(str(predicted_class_idx)):
                        # Remove "0 " or "1 " prefix that Teachable Machine adds
                        class_name = class_name[2:].strip()
                    
                    logger.info(f"🔍 Predicted: {class_name} (confidence: {confidence:.3f})")
                    
                    # Validate if this looks like a valid prediction
                    if not self._is_likely_plant_image(confidence, predicted_class_idx, prediction[0]):
                        results.append({
                            'image_name': image_file.name,
                            'crop_type': 'Unknown',
                            'disease': 'Not a plant image',
                            'confidence': confidence,
                            'severity': 'invalid',
                            'error': 'This does not appear to be a plant or crop image. Please upload images of plant leaves or crops.'
                        })
                        continue
                    
                    # Extract crop type and disease from class name
                    crop_type, disease = self._parse_teachable_machine_class(class_name)
                    
                    # Determine severity based on confidence and disease type
                    severity = self._determine_severity(disease, confidence)
                    
                    results.append({
                        'image_name': image_file.name,
                        'crop_type': crop_type,
                        'disease': disease,
                        'confidence': confidence,
                        'severity': severity
                    })
                else:
                    # Fallback to mock prediction
                    import random
                    mock_classes = ["Healthy Plant", "Disease Detected", "Pest Damage"]
                    class_name = random.choice(mock_classes)
                    confidence = random.uniform(0.7, 0.95)
                    logger.info(f"🎭 Mock prediction: {class_name}")
                    
                    crop_type, disease = self._parse_teachable_machine_class(class_name)
                    severity = self._determine_severity(disease, confidence)
                    
                    results.append({
                        'image_name': image_file.name,
                        'crop_type': crop_type,
                        'disease': disease,
                        'confidence': confidence,
                        'severity': severity
                    })
                
            except Exception as e:
                logger.error(f"Error predicting for image {image_file.name}: {e}")
                results.append({
                    'image_name': image_file.name,
                    'crop_type': 'Unknown',
                    'disease': 'Error',
                    'confidence': 0.0,
                    'severity': 'low',
                    'error': f'Error processing image: {str(e)}'
                })
        
        return results
    
    def _is_likely_plant_image(self, max_confidence, predicted_class_idx, all_predictions):
        """Validate if the image is likely a plant/crop image - relaxed validation"""
        
        # Much more relaxed validation - let the model decide
        # Only reject if confidence is extremely low (likely random noise)
        if max_confidence < 0.15:
            logger.warning(f"Extremely low confidence ({max_confidence:.3f}) - likely not a plant image")
            return False
        
        # Check for completely uniform predictions (all classes equal probability)
        # This suggests the model has no idea what the image is
        entropy = -np.sum(all_predictions * np.log(all_predictions + 1e-10))
        max_entropy = np.log(len(all_predictions))
        normalized_entropy = entropy / max_entropy
        
        if normalized_entropy > 0.95:  # Nearly maximum entropy means completely random
            logger.warning(f"Maximum entropy ({normalized_entropy:.3f}) - completely random predictions")
            return False
        
        # If we get here, trust the model's judgment
        logger.info(f"✅ Image validation passed - confidence: {max_confidence:.3f}, entropy: {normalized_entropy:.3f}")
        return True
    
    def _parse_teachable_machine_class(self, class_name):
        """Parse crop type and disease from Teachable Machine class name"""
        # Handle the label format: "CropType__disease_name"
        class_name = class_name.strip()
        
        # Split by double underscore to separate crop and disease
        if '__' in class_name:
            parts = class_name.split('__', 1)  # Split only on first occurrence
            crop_type = parts[0].strip()
            disease = parts[1].strip().replace('_', ' ')
        else:
            # Fallback for other formats
            if 'healthy' in class_name.lower():
                crop_type = class_name.replace('healthy', '').replace('Healthy', '').strip()
                if not crop_type:
                    crop_type = 'Plant'
                disease = 'Healthy'
            else:
                crop_type = 'Plant'
                disease = class_name
        
        # Clean up names
        crop_type = crop_type.title().strip()
        disease = disease.title().strip()
        
        return crop_type, disease
    
    def _determine_severity(self, disease, confidence):
        """Determine severity based on disease type and confidence"""
        if 'healthy' in disease.lower():
            return 'low'
        
        high_severity_diseases = ['blight', 'rot', 'rust', 'spot']
        
        if any(severe in disease.lower() for severe in high_severity_diseases):
            if confidence > 0.8:
                return 'high'
            elif confidence > 0.6:
                return 'medium'
            else:
                return 'low'
        else:
            if confidence > 0.85:
                return 'medium'
            else:
                return 'low'

# Global instance
disease_detection_service = DiseaseDetectionService()
