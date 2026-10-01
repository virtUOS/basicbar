# Copier-Template

Das Projektgerüst der „-bar“-Tools (`template/project/`, Fragen in
[copier.yml](../copier.yml) im Repo-Root). Neues Tool erzeugen:

```bash
# --vcs-ref HEAD ist Pflicht: ohne den Schalter nimmt Copier den neuesten
# PAKET-Tag (lti/v…, ui/v…) als Template-Version und generiert veraltet.
pipx run copier copy --vcs-ref HEAD https://github.com/virtUOS/basicbar.git mein-tool
cd mein-tool && git init -b main && git add -A && git commit -m "Gerüst aus basicbar-Template"
docker compose up -d && docker compose exec backend python manage.py migrate
```

Die Fragen: Name/Titel/Beschreibung, vier projektfreie Ports, zwei
OKLCH-Farbtöne als Start-Identität, `use_lti` und `ci_host` (`github` =
GitHub Actions + Release-Image nach GHCR, `gitlab` = Pipeline auf der
Uni-GitLab). Copier zeigt nach der Generierung die nächsten Schritte an
(Lockfile committen, main schützen).

Enthalten: Django + DRF auf `basicbar-auth`/`basicbar-integrations` (LTI 1.3
optional), React/Vite auf `@basicbar/ui` (App-Shell mit Login und
`PreferencesMenu`; Farb-Ramps aus den Hue-Fragen), Keycloak-Dev-Realm mit
Demo-Konten, Compose-Stack, ruff-Konfiguration, Basis-Tests, CI — **und das
Prod-Gerüst**: Root-`Dockerfile` (SPA gebacken), `docker-compose.prod.yml`
(Pflichtvariablen per `:?`), `.env.prod.example`, `Caddyfile`, bei GitHub der
Release-Workflow nach GHCR. Die Settings verweigern `DJANGO_DEBUG=0` mit dem
Entwicklungs-`SECRET_KEY`.

## Updates in bestehende Tools

`pipx run copier update --vcs-ref HEAD` im Tool spielt Gerüst-Änderungen als
Diff ein (Basis: `.copier-answers.yml`). Per `_skip_if_exists` bleiben die
Dateien unberührt, die dem Tool gehören: `tailwind.config.js` (Identität),
`App.tsx`, `locales/`, `README.md`, `CLAUDE.md`, `keycloak/realm-export.json`,
`Caddyfile`, `.env.prod.example`. Updates betreffen also compose, Dockerfiles,
CI, `settings.py`, `api.ts` — dort den Diff lesen.

## Qualitätssicherung

Die Repo-CI (`template-probe`) rendert das Template bei jedem Push mit
Defaults (LTI an, `ci_host=github`) und fährt Lint, `manage.py check`,
`makemigrations --check`, die Testsuite gegen PostgreSQL und den
Frontend-Build der generierten Anwendung. Lokal:

```bash
pipx run copier copy --trust --defaults --vcs-ref HEAD --data project_slug=probe . /tmp/probe
```

Erster echter Konsument: **erkennbar** (2026-07-19, inkl. verifiziertem
copier-update-Roundtrip).
