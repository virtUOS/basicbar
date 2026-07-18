# ADR-0001: Drei Mechanismen statt eines — Template, pip-Pakete, npm-Paket

Status: angenommen (2026-07-18)

## Kontext

Vier Tools (ausleihbar, abstimmbar, erkennbar, modulierbar) teilen dasselbe
Fundament: Django + DRF, React + Vite, OIDC/Keycloak, optionale Dienste
(LTI 1.3, LibreTranslate, LiteLLM), Lucide, Dark Mode, de/en, Caddy, Docker
Compose. Bisher wurde per Copy & Paste geteilt; die Analyse (Phase 0) zeigte,
dass Kopien binnen Tagen divergieren (`translation_service.py` wurde beim
Portieren verbessert, ohne dass der Ursprung es zurückbekam; `index.css` war
nach wenigen Wochen fast vollständig auseinander).

Die Bestandteile der Basis haben unterschiedliche Änderungs- und
Kopplungsprofile:

- **Gerüst** (docker-compose, Caddyfile, `config/`, CI): pro Tool angepasst,
  nie als Ganzes austauschbar — Kopie mit Update-Pfad nötig.
- **Backend-Bausteine** (OIDC-Machinerie, Integrations-Clients, LTI): klar
  abgegrenzte Module ohne Tool-Fachlogik — als Abhängigkeit teilbar.
- **Design/UI**: soll über alle Tools synchron aussehen — als Abhängigkeit
  teilbar, Sync per Versions-Bump.
- **Fachlogik** (lending, live, catalog, …): nie teilbar.

## Entscheidung

Kein Monorepo, kein reines Template, keine reine Paketsammlung, sondern drei
Mechanismen mit klarer Zuständigkeit in einem Repo (basicbar):

1. **Copier-Template** (`template/`) für das Gerüst. Copier (nicht
   Cookiecutter), weil `copier update` spätere Template-Änderungen als Diff in
   bestehende Projekte einspielen kann.
2. **pip-Pakete** (`packages/django/`): `basicbar-auth`,
   `basicbar-integrations`, `basicbar-lti` — wiederverwendbare Django-Apps.
3. **npm-Paket** (`packages/ui/`, `@basicbar/ui`): Design-Tokens
   (CSS-Variablen), Theme + Dark Mode, i18n-Bootstrap, Basis-Komponenten.

Fachlogik und konkrete User-Models (ADR-0003) bleiben in den Tools.

## Konsequenzen

- Designänderungen werden einmal im UI-Paket gemacht und per Versions-Bump in
  jedes Tool geholt — bewusst explizit, kein Auto-Update: ein Fehler legt
  nicht alle Tools gleichzeitig lahm.
- Die Basis ist ein eigenes Produkt mit Pflegeaufwand (SemVer, Changelog,
  kleine Releases). Gegen Über-Abstraktion gilt die Rule of Two: extrahiert
  wird nur, was zwei Tools brauchen und eines erprobt hat.
- Tools patchen Paketcode nie lokal; wer etwas ändern muss, ändert es in
  basicbar und bumpt. Erweiterungspunkte (Settings, Hooks) sind Paket-Features.
