# Copier-Template

Das Projektgerüst der „-bar“-Tools (`template/project/`, Fragen in
[copier.yml](../copier.yml) im Repo-Root). Neues Tool erzeugen:

```bash
pipx run copier copy https://gitlab.uni-osnabrueck.de/virtuos/digitale-dienste/basicbar.git mein-tool
cd mein-tool && git init -b main && git add -A && git commit -m "Gerüst aus basicbar-Template"
docker compose up -d && docker compose exec backend python manage.py migrate
```

Enthalten: Django + DRF auf `basicbar-auth`/`basicbar-integrations`
(LTI 1.3 optional per Frage), React/Vite auf `@basicbar/ui` (App-Shell mit
Login/Theme/Sprache; Farb-Ramps aus den Hue-Fragen als Start-Identität),
Keycloak-Dev-Realm mit Demo-Konten, Compose-Stack mit projektfreien Ports,
Caddyfile, GitLab-CI (ruff, Tests gegen PostgreSQL, Frontend-Build),
README/CLAUDE.md.

Spätere Gerüst-Änderungen holt ein Tool mit `pipx run copier update`
(Basis: die generierte `.copier-answers.yml`). Erster echter Konsument:
**erkennbar** (2026-07-19, inkl. verifiziertem copier-update-Roundtrip).
