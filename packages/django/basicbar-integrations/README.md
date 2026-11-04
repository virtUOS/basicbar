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
- `metrics` — token-geschützter Prometheus-Endpunkt (`MetricsView` +
  `Gauges`), aus bis `METRICS_TOKEN` gesetzt ist.

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

## Prometheus-Metriken

`metrics.MetricsView` liefert Gauges im Prometheus-Textformat (0.0.4), ohne
`prometheus_client`. Das Tool leitet ab, implementiert `collect()` und hängt
den View selbst ein — das Paket registriert keine URL:

```python
# lending/metrics.py
from basicbar_integrations.metrics import Gauges, MetricsView

class ToolMetricsView(MetricsView):
    def collect(self, gauges: Gauges) -> None:
        gauges.gauge("tool_items_total", "Anzahl Gegenstände", Item.objects.count())
        gauges.gauge(
            "tool_items_by_status",
            "Gegenstände nach Status",
            labels=[({"status": s}, n) for s, n in counts_by_status()],
        )

# config/urls.py — außerhalb von /api/
path("metrics", ToolMetricsView.as_view()),
```

- `METRICS_TOKEN` (Env, Default `""`): leer → `404`. Sonst nur mit exakt
  `Authorization: Bearer <token>` (Vergleich per `hmac.compare_digest`),
  andernfalls `401` mit `WWW-Authenticate: Bearer`. Nur `GET`/`HEAD`,
  immer `Cache-Control: no-store`.
- `Gauges.gauge(name, help_text, value=None, labels=None)`: `value` ergibt
  ein Sample ohne Labels, `labels` eine Liste von `(label_dict, wert)`.
  Ungültige Metrik-/Label-Namen und doppelte Familien → `ValueError`.
  Label-Werte werden escaped; ganzzahlige Werte erscheinen als `int`.
- Keine personenbezogenen Daten in Labels — nur Aggregate.
- Caddy: `/metrics` an das Backend durchreichen (vor dem SPA-Fallback):

  ```caddy
  handle /metrics {
      reverse_proxy app:8000
  }
  ```

- Prometheus: `authorization: { type: Bearer, credentials_file: … }` im
  Scrape-Job, `metrics_path: /metrics`.

Alle Settings haben Defaults („aus“) — ein Tool ohne Konfiguration startet
unverändert. Tests: `python runtests.py` (oder über die Repo-CI).
