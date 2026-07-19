# Basicbar — Extraktionsplan

Stand: 2026-07-18. Grundlage: Analyse von `ausleihbar` und `abstimmbar` (beide
produktiv erprobt), `erkennbar` (nur `docs/`, Greenfield).

## Ziel

Eine gemeinsame Basis, auf der neue Tools (erkennbar, modulierbar, …) schnell
starten und über die Verbesserungen — insbesondere Design — in bestehende Tools
zurückfließen können. Stack: Django + DRF, React + Vite, OIDC (Keycloak),
LTI 1.3 (optional), Lucide, LibreTranslate/LiteLLM (optional per Env),
Dark Mode, Zweisprachigkeit, Caddy, Docker Compose.

## Befund aus der Analyse

Die Fundamente sind konzeptionell identisch, aber **im Code bereits deutlich
divergiert**:

| Datei/Bereich | Divergenz | Bedeutung |
|---|---|---|
| `config/oidc_discovery.py` | identisch | direkt extrahierbar |
| `common/ai.py` (LiteLLM) | ~40/75 Zeilen | gleiche Idee, gewachsene Varianten |
| `common/translation_service.py` | in abstimmbar aus ausleihbar portiert | Muster ist bewährt, Kopien laufen auseinander |
| `accounts/` | Migrationen interleaved mit tool-spezifischen Feldern (strikes, easy_mode, retention) | **nicht als Ganzes teilbar** — nur Abstraktion teilbar |
| `frontend/src/index.css`, `theme` | fast vollständig divergiert (56/57 Zeilen) | Design ist auseinandergelaufen — genau das Problem, das die Basis lösen soll |
| `contentLang.ts` | stark divergiert | dito |
| `docker-compose.yml`, `Caddyfile` | stark divergiert (Services unterscheiden sich) | Template-Material, kein Paket |

Konsequenz: **Nicht alles wird ein Paket.** Drei Mechanismen mit klarer
Zuständigkeit:

## Architektur der Basis

```
basicbar/
├── template/                  # Copier-Template (Projektgerüst)
│   ├── copier.yml             # Fragen: Projektname, LTI ja/nein, Ports, …
│   ├── backend/               # config/, settings-Gerüst, accounts/ (konkretes User-Model)
│   ├── frontend/              # Vite-Shell, App.tsx, main.tsx, locales/
│   ├── docker-compose.yml.jinja
│   ├── Caddyfile.jinja
│   └── keycloak/
├── packages/
│   ├── django/
│   │   ├── basicbar-auth/         # OIDC-Backend, Discovery, Session-Endpoints,
│   │   │                          #   AbstractBasicUser (abstrakt!), Permissions-Basis
│   │   ├── basicbar-integrations/ # translation_service (LibreTranslate),
│   │   │                          #   ai (LiteLLM), Capabilities-Endpoint
│   │   └── basicbar-lti/          # LTI-1.3-App aus abstimmbar (pyLTI1p3-Muster)
│   └── ui/                        # @basicbar/ui (npm): Design-Tokens (CSS-Variablen),
│                                  #   Theme + Dark Mode, i18n-Setup, contentLang,
│                                  #   Basis-Komponenten (Buttons, Dialoge, Layout, …)
└── docs/
    ├── EXTRAKTIONSPLAN.md         # dieses Dokument
    └── ADR/                       # Architekturentscheidungen
```

### Synchronisationsmodell

| Ebene | Mechanismus | Update im Tool |
|---|---|---|
| Gerüst (compose, Caddy, config, CI) | Copier-Template | `copier update` (merged Diffs) |
| Backend-Bausteine | pip-Pakete via Git-Tag (`basicbar-auth @ git+…@v1.2.0`) | Version im `pyproject.toml` heben |
| Design & UI | npm-Paket `@basicbar/ui` | Version im `package.json` heben |
| Fachlogik (lending, live, catalog, …) | bleibt im Tool | — |

Designänderung einmal in `@basicbar/ui` → Versions-Bump in jedem Tool → alle
Tools sehen gleich aus. Bewusst **kein** Auto-Update: kleine, explizite
Upgrades pro Tool.

### Entscheidungen (Kurzform, Details als ADR festhalten)

1. **User-Model bleibt im Projekt.** Django-Migrationshistorien der Tools sind
   bereits mit tool-spezifischen Feldern verwoben. `basicbar-auth` liefert
   `AbstractBasicUser` + OIDC-Machinerie; jedes Tool definiert
   `accounts.User(AbstractBasicUser)` mit eigenen Migrationen. Bestehende Tools
   müssen ihr User-Model dafür *nicht* umbauen — sie adoptieren zunächst nur
   Backend/Discovery/Views.
2. **Capabilities-Endpoint** in `basicbar-integrations`: `GET /api/capabilities`
   → `{ translation: bool, ai: bool, lti: bool }`. Frontend blendet Features
   automatisch ein/aus; keine Build-Varianten.
3. **Optionalität per Env**, wie bereits etabliert (`LIBRETRANSLATE_URL`,
   `AI_PROVIDER`/`AI_BASE_URL`/…): aus = Feature unsichtbar. Stdlib-`urllib`-
   Ansatz (keine Zusatzabhängigkeiten) beibehalten.
4. **Lizenz & Header** wie gehabt: Apache-2.0, SPDX-Header
   `Copyright Universität Osnabrück (virtUOS)`.
5. **Regel für Konsumenten:** Paketcode wird im Tool nie lokal editiert. Wer
   etwas ändern muss, ändert es in basicbar und bumpt. Erweiterungspunkte
   (Hooks/Settings) sind Paket-Features, keine Forks.
6. **Regel fürs Wachstum der Basis:** Nichts wandert in die Basis, was nicht in
   mindestens zwei Tools konkret gebraucht und in einem erprobt wurde
   (gilt auch für Hilfe/Tutorials/Selbsterklärung, siehe Phase 7).

## Phasen

Reihenfolge nach Risiko und Nutzen: erst konsolidieren, dann das Stabilste
extrahieren, das Template zuletzt — validiert am Greenfield-Projekt erkennbar.

### Phase 0 — Konsolidierung in den Bestandstools (kein basicbar-Code)
Für jede divergierte Fundament-Datei die kanonische Version bestimmen
(i. d. R. die jüngere/portierte, z. B. abstimmbars `translation_service.py`)
und das jeweils andere Tool darauf angleichen. Kleine, einzeln testbare
Änderungen. Nutzen sofort, auch falls basicbar pausiert: die Zwillinge sind
wieder deckungsgleich, spätere Extraktion wird ein Move statt ein Merge.
Betroffen mindestens: `ai.py`, `translation_service.py`, `oidc.py`-Gemeinsamkeiten,
`contentLang.ts`, `i18n.ts`.

Status:
- [x] `common/ai.py` byte-identisch (2026-07-18): ausleihbar-Fassung (Ursprung,
      Typannotationen) + abstimmbars Untrusted-Output-Hinweis; Testsuiten grün
      (ausleihbar 474, abstimmbar 435).
- [x] `common/translation_service.py` byte-identisch (2026-07-18): abstimmbar-
      Fassung (mit `html=True`) kanonisch; in ausleihbar von `catalog/` nach
      `common/` verschoben, Importe in `catalog/views.py`, `accounts/views.py`,
      `catalog/tests.py` angepasst.
- [x] `accounts/oidc.py` strukturell angeglichen (2026-07-18): Docstrings
      neutralisiert, `claims_in_admin_group()` in abstimmbar als Modul-Helfer
      extrahiert (verhaltensneutral). Bewusst NICHT byte-identisch — der
      Rest-Diff sind genau die bewussten Verhaltensunterschiede. Entschieden
      (2026-07-18): beide bleiben vorerst stehen und werden in Phase 4
      Features von basicbar-auth:
      - Subject-Drift-Fallback wird ein Opt-in-Setting (z. B.
        `OIDC_MATCH_BY_USERNAME_FALLBACK`); jedes Tool/Deployment wählt.
      - Ausleihbars Usermanagement (MAX_USERS, optionale Ressourcen-
        Obergrenzen, Retention/Anonymisierung inaktiver Accounts) ist das
        Vorbild für basicbar-auth — als optionale, konfigurierbare
        Bausteine, nicht zwingend in identischer Fassung pro Tool.
      - Dokumentationsauftrag (Phase 4): Betreiber-Doku zur Wahl der
        Fristen. Kernpunkt: Die Sicherheit des Username-Fallbacks und die
        Löschfrist inaktiver Accounts hängen von der IdP-Policy zur
        Wiedervergabe von Usernamen/E-Mail-Adressen ab. Faustregel:
        Anonymisierungs-/Löschfrist deutlich kürzer als die
        Mindest-Vakanzzeit des IdP wählen; ohne Wiedervergabe (wie an der
        UOS) ist der Fallback unkritisch. Software bleibt
        standort-neutral, die Policy ist Konfiguration.
- [x] `frontend/src/i18n.ts` byte-identisch (2026-07-18): ausleihbar-Fassung
      (nur Kommentar-Unterschiede).
- [x] `frontend/src/contentLang.ts` byte-identisch (2026-07-18): Superset —
      abstimmbars `localizedMap()`/`setLocalizedLang()` (generisch statt
      de/en) + ausleihbars `defaultContentLangLabel()`; `LocalizedText`
      kanonisch hier definiert, ausleihbars `types.ts` re-exportiert;
      `AttributeSchemaEditor` nutzt statt lokaler Kopie die Helfer.
- [ ] `frontend/src/index.css` / Theme — Design-Stand wählen (Vorarbeit
      Phase 3; Kandidat für @basicbar/ui statt Datei-Angleichung)
- [x] `TranslatableField.tsx` geprüft (2026-07-18): **nicht datei-angleichbar**
      — nicht nur die Implementierung, der Komponenten-Vertrag selbst ist
      divergiert (Props, `api.translate`-Signatur, Backend-Endpunkt). Eine
      Angleichung jetzt hieße: dritte Variante entwerfen + alle Aufrufstellen
      beider Tools ändern — das ist die Design-Aufgabe von Phase 2/3, nicht
      Phase 0. Details unten bei den Phasen.

**Phase 0 damit abgeschlossen.** Ergebnis: Alles verhaltensneutral
Angleichbare ist byte-identisch; was bleibt, sind dokumentierte, bewusste
Unterschiede (oidc.py) und die als Design-Aufgaben eingeplanten
Vertrags-Divergenzen (Translate-Endpunkt, TranslatableField, Theme).

### Phase 1 — basicbar-Repo aufsetzen ✅ (2026-07-18)
Git-Repo, Layout wie oben, Tooling (uv/pip-Build für die Django-Pakete,
npm-Workspace für ui, Copier), CI (Tests der Pakete gegen unterstützte
Django-/React-Versionen), CHANGELOG-Konvention, erste ADRs.

Umgesetzt: Repo unter `virtuos/digitale-dienste/basicbar`, Layout mit
Platzhalter-READMEs, ADR-0001 (drei Mechanismen), ADR-0002 (SemVer,
`<paket>/vX.Y.Z`-Tags, pip aus Git, npm via GitLab-Registry), ADR-0003
(User-Model bleibt im Tool), CHANGELOG-Konvention, CI mit SPDX-Check.
Paket-Test-CI folgt mit den Paketen (Phase 2/3).

### Phase 2 — `basicbar-integrations` (niedrigstes Risiko zuerst)
`translation_service.py` + `ai.py` + Capabilities-Endpoint als erstes
pip-Paket. Keine Models, keine Migrationen, stdlib-only, in beiden Tools
erprobt. Danach: beide Tools stellen auf das Paket um und löschen ihre Kopien.
**Damit ist der komplette Sync-Workflow (taggen → pinnen → bumpen) einmal
end-to-end bewiesen, bevor Größeres extrahiert wird.**

Zusätzlich (Befund Phase 0): Der **Translate-HTTP-Endpunkt** gehört mit ins
Paket, und sein Vertrag wird hier kanonisch entschieden. Vorlage ist
abstimmbars Fassung (Superset): ``POST {text, source, target, format?} →
{translated}``, mit Sprachvalidierung gegen ``settings.LANGUAGES`` und
serverseitigem HTML-Sanitizing bei ``format=html`` (abstimmbars
``common/html_sanitize.py`` wandert mit). Ausleihbar stellt beim Umstieg um:
``/api/manage/translate/`` → Paket-URL, Response-Key ``translation`` →
``translated``. Die Permission bleibt pro Tool konfigurierbar (ausleihbar:
IsLenderOrAdmin, abstimmbar: IsAuthenticated). Nebenbefund: abstimmbar gibt
deutsche, ausleihbar englische API-Fehlertexte zurück — im Paket
vereinheitlichen (englisch bzw. Django-i18n).

Status: ✅ abgeschlossen (2026-07-19). Paket mit 38 Tests (inkl. der aus
abstimmbar übernommenen HTML-Allowlist-Tests), Tag `integrations/v0.1.0`.
Distribution: Repo öffentlich, Installation als GitLab-Archiv-Tarball vom
Tag (kein git im Image, Dockerfiles unverändert). Umstellungs-MRs:
ausleihbar !166, abstimmbar !90 — beide Suiten grün, Docker-Builds
end-to-end verifiziert. Der Sync-Workflow (taggen → pinnen → bumpen) ist
damit einmal komplett bewiesen. Capabilities-Endpoint ist im Paket, die
Frontend-Adoption in den Tools folgt bei Gelegenheit (z. B. mit Phase 3).

### Phase 3 — `@basicbar/ui` (der Design-Sync, Hauptmotivation)

**Befund der Design-Analyse (2026-07-19):** Die Divergenz war beabsichtigtes
Branding, kein Wildwuchs — beide Tools teilen dieselbe Token-Architektur
(OKLCH-Ramps `slate`+`brand`, identische Helligkeitsstufen, gleiche
Shade-Semantik, Font, Dark-Mode-Strategie) und unterscheiden sich bewusst im
Farbton (ausleihbar Honig ~91, abstimmbar Grün ~150, „decided July 2026“).
Modell daher: **ein Designsystem, pro Tool ein eigener Akzent** — das Paket
teilt Struktur/Verhalten via `createPreset({ colors })`, die Ramps bleiben
als Identität im Tool. Identische Optik wäre trivial möglich (gleiche Ramp
übergeben). Umsetzung: Paket gebaut (Preset-Factory, base.css als Superset
aus ausleihbars A11y-Basis + abstimmbars color-scheme-Regeln, ThemeProvider
= ausleihbars Fassung mit konfigurierbarem storageKey, initI18n-Factory,
contentLang), CI-Build + Tag-Publish in die Generic Package Registry.

1. ~~Design-Stand wählen~~ → erledigt durch obiges Modell.

Status Grundausbau: ✅ `ui/v0.1.0` released (2026-07-19, Tarball anonym
abrufbar), beide Tools umgestellt (ausleihbar !167, abstimmbar !91; tsc,
vite build und visueller Check grün; jedes Tool gewann Basis-Features des
jeweils anderen: ausleihbar color-scheme, abstimmbar Skip-Link/focus-ring/
reduced-motion/Live-Theme-Folge). Komponenten: ✅ `TranslatableField` + `TranslationForm` vereinheitlicht
(`ui/v0.2.1`, 2026-07-19; ausleihbar !168, abstimmbar !92). Abweichung von
der ursprünglichen Vorgabe, bewusst: Der Paket-Vertrag ist per Sprache
(`values` + `onChange(lang, text)`) — der primitivere Vertrag bedient
beide Speichermodelle (ausleihbar `*_de`/`*_en`-Spalten, abstimmbar
`{lang}`-Maps) direkt; abstimmbar behält einen ~70-Zeilen-Wrapper
(Map-Vertrag, `variant="rich"`/TipTap, Easy Mode) — Erweiterungspunkt
statt Fork, alle Aufrufstellen beider Tools blieben unverändert. Der
Translate-HTTP-Aufruf wird dem Provider injiziert (Paket bleibt
API-Client-frei). Wichtig für alle Komponenten-Adoptionen:
`tailwind.config` muss `./node_modules/@basicbar/ui/dist/**/*.js`
scannen. Weitere Komponenten folgen einzeln nach Rule of Two.
2. Extrahieren: Design-Tokens als CSS-Variablen, Theme + Dark Mode,
   i18n-Bootstrap, `contentLang`, Font-Setup, Lucide-Konventionen,
   5–10 wirklich gemeinsame Basis-Komponenten. Nicht mehr — Komponenten
   wandern später einzeln ein, wenn zwei Tools sie brauchen.
3. Beide Tools umstellen. Das eine Tool erhält dabei bewusst das Design-Update
   des anderen — erster realer Design-Sync als Nagelprobe.

**Erste Komponenten-Design-Aufgabe: `TranslatableField`** (Befund Phase 0 —
beide Tools haben eine, mit divergiertem Vertrag). Superset-API aus beiden:

- Wertvertrag wie abstimmbar: ``value: LocalizedText`` + ``onChange(next)``
  (map-basiert, passt zu ``localizedMap``/``setLocalizedLang``); ausleihbars
  ``values``/``onChange(lang, v)``-Aufrufstellen werden dabei umgestellt.
- Sprachen wie ausleihbar: aus ``SUPPORTED_LANGUAGES``, UI-Sprache-zuerst
  sortiert — kein hartes de/en.
- Rendering-Erweiterung: ausleihbars ``renderInput``-Render-Prop als
  generischer Mechanismus; abstimmbars ``variant="rich"`` (RichTextEditor)
  wird eine tool-lokale Spezialisierung darüber.
- Übersetzen-Button: Quellsprachen-Logik von ausleihbar (kanonisch, sonst
  irgendeine gefüllte Sprache) + ``format=html``-Support und
  ``MAX_TRANSLATE_LENGTH``-Kappe von abstimmbar.
- Easy Mode als optionales Prop (z. B. ``singleLanguage``) statt
  App-Kontext-Hook — der Kontext bleibt im Tool.
- Dazu gehört: ``TranslationForm``/``TranslatableEntry``-Vertrag
  vereinheitlichen (existiert ebenfalls in beiden Tools, divergiert) und
  ``api.translate`` auf den Phase-2-Endpunktvertrag umstellen.

### Phase 4 — `basicbar-auth` ✅ (2026-07-19)
OIDC-Backend, `oidc_discovery.py` (schon identisch), Login/Logout/Session-
Views, `AbstractBasicUser`, Permissions-Basis. Tool-Spezifika (strikes,
eligibility, retention, easy_mode) bleiben in den Tools. Umstellung pro Tool
mit besonderer Sorgfalt (Auth = sensibel, Keycloak-Testdurchlauf).

Umgesetzt (`auth/v0.1.0`): OIDCBackend, SilentLoginView, Back-Channel-
Logout, Discovery, `is_oidc_admin`, `AbstractBasicUser`. Die Phase-0-
Unterschiede sind Konfiguration geworden: `MAX_USERS` (mit
`anonymized_at`-Konvention) und `OIDC_MATCH_BY_USERNAME_FALLBACK`
(Default aus; abstimmbar aktiviert es explizit). Betreiber-Doku zu
Löschfristen vs. Kennungs-Vakanz im Paket-README (Faustregel:
Anonymisierungsfrist « IdP-Mindest-Vakanzzeit). 25 Paket-Tests.
Umstellungs-MRs: ausleihbar !169, abstimmbar !93 — Suiten grün (447/402),
Image-Builds verifiziert; manueller Keycloak-Durchlauf beim Review
erbeten. Nicht extrahiert (bewusst): Retention/Anonymisierung — 
`anonymize_user` fasst Tool-Modelle an; Kandidat für später mit
Hook-Design, wenn ein zweites Tool Retention baut. User-Model-Rebase auf
`AbstractBasicUser` folgt pro Tool beim nächsten natürlichen Anlass.

### Phase 5 — `basicbar-lti` ✅ (2026-07-19)
`abstimmbar/backend/lti/` weitgehend 1:1 extrahieren (inkl. Migrationen im
Paket), per `INSTALLED_APPS` + Env aktivierbar. abstimmbar stellt um;
ausleihbar bekommt die Fähigkeit gratis, aktiviert sie aber erst bei Bedarf.

Umgesetzt (`lti/v0.1.2`): Statt 1:1 ein bewusster Library-Schnitt — das
Paket trägt das generische Fundament (Plattform-Registrierung, Tool-Key,
OIDC-Initiation, JWKS, JIT-Provisionierung mit link_by_email, Staff-API,
Frame-Ancestors-Middleware mit konfigurierbaren Pfad-Präfixen); der
Message-Launch und Deep Linking bleiben Tool-Code, denn worauf ein
Kurskontext abbildet (Raum, Pool, …) ist Fachlogik. Das Kontext-Link-
Model bleibt beim Tool (FK auf Fachmodelle). 28 Paket-Tests mit
simuliertem LMS-Handshake. Migrationsweg: Daten-Umzugsmigration
(abstimmbar lti/0003, PK-erhaltend per SQL, normales migrate) — zwei
Anläufe waren nötig: geerbte Tabellennamen + fake-initial scheitern an
Djangos History-Konsistenz-Check (v0.1.0/0.1.1 zurückgezogen), und
UniqueConstraint-Namen brauchen Paket-Präfixe, weil Constraint-Namen in
Postgres schemaweit kollidieren (v0.1.2). Umstellung: abstimmbar !94;
ausleihbar unverändert.

### Phase 6 — Copier-Template + Nagelprobe erkennbar
Projektgerüst aus dem Zieldstand von ausleihbar/abstimmbar destillieren;
Template-Fragen: Projektname, LTI ja/nein, Ports, Sprachen. Dann **erkennbar
aus dem Template generieren** — das Greenfield-Projekt ist der ideale erste
Konsument und deckt jede Lücke im Template auf. Bestehende Tools werden
nachträglich per `copier init --pretend`-Abgleich angebunden, nicht neu
generiert.

### Phase 7 — Zukunftsthemen (Hilfe, Tutorials, Selbsterklärung)
Bewusst *nicht* abstrakt in basicbar entwerfen. Vorgehen: im konkreten Tool
mit dem meisten Nutzerfeedback (ausleihbar) bauen, in einem zweiten Tool
nachziehen, dann das Gemeinsame extrahieren — wie bei translation_service
geschehen, nur diesmal mit basicbar als Ziel statt einer weiteren Kopie.
Kandidaten für spätere Pakete: `basicbar-help` (Seiten/Markdown-Hilfe,
abstimmbars `documents.py`/`markdown.py`-Muster), Tutorial-/Onboarding-Overlay
in `@basicbar/ui`.

## Was bewusst NICHT in die Basis kommt

- Fachlogik (lending, catalog, live, booking, …)
- Konkrete User-Models und deren Migrationen
- Alles, was erst ein Tool braucht (erst Rule of Two erfüllen)
- Deployment-Spezifika einzelner Instanzen

## Risiken

- **Basis-Pflege ist echtes Produkt-Ownership.** Jede API-Änderung an einem
  Paket kostet Upgrades in n Tools → Semver, CHANGELOG, kleine Releases.
- **Über-Abstraktion** ist das Hauptrisiko. Gegenmittel: Rule of Two, Phase 7-
  Vorgehen, Komponenten einzeln statt "UI-Framework auf Vorrat".
- **Divergenz-Rückfall**, wenn Tools Paketcode doch lokal patchen. Gegenmittel:
  Regel 5 + Erweiterungspunkte als First-Class-Feature der Pakete.
