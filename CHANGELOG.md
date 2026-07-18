# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/), ein Abschnitt
pro Paket-Release (Tag `<paket>/vX.Y.Z`). Jeder Eintrag nennt, was sich ändert
und was ein konsumierendes Tool beim Upgrade tun muss („Migration“) — dieses
Changelog ist die Upgrade-Anleitung für die Tools.

## [Unreleased]

### basicbar-integrations (→ wird `integrations/v0.1.0`)
- Erstes Paket (Phase 2): `ai` (LiteLLM-Client) und `translation_service`
  (LibreTranslate-Client) aus den konsolidierten Tool-Fassungen übernommen;
  Settings-Zugriff jetzt mit Paket-Defaults (`conf.py`) — unkonfiguriert ist
  alles aus, ein Tool ohne Settings-Block startet unverändert.
- Kanonischer Translate-Endpunkt: `POST {text, source, target, format?}` →
  `{translated}`; Sprachvalidierung, HTML-Sanitizing (`html_sanitize.py` aus
  abstimmbar, jetzt mit nh3-Abhängigkeit), englische Fehlertexte.
- Neu: Capabilities-Endpoint (`GET` → `{"translation": bool, "ai": bool}`,
  erweiterbar per `extra_capabilities()`).
- Migration ausleihbar: Response-Key `translation` → `translated`, URL
  `/api/manage/translate/` → Paket-URL, `TranslateView`-Subclass für die
  `IsLenderOrAdmin`-Permission, Format-Validierung neu.
- Migration abstimmbar: Fehlertexte nun englisch; Imports `common.ai` /
  `common.translation_service` / `common.html_sanitize` →
  `basicbar_integrations.*`.

### Repo
- Phase 1: Repo-Gerüst, ADRs 0001–0003, CI (SPDX-Check), Extraktionsplan.
- CI: Testjob für basicbar-integrations (python:3.12-slim).
