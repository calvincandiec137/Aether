import requests
import config
import time
import logging
import random
import re

logger = logging.getLogger(__name__)

# -------------------------------
# API Key Rotation for Groq
# -------------------------------
_groq_key_index = 0
_groq_key_usage = {}  # Track usage per key for smart rotation

def parse_retry_after(response_text: str, headers: dict) -> float:
    """
    Parse how long to wait from a 429 response.
    Checks Retry-After header first, then parses the Groq error message body.
    Falls back to 65s (a full TPM window) if nothing is found.
    """
    # Check standard Retry-After header
    retry_after = headers.get("retry-after") or headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after) + 0.5
        except ValueError:
            pass

    # Parse Groq's message: "Please try again in 2.15s."
    match = re.search(r"try again in ([\d.]+)s", response_text)
    if match:
        return float(match.group(1)) + 0.5

    # Default: wait for the 1-minute TPM window to reset
    return 65.0


def get_next_groq_key():
    """Get next Groq API key using round-robin rotation."""
    global _groq_key_index
    
    if not config.GROQ_API_KEYS:
        return None
    
    if len(config.GROQ_API_KEYS) == 1:
        return config.GROQ_API_KEYS[0]
    
    # Round-robin rotation
    key = config.GROQ_API_KEYS[_groq_key_index]
    _groq_key_index = (_groq_key_index + 1) % len(config.GROQ_API_KEYS)
    
    # Track usage
    _groq_key_usage[key] = _groq_key_usage.get(key, 0) + 1
    
    key_num = _groq_key_index if _groq_key_index > 0 else len(config.GROQ_API_KEYS)
    logger.debug(f"🔑 Using Groq API key #{key_num} ({key[:10]}...)")
    
    return key

# -------------------------------
# Provider Delay Handling
# -------------------------------
def get_provider_delay(provider):
    if provider == "groq":
        return config.GROQ_DELAY_SECONDS
    return 0.5  # Default delay

# -------------------------------
# Main LLM Call Function
# -------------------------------
def call_llm(model_spec, prompt, system_prompt=None):
    """
    model_spec format: provider/model_name
    Supported providers: groq
    """

    provider, model_name = model_spec.split("/", 1)
    
    if provider != "groq":
        logger.warning(f"⚠️ Provider '{provider}' not recognized, defaulting to 'groq'")
        provider = "groq"

    logger.info(f"🤖 Calling {provider}/{model_name} (prompt length: {len(prompt)} chars)")

    delay = get_provider_delay(provider)
    if delay > 0:
        time.sleep(delay)

    start_time = time.time()

    for attempt in range(config.MAX_RETRIES):
        try:
            # ==========================================================
            # GROQ (OpenAI-compatible API)
            # ==========================================================
            if not config.GROQ_API_KEYS:
                raise ValueError("No GROQ_API_KEY found in environment variables")
            
            # Get next API key (rotates automatically)
            api_key = get_next_groq_key()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024
            }
            
            response = requests.post(
                config.GROQ_ENDPOINT,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                timeout=60
            )
            
            if response.status_code == 429:
                wait = parse_retry_after(response.text, dict(response.headers))
                logger.warning(f"⏳ Rate limit (429) — waiting {wait:.1f}s before retry #{attempt + 1}...")
                time.sleep(wait)
                continue  # retry the loop without raising

            if response.status_code != 200:
                logger.error(f"❌ Groq API Error: {response.status_code} - {response.text}")
                response.raise_for_status()

            result = response.json()
            text = result["choices"][0]["message"]["content"]
            
            elapsed = time.time() - start_time
            logger.info(f"✓ Response received in {elapsed:.1f}s")
            return text

        except Exception as e:
            logger.error(f"❌ Error calling {provider}/{model_name}: {e}")
            if attempt < config.MAX_RETRIES - 1:
                wait = (config.RETRY_BACKOFF_FACTOR ** attempt) * 2
                logger.warning(f"⏳ Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    return ""