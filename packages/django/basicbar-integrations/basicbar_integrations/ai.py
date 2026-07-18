# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Optional AI features via an OpenAI-compatible LiteLLM endpoint.

Off by default; configured only through env (AI_PROVIDER/AI_BASE_URL/
AI_API_KEY/AI_MODEL). Deliberately dependency-light: talks to the proxy over
the stdlib ``urllib`` — no ``litellm``/``openai`` package. Model output is
always untrusted: callers must re-validate it before using or storing it.
"""

import json
from typing import Any
from urllib import error, request

from . import conf


class AIError(Exception):
    """The AI provider is unavailable or returned an unusable response."""


def is_enabled() -> bool:
    """Whether a usable LiteLLM provider is fully configured."""
    return (
        conf.get("AI_PROVIDER") == "litellm"
        and bool(conf.get("AI_BASE_URL"))
        and bool(conf.get("AI_API_KEY"))
        and bool(conf.get("AI_MODEL"))
    )


def chat_json(system: str, user: str, *, max_tokens: int | None = None) -> Any:
    """Send a system+user prompt to the chat endpoint and return the parsed
    JSON object from the model's reply. Raises ``AIError`` when the provider is
    off, the call fails, or the reply is empty / not valid JSON.

    ``max_tokens`` defaults to the ``AI_MAX_TOKENS`` setting. Reasoning is
    disabled when ``AI_DISABLE_THINKING`` is set, so a reasoning model spends
    its budget on the answer instead of hidden thinking (which otherwise comes
    back as empty ``content``)."""
    if not is_enabled():
        raise AIError("AI is not configured.")
    payload = {
        "model": conf.get("AI_MODEL"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens or conf.get("AI_MAX_TOKENS"),
        "response_format": {"type": "json_object"},
    }
    if conf.get("AI_DISABLE_THINKING"):
        # Forwarded by LiteLLM/vLLM to the model's chat template; ignored by
        # backends that don't support it.
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    url = conf.get("AI_BASE_URL").rstrip("/") + "/chat/completions"
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {conf.get('AI_API_KEY')}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=conf.get("AI_TIMEOUT")) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        if not content:
            raise AIError("empty response from model")
        return json.loads(content)
    except (error.URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise AIError(f"AI request failed: {exc}") from exc
