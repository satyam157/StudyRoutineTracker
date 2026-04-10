#!/usr/bin/env python3
"""Find available Groq models"""

import os
from dotenv import load_dotenv, find_dotenv
from groq import Groq

# Load API key
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)
api_key = os.environ.get("GROQ_API_KEY", "").strip()

client = Groq(api_key=api_key)

# List of models to try (based on Groq's available models)
models_to_test = [
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma-7b-it",
    "llama2-70b-4096",
    "gemma2-9b-it",
]

print("Testing Groq API with available models...\n")
print("=" * 60)

working_models = []

for model in models_to_test:
    print(f"\nTesting model: {model}")
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "Say OK"}],
            model=model,
            max_tokens=10,
        )
        print(f"  ✅ Works! Response: {response.choices[0].message.content.strip()}")
        working_models.append(model)
    except Exception as e:
        error_msg = str(e)
        if "decommissioned" in error_msg:
            print(f"  ❌ Decommissioned")
        elif "not found" in error_msg or "does not exist" in error_msg:
            print(f"  ❌ Model not found")
        elif "authentication" in error_msg or "unauthorized" in error_msg:
            print(f"  ❌ Authentication failed: {error_msg[:50]}")
        else:
            print(f"  ❌ Error: {error_msg[:80]}")

print("\n" + "=" * 60)
if working_models:
    print(f"\n✅ Working models found: {len(working_models)}")
    for m in working_models:
        print(f"   - {m}")
    print(f"\nBest model to use: {working_models[0]}")
else:
    print("\n❌ No working models found!")
