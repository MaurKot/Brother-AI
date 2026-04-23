#!/usr/bin/env python3
"""Demo script to test CustomLLMProvider."""
import asyncio
import os

# Set fake token for demo (replace with real)
os.environ["HF_TOKEN"] = "your_huggingface_token_here"

from kai.llm.custom_provider import CustomLLMProvider


async def main():
    provider = CustomLLMProvider()
    prompt = "Hello, how are you?"
    response = await provider.complete(prompt, depth="fast", max_tokens=50)
    print(f"Prompt: {prompt}")
    print(f"Response: {response}")
    await provider.aclose()


if __name__ == "__main__":
    asyncio.run(main())