# basicbar-auth

OIDC-Fundament der „-bar“-Tools (auf Basis von mozilla-django-oidc):

- `oidc.OIDCBackend` — Claim-Mapping aufs Tool-User-Model, Just-in-time-
  Provisionierung, IdP-Gruppe → Django-Admin, optionale Account-Obergrenze
  und Subject-Drift-Fallback (beides aus per Default).
- `oidc.SilentLoginView` — Silent SSO (`prompt=none`, kein Redirect-Loop).
- `oidc.SafeOIDCCallbackView` — mozillas Callback, der einen wiederholten
  Callback (Browser-„Zurück“ direkt nach dem Login) auf die SPA umleitet
  statt eine 400-Seite zu zeigen; loggt niemanden ein.
- `oidc.backchannel_logout` — OIDC Back-Channel Logout 1.0 (Token-Prüfung,
  löscht alle Sessions des Subjects über den Session-Index).
- `oidc.provider_logout_url`, `oidc.is_oidc_admin`, `oidc.claims_in_admin_group`
- `views.whoami_payload` / `views.whoami`, `views.logout_view`,
  `views.set_language` — die Session-Endpunkte der SPA; `urls.urlpatterns`
  verdrahtet OIDC-Routen und `api/whoami/language/`.
- `discovery.discover_endpoints` — Endpunkte aus `OIDC_OP_ISSUER` ableiten.
- `models.AbstractBasicUser` — Basis fürs konkrete `accounts.User` des Tools
  (`subject`, `claims`, `language`; ADR-0003: Model und Migrationen bleiben
  im Tool). `models.UserSession` — Index Nutzer → Session (eigene
  Migration im Paket).

## Einbinden

```python
INSTALLED_APPS = [..., "basicbar_auth"]   # hat seit 0.2 eine eigene Migration
AUTHENTICATION_BACKENDS = [
    "basicbar_auth.oidc.OIDCBackend",
    "django.contrib.auth.backends.ModelBackend",
]
OIDC_OP_LOGOUT_URL_METHOD = "basicbar_auth.oidc.provider_logout_url"

# urls.py — logout-redirect, silent, backchannel-logout, callback, mozilla,
# api/whoami/language/ in einem Rutsch; api/whoami/ bleibt Sache des Tools:
path("", include("basicbar_auth.urls")),
path("api/whoami/", whoami),

# accounts/models.py
class User(AbstractBasicUser):   # subject, claims, language kommen mit
    ...                           # (ein eigenes, gleiches `language` darf bleiben)

# accounts/views.py — whoami mit Tool-Feldern:
from basicbar_auth.views import whoami_payload
def whoami(request):
    return JsonResponse({**whoami_payload(request), "ai_enabled": ai.is_enabled()})
```

`whoami_payload` liefert `authenticated`, `csrf_token` und — angemeldet —
`username`, `first_name`, `last_name`, `email`, `subject`, `is_staff`,
`language`. Ohne eigene Felder reicht `basicbar_auth.views.whoami` direkt.

Claim-Namen (`OIDC_CLAIM_USERNAME`, …), `OIDC_GROUPS_CLAIM`/`OIDC_ADMIN_GROUP`
und die optionalen Verhalten kommen aus Settings mit Paket-Defaults
(`conf.py`). Bestehende Tools adoptieren ohne Umbau ihres User-Models
(`AbstractUser` + identische Felder funktioniert weiter).

**Admin-Gruppe:** Mit `OIDC_ADMIN_GROUP` verleiht die Gruppenmitgliedschaft
`is_staff`/`is_superuser` und ihr Verlust entzieht sie — aber nur Rechte,
die aus der Gruppe kamen (erkennbar am Claims-Snapshot des letzten Logins).
Eine Beförderung im Tool (Nutzerverwaltung, Django-Admin) überlebt den
nächsten Login; `is_oidc_admin(user)` sagt dem Tool, welche Admins der IdP
verwaltet (die darf das Tool lokal nicht entziehen).

**Session-Index:** `user_logged_in`/`user_logged_out` pflegen `UserSession`;
der Back-Channel-Logout löscht darüber gezielt, statt jede unabgelaufene
Session zu dekodieren (relevant bei vielen anonymen Besucher-Sessions).
Sessions aus der Zeit vor 0.2 kennt der Index nicht — für sie bleibt der
Scan als Fallback, bis sie ablaufen. Voraussetzung ist der DB-Session-Store.

**Discovery:** `discover_endpoints` loggt Fehler (WARNING) und liefert `{}`,
damit der Settings-Import nicht abstürzt. Produktiv sollten die Settings bei
leeren Endpunkten mit `ImproperlyConfigured` abbrechen (so das Template),
sonst scheitert jeder Login später mit einem unklaren Fehler.

## Betreiber-Hinweise (Fristen, Kennungs-Wiedervergabe)

Zwei optionale Verhalten hängen von der **Policy eures Identity Providers zur
Wiedervergabe von Usernamen/E-Mail-Adressen** ab. Die Software bleibt
standort-neutral — die Policy ist Konfiguration:

- **`OIDC_MATCH_BY_USERNAME_FALLBACK`** (Default: aus). Heilt neu vergebene
  Subjects (Realm-Reimport, IdP-Migration) durch Username-Match, statt beim
  Login mit einem Unique-Constraint-Fehler zu scheitern. **Nur aktivieren,
  wenn der IdP Usernamen nie an andere Personen neu vergibt** — sonst könnte
  eine neue Person das verwaiste Konto (samt Historie!) ihrer Vorgängerin
  erben. An Hochschulen üblich sind Mindest-Vakanzzeiten für Kennungen;
  fragt eure IdP-Betreiber.
- **Löschfrist für inaktive Accounts** (Retention/Anonymisierung — die
  Umsetzung liegt derzeit im jeweiligen Tool, z. B. ausleihbar; das Paket
  liefert dafür `last_login`-Pflege und die `anonymized_at`-Konvention).
  Faustregel: **Anonymisierungsfrist deutlich kürzer wählen als die
  Mindest-Vakanzzeit des IdP.** Dann ist ein Konto längst anonymisiert,
  bevor seine Kennung theoretisch neu vergeben werden könnte, und der
  Username-Fallback bleibt auch mit Wiedervergabe risikofrei. Werden
  Kennungen nie neu vergeben, sind beide Schalter unkritisch.
- **`MAX_USERS`** (Default: unbegrenzt): Obergrenze für Konten; anonymisierte
  Konten (Konvention: Feld `anonymized_at`) belegen keinen Platz. Bestehende
  Nutzer können sich immer anmelden, nur neue Identitäten werden abgewiesen.

Tests: `python runtests.py` (oder über die Repo-CI).
