# basicbar-integrations

Optionale externe Dienste für die „-bar“-Tools, alle **aus per Default** und
rein per Umgebungs-Settings aktivierbar. Stdlib-`urllib`-Clients — keine
Provider-SDKs.

- `translation_service` — LibreTranslate-Client (`CONTENT_TRANSLATION_PROVIDER=libretranslate`
  + `LIBRETRANSLATE_URL`, optional `LIBRETRANSLATE_API_KEY`)
- `ai` — OpenAI-kompatibler LiteLLM-Client (`AI_PROVIDER=litellm` +
  `AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL`, optional `AI_TIMEOUT`/`AI_MAX_TOKENS`/
  `AI_DISABLE_THINKING`)
- `views.TranslateView` — `POST {text, source, target, format?}` →
  `{translated}`; validiert Sprachen gegen `settings.LANGUAGES`, sanitized
  HTML-Ergebnisse serverseitig. Permission per Subclass anpassbar
  (Default `IsAuthenticated`).
- `views.CapabilitiesView` — `GET` → `{"translation": bool, "ai": bool, …}`,
  damit das Frontend Features ohne Build-Varianten ein-/ausblendet;
  erweiterbar über `extra_capabilities()`.
- `html_sanitize` — die eine HTML-Allowlist für Rich-Content (nh3-basiert).

## Einbinden

```python
INSTALLED_APPS = [..., "basicbar_integrations"]

# urls.py
path("api/", include("basicbar_integrations.urls")),  # translate/ + capabilities/
```

Alle Settings haben Defaults („aus“) — ein Tool ohne Konfiguration startet
unverändert. Tests: `python runtests.py` (oder über die Repo-CI).
