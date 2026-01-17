#!/usr/bin/env python3
"""
Test script to verify provider chain configuration
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.dsl_generate import natural_language_to_yaml

def main():
    parser = argparse.ArgumentParser(description="Test LLM provider chain")
    parser.add_argument("-m", "--model", help="Specific model/provider to test (groq, gemini, openrouter, ollama)")
    args = parser.parse_args()

    # Test with default chain
    print(f"Testing provider chain (Preferred: {args.model})")
    print("=" * 60)

    description = "Create a simple blog with users and posts"

    try:
        result = natural_language_to_yaml(description, primary_model=args.model)
        print("\n✅ SUCCESS! Generated YAML:")
        print("=" * 60)
        print(result.content[:500])  # Print first 500 chars
        print("...")
        print("=" * 60)
        print("\nStats:")
        print(f"Provider: {result.provider}")
        print(f"Time: {result.duration_seconds}s")

        if result.total_tokens:
            print(f"Input tokens: {result.input_tokens}")
            print(f"Output tokens: {result.output_tokens}")
            print(f"Total amount of tokens: {result.total_tokens}")
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")

    print("\n\nTo test with different provider chains, use:")
    print("  python tests/test_providers.py -m groq")
    print("  python tests/test_providers.py -m gemini")
    print("  python tests/test_providers.py -m ollama")

if __name__ == "__main__":
    main()
