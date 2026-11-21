# basicbar-integrations

Optionale externe Dienste für die „-bar“-Tools, alle **aus per Default** und
rein per Umgebungs-Settings aktivierbar. LibreTranslate und LiteLLM laufen
über Stdlib-`urllib`, keine Provider-SDKs; `gitlab` und `encryption` brauchen
je ein Extra (siehe unten).

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
  `Gauges`); ohne `METRICS_TOKEN` antwortet er mit `404`.
- `gitlab` — GitLab-Client (Extra `[gitlab]`): Projekt prüfen, Datei
  hochladen, Issue anlegen (siehe „GitLab-Client“)
- `encryption` — Fernet-Verschlüsselung für gespeicherte Geheimnisse (Extra
  `[encryption]`, siehe „Token-Verschlüsselung“)

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
  andernfalls `401` mit `WWW-Authenticate: Bearer`. Das Token muss ASCII
  sein (Django dekodiert Header als Latin-1 — z. B.
  `python -c "import secrets; print(secrets.token_urlsafe(32))"`). Nur
  `GET`/`HEAD`, immer `Cache-Control: no-store`; der `Accept`-Header wird
  ignoriert (immer Textformat), Projekt-Default-Throttles greifen nicht.
- `Gauges.gauge(name, help_text, value=None, labels=None)`: `value` ergibt
  ein Sample ohne Labels, `labels` eine Liste von `(label_dict, wert)`.
  Ungültige Metrik-/Label-Namen, doppelte Familien und doppelte Label-Sets
  innerhalb einer Familie → `ValueError`.
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

## GitLab-Client und Token-Verschlüsselung

Beide Module sind optional: ohne die Extras importiert das Paket weiter, und
`django.setup()` sowie `manage.py check` laufen. Einbinden mit

```
basicbar-integrations[gitlab,encryption] @ https://github.com/virtUOS/basicbar/archive/refs/tags/integrations/v0.6.0.tar.gz#subdirectory=packages/django/basicbar-integrations
```

(`gitlab` = `httpx>=0.27`, `encryption` = `cryptography>=42`, `test` = beide.)

```python
from basicbar_integrations import gitlab
from basicbar_integrations.encryption import decrypt, encrypt

stored = encrypt("glpat-…")               # in der Datenbank ablegen
issue = gitlab.create_issue(
    "https://git.example.org/group/project", decrypt(stored),
    title="…", description="…", confidential=True, labels=["tool"],
)                                          # Issue(iid=17, web_url="https://…/-/issues/17")
```

- **`gitlab`**: `parse_project_url(url, allow_http=False)`,
  `same_origin(a, b)`, `check_project(url, token)` (wirft nie),
  `upload_file(url, token, filename=, data=, content_type=)` (liefert das
  Markdown), `create_issue(url, token, title=, description=,
  confidential=False, labels=())` (`labels` ist eine Sequenz von Strings;
  ein einzelner `str` löst einen `TypeError` aus). Fehler sind `GitLabError`.
  `create_issue(confidential=True)` verlangt, dass die Antwort
  `confidential: true` zeigt. `Issue.iid` ist `None`, wenn GitLab keine
  Nummer liefert (das Tool entscheidet, ob das ein Fehler ist);
  `Issue.web_url` ist nur gesetzt, wenn es zur Projekt-URL passt.
- **`encryption`**: `encrypt`/`decrypt` (leer bleibt leer; `decrypt` liefert bei
  falschem Schlüssel `""` und warnt einmal pro Prozess und Art),
  `EncryptionKeyError`, `reset_warnings()` für Tests.
- **Settings**: `TOKEN_ENCRYPTION_KEY` (Default `""` = aus `SECRET_KEY`
  abgeleitet). Einen Schlüssel erzeugen: `python -c "from cryptography.fernet
  import Fernet; print(Fernet.generate_key().decode())"`. Der System-Check
  `basicbar_integrations.E001` prüft ihn, nur wenn er gesetzt ist. Wer den
  Schlüssel wechselt, macht gespeicherte Token unlesbar.
- **Datenschutz**: Das Paket selbst loggt nichts, und weder Token, Klartext,
  Chiffrat, Schlüssel, Antwort-Body noch Issue-Inhalt landen in
  Exception-Texten (nur HTTP-Status oder Exception-Klasse). Das Token geht nur
  im Header `PRIVATE-TOKEN` an den konfigurierten Host; Weiterleitungen
  werden nie verfolgt. `http://` wird ohne `allow_http=True` abgewiesen, bevor
  eine Anfrage rausgeht, ebenso URLs mit Benutzerinfo oder ohne Projektpfad.
  Achtung: httpx loggt auf dem eigenen Logger `httpx` bei INFO eine Zeile
  `HTTP Request: POST <URL>` mit dem Projektpfad (nie mit dem Token). Tools,
  die Projektpfade nicht im Log haben wollen, setzen den Logger `httpx` auf
  `WARNING`.
- **Test-Naht**: `basicbar_integrations.gitlab._transport` nimmt einen
  httpx-Transport; `None` ist das echte Netz.

  ```python
  with mock.patch.object(gitlab, "_transport", httpx.MockTransport(handler)):
      ...
  ```

Alle Settings haben Defaults („aus“) — ein Tool ohne Konfiguration startet
unverändert. Tests: `python runtests.py` (oder über die Repo-CI).
