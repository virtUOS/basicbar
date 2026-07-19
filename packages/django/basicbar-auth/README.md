# basicbar-auth

OIDC-Fundament der „-bar“-Tools (auf Basis von mozilla-django-oidc):

- `oidc.OIDCBackend` — Claim-Mapping aufs Tool-User-Model, Just-in-time-
  Provisionierung, IdP-Gruppen → Django-Admin (autoritativ), optionale
  Account-Obergrenze und Subject-Drift-Fallback (beides aus per Default).
- `oidc.SilentLoginView` — Silent SSO (`prompt=none`, kein Redirect-Loop).
- `oidc.backchannel_logout` — OIDC Back-Channel Logout 1.0 (Token-Prüfung,
  löscht alle Sessions des Subjects).
- `oidc.provider_logout_url`, `oidc.is_oidc_admin`, `oidc.claims_in_admin_group`
- `discovery.discover_endpoints` — Endpunkte aus `OIDC_OP_ISSUER` ableiten.
- `models.AbstractBasicUser` — Basis fürs konkrete `accounts.User` des Tools
  (`subject` + `claims`; ADR-0003: Model und Migrationen bleiben im Tool).

## Einbinden

```python
INSTALLED_APPS = [..., "basicbar_auth"]
AUTHENTICATION_BACKENDS = [
    "basicbar_auth.oidc.OIDCBackend",
    "django.contrib.auth.backends.ModelBackend",
]
OIDC_OP_LOGOUT_URL_METHOD = "basicbar_auth.oidc.provider_logout_url"

# urls.py
from basicbar_auth.oidc import SilentLoginView, backchannel_logout
path("oidc/silent/", SilentLoginView.as_view(), name="oidc-silent"),
path("oidc/backchannel-logout/", backchannel_logout, name="oidc-backchannel-logout"),
path("oidc/", include("mozilla_django_oidc.urls")),
```

Claim-Namen (`OIDC_CLAIM_USERNAME`, …), `OIDC_GROUPS_CLAIM`/`OIDC_ADMIN_GROUP`
und die optionalen Verhalten kommen aus Settings mit Paket-Defaults
(`conf.py`). Bestehende Tools adoptieren ohne Umbau ihres User-Models.

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
