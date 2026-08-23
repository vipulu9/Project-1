"""Example OpenAI client usage for local experimentation.

This file should not be executed in production. Keep any real API calls in a
proper application service and store keys in environment variables.
"""

from openai import OpenAI


def build_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


if __name__ == "__main__":
    raise RuntimeError("This example client is not meant to run directly in production.")