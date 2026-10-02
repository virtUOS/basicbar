# Basicbar — Hinweise für Claude

Gemeinsame Basis der virtUOS „-bar“-Tools (ausleihbar, abstimmbar,
erkennbar, …): **vier versionierte Pakete + ein Copier-Template**, kein
lauffähiges Produkt. Konsumenten sind die Tool-Repos daneben in `~/dev/<tool>`
— teils noch auf der Uni-GitLab (`virtuos/digitale-dienste/<tool>`), teils
öffentlich auf GitHub (z. B. `virtUOS/abstimmbar`). basicbar selbst liegt seit
2026-08-04 auf `github.com/virtUOS/basicbar` (ADR-0004), u. a. damit
GitHub-Actions-Runner öffentlicher „-bar“-Tools die Pakete erreichen können.

## Layout

- `packages/django/basicbar-integrations` — LibreTranslate-/LiteLLM-Clients,
  Translate-Endpoint, `capabilities_payload()` fürs `whoami` der Tools,
  HTML-Allowlist (nh3), Übersetzungs-Sync-Helfer.
- `packages/django/basicbar-auth` — OIDC (mozilla-django-oidc): Backend,
  Silent Login, Back-Channel-Logout (mit Session-Index `UserSession`, eigene
  Migration), Discovery, `AbstractBasicUser`, Session-Endpunkte
  (`views.whoami_payload`/`logout_view`/`set_language`, `urls`), optionale
  Limits (`MAX_USERS`, Drift-Fallback). Betreiber-Doku im README.
- `packages/django/basicbar-lti` — LTI-1.3-Fundament (PyLTI1p3):
  Plattform-Registrierung, Tool-Key, Provisionierung, Middleware.
  Launch/Deep-Linking bleiben Tool-Code.
- `packages/ui` — `@basicbar/ui`: Tailwind-Preset (`createPreset`),
  `base.css`, ThemeProvider, `initI18n`, `contentLang`,
  `TranslatableField`/`TranslationForm`. Build: tsup.
- `template/project` + `copier.yml` (Repo-Root) — Projektgerüst neuer Tools.
- `docs/EXTRAKTIONSPLAN.md` (Phasen + Entscheidungen), `docs/ADR/`,
  `CHANGELOG.md` (= Upgrade-Anleitung der Tools).

## Befehle

```bash
# Django-Pakete (brauchen nur ihre pyproject-Dependencies):
cd packages/django/<paket> && python runtests.py
# ohne lokales venv: im Backend-Container eines Tools
docker cp packages/django/<paket> <tool>_backend:/tmp/pkg \
  && docker exec <tool>_backend sh -c "cd /tmp/pkg && python runtests.py"

# UI-Paket:
cd packages/ui && npm install && npm run build && npx tsc --noEmit

# Template rendern (Nagelprobe). --vcs-ref HEAD ist bei copier PFLICHT:
# ohne den Schalter gilt der neueste Paket-Tag als Template-Version.
pipx run copier copy . /tmp/probe --trust --defaults --vcs-ref HEAD --data project_slug=probe
```

## Workflow & Releases

- **Branch + PR, nie direkt auf main** (main ist geschützt); der Mensch merged.
- Release eines Pakets: Version in `pyproject.toml`/`package.json` heben,
  `CHANGELOG.md`-Eintrag **mit Migrationsschritten für die Tools**, PR.
  **Tag `<paket>/vX.Y.Z` erst nach dem Merge** auf den main-Commit setzen
  (sonst zeigt er auf verwaiste Commits). Beim Tag `ui/v*` packt die CI
  `@basicbar/ui` per `npm pack` und hängt den Tarball als GitHub-Release-Asset
  an — **als Draft**: Assets eines Drafts sind nicht öffentlich, die URL in
  den Tool-`package.json`s funktioniert erst nach dem manuellen „Publish
  release“ (`gh release edit ui/vX.Y.Z --draft=false`). Die Django-Pakete
  werden von den Tools direkt als GitHub-Archiv-Tarball
  vom Tag installiert (`/archive/refs/tags/<tag>.tar.gz#subdirectory=…` — Repo
  ist deshalb öffentlich). Details/Gründe des Hosts:
  [ADR-0004](docs/ADR/0004-umzug-nach-github.md).
- Nach dem Paket-Release: Konsumenten-PRs in den Tools (Version bumpen,
  Migrationsschritte aus dem Changelog ausführen, Suite + Build grün).

## Konventionen

- Apache-2.0, SPDX-Header in jeder Quelldatei (CI prüft packages/ + template/).
- **Rule of Two:** In die Basis wandert nur, was zwei Tools brauchen und
  eines erprobt hat. Keine Fachlogik, keine konkreten User-Models (ADR-0003).
- Paket-Apps: Constraint-/Index-Namen mit Paket-Präfix (Postgres hat einen
  schemaweiten Namensraum — Lehre aus lti/v0.1.x).
- App-Extraktion mit Bestandsdaten: Daten-Umzugsmigration im Tool
  (Vorlage abstimmbar `lti/0003`), nie History-Rewrite + fake-initial.
- Settings-Zugriff in Paketen über `conf.py` mit Defaults („aus per
  Default“ — unkonfiguriert ändert sich nichts).
- Template-Dateien mit Platzhaltern enden auf `.jinja`; die generierte
  `.copier-answers.yml` ist die Basis für `copier update`.
