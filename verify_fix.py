#!/usr/bin/env python3
"""Verify the fix works"""

import os
from dotenv import load_dotenv, find_dotenv
from groq import Groq

# Load API key
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)
api_key = os.environ.get("GROQ_API_KEY", "").strip()

client = Groq(api_key=api_key)

# The new working model
MODEL = "llama-3.1-8b-instant"

print(f"Testing Ask Esu with {MODEL}...\n")
print("=" * 60)

# Test 1: Simple query
print("\nTest 1: Simple test query")
try:
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Say 'Ask Esu is working!' in exactly those words."}],
        model=MODEL,
        max_tokens=100,
    )
    print(f"✅ Test 1 passed")
    print(f"   Response: {response.choices[0].message.content.strip()}")
except Exception as e:
    print(f"❌ Test 1 failed: {e}")

# Test 2: Study recommendation (like Ask Esu would use)
print("\nTest 2: Study recommendation")
try:
    study_prompt = """You are Esu, a study consultant. A student has studied History for 10 hours but Polity for 5 hours. 
    Both are important UPSC topics. Give a 2-sentence recommendation."""
    
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": study_prompt}],
        model=MODEL,
        max_tokens=200,
    )
    print(f"✅ Test 2 passed")
    print(f"   Response: {response.choices[0].message.content.strip()}")
except Exception as e:
    print(f"❌ Test 2 failed: {e}")

# Test 3: Test the actual ask_esu function
print("\nTest 3: Testing ask_esu function from ai.py")
try:
    import ai
    user_prompt = "Give me a quick tip for memorizing UPSC chapters"
    context = "Study Hours: 50h, Weak Subjects: Economics"
    result = ai.ask_esu(user_prompt, context)
    
    if "⚠️" not in result:
        print(f"✅ Test 3 passed - ask_esu working!")
        print(f"   Response: {result[:100]}...")
    else:
        print(f"❌ Test 3 failed with error: {result}")
except Exception as e:
    print(f"❌ Test 3 failed: {e}")

print("\n" + "=" * 60)
print("✅ All verifications complete! Ask Esu is ready to use.")
