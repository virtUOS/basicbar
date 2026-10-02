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
- `capabilities.capabilities_payload()` — `{"ai_enabled", "content_default_language",
  "content_translation_enabled"}` für das `whoami` des Tools (neben
  `basicbar_auth.views.whoami_payload`), damit das Frontend Features ohne
  zweiten Request und ohne Build-Varianten ein-/ausblendet.
- `translation_sync` — Helfer für den Übersetzungs-Sync-Zustand pro Feld
  (`record_synced`, `stale_map`, `modeltranslation_values`, …).
- `html_sanitize` — die eine HTML-Allowlist für Rich-Content (nh3-basiert).

## Einbinden

```python
INSTALLED_APPS = [..., "basicbar_integrations"]

# urls.py
path("api/", include("basicbar_integrations.urls")),  # translate/

# accounts/views.py
from basicbar_auth.views import whoami_payload
from basicbar_integrations.capabilities import capabilities_payload

def whoami(request):
    return JsonResponse({**whoami_payload(request), **capabilities_payload()})
```

Alle Settings haben Defaults („aus“) — ein Tool ohne Konfiguration startet
unverändert. Tests: `python runtests.py` (oder über die Repo-CI).
