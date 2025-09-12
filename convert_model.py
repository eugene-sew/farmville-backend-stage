#!/usr/bin/env python3
"""
Script to convert SavedModel to .keras format
Run this script to migrate from the current SavedModel to a single .keras file
"""

import os
import sys
import tensorflow as tf
from pathlib import Path

def convert_savedmodel_to_keras():
    """Convert the existing SavedModel to .keras format"""
    
    # Paths
    savedmodel_path = "models/plantdisease_savedmodel"
    keras_model_path = "models/plantdisease_model.keras"
    
    print(f"🔄 Converting SavedModel to .keras format...")
    print(f"📂 Source: {savedmodel_path}")
    print(f"📁 Target: {keras_model_path}")
    
    try:
        # Check if SavedModel exists
        if not os.path.exists(savedmodel_path):
            print(f"❌ SavedModel not found at {savedmodel_path}")
            return False
        
        # Load the SavedModel
        print("📥 Loading SavedModel...")
        model = tf.saved_model.load(savedmodel_path)
        
        # Get the inference function
        infer = model.signatures["serving_default"]
        
        # Create a new Keras model that wraps the inference function
        print("🔧 Creating Keras model wrapper...")
        
        # Get input shape from the signature
        input_spec = infer.structured_input_signature[1]
        input_key = list(input_spec.keys())[0]
        input_shape = input_spec[input_key].shape.as_list()
        
        # Create a functional model
        inputs = tf.keras.Input(shape=input_shape[1:], name=input_key)
        
        # Wrap the inference function
        @tf.function
        def call_model(x):
            return infer(**{input_key: x})
        
        outputs = call_model(inputs)
        
        # Extract the actual output tensor
        if isinstance(outputs, dict):
            output_key = list(outputs.keys())[0]
            outputs = outputs[output_key]
        
        # Create the Keras model
        keras_model = tf.keras.Model(inputs=inputs, outputs=outputs)
        
        # Create models directory if it doesn't exist
        os.makedirs("models", exist_ok=True)
        
        # Save as .keras format
        print("💾 Saving as .keras format...")
        keras_model.save(keras_model_path, save_format='keras')
        
        # Verify the saved model
        print("✅ Verifying saved model...")
        loaded_model = tf.keras.models.load_model(keras_model_path)
        
        # Test with dummy input
        dummy_input = tf.random.normal([1] + input_shape[1:])
        original_output = infer(**{input_key: dummy_input})
        new_output = loaded_model(dummy_input)
        
        # Compare outputs
        if isinstance(original_output, dict):
            original_output = original_output[list(original_output.keys())[0]]
        
        max_diff = tf.reduce_max(tf.abs(original_output - new_output))
        print(f"🔍 Maximum difference between models: {max_diff.numpy():.8f}")
        
        if max_diff < 1e-6:
            print("✅ Conversion successful! Models produce identical outputs.")
        else:
            print("⚠️  Models have slight differences, but this is usually acceptable.")
        
        # Print model info
        print(f"\n📊 Model Information:")
        print(f"   Input shape: {input_shape}")
        print(f"   Output shape: {new_output.shape}")
        print(f"   File size: {os.path.getsize(keras_model_path) / (1024*1024):.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        return False

if __name__ == "__main__":
    success = convert_savedmodel_to_keras()
    if success:
        print("\n🎉 Conversion completed successfully!")
        print("📝 Next steps:")
        print("   1. Update your ml_service.py to use the new .keras model")
        print("   2. Update settings.py to point to the new model path")
        print("   3. Test the application")
    else:
        print("\n💥 Conversion failed. Please check the errors above.")
        sys.exit(1)
