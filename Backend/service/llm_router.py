"""
LLM Router — Multi-provider, key rotation, retry, fallback.
Supports: OpenAI, Anthropic, Gemini, Groq, Ollama
"""
import json
import logging
import time
import threading
from typing import Optional

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

AGENT_PROVIDER_MAP = {
    "parser": "PARSER_PROVIDER",
    "matcher": "MATCHER_PROVIDER",
    "chat": "CHAT_PROVIDER",
}

# ── Provider rotation for load balancing ───────────────────────────────────────

_available_providers = []
_provider_index = 0
_provider_lock = threading.Lock()


def _init_available_providers():
    global _available_providers
    providers = []
    
    # Check which providers have valid keys
    if settings.GROQ_API_KEY or settings.GROQ_API_KEYS:
        if settings.GROQ_API_KEY and len(settings.GROQ_API_KEY) > 10:
            providers.append("groq")
        elif settings.GROQ_API_KEYS and len(settings.GROQ_API_KEYS) > 10:
            providers.append("groq")
    
    if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 10:
        providers.append("gemini")
    
    if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 10 and not settings.OPENAI_API_KEY.startswith("sk-..."):
        providers.append("openai")
    
    if settings.ANTHROPIC_API_KEY and len(settings.ANTHROPIC_API_KEY) > 10 and not settings.ANTHROPIC_API_KEY.startswith("sk-ant-..."):
        providers.append("anthropic")
    
    _available_providers = providers
    logger.info(f"Available providers for load balancing: {providers}")


def _get_next_provider() -> str:
    """Get next provider in rotation for load balancing"""
    global _provider_index
    with _provider_lock:
        if not _available_providers:
            _init_available_providers()
        
        if not _available_providers:
            return settings.LLM_PROVIDER  # fallback to default
        
        provider = _available_providers[_provider_index % len(_available_providers)]
        _provider_index += 1
        return provider


def _get_provider_for_agent(agent: Optional[str]) -> str:
    """Get provider for specific agent, or use rotation if not specified"""
    if agent:
        env_attr = AGENT_PROVIDER_MAP.get(agent.lower())
        if env_attr:
            p = getattr(settings, env_attr, "")
            if p and p.strip():
                return p.lower().strip()
    
    # Use load balancing rotation
    return _get_next_provider()


_init_available_providers()

# ── Groq key rotation (thread-safe) ──────────────────────────────────────────

_groq_keys: list[str] = []
_groq_index = 0
_groq_lock = threading.Lock()


def _init_groq_keys():
    global _groq_keys
    raw = settings.GROQ_API_KEYS or settings.GROQ_API_KEY
    if raw:
        _groq_keys = [k.strip() for k in raw.split(",") if k.strip()]


def _get_groq_key() -> str:
    global _groq_index
    with _groq_lock:
        if not _groq_keys:
            _init_groq_keys()
        if not _groq_keys:
            return ""
        key = _groq_keys[_groq_index % len(_groq_keys)]
        _groq_index += 1
        return key


_init_groq_keys()


# ── Provider availability ─────────────────────────────────────────────────────

def _has_key(provider: str) -> bool:
    if provider == "ollama":
        return True
    if provider == "groq":
        return bool(_groq_keys or settings.GROQ_API_KEY)
    keys = {
        "openai": settings.OPENAI_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
        "gemini": settings.GEMINI_API_KEY,
    }
    k = keys.get(provider, "")
    return bool(k and len(k) > 10)


def _resolve_provider(agent: Optional[str] = None, provider: Optional[str] = None) -> str:
    if provider:
        return provider.lower().strip()
    
    # Use load balancing for agent-specific providers
    return _get_provider_for_agent(agent)


# ── Provider implementations ──────────────────────────────────────────────────

def _call_groq(system: str, user: str, max_tokens: int, temperature: float) -> str:
    import importlib
    groq = importlib.import_module("groq")
    key = _get_groq_key()
    if not key:
        raise ValueError("No Groq API key configured")
    client = groq.Groq(api_key=key, timeout=60.0)
    
    # Add JSON instruction to system prompt for Groq
    json_instruction = " IMPORTANT: Return ONLY valid JSON, no markdown, no code fences, no explanation."
    enhanced_system = system + json_instruction
    
    resp = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": enhanced_system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content.strip()


def _call_openai(system: str, user: str, max_tokens: int, temperature: float) -> str:
    import importlib
    openai = importlib.import_module("openai")
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content.strip()


def _call_anthropic(system: str, user: str, max_tokens: int, temperature: float) -> str:
    import importlib
    anthropic = importlib.import_module("anthropic")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=temperature,
    )
    return resp.content[0].text.strip()


def _call_gemini(system: str, user: str, max_tokens: int, temperature: float) -> str:
    import importlib
    genai = importlib.import_module("google.generativeai")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    # Add JSON instruction to system prompt
    json_instruction = " IMPORTANT: Return ONLY valid JSON, no markdown, no code fences, no explanation."
    enhanced_system = system + json_instruction
    
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=enhanced_system,
        generation_config=genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    return model.generate_content(user).text.strip()


def _call_ollama(system: str, user: str, max_tokens: int, temperature: float) -> str:
    import httpx
    resp = httpx.post(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        json={
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


DISPATCH = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "gemini": _call_gemini,
    "groq": _call_groq,
    "ollama": _call_ollama,
}


# ── Fallback system: Groq → Gemini → no analysis ───────────────────────────

def llm_complete_with_fallback(
    system: str,
    user: str,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    agent: Optional[str] = None,
) -> str:
    """
    Try Groq first, fallback to Gemini if Groq fails, return empty if both fail.
    """
    # 1. Try Groq first
    try:
        result = _call_groq(system=system, user=user, max_tokens=max_tokens, temperature=temperature)
        logger.info(f"LLM success → provider=groq len={len(result)}")
        return result
    except Exception as e:
        logger.warning(f"Groq failed, falling back to Gemini: {e}")
        
    # 2. Fallback to Gemini
    try:
        result = _call_gemini(system=system, user=user, max_tokens=max_tokens, temperature=temperature)
        logger.info(f"LLM success → provider=gemini (fallback) len={len(result)}")
        return result
    except Exception as e:
        logger.error(f"Gemini also failed: {e}")
        
    # 3. Both failed - return empty/demo data
    logger.warning("Both Groq and Gemini failed, returning demo data")
    return _demo_text(agent)


# ── Main public API ───────────────────────────────────────────────────────────

def llm_complete(
    system: str,
    user: str,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    agent: Optional[str] = None,
    provider: Optional[str] = None,
    retries: int = 2,
) -> str:
    resolved = _resolve_provider(agent=agent, provider=provider)
    logger.info(f"LLM call → agent={agent} provider={resolved} userLen={len(user)}")

    if not _has_key(resolved):
        logger.warning(f"No key for {resolved}, returning demo")
        return _demo_text(agent)

    fn = DISPATCH.get(resolved)
    if fn is None:
        raise ValueError(f"Unknown provider: {resolved}")

    last_err = None
    for attempt in range(retries + 1):
        try:
            t0 = time.time()
            result = fn(system=system, user=user, max_tokens=max_tokens, temperature=temperature)
            elapsed = int((time.time() - t0) * 1000)
            logger.info(f"LLM success → provider={resolved} ms={elapsed} len={len(result)}")
            return result
        except Exception as e:
            last_err = e
            logger.warning(f"LLM attempt {attempt+1} failed ({resolved}): {e}")
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                # rotate key on retry for groq
                if resolved == "groq":
                    _get_groq_key()

    logger.error(f"All {retries+1} attempts failed for {resolved}: {last_err}")
    return _demo_text(agent)


def llm_complete_json(
    system: str,
    user: str,
    max_tokens: int = 2000,
    agent: Optional[str] = None,
    provider: Optional[str] = None,
) -> dict:
    raw = llm_complete(
        system=system, user=user, max_tokens=max_tokens,
        temperature=0.0, agent=agent, provider=provider,
    )
    return _parse_json(raw, agent=agent, user=user)


def _parse_json(raw: str, agent: Optional[str] = None, user: str = "") -> dict:
    """Parse JSON from LLM response - exported for use in other modules"""
    text = raw.strip()
    # Strip markdown fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except Exception:
                continue
    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    logger.error(f"JSON parse failed. Raw preview: {raw[:300]}")
    return {}


def _demo_text(agent: Optional[str]) -> str:
    if agent == "matcher":
        return json.dumps({
            "overall_score": 0, "skill_match": 0, "experience_match": 0,
            "education_match": 0, "seniority_match": 0, "location_match": 0,
            "ai_confidence": 0, "recommendation": "Consider",
            "recommendation_reason": "AI unavailable - manual review required",
            "ai_summary": "AI analysis unavailable",
            "strengths": [], "weaknesses": [], "missing_skills": [], "missing_certs": [],
            "skill_gap_analysis": "", "ats_score": 0, "ats_issues": [], "ats_suggestions": [],
        })
    if agent == "chat":
        return "AI assistant unavailable. Please review the candidate profile manually."
    return json.dumps({
        "full_name": "Unknown", "email": None, "phone": None,
        "current_position": None, "years_experience": 0,
        "technical_skills": {}, "education": [], "location": None,
    })


def get_active_providers() -> dict:
    return {
        "parser": _resolve_provider("parser"),
        "matcher": _resolve_provider("matcher"),
        "chat": _resolve_provider("chat"),
        "default": settings.LLM_PROVIDER,
    }
