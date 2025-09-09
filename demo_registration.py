#!/usr/bin/env python
"""
Demo script to show farmer registration functionality
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmville.settings')
django.setup()

from accounts.models import User
from accounts.serializers import UserRegistrationSerializer
from rest_framework_simplejwt.tokens import RefreshToken

def demo_farmer_registration():
    print("🌾 FarmVille Backend - Farmer Registration Demo")
    print("=" * 50)
    
    # Test data for farmer registration
    farmer_data = {
        'username': 'john_farmer',
        'email': 'john@farm.com',
        'password': 'securepass123',
        'password_confirm': 'securepass123',
        'role': 'farmer'
    }
    
    print(f"📝 Registering new farmer: {farmer_data['username']}")
    
    # Use the serializer to validate and create user
    serializer = UserRegistrationSerializer(data=farmer_data)
    
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        print("✅ Registration successful!")
        print(f"   User ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role}")
        print(f"   Date Joined: {user.date_joined}")
        
        print("\n🔑 JWT Tokens generated:")
        print(f"   Access Token: {str(refresh.access_token)[:50]}...")
        print(f"   Refresh Token: {str(refresh)[:50]}...")
        
        print("\n📱 Frontend Integration:")
        print("   The farmer can now:")
        print("   ✓ Login with email/password")
        print("   ✓ Upload crop images for analysis")
        print("   ✓ Receive AI disease detection")
        print("   ✓ Get treatment recommendations")
        print("   ✓ View analysis history")
        
        return user
    else:
        print("❌ Registration failed:")
        for field, errors in serializer.errors.items():
            print(f"   {field}: {', '.join(errors)}")
        return None

def demo_admin_registration():
    print("\n👨‍💼 Creating Admin User")
    print("-" * 30)
    
    admin_data = {
        'username': 'admin_user',
        'email': 'admin@farmville.com',
        'password': 'adminpass123',
        'password_confirm': 'adminpass123',
        'role': 'admin'
    }
    
    serializer = UserRegistrationSerializer(data=admin_data)
    
    if serializer.is_valid():
        admin = serializer.save()
        print(f"✅ Admin created: {admin.username} ({admin.role})")
        
        print("\n🔧 Admin can:")
        print("   ✓ Review AI recommendations")
        print("   ✓ Approve/reject treatments")
        print("   ✓ Provide expert opinions")
        print("   ✓ View dashboard analytics")
        
        return admin
    else:
        print("❌ Admin creation failed")
        return None

def demo_database_check():
    print("\n📊 Database Status")
    print("-" * 20)
    
    farmer_count = User.objects.filter(role='farmer').count()
    admin_count = User.objects.filter(role='admin').count()
    total_users = User.objects.count()
    
    print(f"   Total Users: {total_users}")
    print(f"   Farmers: {farmer_count}")
    print(f"   Admins: {admin_count}")

if __name__ == "__main__":
    try:
        # Demo farmer registration
        farmer = demo_farmer_registration()
        
        # Demo admin registration
        admin = demo_admin_registration()
        
        # Show database status
        demo_database_check()
        
        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("1. Start Django server: python manage.py runserver")
        print("2. Test API endpoints at: http://localhost:8000/api/")
        print("3. View API docs at: http://localhost:8000/api/docs/")
        print("4. Integrate with your Next.js frontend")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
