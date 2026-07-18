# Basicbar

Die gemeinsame Basis der „-bar“-Tools des virtUOS (ausleihbar, abstimmbar,
erkennbar, …): ein Projekt-Template plus versionierte Pakete, aus denen neue
Tools schnell starten und über die Verbesserungen — insbesondere Design — in
bestehende Tools zurückfließen.

**Stack:** Django + DRF · React + Vite · OIDC (Keycloak) · optional LTI 1.3,
LibreTranslate, LiteLLM (per Env aktivierbar) · Lucide Icons · Dark Mode ·
Zweisprachigkeit (de/en) · Caddy · Docker Compose

## Architektur: drei Mechanismen

| Ebene | Mechanismus | Sync in die Tools |
|---|---|---|
| Projektgerüst (compose, Caddy, config, CI) | Copier-Template ([template/](template/)) | `copier update` |
| Backend-Bausteine (Auth/OIDC, Integrationen, LTI) | pip-Pakete ([packages/django/](packages/django/)) | Version pinnen & heben |
| Design & UI (Tokens, Theme, Komponenten, i18n) | npm-Paket ([packages/ui/](packages/ui/)) | Version pinnen & heben |

Fachlogik bleibt immer im jeweiligen Tool. Details und Begründungen:
[docs/ADR/](docs/ADR/), Vorgehen und Status: [docs/EXTRAKTIONSPLAN.md](docs/EXTRAKTIONSPLAN.md).

## Status

- **Phase 0 (Konsolidierung)** ✅ abgeschlossen — die Fundament-Dateien von
  ausleihbar und abstimmbar sind wieder deckungsgleich.
- **Phase 1 (dieses Repo)** ✅ Gerüst, ADRs, CI.
- **Phase 2** ⏳ als Nächstes: `basicbar-integrations` als erstes pip-Paket.

## Konventionen

- Lizenz Apache-2.0; jede Quelldatei trägt einen SPDX-Header
  (`SPDX-License-Identifier: Apache-2.0`, Copyright Universität Osnabrück
  (virtUOS)). Die CI prüft das.
- Commits: [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat(ui): …`, `fix(integrations): …`).
- Versionierung: SemVer pro Paket, Git-Tags `<paket>/vX.Y.Z`
  (siehe [ADR-0002](docs/ADR/0002-versionierung-und-sync.md)).
- Änderungen an Paketen werden im [CHANGELOG.md](CHANGELOG.md) festgehalten —
  das ist die Upgrade-Anleitung für die Tools.
- In die Basis wandert nur, was mindestens zwei Tools konkret brauchen und in
  einem erprobt wurde („Rule of Two“). Paketcode wird in den Tools nie lokal
  gepatcht; Erweiterungspunkte sind Paket-Features.
