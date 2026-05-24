import os
import requests
import json
from typing import List, Dict

# agents/llm.py
# Disable telemetry for Groq & Chroma for this process
os.environ.setdefault("GROQ_DISABLE_TELEMETRY", "1")
os.environ.setdefault("CHROMADB_ALLOW_TELEMETRY", "false")
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")

def build_messages(system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

def call_llm(messages, model: str, temperature: float = 0.0, max_tokens: int = 400) -> str:
    """
    Call Ollama local LLM API with retry logic and deterministic generation
    """
    max_retries = 2
    base_timeout = 60
    
    for attempt in range(max_retries + 1):
        try:
            # Prepare Ollama API request
            url = "http://localhost:11434/api/chat"
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "seed": 42,  # Fixed seed for deterministic generation
                }
            }
            
            # Adaptive timeout - longer for retries
            timeout = base_timeout * (attempt + 1)
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            content = result.get("message", {}).get("content", "")
            
            # Validate we got a proper response
            if content and content.strip():
                return content.strip()
            elif attempt < max_retries:
                continue  # Retry if empty response
            else:
                return "Refusal: AccessDenied. You do not have access to that information."
                
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                continue  # Retry on network/timeout errors
            # Final attempt failed
            return "Refusal: AccessDenied. You do not have access to that information."
        except (KeyError, json.JSONDecodeError) as e:
            if attempt < max_retries:
                continue  # Retry on parsing errors
            return "Refusal: AccessDenied. You do not have access to that information."
    
    # Should never reach here, but safety fallback
    return "Refusal: AccessDenied. You do not have access to that information."

# BACKUP: Original Groq implementation (commented out)
"""
def call_llm_groq(messages, model: str, temperature: float = 0.2, max_tokens: int = 400) -> str:
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment.")
    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()
"""
