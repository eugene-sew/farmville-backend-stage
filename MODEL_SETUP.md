# Model Setup Instructions

Due to GitHub's file size limitations, the TensorFlow model files are not included in this repository. Follow these steps to set up the model:

## Option 1: Download Pre-trained Model
1. Download the model from [your model hosting location]
2. Extract to `models/plantdisease_savedmodel/`
3. Ensure the directory structure matches:
   ```
   models/
   └── plantdisease_savedmodel/
       ├── fingerprint.pb
       ├── saved_model.pb
       ├── assets/
       └── variables/
           ├── variables.data-00000-of-00001
           └── variables.index
   ```

## Option 2: Use Git LFS (Recommended for team development)
1. Install Git LFS: `git lfs install`
2. Track model files: `git lfs track "models/**"`
3. Add and commit: `git add .gitattributes models/`
4. Push: `git push origin main`

## Option 3: Train Your Own Model
1. Use the training scripts in the `training/` directory
2. Export model in SavedModel format:
   ```python
   model.save('models/plantdisease_savedmodel', save_format='tf')
   ```

## Model Requirements
- **Format**: TensorFlow SavedModel (.pb + variables)
- **Input Shape**: (None, 224, 224, 3)
- **Output**: Disease classification probabilities
- **Classes**: Must match the class names in `ml_service.py`

## Fallback Behavior
If no model is found, the system will:
- Return mock predictions for development
- Log warnings about missing model
- Continue to function for API testing
