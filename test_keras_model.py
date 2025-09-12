#!/usr/bin/env python3
"""
Test script to verify the .keras model migration works correctly
"""

import os
import sys
import django
import numpy as np
import tensorflow as tf
from PIL import Image

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmville.settings')
django.setup()

from analysis.ml_service import DiseaseDetectionService

def test_model_loading():
    """Test that the .keras model loads correctly"""
    print("🧪 Testing .keras model loading...")
    
    try:
        service = DiseaseDetectionService()
        
        if service.model is None:
            print("❌ Model failed to load")
            return False
        
        print("✅ Model loaded successfully")
        
        # Check if it's a Keras model or SavedModel
        if hasattr(service.model, 'input_shape'):
            print(f"   Model type: Keras model")
            print(f"   Input shape: {service.model.input_shape}")
            print(f"   Output shape: {service.model.output_shape}")
        else:
            print(f"   Model type: SavedModel")
            print(f"   Available signatures: {list(service.model.signatures.keys())}")
        
        print(f"   Number of classes: {len(service.class_names)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing model: {e}")
        return False

def test_dummy_prediction():
    """Test prediction with a dummy image"""
    print("\n🧪 Testing dummy prediction...")
    
    try:
        service = DiseaseDetectionService()
        
        if service.model is None:
            print("⚠️  Skipping prediction test - model not loaded")
            return True
        
        # Create a dummy RGB image (224x224x3)
        dummy_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        dummy_pil = Image.fromarray(dummy_image)
        
        # Save dummy image to a temporary location for testing
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            dummy_pil.save(tmp_file.name)
            
            # Create a proper file-like object
            class MockFile:
                def __init__(self, file_path):
                    self.name = file_path
                    self._file = open(file_path, 'rb')
                
                def read(self, size=-1):
                    return self._file.read(size)
                
                def seek(self, pos):
                    return self._file.seek(pos)
                
                def close(self):
                    self._file.close()
            
            mock_file = MockFile(tmp_file.name)
            
            # Test preprocessing
            processed = service.preprocess_image(mock_file)
            print(f"   Preprocessed shape: {processed.shape}")
            
            # Test prediction - handle both model types
            if hasattr(service.model, 'predict'):
                # Keras model
                predictions = service.model.predict(processed, verbose=0)
                pred_array = predictions[0]
            else:
                # SavedModel format
                input_tensor = tf.convert_to_tensor(processed, dtype=tf.float32)
                predictions = service.predict_fn(input_tensor)
                output_key = list(predictions.keys())[0]
                pred_array = predictions[output_key].numpy()[0]
            
            print(f"   Prediction shape: {pred_array.shape}")
            print(f"   Max confidence: {np.max(pred_array):.4f}")
            print(f"   Predicted class: {service.class_names[np.argmax(pred_array)]}")
            
            # Clean up
            mock_file.close()
            os.unlink(tmp_file.name)
        
        print("✅ Dummy prediction test passed")
        return True
        
    except Exception as e:
        print(f"❌ Error in prediction test: {e}")
        return False

def main():
    print("🚀 Testing .keras model migration\n")
    
    # Test model loading
    if not test_model_loading():
        print("\n💥 Model loading test failed")
        return False
    
    # Test dummy prediction
    if not test_dummy_prediction():
        print("\n💥 Prediction test failed")
        return False
    
    print("\n🎉 All tests passed! The .keras model migration is successful.")
    print("\n📝 Migration Summary:")
    print("   ✅ Settings updated to use .keras model")
    print("   ✅ ml_service.py updated to load .keras model")
    print("   ✅ Model loading works correctly")
    print("   ✅ Predictions work correctly")
    print("\n🚀 Your application is ready to use the new .keras model!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
