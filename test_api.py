#!/usr/bin/env python
"""
Simple test script to verify API endpoints
Run after setting up the Django server
"""

import requests
import json
import os

BASE_URL = "http://localhost:8000/api"

def test_registration():
    """Test user registration"""
    data = {
        "username": "testfarmer",
        "email": "farmer@test.com", 
        "password": "testpass123",
        "password_confirm": "testpass123",
        "role": "farmer"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register/", json=data)
    print(f"Registration: {response.status_code}")
    if response.status_code == 201:
        result = response.json()
        print(f"User created: {result['user']['username']}")
        return result['tokens']['access']
    else:
        print(f"Error: {response.json()}")
        return None

def test_login():
    """Test user login"""
    data = {
        "email": "farmer@test.com",
        "password": "testpass123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login/", json=data)
    print(f"Login: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Login successful: {result['user']['role']}")
        return result['tokens']['access']
    else:
        print(f"Error: {response.json()}")
        return None

def test_profile(token):
    """Test profile endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/profile/", headers=headers)
    print(f"Profile: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Profile: {result['username']} ({result['role']})")
    else:
        print(f"Error: {response.json()}")

def test_analysis_upload(token):
    """Test analysis upload (mock)"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a simple test image file
    test_image_content = b"fake image content for testing"
    files = {
        'images': ('test.jpg', test_image_content, 'image/jpeg')
    }
    
    response = requests.post(f"{BASE_URL}/analysis/upload/", 
                           headers=headers, files=files)
    print(f"Analysis Upload: {response.status_code}")
    if response.status_code == 201:
        result = response.json()
        print(f"Analysis created: {result['crop_type']} - {result['disease']}")
        return result['id']
    else:
        print(f"Error: {response.json()}")
        return None

def test_analysis_history(token):
    """Test analysis history"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/analysis/history/", headers=headers)
    print(f"Analysis History: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Found {len(result.get('results', []))} analyses")
    else:
        print(f"Error: {response.json()}")

def main():
    print("Testing FarmVille API...")
    print("=" * 40)
    
    # Test registration or login
    token = test_registration()
    if not token:
        token = test_login()
    
    if token:
        print("\n" + "=" * 40)
        test_profile(token)
        print("\n" + "=" * 40)
        analysis_id = test_analysis_upload(token)
        print("\n" + "=" * 40)
        test_analysis_history(token)
    else:
        print("Could not authenticate, skipping other tests")

if __name__ == "__main__":
    main()
