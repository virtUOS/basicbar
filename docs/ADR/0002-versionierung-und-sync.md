# ADR-0002: Versionierung, Distribution und Sync-Workflow

Status: angenommen (2026-07-18)

## Kontext

Die Pakete aus ADR-0001 müssen die Tools erreichen, ohne dass wir sofort eine
Registry-Infrastruktur betreiben; Updates sollen bewusst und pro Tool
passieren.

## Entscheidung

- **SemVer pro Paket**, Git-Tags im Schema `<paket>/vX.Y.Z`
  (z. B. `integrations/v1.2.0`, `ui/v0.3.1`).
- **pip-Pakete: als Git-Archiv-Tarball vom Tag**, kein Registry-Betrieb und
  kein ``git`` im Docker-Image nötig (Entscheidung 2026-07-19: Repo ist dafür
  öffentlich, damit Docker-Builds ohne Credentials installieren):
  `basicbar-integrations @ https://github.com/virtUOS/basicbar/archive/refs/tags/integrations/v0.1.0.tar.gz#subdirectory=packages/django/basicbar-integrations`
  (ursprünglich als GitLab-Archiv-Tarball, seit dem Umzug auf GitHub — siehe
  [ADR-0004](0004-umzug-nach-github.md) — als GitHub-Archiv-Tarball, gleiches
  Prinzip).
- **npm-Paket: GitHub Release Asset** (npm kann — anders als pip — nicht aus
  einem Unterverzeichnis eines Git-Repos installieren, und ein öffentliches
  Release-Asset braucht wie die Django-Tarballs keine Registry/Credentials).
  Publish per CI-Job beim Taggen von `ui/vX.Y.Z`.
- **Template:** Copier arbeitet direkt gegen das Git-Repo
  (`copier copy https://github.com/virtUOS/basicbar.git …`); `copier update`
  nutzt die im Projekt hinterlegte Template-Version (`.copier-answers.yml`).
- **Changelog als Upgrade-Vertrag:** Jeder Release-Eintrag im CHANGELOG.md
  nennt nötige Migrationsschritte der Tools. Breaking Change ⇒ Major-Bump.

## Sync-Workflow (der „Design-Sync“)

1. Änderung in basicbar committen, `CHANGELOG.md` ergänzen.
2. Tag `<paket>/vX.Y.Z` setzen und pushen (CI published ggf. das npm-Paket).
3. In jedem Tool bei Gelegenheit: Version im `pyproject.toml`/`package.json`
   heben, Changelog-Migrationsschritte ausführen, Tests laufen lassen — pro
   Tool ein kleiner, reviewbarer Commit.

## Konsequenzen

- Kein Auto-Update: Tools können Versionen unterschiedlich lange fahren;
  divergierende Optik zwischen Releases ist akzeptiert und gewollt reversibel.
- Sollte die Paketzahl oder Release-Frequenz stark wachsen, kann später auf
  eine PyPI-/npm-Registry umgestellt werden, ohne die Tags zu ändern.

**Update 2026-08-04:** Repo-Host von GitLab auf GitHub gewechselt (Details und
Gründe: [ADR-0004](0004-umzug-nach-github.md)); die Distributionsmechanik
(Archiv-Tarball für pip, Release-Asset für npm) bleibt unverändert, nur die
URLs zeigen jetzt auf `github.com/virtUOS/basicbar`.
