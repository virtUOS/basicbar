# Stack-Upgrade November 2026: Vite 8, React 19, Django 6.1, Tailwind 4

Erfahrungsbericht und Anleitung für die „-bar“-Tools. Durchgeführt in
abstimmbar (2.0-Linie) und zuvor teilweise in ausleihbar. Jeder Abschnitt
nennt die Schritte, die Stolperfallen mit Fehlermeldung, Ursache und Lösung
sowie die Prüfungen, die sich bewährt haben. Für die Details der
Bibliotheken gelten die offiziellen Upgrade-Guides (verlinkt); hier steht
nur, was bei uns zusätzlich zu beachten war.

| Schritt | abstimmbar | ausleihbar | Stand der übrigen Tools (Nov. 2026) |
|---|---|---|---|
| Vite 8 + plugin-react 6 | virtUOS/abstimmbar#326 | erledigt (8346f68) | Vite 5/6 |
| React 19 | virtUOS/abstimmbar#328 | erledigt (b4dabef) | React 18 |
| Django 6.1 | virtUOS/abstimmbar#327, Fix #329 | erledigt (Dependabot #183) | Django 5.1 |
| Tailwind 4 | virtUOS/abstimmbar#330 | offen | Tailwind 3 |

**Reihenfolge:** Vite → React → Django → Tailwind. Vite, React und Django
hängen nicht an basicbar und lassen sich einzeln mergen. Django betrifft nur
das Backend und kann parallel zu einem Frontend-PR laufen. Immer nur **einen**
Frontend-PR gleichzeitig offen halten, weil jeder das `package-lock.json`
umschreibt. Keine gestapelten PRs: jeder PR geht gegen `main`.

**Ein Tool mit Release-Linie** (z. B. abstimmbar `release/1.0`) bleibt dort
auf dem alten Stand (Django 5.2 LTS). Beim „Merge up“ in `main` bei einem
Versionskonflikt die Version von `main` behalten.

**basicbar-Pakete: zwei Mindestversionen.** Unter mozilla-django-oidc 5
braucht es `basicbar-auth` ab 0.3.0 (sonst 500 beim Login bei
Uhrabweichung), unter Tailwind 4 `@basicbar/ui` ab 0.11.2 (Fokus im
Kontrastmodus). Ansonsten laufen `@basicbar/ui` (Peer `react >=18`,
Tailwind-Preset als JS) und die Django-Pakete (`Django>=5.1`) unverändert.

---

## 1. Vite 8 und `@vitejs/plugin-react` 6

Offizieller Guide: <https://vite.dev/guide/migration>

**Schritte**

1. `vite` und `@vitejs/plugin-react` **zusammen** heben.
2. Die `optionalDependencies` `@rollup/rollup-linux-*` entfernen. Sie waren
   der Workaround für npm/cli#4828 im Docker-Build. Vite 8 bündelt mit
   Rolldown, und das Lockfile enthält jetzt `@rolldown/binding-*` für alle
   Plattformen.
3. `vite.config.ts` braucht nur dann eine Änderung, wenn dort
   `build.rollupOptions` steht (wird `build.rolldownOptions`).
4. Kommentare im `frontend/Dockerfile`, die Rollup nennen, anpassen.

**Stolperfalle: Dependabot hebt nur Vite.**
`npm ci` scheitert mit `ERESOLVE … @vitejs/plugin-react@4.7.0 … Found:
vite@8.x`. Ursache: plugin-react 4 erlaubt nur Vite bis 7. Lösung: beide
Pakete in einem PR heben und den Dependabot-PR schließen („Supersedes #…“).

**Prüfen**

- `npm ci && npm run build` im Image des Produktions-Builds
  (`node:24-slim`), **auf `linux/arm64` und `linux/amd64`**
  (`docker run --platform …`).
- Den Dev-Server starten und `/src/main.tsx` abrufen. Die Antwort muss 200
  sein und den React-Refresh-Preamble enthalten.
- Dev-Stack: Der Frontend-Container hat ein eigenes `node_modules`-Volume,
  danach also `docker compose exec frontend npm ci` und den Container neu
  starten.

## 2. React 19

Offizieller Guide: <https://react.dev/blog/2024/04/25/react-19-upgrade-guide>

**Schritte**

1. `react`, `react-dom`, `@types/react` und `@types/react-dom` **in einem
   Schritt** auf 19 heben.
2. `npx tsc -b` laufen lassen und die Typfehler beheben. Bei uns waren es
   ausschließlich diese beiden Muster:
   - `useRef<T>(null)` liefert jetzt `RefObject<T | null>`. Parameter und
     Props vom Typ `RefObject<HTMLDivElement>` auf
     `RefObject<HTMLDivElement | null>` umstellen.
   - Der globale `JSX`-Namespace entfällt. Stattdessen
     `import type { JSX } from "react"` schreiben (ausleihbar).
3. Mit `npm ls react` prüfen, dass nur eine deduplizierte React-Version
   installiert ist (für @basicbar/ui inkl. TipTap, dnd-kit, react-router,
   lucide, react-i18next).

**Stolperfalle: Dependabot trennt `react` und `react-dom`.**
Jeder der beiden PRs scheitert für sich an `npm ci`
(`ERESOLVE … @types/react-dom@18 … Found: @types/react@19`). Empfehlung für
`dependabot.yml`: eine Gruppe für diese vier Pakete.

```yaml
groups:
  react:
    patterns: ["react", "react-dom", "@types/react", "@types/react-dom"]
```

**Prüfen**

Die komplette Playwright-Suite auf einem isolierten Stack laufen lassen,
**zuerst mit dem alten Stand als Vergleich**, dann mit React 19 auf
demselben Stack. Ohne Vergleichslauf sind umgebungsbedingte Fehler (keine
KI, kein Impressum, Tour-Overlay) nicht von echten Regressionen zu trennen.
abstimmbar: keine neuen Fehler. Zwei Tests waren nur unter Volllast
abgebrochen und liefen bei Wiederholung grün.

## 3. Django 6.1

Offizielle Release-Notes: <https://docs.djangoproject.com/en/6.1/releases/6.0/>
und <https://docs.djangoproject.com/en/6.1/releases/6.1/>

**Schritte**

1. **Vorher** die Suite unter dem alten Django mit
   `PYTHONWARNINGS=always` laufen lassen und nach `RemovedInDjango60Warning`
   suchen (abstimmbar und ausleihbar: keine).
2. `Django==6.1.x` in `requirements.txt`. Bei uns musste kein anderer Pin
   mitwandern: DRF 3.18, mozilla-django-oidc 5.0.2, django-modeltranslation
   0.20.6, PyLTI1p3 2.0.0, django-cors-headers 4.9 und alle basicbar-Pakete
   laufen; mit mozilla-django-oidc 5 aber erst mit `basicbar-auth` ab 0.3.0
   (sonst 500 beim Login bei Uhrabweichung, Zeitsynchronisation per NTP
   bleibt trotzdem empfohlen).
3. Die Suite unter 6.1 mit `PYTHONWARNINGS=always` laufen lassen, dazu
   `check --deploy`, `makemigrations --check` und `pip check`.
4. Den Dev-Stack mit `docker compose build backend` neu bauen, weil sich
   `requirements.txt` geändert hat.

**Mailversand: die einzige Deprecation (Entfall in „Django 2028“).**
Betroffen sind die `EMAIL_*`-Settings, `get_connection()`, das Argument
`connection=` und `fail_silently=`. Ersatz ist das Setting `MAILERS`. Die
Umgebungsvariablen können `EMAIL_*` heißen bleiben, dann ändert sich am
Server nichts:

```python
# config/mail.py — reine Funktion, testbar ohne Django-Settings
SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

def mailers_from_env(env):
    backend = env.get("EMAIL_BACKEND", "") or SMTP_BACKEND
    if backend != SMTP_BACKEND:
        return {"default": {"BACKEND": backend}}   # console/locmem/file: KEINE Optionen
    use_ssl = env.get("EMAIL_USE_SSL", "0") == "1"
    return {"default": {"BACKEND": backend, "OPTIONS": {
        "host": env.get("EMAIL_HOST", ""), "port": int(env.get("EMAIL_PORT") or 587),
        "username": env.get("EMAIL_HOST_USER", ""), "password": env.get("EMAIL_HOST_PASSWORD", ""),
        "use_ssl": use_ssl, "use_tls": env.get("EMAIL_USE_TLS", "1") == "1" and not use_ssl,
        "timeout": int(env.get("EMAIL_TIMEOUT") or 10),
    }}}

# settings.py
MAILERS = mailers_from_env(os.environ)
```

Gesendet wird mit `from django.core.mail import mailers` und
`mailers.default.send_messages([msg])` (eine SMTP-Sitzung für viele
Nachrichten) oder mit `msg.send(using="default")`. `mailers` gibt es erst ab
6.1, solcher Code darf also **nicht auf eine Release-Linie mit 5.2**
gelangen.

**Stolperfalle (bei uns erst nach dem Merge entdeckt, behoben in
virtUOS/abstimmbar#329):**
`InvalidMailer: MAILERS['default']: Unknown options 'host', 'port', …`
Ursache: Django 6.1 prüft die `OPTIONS` gegen das Backend. Das
Konsolen-Backend der Dev-Compose akzeptiert keine SMTP-Optionen, das
Einladen per Mail lieferte deshalb HTTP 500. Die Unit-Tests merken das
**nicht**, weil der Test-Runner `MAILERS` vollständig durch locmem ersetzt.
Lösung: die SMTP-Optionen nur an das SMTP-Backend geben (siehe oben) und
einen Test schreiben, der die echten Backends instanziiert:

```python
with self.settings(MAILERS=mailers_from_env({"EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend", "EMAIL_HOST": "x"})):
    mailers.default   # darf nicht werfen
```

`mail.outbox` und `mock.patch.object(smtp.EmailBackend, …)` funktionieren in
Tests unverändert.

**Prüfen: Lasttest (SSE-Tools).** In abstimmbar ergab der Lasttest mit 1000
Teilnehmenden auf uvicorn dieselben Werte wie unter 5.2 (1000/1000 Stimmen,
Fan-out-Streuung rund 110 ms). Laufen Lastgenerator und Server im selben
Container, braucht es `docker run --ulimit nofile=65536:65536`, sonst
erscheint `Too many open files`.

## 4. Tailwind CSS 4

Offizieller Guide: <https://tailwindcss.com/docs/upgrade-guide>

**Browser-Mindestversionen:** Chrome/Edge 111, Firefox 128, Safari 16.4.
Betroffen sind nur Oberflächen mit Tailwind. In abstimmbar ist die
Teilnahmeseite ein Django-Template ohne Tailwind und deshalb nicht
betroffen. Die Mindestversionen in die Anleitung des Tools aufnehmen.

**Das basicbar-Preset funktioniert unverändert.** Tailwind 4 liest die
bisherige JS-Konfiguration (`tailwind.config.js` mit
`createPreset({ colors })`) über `@config`. Bei uns funktionierten die
`/ <alpha-value>`-Rampen (`bg-slate-900/90`), Tokens der Form
`oklch(var(--x) / <alpha-value>)` und der Dunkelmodus über die
`.dark`-Klasse (`darkMode: "class"` wird zu `:where(.dark, .dark *)`). Auch
`@basicbar/ui/base.css` mit seinen `@apply`-Regeln kompiliert.

**Schritte**

1. Das offizielle Werkzeug **auf dem Host im Worktree** ausführen:
   `cd frontend && npm ci && npx @tailwindcss/upgrade@4 --force`.
   Im `node:24-slim`-Container lief es bei uns stumm ohne Ergebnis,
   vermutlich weil das `.git` eines Worktrees außerhalb des Mounts liegt.
   Das Werkzeug benennt Klassen um (`rounded`→`rounded-sm`,
   `rounded-sm`→`rounded-xs`, `shadow-sm`→`shadow-xs`,
   `outline-none`→`outline-hidden`, `outline`→`outline-solid`,
   `blur`→`blur-sm` …). Außerdem ersetzt es `tailwindcss` + `autoprefixer`
   in PostCSS durch `@tailwindcss/postcss` und ergänzt einen Kompat-Block
   für die Standard-Rahmenfarbe.
2. `index.css` von Hand aufräumen. Das Werkzeug lässt Kommentare verwaist
   stehen. Ziel:

   ```css
   @import 'tailwindcss';
   @import '@basicbar/ui/base.css';
   @config '../tailwind.config.js';
   /* danach: Kompat-Block, Tool-Variablen in @layer base, eigene Styles */
   ```

   `base.css` bleibt **ohne** `layer(base)`. Mit `layer()` werden die
   Ebenen von `base.css` zu Unterebenen von `base` und verlieren gegen den
   Preflight. Der Skip-Link erscheint dann ohne Abstand, dunkel auf dunkel.

3. Jede **separat importierte** CSS-Datei, die `theme()` oder `@apply`
   nutzt, braucht `@reference "../index.css";`. Das Werkzeug macht das nicht.

**Stolperfallen**

- **`@import` nach `@config` wird still verworfen.** Nach CSS-Regel muss
  jedes `@import` vor allen anderen Anweisungen stehen. Bei uns fehlte dadurch
  zunächst das komplette `base.css` (Skip-Link, Fokusring, `::selection`,
  ProseMirror), ohne Fehlermeldung. Prüfen:
  `grep -c skip-link dist/assets/*.css` muss ≥ 1 ergeben. Das reicht allein
  nicht (siehe nächster Punkt).
- **Skip-Link per Tab prüfen.** Die Regel kann im Build stehen und trotzdem
  gegen den Preflight verlieren. Im Browser einmal Tab drücken: Der Skip-Link
  hat sichtbaren Innenabstand und deutlichen Kontrast (im hellen Theme
  heller Text auf dunklem Grund, im dunklen umgekehrt).
- **Eigene Komponentenklassen (etwa `.btn-*`) gehören in
  `@layer components`.** Ungeschichtete Klassen überstimmen in v4 jede
  Utility am selben Element, auch `hover:`, `disabled:` und `aria-pressed:`.
  Die Hover- und Disabled-Zustände wirken dann nicht mehr.
- `Could not resolve value for theme function: theme(colors.white)`
  bedeutet, dass in einer eigenen CSS-Datei das `@reference` fehlt (siehe
  Schritt 3).
- **Transform-Utilities** (`translate-*`, `rotate-*`, `scale-*`) setzen in
  v4 die CSS-Eigenschaften `translate`, `rotate` und `scale` statt
  `transform`. Ein Inline-`style.transform` auf demselben Element ersetzt die
  Klasse deshalb nicht mehr, beide wirken zusammen. Solche Elemente suchen
  (abstimmbar: keine). Tests, die `getComputedStyle(el).transform` prüfen,
  auch `rotate`/`translate` prüfen lassen.
- **Zeilenhöhe:** `text-sm` usw. setzen jetzt eine einheitenlose
  Zeilenhöhe. Kinder mit `text-[11px]` erben das Verhältnis statt 20 px,
  kleine Abzeichen werden dadurch 1–4 px flacher. Optisch unbedenklich.
- Die nativen Bindings (`@tailwindcss/oxide-*`, `lightningcss-*`) stehen für
  alle Plattformen im Lockfile, auch wenn es auf macOS erzeugt wurde. Trotzdem
  im Linux-Container auf beiden Architekturen bauen.

**Prüfen: visueller Vergleich.** Bewährt hat sich Playwright
`toHaveScreenshot` (`fullPage`, `animations: 'disabled'`) auf einem
isolierten Stack mit **einem** Seed:

1. Mit Tailwind 3 aufnehmen (`--update-snapshots`).
2. Ohne Änderung wiederholen, um zu prüfen, dass die Bilder pixelgenau
   reproduzierbar sind.
3. Auf Tailwind 4 umschalten (Dateien per `git checkout` wechseln, im
   Container `npm ci`) und vergleichen.

abstimmbar, 12 Seiten × hell/dunkel × 1280/324 px: 44 von 48 Seiten
pixelgleich, die übrigen vier mit den flacheren Abzeichen von oben. Danach
die volle e2e-Suite mit Vergleichslauf (siehe React).

**`outline-none` in `base.css`:** `base.css` nutzte im Fokusstil
`@apply outline-none`. In v4 bedeutet das `outline-style: none`. In v3 war
es eine transparente Outline, die im Windows-Kontrastmodus sichtbar wird.
Behoben in `@basicbar/ui` 0.11.2 mit einer transparenten Outline, die unter
Tailwind 3 und 4 gleich wirkt. Tools, die selbst eine `forced-colors`-Regel
dagegen gesetzt haben, können sie nach dem Upgrade entfernen.

Das Template (`template/project/frontend`) steht noch auf React 18, Vite 6,
Tailwind 3 und Django 5.1. Heben, sobald die ersten Tools umgestellt sind.

---

## Anhang: isolierter Prüf-Stack (Muster abstimmbar)

So läuft ein zweiter Stack neben dem Dev-Stack, ohne dessen Datenbank
anzufassen:

```bash
export COMPOSE_PROJECT_NAME=<tool>fix POSTGRES_PORT=5434 BACKEND_PORT=8003 FRONTEND_PORT=5175 \
  FRONTEND_BASE_URL=http://localhost:5175/ OIDC_LOGIN_REDIRECT_URL=http://localhost:5175/ \
  OIDC_LOGOUT_REDIRECT_URL=http://localhost:5175/ VITE_API_BASE_URL=http://localhost:8003
docker compose -f docker-compose.yml -f fix.override.yml up -d --no-deps --no-build db backend frontend
```

Die Override-Datei setzt eigene `container_name`s, nutzt per `image:` die
vorhandenen Dev-Images statt eines Builds und stellt CORS/CSRF auf
5175/8003 um.

Dazu gehören diese Handgriffe:
- **Keycloak:** Den Redirect `http://localhost:8003/*` per `kcadm` am
  Backend-Client ergänzen und danach wieder entfernen.
- **Frontend:** Das `node_modules`-Volume wird aus dem Image initialisiert,
  deshalb im Container `npm ci` ausführen.
- **Testkonten:** Frische Konten sehen die Willkommens-Tour, die Klicks
  blockiert. Für alle Konten das Tour-Flag setzen, auch für das Admin-Konto.
- **e2e:** Gegen andere Ports eine Kopie der Specs mit `5174→5175` und eine
  angepasste Playwright-Config verwenden.
- **colima:** Bind-Mounts funktionieren nur unter `/Users`, nicht unter
  `/private/tmp`.
- **Aufräumen:** zum Schluss `docker compose … down -v`.
