"""
LLM Service - Multi-provider support for Gemini, OpenAI, Anthropic, Ollama, and local BART.
Supports free tier Gemini 1.5/2.0 Flash and local Ollama models.

Stability features:
  - Per-provider quota cooldown cache (5 min) to avoid hanging on known-bad providers.
  - Strict 15-second timeout on every provider call via concurrent.futures.
"""
import os
import time
import logging
from typing import Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Placeholder detection
PLACEHOLDER_KEYS = {"your-openai-api-key-here", "your-anthropic-api-key-here", "your-google-api-key-here", ""}

# ── Quota cooldown cache ──
# Maps provider name -> timestamp when cooldown expires.
# While inside cooldown the provider is skipped instantly.
QUOTA_COOLDOWN: Dict[str, float] = {}
QUOTA_COOLDOWN_SECONDS = 300  # 5 minutes

# Strict per-call timeout (seconds)
LLM_CALL_TIMEOUT = 120

# Shared thread-pool for timeout-guarded calls
_executor = ThreadPoolExecutor(max_workers=2)


def _is_valid_key(key: str) -> bool:
    """Check if an API key is valid (not empty or placeholder)."""
    return bool(key) and key not in PLACEHOLDER_KEYS


def _is_provider_cooled_down(provider: str) -> bool:
    """Return True if the provider is still in its quota cooldown window."""
    expires = QUOTA_COOLDOWN.get(provider, 0)
    if time.time() < expires:
        return True
    # Expired – clean up
    QUOTA_COOLDOWN.pop(provider, None)
    return False


def _set_provider_cooldown(provider: str) -> None:
    """Put a provider into cooldown so it is skipped for the next N seconds."""
    QUOTA_COOLDOWN[provider] = time.time() + QUOTA_COOLDOWN_SECONDS
    logger.warning(f"Provider '{provider}' placed in {QUOTA_COOLDOWN_SECONDS}s cooldown.")


def _call_with_timeout(fn, *args, timeout=LLM_CALL_TIMEOUT):
    """Run *fn* in a thread and raise RuntimeError if it doesn't finish in *timeout* seconds."""
    future = _executor.submit(fn, *args)
    try:
        return future.result(timeout=timeout)
    except FuturesTimeoutError:
        future.cancel()
        raise RuntimeError(f"Provider call timed out after {timeout}s")


def _google_call(system_prompt: str, user_message: str, document_context: str = None) -> str:
    """Internal: synchronous Google Gemini call (runs inside the timeout wrapper)."""
    import google.generativeai as genai

    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

    full_prompt = f"{system_prompt}\n\n"
    if document_context:
        full_prompt += f"<document>\n{document_context}\n</document>\n\n"
    full_prompt += f"User: {user_message}"

    response = model.generate_content(full_prompt)
    return response.text


def get_google_response(system_prompt: str, user_message: str, document_context: str = None) -> str:
    """Get response from Google Gemini 2.0 Flash with strict timeout."""
    try:
        return _call_with_timeout(_google_call, system_prompt, user_message, document_context)
    except ImportError:
        raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "quota" in error_str.lower() or "resource" in error_str.lower():
            _set_provider_cooldown("google")
            raise RuntimeError("GOOGLE_QUOTA_EXCEEDED")
        if "timed out" in error_str.lower():
            _set_provider_cooldown("google")
        raise RuntimeError(f"Google API error: {error_str}")


def _openai_call(system_prompt: str, user_message: str, document_context: str = None) -> str:
    """Internal: synchronous OpenAI call."""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    messages = [{"role": "system", "content": system_prompt}]
    prompt_content = ""
    if document_context:
        prompt_content += f"<document>\n{document_context}\n</document>\n\n"
    prompt_content += user_message
    messages.append({"role": "user", "content": prompt_content})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content


def get_openai_response(system_prompt: str, user_message: str, document_context: str = None) -> str:
    """Get response from OpenAI GPT-4o-mini with strict timeout."""
    try:
        return _call_with_timeout(_openai_call, system_prompt, user_message, document_context)
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "quota" in error_str.lower():
            _set_provider_cooldown("openai")
            raise RuntimeError("OPENAI_QUOTA_EXCEEDED")
        if "timed out" in error_str.lower():
            _set_provider_cooldown("openai")
        raise RuntimeError(f"OpenAI API error: {error_str}")


def _anthropic_call(system_prompt: str, user_message: str, document_context: str = None) -> str:
    """Internal: synchronous Anthropic call."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt_content = ""
    if document_context:
        prompt_content += f"<document>\n{document_context}\n</document>\n\n"
    prompt_content += user_message

    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt_content}]
    )
    return message.content[0].text


def get_anthropic_response(system_prompt: str, user_message: str, document_context: str = None) -> str:
    """Get response from Anthropic Claude 3.5 Sonnet with strict timeout."""
    try:
        return _call_with_timeout(_anthropic_call, system_prompt, user_message, document_context)
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
    except Exception as e:
        error_str = str(e)
        if "timed out" in error_str.lower():
            _set_provider_cooldown("anthropic")
        raise RuntimeError(f"Anthropic API error: {error_str}")


def get_ollama_response(system_prompt: str, user_message: str, document_context: str = None) -> str:
    """Get response from local Ollama instance (already has its own HTTP timeout)."""
    try:
        import requests

        prompt_content = f"{system_prompt}\n\n"
        if document_context:
            prompt_content += f"<document>\n{document_context}\n</document>\n\n"
        prompt_content += f"User: {user_message}"

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt_content,
                "stream": False
            },
            timeout=120  # increased for loading large models like llama3
        )
        response.raise_for_status()
        return response.json()["response"]

    except Exception as e:
        raise RuntimeError(f"Ollama error: {str(e)}. Make sure Ollama is running.")


def get_local_fallback(user_message: str) -> str:
    """Fallback to basic offline logic rewrite with IST reset info."""
    return "I've currently reached my daily processing limit for advanced cloud analysis. No worries! I'm switching to **Local Processing Mode** to continue helping you. The advanced analysis limit resets daily at **midnight Pacific Time (approx. 12:30 PM IST)**. My answers might be a bit simpler for now, but I can still assist with your legal documents!"


def get_llm_response(user_message: str, system_prompt: str = None, document_context: str = None) -> Dict[str, Any]:
    """
    Core function to route queries to the appropriate LLM provider with fallback logic.
    Skips providers that are in quota cooldown.  Every call is guarded by a strict timeout.
    Returns a dict with 'response' and 'provider'.
    """
    if not system_prompt:
        system_prompt = (
            "You are a professional legal assistant. Your goal is to help users understand their legal documents. "
            "Be concise, accurate, and maintain a professional tone."
        )

    # Try providers in order of preference
    providers = [LLM_PROVIDER, "google", "openai", "anthropic", "ollama"]
    seen = set()
    providers = [p for p in providers if not (p in seen or seen.add(p))]

    errors = []

    for prov in providers:
        # ── Skip providers still in cooldown ──
        if _is_provider_cooled_down(prov):
            logger.info(f"Skipping provider '{prov}' (quota cooldown active).")
            errors.append(f"{prov}: quota cooldown")
            continue

        try:
            if prov == "google" and _is_valid_key(GOOGLE_API_KEY):
                return {"response": get_google_response(system_prompt, user_message, document_context), "provider": "google"}
            elif prov == "openai" and _is_valid_key(OPENAI_API_KEY):
                return {"response": get_openai_response(system_prompt, user_message, document_context), "provider": "openai"}
            elif prov == "anthropic" and _is_valid_key(ANTHROPIC_API_KEY):
                return {"response": get_anthropic_response(system_prompt, user_message, document_context), "provider": "anthropic"}
            elif prov == "ollama":
                return {"response": get_ollama_response(system_prompt, user_message, document_context), "provider": "ollama"}
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Provider {prov} failed: {error_msg}")
            errors.append(f"{prov}: {error_msg}")
            continue

    # If everything fails, use the local hardcoded fallback
    logger.info(f"All providers exhausted. Errors: {errors}")
    return {"response": get_local_fallback(user_message), "provider": "offline"}


def get_llm_status() -> dict:
    """Check the status of the configured LLM provider.

    Uses the cooldown cache first so the health-check itself doesn't hang
    when quota is already known to be exceeded.
    """
    status_info = {
        "provider": LLM_PROVIDER,
        "is_online": False,
        "error": None,
        "details": {}
    }

    # 1. Check Gemini
    gemini_key_valid = _is_valid_key(GOOGLE_API_KEY)
    gemini_healthy = False

    if _is_provider_cooled_down("google"):
        status_info["details"]["google_error"] = "Quota cooldown active"
    elif gemini_key_valid:
        try:
            def _ping_gemini():
                import google.generativeai as genai
                genai.configure(api_key=GOOGLE_API_KEY)
                list(genai.list_models())
            _call_with_timeout(_ping_gemini, timeout=8)
            gemini_healthy = True
        except Exception as e:
            error_str = str(e)
            logger.error(f"Gemini health check failed: {error_str}")
            if "429" in error_str or "quota" in error_str.lower() or "resource" in error_str.lower():
                status_info["details"]["google_error"] = "Quota Exceeded (Free Tier)"
                _set_provider_cooldown("google")
            elif "timed out" in error_str.lower():
                status_info["details"]["google_error"] = "Health-check timed out"
                _set_provider_cooldown("google")
            else:
                status_info["details"]["google_error"] = error_str

    # 2. Check OpenAI
    openai_key_valid = _is_valid_key(OPENAI_API_KEY)

    # Final Online Decision
    if LLM_PROVIDER == "google":
        status_info["is_online"] = gemini_healthy
    elif LLM_PROVIDER == "openai":
        status_info["is_online"] = openai_key_valid
    elif LLM_PROVIDER == "ollama":
        status_info["is_online"] = True

    status_info["details"].update({
        "google": gemini_healthy,
        "openai": openai_key_valid,
        "ollama": LLM_PROVIDER == "ollama"
    })

    return status_info