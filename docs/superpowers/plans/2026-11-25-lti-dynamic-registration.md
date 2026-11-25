# LTI Dynamic Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein Tool-Admin erzeugt einen Einmal-Link, ein Moodle-Admin trägt ihn in Moodle ein, und Tool und Moodle registrieren sich gegenseitig per LTI Dynamic Registration — Mechanismus in `basicbar-lti` 0.2.0, Anbindung in abstimmbar und ausleihbar.

**Architecture:** Neues Modell `LtiRegistrationToken` (gehashter Einmal-Token), ein abgeschotteter HTTP-Client für die zwei ausgehenden Requests, die Registrierungslogik als reine Funktionen und eine HTML-View `lti_register`, die Moodle im iframe öffnet. Die Tools verdrahten URL, Staff-API und einen Admin-Dialog; was sie anmelden, steht im Setting `LTI_TOOL_REGISTRATION`.

**Tech Stack:** Django 5.1, DRF, PyLTI1p3 2.0 (unverändert), stdlib `urllib`/`socket`/`ipaddress`/`hashlib`/`secrets`; Tools: React + TypeScript, react-i18next.

**Spec:** `docs/superpowers/specs/2026-11-25-lti-dynamic-registration-design.md`

## Global Constraints

- Keine neue Python-Abhängigkeit im Paket (`pyproject.toml` `dependencies` bleibt gleich).
- SPDX-Header `# SPDX-License-Identifier: Apache-2.0` + `# Copyright 2026 Universität Osnabrück (virtUOS)` in jeder neuen Quelldatei.
- Constraint-/Index-Namen mit Präfix `basicbar_lti_`.
- Settings nur über `basicbar_lti/conf.py` mit Defaults; unkonfiguriert und ohne verdrahtete URL ändert sich nichts.
- `LTI_REGISTRATION_TOKEN_TTL` Default `timedelta(days=7)`; `LTI_REGISTRATION_ALLOW_HTTP` Default `False`.
- Token-Klartext nie speichern, nur SHA-256-Hex; Klartext genau einmal in der Create-Antwort.
- Neue Plattform: `is_active=True`, `link_by_email=False`.
- Abgelehnte Zieladressen: Loopback (`127.0.0.0/8`, `::1`), link-lokal (`169.254.0.0/16`, `fe80::/10`), unspezifiziert (`0.0.0.0`, `::`). Private Netze erlaubt. `LTI_REGISTRATION_ALLOW_HTTP=True` hebt Schema- und Adressprüfung auf.
- Seitentexte zweisprachig: deutscher Satz, darunter englischer Satz (keine i18n-Maschinerie im Paket).
- Spec-Konstanten: Close-Nachricht `{subject: "org.imsglobal.lti.close"}` an `window.opener || window.parent`, Ziel-Origin `"*"`; LTI-Block-Schlüssel `https://purl.imsglobal.org/spec/lti-tool-configuration`, Plattform-Block `https://purl.imsglobal.org/spec/lti-platform-configuration`.
- Paketversion `0.2.0`; Tag `lti/v0.2.0` erst nach dem Merge (der Mensch merged). Push nach GitHub über SSH.
- Paket-Tests: `docker cp packages/django/basicbar-lti abstimmbar_backend:/tmp/pkg && docker exec abstimmbar_backend sh -c "cd /tmp/pkg && python runtests.py"` (vorher `rm -rf` des Ziels im Container).

## Review Focus

1. **Link direkt im Browser geöffnet** (ohne `openid_configuration`) → erklärende 400-Seite „In Moodle als Tool-URL eintragen“, kein 500 — Test in Task 4.
2. **Link nach Erfolg ein zweites Mal benutzt** → Seite „Link bereits verwendet oder abgelaufen“, kein ausgehender Request — Test in Task 4.
3. **LMS antwortet mit HTML-Fehlerseite oder 4xx** auf Konfiguration oder Registrierung → lesbare Fehlerseite mit Status, Token bleibt offen — Tests in Task 2 und Task 3.
4. **Tool hinter Reverse-Proxy baut `http://`-URLs** (fehlendes `SECURE_PROXY_SSL_HEADER`) → Registrierung bricht mit klarer Meldung ab statt Moodle falsche URLs zu schicken — Test in Task 3.
5. **Registrierungsantwort ohne `deployment_id`** (Nicht-Moodle-LMS) → Plattform entsteht mit `deployment_ids=[]`, Erfolgsseite weist auf manuelles Nachtragen hin — Test in Task 3/4.

---

## Datei-Übersicht (Paket `packages/django/basicbar-lti/basicbar_lti/`)

| Datei | Verantwortung |
|---|---|
| `models.py` (ändern) | `LtiRegistrationToken` |
| `migrations/0002_ltiregistrationtoken.py` (neu) | Migration |
| `conf.py` (ändern) | neue Defaults + `tool_registration()` |
| `dynreg_http.py` (neu) | ausgehende Requests: Schema, Adressen, Redirects, Größe, JSON |
| `dynreg.py` (neu) | Plattform-Konfiguration prüfen, Tool-Payload bauen, registrieren + Plattform anlegen |
| `dynreg_pages.py` (neu) | HTML der Registrierungsseiten |
| `views.py` (ändern) | `lti_register`, `LtiRegistrationTokenViewSet`, `LtiToolInfoView` per `reverse()` |
| `serializers.py` (ändern) | `LtiRegistrationTokenSerializer` |
| `middleware.py` (ändern) | von der View gesetzte `frame-ancestors` stehen lassen |
| `checks.py` (neu) + `apps.py` (ändern) | Warnung `basicbar_lti.W001` |
| `admin.py` (ändern) | Token im Django-Admin |
| `tests/test_dynreg.py` (neu), `tests/urls.py`, `tests/settings.py` (ändern) | Tests |

---

### Task 1: Token-Modell, Settings, Admin

**Files:**
- Modify: `packages/django/basicbar-lti/basicbar_lti/models.py`, `conf.py`, `admin.py`
- Create: `packages/django/basicbar-lti/basicbar_lti/migrations/0002_ltiregistrationtoken.py`
- Test: `packages/django/basicbar-lti/basicbar_lti/tests/test_dynreg.py` (neu, Klasse `RegistrationTokenTests`)

**Interfaces:**
- Produces:
  - `LtiRegistrationToken` mit Feldern `token_hash: CharField(64, unique)`, `note: CharField(200, blank)`, `created_by: FK(AUTH_USER_MODEL, SET_NULL, null, related_name="+")`, `created_at: auto_now_add`, `expires_at: DateTimeField`, `used_at: DateTimeField(null)`, `platform: FK(LtiPlatform, SET_NULL, null, related_name="registration_tokens")`.
  - `LtiRegistrationToken.issue(*, note: str = "", created_by=None) -> tuple[LtiRegistrationToken, str]` — Klartext via `secrets.token_urlsafe(32)`, `expires_at = now + conf.get("LTI_REGISTRATION_TOKEN_TTL")`.
  - `LtiRegistrationToken.find_valid(raw: str) -> LtiRegistrationToken | None` — per Hash, `used_at is None` und `expires_at > now`; leerer/unbekannter Token → `None`.
  - `LtiRegistrationToken.hash(raw: str) -> str` (staticmethod, SHA-256 hex).
  - Property `status -> "open" | "used" | "expired"`.
  - `conf.tool_registration() -> dict` — `DEFAULTS["LTI_TOOL_REGISTRATION"]` mit dem Projekt-Setting **flach** überschrieben (Schlüssel für Schlüssel).
  - Neue `conf.DEFAULTS`: `LTI_REGISTRATION_TOKEN_TTL: timedelta(days=7)`, `LTI_REGISTRATION_ALLOW_HTTP: False`, `LTI_TOOL_REGISTRATION: {"client_name": "LTI Tool", "description": "", "logo_path": "", "messages": [{"type": "LtiResourceLinkRequest"}], "claims": ["iss", "sub", "name", "given_name", "family_name", "email"], "scope": "", "custom_parameters": {}}`.

- [ ] **Step 1: Failing tests** in `RegistrationTokenTests`:
  - `test_issue_stores_only_hash` — `obj, raw = issue(note="Moodle")`; `obj.token_hash == hashlib.sha256(raw.encode()).hexdigest()`; `raw not in` irgendeinem Feldwert; `obj.status == "open"`.
  - `test_default_ttl_is_seven_days` — `obj.expires_at - obj.created_at` liegt zwischen 6 Tagen 23 h und 7 Tagen 1 min.
  - `test_ttl_setting` — `@override_settings(LTI_REGISTRATION_TOKEN_TTL=timedelta(hours=1))` → Ablauf ≈ 1 h.
  - `test_find_valid` — gültig → Objekt; `find_valid("")`, `find_valid("nope")` → `None`; nach `used_at=now` → `None`, `status == "used"`; mit `expires_at` in der Vergangenheit → `None`, `status == "expired"`.
  - `test_tool_registration_merges_flat` — `@override_settings(LTI_TOOL_REGISTRATION={"client_name": "abstimmbar"})` → `client_name == "abstimmbar"`, `claims` = Default-Liste.
- [ ] **Step 2: Run, expect FAIL** (ImportError). Befehl siehe Global Constraints.
- [ ] **Step 3: Implementieren** (Modell, Klassenmethoden, `conf`), dann `python manage.py makemigrations basicbar_lti --name ltiregistrationtoken` gegen die Test-Settings (`DJANGO_SETTINGS_MODULE=basicbar_lti.tests.settings django-admin makemigrations basicbar_lti`) und SPDX-Header in die Migration. Admin: `LtiRegistrationTokenAdmin` mit `list_display = ("note", "created_by", "created_at", "expires_at", "status", "platform")`, alle Felder read-only, kein „Hinzufügen“ (`has_add_permission → False`), Löschen erlaubt (= Widerrufen).
- [ ] **Step 4: Run, expect PASS**; gesamte Paket-Suite grün.
- [ ] **Step 5: Commit** `feat(lti): LtiRegistrationToken und Settings für Dynamic Registration`

---

### Task 2: Abgeschotteter HTTP-Client

**Files:**
- Create: `packages/django/basicbar-lti/basicbar_lti/dynreg_http.py`
- Test: `tests/test_dynreg.py`, Klasse `HttpClientTests`

**Interfaces:**
- Produces:
  - `class RegistrationError(Exception)` — `str(exc)` ist die Meldung für den Moodle-Admin (deutsch); optional `detail: str` fürs Log.
  - `request_json(url: str, *, bearer: str | None = None, payload: dict | None = None) -> dict` — GET ohne `payload`, sonst POST mit `Content-Type: application/json`; `Authorization: Bearer …` wenn `bearer`; `Accept: application/json`.
  - Modul-Konstanten `TIMEOUT = 10` (s), `MAX_BYTES = 256 * 1024`.
  - Interne Naht für Tests: `_open(req: urllib.request.Request) -> http.client.HTTPResponse`-artiges Objekt (über einen eigenen `OpenerDirector` mit Redirect-Handler).

Regeln (in dieser Reihenfolge, jede Verletzung → `RegistrationError`, **bevor** `_open` aufgerufen wird):
1. Schema `https`; `http` nur bei `LTI_REGISTRATION_ALLOW_HTTP`.
2. Host per `socket.getaddrinfo(host, port)` auflösen; ist **eine** Adresse `is_loopback`, `is_link_local` oder `is_unspecified` → ablehnen (entfällt bei `ALLOW_HTTP`). Auflösung schlägt fehl → `RegistrationError`.
3. Redirects: nur auf denselben `scheme://host[:port]`; sonst Fehler.
4. Antwort: mehr als `MAX_BYTES` → Fehler; kein JSON-Objekt (`dict`) → Fehler „keine gültige JSON-Antwort“; `HTTPError` → Fehler mit Statuscode, Body-Auszug (max. 500 Zeichen) nur in `detail`.

- [ ] **Step 1: Failing tests** (`socket.getaddrinfo` und `dynreg_http._open` per `unittest.mock.patch`):
  - `test_rejects_http_by_default` — `request_json("http://moodle.example.org/x")` → `RegistrationError`; `_open` nicht aufgerufen.
  - `test_allow_http_setting` — mit `LTI_REGISTRATION_ALLOW_HTTP=True` und `getaddrinfo` → `127.0.0.1`: `_open` wird aufgerufen.
  - `test_rejects_loopback_link_local_unspecified` — je für `127.0.0.1`, `::1`, `169.254.169.254`, `fe80::1`, `0.0.0.0` → Fehler, `_open` nicht aufgerufen.
  - `test_allows_private_network` — `10.1.2.3` → `_open` aufgerufen, Rückgabe-Dict durchgereicht.
  - `test_bearer_and_post` — `payload={"a": 1}, bearer="t"` → Request-Methode `POST`, Header `Authorization: Bearer t`, Body `{"a": 1}`.
  - `test_non_json_response` — Body `b"<html>Login</html>"` → Fehler, Meldung enthält „JSON“.
  - `test_http_error_status_in_message` — `_open` wirft `HTTPError(…, 401, …)` → Meldung enthält `401`.
  - `test_too_large` — Body `MAX_BYTES + 1` Bytes → Fehler.
  - `test_cross_host_redirect_refused` — Redirect-Handler direkt: `redirect_request` mit `Location` auf anderen Host → Fehler; gleicher Host → Request-Objekt.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implementieren** `request_json` und den Redirect-Handler (Unterklasse von `urllib.request.HTTPRedirectHandler`, `redirect_request` prüft den Ziel-Origin).
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** `feat(lti): abgeschotteter HTTP-Client für Dynamic Registration`

---

### Task 3: Registrierungslogik

**Files:**
- Create: `packages/django/basicbar-lti/basicbar_lti/dynreg.py`
- Test: `tests/test_dynreg.py`, Klassen `PlatformConfigTests`, `PayloadTests`, `RegisterTests`
- Modify: `tests/urls.py` — `path("lti/register/", lti_register, name="lti-register")` vorbereiten (View kommt in Task 4; bis dahin Platzhalter-Funktion in `tests/urls.py` ist erlaubt).

**Interfaces:**
- Consumes: `request_json`, `RegistrationError` (Task 2); `LtiRegistrationToken`, `conf.tool_registration()` (Task 1).
- Produces:
  - `@dataclass(frozen=True) class PlatformConfig: issuer: str; authorization_endpoint: str; token_endpoint: str; jwks_uri: str; registration_endpoint: str; product_family_code: str` (`""` wenn nicht geliefert).
  - `load_platform_config(config_url: str, registration_token: str | None) -> PlatformConfig` — holt per `request_json(config_url, bearer=registration_token)`; Fehler, wenn ein Pflichtfeld fehlt, wenn `config_url` nicht mit `issuer` beginnt, oder wenn einer der vier Endpunkte einen anderen `netloc` als `issuer` hat.
  - `tool_urls(request) -> dict[str, str]` — Schlüssel `login`, `launch`, `jwks`, `register` per `request.build_absolute_uri(reverse("lti-login" | "lti-launch" | "lti-jwks" | "lti-register"))`.
  - `tool_registration_payload(request) -> dict` — Felder exakt laut Spec Schritt 5: `application_type="web"`, `response_types=["id_token"]`, `grant_types=["implicit", "client_credentials"]`, `token_endpoint_auth_method="private_key_jwt"`, `initiate_login_uri`, `redirect_uris=[launch]`, `jwks_uri`, `client_name`, `scope`, `logo_uri` nur wenn `logo_path` gesetzt (absolut gemacht); LTI-Block mit `domain` (Host der Launch-URL), `target_link_uri` (launch), `claims`, `description`, `custom_parameters`, `messages` (jede Nachricht ohne `target_link_uri` bekommt die Launch-URL). Wirft `RegistrationError`, wenn eine Tool-URL nicht `https` ist und `ALLOW_HTTP` aus ist.
  - `known_issuer(config: PlatformConfig) -> bool` — aktive `LtiPlatform` mit gleichem `issuer` (Vergleich nach `rstrip("/")`).
  - `register_platform(request, token: LtiRegistrationToken, config: PlatformConfig, registration_token: str | None) -> LtiPlatform` — in `transaction.atomic()`: Token per `select_for_update()` neu laden und erneut prüfen (`used_at is None`, nicht abgelaufen, sonst `RegistrationError("Link bereits verwendet oder abgelaufen.")`); `request_json(config.registration_endpoint, bearer=registration_token, payload=tool_registration_payload(request))`; `client_id` Pflicht (sonst Fehler); `deployment_id` aus dem LTI-Block der Antwort (fehlt → `[]`); Plattform anlegen (`name` = `token.note` oder `f"{product_family_code or 'LMS'} ({issuer-host})"`, Endpunkte aus `config`, `key_set_url=config.jwks_uri`); `token.used_at=now`, `token.platform=platform`. Jede Ausnahme rollt zurück — Token bleibt offen.

- [ ] **Step 1: Failing tests** (Moodle-förmige Fixtures: `issuer="https://moodle.example.org"`, Konfig-URL `https://moodle.example.org/mod/lti/openid-configuration.php`, Endpunkte `/mod/lti/auth.php`, `/mod/lti/token.php`, `/mod/lti/certs.php`, `/mod/lti/openid-registration.php`, `product_family_code="moodle"`; Antwort `{"client_id": "abc", "https://purl.imsglobal.org/spec/lti-tool-configuration": {"deployment_id": "7"}}`; `request_json` gepatcht in `basicbar_lti.dynreg`):
  - `test_config_ok` — alle Felder übernommen.
  - `test_config_issuer_not_prefix` — Konfig-URL `https://evil.example/...` mit Moodle-Issuer → Fehler.
  - `test_config_endpoint_other_host` — `jwks_uri` auf `https://cdn.example.org/...` → Fehler.
  - `test_config_missing_registration_endpoint` → Fehler.
  - `test_payload_shape` — Request mit `secure=True` (`RequestFactory().get("/", secure=True)`): `initiate_login_uri == "https://testserver/lti/login/"`, `redirect_uris == ["https://testserver/lti/launch/"]`, `token_endpoint_auth_method == "private_key_jwt"`, LTI-Block `messages == [{"type": "LtiResourceLinkRequest", "target_link_uri": "https://testserver/lti/launch/"}]`, `claims` = Default, kein `logo_uri`.
  - `test_payload_tool_settings` — `LTI_TOOL_REGISTRATION={"client_name": "abstimmbar", "logo_path": "/lti/icon.svg", "messages": [{"type": "LtiResourceLinkRequest"}, {"type": "LtiDeepLinkingRequest", "label": "Raum wählen"}]}` → `client_name`, `logo_uri == "https://testserver/lti/icon.svg"`, zweite Nachricht mit Launch-URL und Label.
  - `test_payload_refuses_http_tool_urls` — Request ohne `secure` → `RegistrationError`, Meldung nennt `SECURE_PROXY_SSL_HEADER`.
  - `test_register_creates_platform_and_consumes_token` — Plattform mit `issuer`, `client_id="abc"`, `deployment_ids=["7"]`, `auth_login_url` = auth.php, `key_set_url` = certs.php, `is_active=True`, `link_by_email=False`, `name == "Moodle Test"` (Token-Notiz); Token `status == "used"`, `token.platform == platform`; gesendeter Bearer = `registration_token`.
  - `test_register_name_fallback` — Token ohne Notiz → `name == "moodle (moodle.example.org)"`.
  - `test_register_without_deployment_id` — Antwort ohne LTI-Block → `deployment_ids == []`.
  - `test_register_lms_error_keeps_token_open` — `request_json` wirft `RegistrationError` → keine Plattform, Token `open`.
  - `test_register_missing_client_id_keeps_token_open` → Fehler, Token `open`.
  - `test_register_used_token_refused` — Token vorher verbraucht → Fehler, `request_json` nicht aufgerufen.
  - `test_known_issuer` — aktive Plattform mit `issuer + "/"` → `True`; nur inaktive → `False`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implementieren.**
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** `feat(lti): Registrierungslogik für Dynamic Registration`

---

### Task 4: View `lti_register`, Seiten, Einbetten, System-Check

**Files:**
- Create: `packages/django/basicbar-lti/basicbar_lti/dynreg_pages.py`, `checks.py`
- Modify: `views.py`, `middleware.py`, `apps.py` (`ready()` importiert `checks`), `tests/urls.py`
- Test: `tests/test_dynreg.py`, Klassen `RegisterViewTests`, `FrameAncestorsRegisterTests`, `CheckTests`

**Interfaces:**
- Consumes: Task 1–3.
- Produces:
  - `lti_register(request) -> HttpResponse` (`@csrf_exempt`, GET und POST). Parameter aus `request.POST` vor `request.GET`: `token`, `openid_configuration`, `registration_token`, `confirm`.
  - `dynreg_pages.page(title_de: str, title_en: str, body_html: str, *, close: bool = False) -> str` — vollständiges HTML-Dokument, alle eingesetzten Werte via `django.utils.html.format_html`/`escape`; bei `close=True` ein Inline-Skript, das `{subject: "org.imsglobal.lti.close"}` an `window.opener || window.parent` mit `"*"` postet.

Verhalten der View:
| Fall | Status | Seite | ausgehende Requests |
|---|---|---|---|
| Token ungültig/verbraucht/abgelaufen | 403 | „Link ungültig, bereits verwendet oder abgelaufen — neuen Link beim Tool-Admin anfordern“ | keine |
| Token gültig, `openid_configuration` fehlt | 400 | „Diese Adresse in Moodle als Tool-URL eintragen (Externe Tools → Tools verwalten)“ | keine |
| `load_platform_config` wirft | 502 | Fehlermeldung aus der Exception | 1 |
| `known_issuer` und nicht `confirm` | 200 | Hinweis „bestehende Verknüpfung wird nicht übernommen (Kursverknüpfungen und Konten hängen an der alten)“, Formular POST mit versteckten Feldern + `confirm=1` („Trotzdem neu registrieren“), Button „Abbrechen“ → Close-Nachricht | 1 |
| `register_platform` wirft | 502 | Fehlermeldung | 2 |
| Erfolg | 200, `close=True` | „Registrierung abgeschlossen. Nächste Schritte in Moodle: Tool aktivieren; Tool bearbeiten → Standard-Startcontainer „Neues Fenster“.“ Bei `deployment_ids == []` zusätzlich: „Das LMS hat keine Deployment-ID geliefert — im Tool-Admin nachtragen.“ | 2 |

`frame-ancestors`: Ist der Token gültig **und** ist der Origin von `openid_configuration` ein gültiger Origin (`middleware._ORIGIN_RE`), setzt die View `Content-Security-Policy: frame-ancestors 'self' <origin>`. Middleware: Enthält die Antwort bereits einen `Content-Security-Policy`-Header mit `frame-ancestors`, wird er nicht ersetzt (`X-Frame-Options` wird trotzdem entfernt).

System-Check `basicbar_lti.W001` (Warning): `LTI_REGISTRATION_ALLOW_HTTP` ist `True` und `DEBUG` ist `False`.

Fehler-Logging: jede `RegistrationError` mit `logger.warning("LTI registration failed (config=%r): %s %s", url, exc, exc.detail)`.

- [ ] **Step 1: Failing tests** (`dynreg.request_json` gepatcht; Fixtures wie Task 3; URL `/lti/register/?token=…&openid_configuration=…&registration_token=rt`, Requests mit `secure=True`):
  - `test_invalid_token_403_no_request` und `test_used_token_403_no_request` (Review Focus 2).
  - `test_missing_openid_configuration_400` (Review Focus 1).
  - `test_success_creates_platform_and_closes` — 200, Plattform existiert, Body enthält `org.imsglobal.lti.close` und „Neues Fenster“.
  - `test_success_without_deployment_warns` (Review Focus 5) — Body enthält „Deployment-ID“.
  - `test_lms_error_502_token_open` (Review Focus 3) — Body enthält die Meldung, Token `open`.
  - `test_known_issuer_asks_first` — GET → 200 mit Formular (`name="confirm"`), **ein** gemockter Aufruf, keine neue Plattform; POST mit `confirm=1` → Plattform angelegt.
  - `test_cancel_does_not_consume` — Bestätigungsseite enthält Close-Skript für „Abbrechen“; Token danach `open`.
  - `test_values_are_escaped` — Token-Notiz `<script>x</script>` erscheint in keiner Seite unescaped.
  - `FrameAncestorsRegisterTests.test_valid_token_allows_config_origin` — CSP `frame-ancestors 'self' https://moodle.example.org`, kein `X-Frame-Options`.
  - `test_invalid_token_keeps_default_policy` — CSP ohne `moodle.example.org`.
  - `test_other_lti_pages_unchanged` — `/lti/page/` wie bisher (bestehende Tests bleiben grün).
  - `CheckTests.test_w001` — `ALLOW_HTTP=True, DEBUG=False` → Warning mit id `basicbar_lti.W001`; `DEBUG=True` → keine.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implementieren**; `tests/urls.py` bindet die echte `lti_register` ein.
- [ ] **Step 4: Run, expect PASS**; gesamte Paket-Suite grün.
- [ ] **Step 5: Commit** `feat(lti): Registrierungsseite lti_register mit eng gefasstem Einbetten`

---

### Task 5: Staff-API, Tool-Info per `reverse()`, Doku, Release-PR

**Files:**
- Modify: `views.py`, `serializers.py`, `tests/urls.py`, `packages/django/basicbar-lti/README.md`, `packages/django/basicbar-lti/pyproject.toml` (`version = "0.2.0"`), `CHANGELOG.md` (Repo-Root), `CLAUDE.md` (Layout-Zeile basicbar-lti: „Dynamic Registration per Einmal-Link“)
- Test: `tests/test_dynreg.py`, Klasse `RegistrationTokenApiTests`; bestehender `test_tool_info_admin_only_and_urls` muss grün bleiben

**Interfaces:**
- Consumes: Task 1, `tool_urls` (Task 3).
- Produces:
  - `LtiRegistrationTokenViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, GenericViewSet)` — `permission_classes = [IsAdminUser]` (Tools überschreiben), Queryset neueste zuerst.
  - `LtiRegistrationTokenSerializer` — Felder `id`, `note`, `created_by` (Username, read-only), `created_at`, `expires_at`, `used_at`, `status`, `platform` (id, read-only), `platform_name` (read-only); schreibbar nur `note`. Die **Create-Antwort** enthält zusätzlich `url` = `tool_urls(request)["register"] + "?token=" + raw` — nur dort, nie in `list`.
  - `destroy` nur für `status == "open"`, sonst `400` `{"detail": "Nur offene Links können widerrufen werden."}`.
  - `LtiToolInfoView.get` baut alle URLs per `tool_urls(request)` (+ `icon_url` aus `conf.tool_registration()["logo_path"]`, absolut, `""` wenn leer) statt aus `FRONTEND_BASE_URL`; zusätzlich Schlüssel `register_url`.

- [ ] **Step 1: Failing tests:**
  - `test_requires_admin` — anonym 403, Nicht-Staff 403.
  - `test_create_returns_url_once` — POST `{"note": "Moodle"}` → 201, `url` beginnt mit `http://testserver/lti/register/?token=`, `LtiRegistrationToken.find_valid(<token aus url>)` ist das Objekt; GET-Liste enthält kein `url` und keinen Token.
  - `test_destroy_open_only` — offen → 204; verbraucht → 400.
  - `test_tool_info_uses_reverse` — `register_url == "http://testserver/lti/register/"`; ohne `FRONTEND_BASE_URL` in den Settings (`override_settings` mit gelöschtem Wert) weiterhin 200.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implementieren**; README-Abschnitt „Dynamic Registration“ (Ablauf, Settings mit Defaults, Sicherheitsmodell aus der Spec, Verdrahtung: URL `lti/register/` Name `lti-register` ohne Namespace, ViewSet mit Tool-Permission, `SECURE_PROXY_SSL_HEADER` hinter Proxy, Nachschritt „Neues Fenster“, nur neue Verknüpfungen). CHANGELOG unter `[Unreleased]`: `### basicbar-lti (→ wird lti/v0.2.0)` mit Migrationsschritten: `migrate`; `path("lti/register/", lti_register, name="lti-register")`; Token-ViewSet mit Tool-Permission registrieren; `LTI_TOOL_REGISTRATION` setzen; `SECURE_PROXY_SSL_HEADER` prüfen; Admin-UI; `LtiToolInfoView` braucht kein `FRONTEND_BASE_URL` mehr.
- [ ] **Step 4: Run, expect PASS**; Paket-Suite, `spdx`-Check (`grep -L` wie in `.github/workflows/ci.yml`) und Template-Probe laut CLAUDE.md lokal grün.
- [ ] **Step 5: Commit** `feat(lti): Token-API, Tool-Info per reverse, Doku — basicbar-lti 0.2.0`
- [ ] **Step 6: PR** von `feat/lti-dynamic-registration` gegen `main` öffnen (Design- und Plan-Dokument aus PR #59 bleiben dort), CI grün abwarten. **Stopp:** Merge durch den Menschen; danach Tag `lti/v0.2.0` auf den Merge-Commit setzen und pushen.

---

### Task 6: abstimmbar anbinden

Voraussetzung: Tag `lti/v0.2.0` existiert. Arbeit in einem Worktree im Scratchpad, Branch `feat/lti-dynamic-registration`, PR auf GitHub (`virtUOS/abstimmbar`).

**Files:**
- Modify: `backend/requirements.txt` (lti → `v0.2.0`), `backend/lti/urls.py`, `backend/lti/api_urls.py`, `backend/lti/views.py`, `backend/config/settings.py`, `backend/lti/tests.py`, `frontend/src/api.ts`, `frontend/src/pages/AdminPage.tsx`, `frontend/src/locales/de/translation.json` (+ `en`, falls dort Plural-/Sonderformen nötig), `docs/lti.md`

**Interfaces:**
- Consumes: `lti_register`, `LtiRegistrationTokenViewSet`, Create-Antwort mit `url`, Liste mit `status`/`platform_name` (Task 5).
- Produces (Frontend): `interface LtiRegistrationLink { id: number; note: string; created_by: string | null; created_at: string; expires_at: string; used_at: string | null; status: "open" | "used" | "expired"; platform: number | null; platform_name: string | null; url?: string }`; `api.listLtiRegistrationLinks()`, `api.createLtiRegistrationLink(note: string)`, `api.revokeLtiRegistrationLink(id: number)` gegen `/api/lti/registration-links/`.

- [ ] **Step 1: Failing Backend-Tests** in `backend/lti/tests.py`: `RegistrationLinkApiTests.test_admin_only` (Nicht-Admin 403 mit abstimmbars `IsAdmin`), `test_create_url_points_to_register` (`url` enthält `/lti/register/?token=`), `test_settings_payload` (`tool_registration_payload` enthält `client_name == "abstimmbar"`, `LtiDeepLinkingRequest`, `logo_uri` endet auf `/lti/icon.svg`).
- [ ] **Step 2: Run, expect FAIL** — `docker cp <worktree>/backend abstimmbar_backend:/tmp/bump` nach Paket-Install `pip install "<tarball-url>"` im Container; `cd /tmp/bump && python manage.py test lti`.
- [ ] **Step 3: Implementieren:** `path("lti/register/", lti_register, name="lti-register")`; Router `registration-links` → `LtiRegistrationTokenViewSet`-Unterklasse mit `permission_classes = [IsAdmin]`; `LTI_TOOL_REGISTRATION = {"client_name": "abstimmbar", "description": <Kurzbeschreibung aus README>, "logo_path": "/lti/icon.svg", "messages": [{"type": "LtiResourceLinkRequest"}, {"type": "LtiDeepLinkingRequest", "label": "abstimmbar-Raum auswählen"}]}`; `migrate`.
- [ ] **Step 4: Frontend** in `LtiPlatformsSection`: Unterabschnitt „Registrierungs-Links“ — Button „Registrierungs-Link erzeugen“ → Dialog mit Notizfeld → nach Erzeugen URL einmal anzeigen mit Kopieren-Knopf und Hinweistext: „Gilt 7 Tage, einmal verwendbar. Der Moodle-Admin trägt ihn unter Website-Administration → Plugins → Externe Tools → Tools verwalten als Tool-URL ein, aktiviert das Tool und stellt den Standard-Startcontainer auf „Neues Fenster“. Nur für neue Verknüpfungen.“; Tabelle Notiz/Erstellt von/Ablauf/Status/Plattform, „Widerrufen“ bei `open`. Strings als englische Schlüssel mit deutschen Einträgen in `de/translation.json`. Die manuelle Plattform-Erfassung bleibt unverändert.
- [ ] **Step 5: Verifizieren:** Backend-Suite komplett grün; `ruff check .` im Backend; `docker compose exec -T frontend npx tsc -b` grün; Frontend-Build grün.
- [ ] **Step 6: Doku** `docs/lti.md`: neuer Abschnitt „Moodle mit Registrierungs-Link (empfohlen)“ vor der manuellen Anleitung; die manuelle bleibt für andere LMS.
- [ ] **Step 7: Commit + PR** (deutscher Prosa-Titel, abstimmbar-Stil), CI grün. **Stopp:** Merge durch den Menschen.

---

### Task 7: ausleihbar anbinden

Wie Task 6, mit diesen Unterschieden (Branch `feat/lti-dynamic-registration`, Conventional Commits, PR auf `virtUOS/ausleihbar`):

- `lti/register/` in `backend/config/urls.py` neben `lti/login/` und `lti/jwks/`.
- Router in `backend/lti/api_urls.py`: `manage/lti/registration-links` → Unterklasse in `backend/lti/api.py` mit `permission_classes = [IsAdmin]`. Frontend-Endpunkte entsprechend `/api/manage/lti/registration-links/`; Typ `LtiRegistrationLink` in `frontend/src/types.ts`.
- `LTI_TOOL_REGISTRATION = {"client_name": "ausleihbar", "description": <aus README>, "messages": [{"type": "LtiResourceLinkRequest"}, {"type": "LtiDeepLinkingRequest", "label": "ausleihbar-Pool verknüpfen"}]}` (kein Icon).
- ausleihbars eigene `LtiToolInfoView` (baut schon per `reverse()`) um `register_url` ergänzen oder auf die Paket-Version zurückführen, wenn das Ergebnis gleich ist (inkl. `public_key`).
- UI in `frontend/src/pages/AdminLmsPage.tsx`, Komponenten aus `components/` (`useConfirm`, `useToast`, `Copy`-Icon wie vorhanden).
- Tests: vor `manage.py test` `compilemessages -l de` (sonst 12 E-Mail-Tests rot); Lockfile nur in den nötigen Zeilen ändern (keine npm-11-Neugenerierung).
- Doku: `docs/INSTALL.md`, LTI-Abschnitt — Registrierungs-Link als empfohlener Weg für Moodle.

- [ ] **Step 1–7** analog Task 6.

---

### Task 8: Abnahme gegen ein echtes Moodle

**Files:** keine Code-Dateien; Ergebnisse als Kommentar in den PRs und ggf. Korrektur der Tool-Doku.

- [ ] **Step 1:** Moodle 4.5 lokal per Docker (z. B. `moodlehq/moodle-docker`) oder Test-Moodle der Uni; Tool lokal mit `LTI_REGISTRATION_ALLOW_HTTP=True` (lokal) bzw. echt per HTTPS.
- [ ] **Step 2:** Link im Tool erzeugen, in Moodle eintragen. Prüfen und festhalten: Moodle öffnet die Seite im iframe (oder Fenster) ohne CSP-Blockade; `registration_token` kommt an; Dialog schließt sich nach Erfolg (`org.imsglobal.lti.close`); Tool steht in Moodle als ausstehend; Plattform im Tool aktiv mit Deployment-ID.
- [ ] **Step 3:** In Moodle aktivieren, Startcontainer „Neues Fenster“, Aktivität anlegen: Launch als Lehrende(r) und Studierende(r), Deep Linking (abstimmbar: Raum, ausleihbar: Pool).
- [ ] **Step 4:** Bekannter-Issuer-Fall: zweiten Link mit derselben Moodle-Instanz → Nachfrage erscheint; „Abbrechen“ schließt den Dialog, Link bleibt offen.
- [ ] **Step 5:** Abweichungen von der Spec-Liste „Noch gegen ein echtes Moodle zu verifizieren“ in Spec und Tool-Doku nachtragen; Moodle-Versionen der Uni erfragen und notieren.
