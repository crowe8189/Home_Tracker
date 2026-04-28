"""Run this locally to see which Gemini models your API key can access.
Usage: python list_gemini_models.py
"""
import os
import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY") or input("Paste your GEMINI_API_KEY: ").strip()
genai.configure(api_key=api_key)

print("\nAvailable models that support generateContent:\n")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"  {m.name}")
