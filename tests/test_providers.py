#!/usr/bin/env python3
"""
Test script to verify provider chain configuration
"""

from src.llm.yaml_generator_multi import natural_language_to_yaml

# Test with default chain: Groq → OpenRouter → Gemini
print("Testing provider chain: Groq → OpenRouter → Gemini")
print("=" * 60)

description = "Create a simple blog with users and posts"

try:
    yaml_output = natural_language_to_yaml(description)
    print("\n✅ SUCCESS! Generated YAML:")
    print("=" * 60)
    print(yaml_output[:500])  # Print first 500 chars
    print("...")
    print("=" * 60)
except Exception as e:
    print(f"\n❌ FAILED: {e}")

print("\n\nTo test with different provider chains, use:")
print("  python llm/yaml_generator_multi.py 'your description' -p groq openrouter")
print("  python llm/yaml_generator_multi.py 'your description' -p gemini")
print("  python llm/yaml_generator_multi.py 'your description' -p ollama")
