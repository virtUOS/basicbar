# basicbar-lti

LTI-1.3-Fundament der „-bar“-Tools (auf Basis von PyLTI1p3):

- **Models:** `LtiPlatform` (Registrierung inkl. `link_by_email`-Opt-in),
  `LtiToolKey` (Tool-Keypair, auto-generiert), `LtiUserLink`
  (LTI-Subject ↔ lokaler User, plattform-scoped).
- **`tool_conf.build_tool_conf()`** — Brücke von den DB-Registrierungen zu
  pylti1p3.
- **Views:** `lti_login` (OIDC-Initiation), `lti_jwks`,
  `LtiPlatformViewSet` + `LtiToolInfoView` (Staff-API; Permission per
  Subclass anpassbar).
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
path("lti/login/", lti_login), path("lti/jwks/", lti_jwks),
# + Tool-eigener /lti/launch/ aus den provisioning-Primitiven
```

## Bestands-Deployment adoptieren (abstimmbar-Muster)

Die Tabellen behalten den historischen `lti_*`-Präfix. Ein Tool, das die
Models bisher selbst trug: alte Migrationshistorie auf das eigene
Kontext-Link-Model reduzieren (Abhängigkeit auf `basicbar_lti.0001`) und
einmalig **`python manage.py migrate --fake-initial`** ausführen — die
vorhandenen Tabellen werden übernommen, nichts wird angefasst. Frische
Installationen migrieren normal.

Tests: `python runtests.py` (simuliert den kompletten LMS-Handshake:
OIDC-Initiation, signierte id_tokens, JWKS, Account-Verknüpfung).
