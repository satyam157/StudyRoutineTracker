#!/usr/bin/env python3
"""Test Groq API connection"""

import os
import sys
from dotenv import load_dotenv, find_dotenv

# Load from explicit path
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
print(f"Loading .env from: {_env_path}")
print(f".env exists: {os.path.exists(_env_path)}")

load_dotenv(_env_path)

# Get API key
api_key = os.environ.get("GROQ_API_KEY", "").strip()
print(f"\n1. API Key loaded: {'Yes' if api_key else 'No'}")
print(f"   Key length: {len(api_key)} characters")
print(f"   Key starts with: {api_key[:10]}..." if api_key else "   No key")
print(f"   Key ends with: ...{api_key[-10:]}" if api_key else "   No key")

if not api_key:
    print("\n❌ FAIL: API key not found in .env")
    sys.exit(1)

# Test Groq import
print(f"\n2. Testing Groq import...")
try:
    from groq import Groq
    print("   ✅ Groq library imported successfully")
except ImportError as e:
    print(f"   ❌ FAIL: Could not import Groq: {e}")
    sys.exit(1)

# Test client initialization
print(f"\n3. Testing Groq client initialization...")
try:
    client = Groq(api_key=api_key)
    print("   ✅ Groq client initialized successfully")
except Exception as e:
    print(f"   ❌ FAIL: {e}")
    sys.exit(1)

# Test API call
print(f"\n4. Testing Groq API call with mixtral-8x7b-32768...")
try:
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Say 'Hello' in one word only."}],
        model="mixtral-8x7b-32768",
        max_tokens=100,
    )
    
    if response and response.choices and len(response.choices) > 0:
        message = response.choices[0].message.content
        print(f"   ✅ API call successful!")
        print(f"   Response: '{message}'")
    else:
        print(f"   ⚠️ Empty response from API")
        print(f"   Response object: {response}")
        
except Exception as e:
    error_msg = str(e)
    print(f"   ❌ FAIL: {error_msg}")
    
    if "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
        print(f"\n   This is an authentication error. Possible causes:")
        print(f"   - API key is invalid or expired")
        print(f"   - API key has been revoked")
        print(f"   - Groq account has been suspended")
    elif "model" in error_msg.lower():
        print(f"\n   This is a model error. The model might not exist or be available.")
    elif "rate" in error_msg.lower():
        print(f"\n   This is a rate limit error. Wait and try again.")
    
    sys.exit(1)

print(f"\n✅ ALL TESTS PASSED! Groq API is working correctly.")
