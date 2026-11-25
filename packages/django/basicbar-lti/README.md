# basicbar-lti

LTI-1.3-Fundament der „-bar“-Tools (auf Basis von PyLTI1p3):

- **Models:** `LtiPlatform` (Registrierung inkl. `link_by_email`-Opt-in),
  `LtiToolKey` (Tool-Keypair, auto-generiert), `LtiUserLink`
  (LTI-Subject ↔ lokaler User, plattform-scoped).
- **`tool_conf.build_tool_conf()`** — Brücke von den DB-Registrierungen zu
  pylti1p3.
- **Views:** `lti_login` (OIDC-Initiation), `lti_jwks`, `lti_register`
  (Dynamic Registration), `LtiPlatformViewSet`,
  `LtiRegistrationTokenViewSet` + `LtiToolInfoView` (Staff-API; Permission
  per Subclass anpassbar).
- **`provisioning`** — `provision_user` (JIT-User mit Link-Tabelle,
  E-Mail-Unifizierung als Plattform-Opt-in, OIDC-Profile werden nie
  überschrieben), `is_instructor`, `platform_for`, `launch_storage`, `CLAIM`.
- **`LtiFrameAncestorsMiddleware`** — erlaubt das Einbetten der
  konfigurierten Pfade (`LTI_FRAME_PATH_PREFIXES`) in iframes der aktiven
  Plattformen (CSP `frame-ancestors`, injektionssicher validiert).

**Bewusst nicht im Paket:** der Message-Launch-Endpunkt und Deep Linking —
worauf ein LMS-Kurskontext abbildet (ein Raum, ein Pool, …) ist Fachlogik.
Ein Tool definiert sein eigenes Kontext-Link-Model (FK auf `LtiPlatform`)
und komponiert seinen Launch aus den Primitiven (Vorbild: abstimmbars
`lti`-App). Der User braucht `subject`/`claims`
(`basicbar_auth.AbstractBasicUser`-Konvention).

## Einbinden

```python
INSTALLED_APPS = [..., "basicbar_lti"]        # + die Tool-eigene Launch-App
MIDDLEWARE = ["basicbar_lti.middleware.LtiFrameAncestorsMiddleware", ...]
LTI_FRAME_PATH_PREFIXES = ("/lti/", "/p/")    # einbettbare HTML-Pfade

# urls.py
from basicbar_lti.views import lti_login, lti_jwks
path("lti/login/", lti_login, name="lti-login"),
path("lti/jwks/", lti_jwks, name="lti-jwks"),
# + Tool-eigener /lti/launch/ aus den provisioning-Primitiven; die View muss
#   `lti-launch` heißen (für Dynamic Registration zusätzlich `lti-register`)
```

## Dynamic Registration (ab 0.2.0)

Statt Issuer, Client-ID und Endpunkte von Hand zu kopieren, trägt der
LMS-Admin nur einen **Einmal-Link** in Moodle ein
(IMS LTI Dynamic Registration 1.0; Referenz ist Moodle, andere LMS laufen
weiter über die manuelle Registrierung). Gilt nur für **neue**
Verknüpfungen: Eine Neuregistrierung legt eine neue `LtiPlatform` mit neuer
Client-ID an; Kursverknüpfungen und Konten bestehender Plattformen bleiben
an der alten hängen.

### Ablauf

1. Der Tool-Admin erzeugt im Web-Admin einen Link
   (`LtiRegistrationTokenViewSet`, `POST`, optional mit Notiz). Die Antwort
   enthält `url` = `https://<tool>/lti/register/?token=<geheim>` **genau
   einmal**; gespeichert wird nur der SHA-256-Hash.
2. Der Moodle-Admin trägt den Link ein (Website-Administration → Plugins →
   Externe Tools → Tools verwalten → Tool-URL → „LTI Advantage hinzufügen“).
3. `lti_register` prüft den Token (offen, nicht abgelaufen), holt die
   `openid_configuration`, registriert das Tool beim LMS und legt die
   `LtiPlatform` an (`is_active=True`, `link_by_email=False`, Deployment-ID
   aus der Antwort, Name = Notiz des Links). Der Token wird im selben
   Datenbankvorgang verbraucht.
4. Bei bereits bekanntem Issuer fragt die Seite vorher nach (die bestehende
   Verknüpfung wird nicht übernommen); Abbrechen verbraucht den Token nicht.
5. Der Moodle-Admin **aktiviert** das Tool in Moodle.

**Nachschritt in Moodle:** Moodle setzt bei dynamischer Registration den
Startcontainer fest auf „Eingebettet, ohne Blöcke“. Tool bearbeiten →
Standard-Startcontainer **„Neues Fenster“** (eingebettet braucht
`SESSION_COOKIE_SAMESITE=None` und passende `frame-ancestors` am Tool). Die
Erfolgsseite nennt das, **schickt aber sofort die Schließen-Nachricht**
(`org.imsglobal.lti.close`); der Moodle-Admin sieht den Text womöglich gar
nicht. Deshalb gehören der Nachschritt „Neues Fenster“ und der Hinweis
„nur neue Verknüpfungen“ auch in den **Admin-Dialog** des Tools (neben dem
erzeugten Link) und in die Tool-Doku.

### Verdrahtung im Tool

```python
# urls.py — Name ohne Namespace, die Tool-URLs werden per reverse() gebaut
from basicbar_lti.views import lti_register, LtiRegistrationTokenViewSet
path("lti/register/", lti_register, name="lti-register"),
router.register("registration-links", LtiRegistrationTokenViewSet,
                basename="lti-registration-link")
```

Voraussetzung sind die URL-Namen `lti-login`, `lti-launch`, `lti-jwks`,
`lti-register`; `LtiToolInfoView` und die Registrierung bauen alle
Adressen daraus (`dynreg.tool_urls`), `FRONTEND_BASE_URL` wird nicht mehr
gebraucht. Das ViewSet ist per Default `IsAdminUser`; das Tool
überschreibt `permission_classes` wie bei `LtiPlatformViewSet`.
`list` zeigt Notiz, Ersteller, Ablauf, `status` (`open`/`used`/`expired`),
verknüpfte Plattform, nie den Token. `destroy` (= widerrufen, Zeile wird
gelöscht) geht nur für offene Links, sonst `400`.

**Hinter einem Reverse-Proxy** muss `SECURE_PROXY_SSL_HEADER` gesetzt sein
(z. B. `("HTTP_X_FORWARDED_PROTO", "https")`), sonst erscheinen die
Tool-URLs als `http://` und die Registrierung lehnt sie ab.

### Settings (alle optional, Defaults ändern nichts)

| Setting | Default | Bedeutung |
|---|---|---|
| `LTI_REGISTRATION_TOKEN_TTL` | `timedelta(days=7)` | Gültigkeit eines Links |
| `LTI_REGISTRATION_ALLOW_HTTP` | `False` | erlaubt `http://` und Loopback/link-lokal für lokale Entwicklung; ein System-Check (`basicbar_lti.W001`) warnt bei `DEBUG=False` |
| `LTI_TOOL_REGISTRATION` | siehe unten | was das Tool dem LMS meldet; wird Schlüssel für Schlüssel über die Defaults gelegt |

`LTI_TOOL_REGISTRATION`-Schlüssel: `client_name` (Default `"LTI Tool"`),
`description`, `logo_path` (z. B. `/lti/icon.svg`, wird absolut gemacht;
leer = kein Logo; liefert auch `icon_url` der `LtiToolInfoView`),
`messages` (Default nur `LtiResourceLinkRequest`; Tools mit Deep Linking
ergänzen `LtiDeepLinkingRequest`), `claims`
(`iss, sub, name, given_name, family_name, email`), `scope` (leer),
`custom_parameters` (`{}`).

### Sicherheitsmodell

- **Ohne gültigen Token passiert nichts:** Kein ausgehender Request, keine
  Plattform. Der Link ist geheim, einmalig, befristet und widerrufbar.
- **SSRF-Schutz:** Nur `https`; Timeout 10 s, Antworten max. 256 KiB,
  Weiterleitungen nur innerhalb desselben Origins. Abgelehnt werden
  Loopback, link-lokale (u. a. Cloud-Metadaten) und unspezifizierte
  Adressen; private Netze bleiben erlaubt (Campus-Moodle). Die
  Plattform-Endpunkte müssen auf dem Host des Issuers liegen.
- **Bekannte Grenze:** Das Festnageln der IP gegen DNS-Rebinding fehlt, und
  ausgehende Proxys aus den Umgebungsvariablen (`HTTPS_PROXY` o. ä.) werden
  beachtet — die Adressprüfung validiert dann die lokale DNS-Auflösung. Das
  ist bewusst akzeptiert, weil der Link geheim, einmalig und kurzlebig ist.
- **Fehler antworten mit `400`, nicht `502`:** 5xx-Antworten loggt
  `django.request` auf ERROR mit dem vollständigen Request — der Klartext-
  Token stünde im Query-String in Admin-Mails und Sentry. Das Paket loggt
  nur den Fehlertext und die Config-URL. Fehlgeschlagene Versuche
  verbrauchen den Token nicht.
- **Einbetten:** Nur bei gültigem Token setzt `lti_register` selbst
  `frame-ancestors 'self' <Origin der openid_configuration>`. Die
  Middleware behält ein von einer View auf `/lti/`-Seiten gesetztes
  `frame-ancestors` (nur `X-Frame-Options` entfällt) — ein Tool darf dort
  also **keine** breitere Policy selbst setzen.
- Der Token-Klartext steht nur in der Create-Antwort und in dem Link, den
  der Admin weitergibt; nie in `list`, nie in der Datenbank.

## Bestands-Deployment adoptieren (abstimmbar-Muster)

Ein Tool, das die Models bisher selbst trug, behält seine
Migrationshistorie und ergänzt **eine Daten-Umzugsmigration** (Vorlage:
abstimmbars `lti/0003_move_to_basicbar_lti`): Zeilen PK-erhaltend in die
Paket-Tabellen kopieren, Sequenzen nachziehen, den Kontext-Link-FK per
`AlterField` auf `basicbar_lti.LtiPlatform` umhängen, alte Models löschen.
Läuft als ganz normales `manage.py migrate` — kein manueller Schritt;
frische Installationen migrieren ohnehin sauber.

Tests: `python runtests.py` (simuliert den kompletten LMS-Handshake:
OIDC-Initiation, signierte id_tokens, JWKS, Account-Verknüpfung).
