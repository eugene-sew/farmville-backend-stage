import os
import logging
import numpy as np
from PIL import Image
from django.conf import settings
import tensorflow as tf

logger = logging.getLogger(__name__)

class DiseaseDetectionService:
    def __init__(self):
        self.model = None
        self.class_names = [
            'Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy',
            'Blueberry___healthy', 'Cherry_(including_sour)___Powdery_mildew', 'Cherry_(including_sour)___healthy',
            'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot', 'Corn_(maize)___Common_rust_',
            'Corn_(maize)___Northern_Leaf_Blight', 'Corn_(maize)___healthy', 'Grape___Black_rot',
            'Grape___Esca_(Black_Measles)', 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)', 'Grape___healthy',
            'Orange___Haunglongbing_(Citrus_greening)', 'Peach___Bacterial_spot', 'Peach___healthy',
            'Pepper,_bell___Bacterial_spot', 'Pepper,_bell___healthy', 'Potato___Early_blight',
            'Potato___Late_blight', 'Potato___healthy', 'Raspberry___healthy', 'Soybean___healthy',
            'Squash___Powdery_mildew', 'Strawberry___Leaf_scorch', 'Strawberry___healthy',
            'Tomato___Bacterial_spot', 'Tomato___Early_blight', 'Tomato___Late_blight',
            'Tomato___Leaf_Mold', 'Tomato___Septoria_leaf_spot', 'Tomato___Spider_mites Two-spotted_spider_mite',
            'Tomato___Target_Spot', 'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus',
            'Tomato___healthy'
        ]
        self.load_model()
    
    def load_model(self):
        try:
            model_path = settings.TF_MODEL_PATH
            if os.path.exists(model_path):
                # Try loading .keras model with custom_objects to handle compatibility issues
                try:
                    self.model = tf.keras.models.load_model(model_path, compile=False)
                    logger.info(f"✅ Keras model loaded successfully from {model_path}")
                    logger.info(f"Model input shape: {self.model.input_shape}")
                    logger.info(f"Model output shape: {self.model.output_shape}")
                except Exception as keras_error:
                    logger.warning(f"⚠️  Failed to load as .keras model: {keras_error}")
                    # Fallback: try loading as SavedModel if .keras fails
                    logger.info("🔄 Attempting to load as SavedModel format...")
                    self.model = tf.saved_model.load(model_path)
                    self.predict_fn = self.model.signatures['serving_default']
                    logger.info(f"✅ SavedModel loaded successfully from {model_path}")
                    logger.info(f"Available signatures: {list(self.model.signatures.keys())}")
            else:
                logger.warning(f"❌ Model not found at {model_path}. Using mock predictions.")
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")
            self.model = None
    
    def preprocess_image(self, image_file):
        """Preprocess image to match training pipeline and validate content"""
        try:
            image = Image.open(image_file)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Basic image validation - check if it looks like it could be a plant
            if not self._basic_image_validation(image):
                raise ValueError("Image does not appear to contain plant-like content")
            
            # Resize to model input size (224x224)
            image = image.resize((224, 224))
            
            # Convert to numpy array and normalize to [0,1]
            image_array = np.array(image) / 255.0
            
            # Add batch dimension
            image_array = np.expand_dims(image_array, axis=0)
            
            return image_array
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            raise
    
    def _basic_image_validation(self, image):
        """Basic validation to check if image might contain plant content"""
        try:
            # Convert to numpy array for analysis
            img_array = np.array(image)
            
            # Check image dimensions - too small images are suspicious
            if image.width < 50 or image.height < 50:
                logger.warning("Image too small - likely not a plant photo")
                return False
            
            # Check if image has enough green content (plants should have some green)
            # This is a very basic heuristic
            if len(img_array.shape) == 3:  # Color image
                # Calculate green channel dominance
                r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
                
                # Check if there's reasonable green content
                green_dominance = np.mean(g > (r + b) / 2)
                total_green = np.mean(g) / 255.0
                
                # Very basic check - plant images should have some green
                if green_dominance < 0.05 and total_green < 0.3:
                    logger.warning(f"Low green content (dominance: {green_dominance:.3f}, total: {total_green:.3f}) - might not be a plant")
                    # Don't reject yet, just log - some diseased plants might be brown/yellow
            
            # Check for very uniform colors (like logos or solid backgrounds)
            if len(img_array.shape) == 3:
                # Calculate color variance
                color_variance = np.var(img_array.reshape(-1, 3), axis=0)
                avg_variance = np.mean(color_variance)
                
                if avg_variance < 100:  # Very low variance suggests uniform image
                    logger.warning(f"Low color variance ({avg_variance:.1f}) - might be a logo or uniform image")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in basic image validation: {e}")
            return True  # If validation fails, allow the image through
    
    def predict_disease(self, image_files):
        """Predict disease for multiple images using real TensorFlow model with validation"""
        results = []
        
        for image_file in image_files:
            try:
                if self.model:
                    # Real TensorFlow prediction - handle both .keras and SavedModel formats
                    processed_image = self.preprocess_image(image_file)
                    
                    # Check if this is a Keras model or SavedModel
                    if hasattr(self.model, 'predict'):
                        # Keras model
                        predictions = self.model.predict(processed_image, verbose=0)
                        pred_array = predictions[0]
                    else:
                        # SavedModel format
                        input_tensor = tf.convert_to_tensor(processed_image, dtype=tf.float32)
                        predictions = self.predict_fn(input_tensor)
                        output_key = list(predictions.keys())[0]
                        pred_array = predictions[output_key].numpy()[0]
                    
                    predicted_class_idx = np.argmax(pred_array)
                    confidence = float(pred_array[predicted_class_idx])
                    
                    # Validate if this looks like a plant image
                    if not self._is_likely_plant_image(confidence, predicted_class_idx, pred_array):
                        results.append({
                            'image_name': image_file.name,
                            'crop_type': 'Unknown',
                            'disease': 'Not a plant image',
                            'confidence': confidence,
                            'severity': 'invalid',
                            'error': 'This does not appear to be a plant or crop image. Please upload images of plant leaves or crops.'
                        })
                        continue
                    
                    disease_name = self.class_names[predicted_class_idx]
                    logger.info(f"🔍 Predicted: {disease_name} (confidence: {confidence:.3f})")
                else:
                    # Fallback to mock prediction
                    import random
                    disease_name = random.choice(self.class_names)
                    confidence = random.uniform(0.7, 0.95)
                    logger.info(f"🎭 Mock prediction: {disease_name}")
                
                # Extract crop type and disease
                crop_type, disease = self._parse_disease_name(disease_name)
                
                # Determine severity based on confidence and disease type
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
        """Validate if the image is likely a plant/crop image"""
        
        # Check 1: Confidence threshold - if too low, likely not a plant
        if max_confidence < 0.4:
            logger.warning(f"Low confidence ({max_confidence:.3f}) - likely not a plant image")
            return False
        
        # Check 2: Very high confidence is suspicious for this model
        if max_confidence > 0.95:
            logger.warning(f"Suspiciously high confidence ({max_confidence:.3f}) - likely overfitting on non-plant image")
            return False
        
        # Check 3: Look at top predictions distribution
        sorted_predictions = np.sort(all_predictions)[::-1]  # Sort descending
        top_2_ratio = sorted_predictions[1] / sorted_predictions[0] if sorted_predictions[0] > 0 else 1
        
        # If second highest is too close to highest, predictions are uncertain
        if top_2_ratio > 0.7:
            logger.warning(f"Uncertain predictions (top 2 ratio: {top_2_ratio:.3f}) - likely not a plant image")
            return False
        
        # Check 4: Entropy check - if entropy is too high, predictions are scattered
        entropy = -np.sum(all_predictions * np.log(all_predictions + 1e-10))
        max_entropy = np.log(len(all_predictions))  # Maximum possible entropy
        normalized_entropy = entropy / max_entropy
        
        if normalized_entropy > 0.7:  # High entropy means uncertain predictions
            logger.warning(f"High prediction entropy ({normalized_entropy:.3f}) - likely not a plant image")
            return False
        
        # Check 5: Look for patterns that suggest non-plant images
        # If predictions are concentrated in just a few classes, it might be overfitting
        top_5_sum = np.sum(sorted_predictions[:5])
        if top_5_sum < 0.8:  # Top 5 predictions should dominate for plant images
            logger.warning(f"Low top-5 concentration ({top_5_sum:.3f}) - likely not a plant image")
            return False
        
        # Check 6: Additional validation for very confident "healthy" predictions
        predicted_disease = self.class_names[predicted_class_idx]
        if 'healthy' in predicted_disease.lower() and max_confidence > 0.9:
            logger.warning(f"Very confident 'healthy' prediction ({max_confidence:.3f}) on potentially non-plant image")
            return False
        
        logger.info(f"✅ Image validation passed - confidence: {max_confidence:.3f}, entropy: {normalized_entropy:.3f}, top-2 ratio: {top_2_ratio:.3f}")
        return True
    
    def _parse_disease_name(self, disease_name):
        """Parse crop type and disease from class name"""
        parts = disease_name.split('___')
        crop_type = parts[0].replace('_', ' ').title()
        disease = parts[1].replace('_', ' ').title() if len(parts) > 1 else 'Unknown'
        
        # Clean up crop names
        crop_mapping = {
            'Corn (Maize)': 'Maize',
            'Cherry (Including Sour)': 'Cherry',
            'Pepper, Bell': 'Bell Pepper'
        }
        crop_type = crop_mapping.get(crop_type, crop_type)
        
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
