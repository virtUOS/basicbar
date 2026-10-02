# Basicbar

Die gemeinsame Basis der virtUOS „-bar“-Tools ([ausleihBAR](https://gitlab.uni-osnabrueck.de/virtuos/digitale-dienste/ausleihbar),
[abstimmBAR](https://github.com/virtUOS/abstimmbar),
[erkennBAR](https://gitlab.uni-osnabrueck.de/virtuos/digitale-dienste/erkennbar), …).

Dieses Repo ist **kein lauffähiges Produkt**, sondern liefert zwei Dinge:

1. **Vier versionierte Pakete** mit den Bausteinen, die alle Tools teilen —
   Verbesserungen werden einmal hier gemacht und erreichen jedes Tool über
   einen Versions-Bump.
2. **Ein Copier-Template**, aus dem ein neues Tool in Minuten als
   lauffähiges Gerüst entsteht (Django + React + Keycloak + CI) und das
   spätere Gerüst-Verbesserungen per `copier update` nachliefert.

**Stack:** Python/Django + DRF · React + Vite + Tailwind · OIDC (Keycloak) ·
optional LTI 1.3, LibreTranslate, LiteLLM (per Env aktivierbar) · Docker
Compose · Caddy. Lizenz Apache-2.0.

## Die Pakete

| Paket | Inhalt |
|---|---|
| `basicbar-auth` | OIDC-Login (mozilla-django-oidc): Backend mit Claim-Mapping und IdP-Gruppen→Admin, Silent SSO, Back-Channel-Logout, Endpoint-Discovery, `AbstractBasicUser`, optionale Account-Obergrenze und Subject-Drift-Heilung. Session-Endpunkte (`whoami_payload`, `logout_view`, `set_language`) und URL-Verdrahtung. Betreiber-Hinweise zu Löschfristen/Kennungs-Vakanz im Paket-README. |
| `basicbar-integrations` | Optionale Dienste, aus per Default: LibreTranslate-Client + Übersetzungs-Endpunkt, LiteLLM-Client (OpenAI-kompatibel), `capabilities_payload()` fürs `whoami`, HTML-Allowlist (nh3), Übersetzungs-Sync-Helfer. |
| `basicbar-lti` | LTI-1.3-Fundament (PyLTI1p3): Plattform-Registrierung + Staff-API, Tool-Keypair, OIDC-Initiation/JWKS, JIT-Nutzer-Provisionierung mit optionaler E-Mail-Unifizierung, iframe-Middleware. Der Launch selbst bleibt Tool-Code (Kurskontext → Fachmodell). |
| `@basicbar/ui` | Designsystem-Basis: Tailwind-Preset (Font, Dark Mode, Motion — die Farb-Ramps bleiben als Identität im Tool: „ein System, pro Tool ein Akzent“), `base.css` (A11y-Grundausstattung), ThemeProvider, i18n-Bootstrap, `contentLang`, `TranslatableField`/„alle Felder übersetzen“, Preferences-Menü, `RichText`; `RichTextEditor` (TipTap) als eigener Entry. |

Aktuelle Versionen: die Tags `<paket>/vX.Y.Z` bzw. [CHANGELOG.md](CHANGELOG.md)
(dort auch die Migrationsschritte je Release). Details und Begründungen:
[docs/ADR/](docs/ADR/) · Historie und Vorgehen:
[docs/EXTRAKTIONSPLAN.md](docs/EXTRAKTIONSPLAN.md).

## Neues Tool erzeugen

```bash
pipx run copier copy --vcs-ref HEAD https://github.com/virtUOS/basicbar.git mein-tool
cd mein-tool
git init -b main && git add -A && git commit -m "Gerüst aus basicbar-Template"
docker compose up -d
docker compose exec backend python manage.py migrate
```

Copier fragt Name, Titel, Ports (kollisionsfrei zu den anderen Tools) und
zwei OKLCH-Farbtöne als Start-Identität; LTI ist zuschaltbar. Danach läuft
ein anmeldbares Gerüst: SPA mit Login/Theme/Sprachumschalter, Keycloak-Realm
mit Demo-Konten (`demo`/`demo`, Admin `admin-demo`), Tests und CI inklusive.

## Basis in einem Tool nutzen und aktualisieren

Das [CHANGELOG.md](CHANGELOG.md) ist die Upgrade-Anleitung: Jeder
Release-Eintrag nennt die Migrationsschritte.

- **Django-Pakete** (`backend/requirements.txt`) — Installation direkt vom
  Git-Tag, ohne Registry und ohne git im Docker-Image:

  ```
  basicbar-auth @ https://github.com/virtUOS/basicbar/archive/refs/tags/auth/v0.1.0.tar.gz#subdirectory=packages/django/basicbar-auth
  ```

- **`@basicbar/ui`** (`frontend/package.json`) — Tarball-URL auf ein GitHub
  Release (die CI hängt den Tarball beim Tag `ui/vX.Y.Z` als Release-Asset an):

  ```
  "@basicbar/ui": "https://github.com/virtUOS/basicbar/releases/download/ui/v0.2.1/basicbar-ui-0.2.1.tgz"
  ```

- **Projektgerüst** (compose, Caddy, CI, config, App-Shell) —
  `pipx run copier update --vcs-ref HEAD` im Tool spielt Template-Änderungen
  als Diff ein (Basis: die generierte `.copier-answers.yml`).

**Wichtig:** Copier immer mit `--vcs-ref HEAD` aufrufen. Ohne den Schalter
hält Copier den neuesten *Paket*-Tag (`lti/v…`, `ui/v…`) für die
Template-Version und generiert von einem alten Stand — die Paket-Tags
versionieren die Pakete, nicht das Template.

Grundregel: **Paketcode wird im Tool nie lokal gepatcht.** Änderungen
gehören hierher; Erweiterungspunkte (Settings, Subclassing, Render-Props)
sind Paket-Features.

## An der Basis mitarbeiten

- Branch + PR (main ist geschützt); CI: SPDX-Header-Check, Testsuiten aller
  drei Django-Pakete, UI-Build, Tag-Publish.
- Paket-Tests lokal: `cd packages/django/<paket> && python runtests.py` ·
  UI: `cd packages/ui && npm install && npm run build && npx tsc --noEmit`.
- Release: Version heben, CHANGELOG-Eintrag mit Migrationsschritten, PR;
  **nach dem Merge** Tag `<paket>/vX.Y.Z` auf `main` setzen.
- **Rule of Two:** Extrahiert wird nur, was mindestens zwei Tools konkret
  brauchen und eines erprobt hat. Fachlogik und konkrete User-Models bleiben
  in den Tools ([ADR-0003](docs/ADR/0003-user-model-bleibt-im-tool.md)).
- Weitere Konventionen für die Arbeit im Repo: [CLAUDE.md](CLAUDE.md).
