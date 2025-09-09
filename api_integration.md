# Frontend Integration Guide

## Updating the Frontend API Service

To integrate with this Django backend, update your frontend's `lib/services/api.ts` file:

```typescript
// Update the API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

// Update the uploadAndAnalyze method
async uploadAndAnalyze(request: UploadImagesRequest): Promise<ApiResponse<AnalysisResponse>> {
  const formData = new FormData()
  
  // Add images to form data
  request.images.forEach((image, index) => {
    formData.append('images', image)
  })
  
  try {
    const response = await fetch(`${API_BASE_URL}/analysis/upload/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getAccessToken()}`, // Add your JWT token here
      },
      body: formData,
    })

    const data = await response.json()

    if (!response.ok) {
      return {
        success: false,
        error: data.error || 'Analysis failed',
      }
    }

    return {
      success: true,
      data: {
        id: data.id,
        disease: data.disease,
        confidence: data.confidence,
        severity: data.severity,
        affectedAreas: data.affectedAreas || [],
        cropType: data.crop_type,
      },
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Network error',
    }
  }
}
```

## Authentication Integration

Add JWT token management to your auth store:

```typescript
// In your auth store, after login:
const response = await fetch(`${API_BASE_URL}/auth/login/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ email, password }),
})

const data = await response.json()

if (response.ok) {
  // Store tokens
  localStorage.setItem('access_token', data.tokens.access)
  localStorage.setItem('refresh_token', data.tokens.refresh)
  
  // Set user data
  set({ 
    user: data.user, 
    isAuthenticated: true 
  })
}
```

## API Endpoints Mapping

| Frontend Expectation | Django Backend Endpoint |
|---------------------|------------------------|
| `POST /api/upload` | `POST /api/analysis/upload/` |
| `GET /api/history` | `GET /api/analysis/history/` |
| `GET /api/analysis/:id` | `GET /api/analysis/:id/` |
| `POST /api/auth/login` | `POST /api/auth/login/` |
| `GET /api/admin/pending` | `GET /api/admin/pending/` |
| `POST /api/admin/review/:id` | `POST /api/admin/review/:id/` |

## Response Format Compatibility

The Django backend returns responses in the exact format expected by your frontend:

```json
{
  "analysis_id": "uuid",
  "id": "uuid",
  "crop_type": "Tomato", 
  "disease": "Late Blight",
  "confidence": "89%",
  "severity": "high",
  "results": [
    {
      "image_name": "leaf1.jpg",
      "disease": "Late Blight", 
      "severity": "High",
      "confidence": 0.89
    }
  ],
  "recommendations": [
    {
      "id": "uuid",
      "generated_by": "AI",
      "content": "Treatment recommendations...",
      "status": "pending"
    }
  ]
}
```
