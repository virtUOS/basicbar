# LTI Dynamic Registration — Design

Stand 2026-11-25. Status: Entwurf zur Abstimmung (Builder-Check eingearbeitet).

## Absicht

Die -bar-Tools mit LTI (abstimmbar, ausleihbar) werden heute von Hand mit
einem LMS verknüpft: Der Tool-Admin legt im Web-Admin eine `LtiPlatform`
an (Issuer, Client-ID, drei Plattform-URLs, Deployment-IDs), der
LMS-Admin trägt die Tool-URLs aus `LtiToolInfoView` in Moodle ein. Das
geht hin und her — Moodle vergibt die Deployment-ID erst nach dem
Speichern — und ist fehleranfällig (abschließender Slash im Issuer,
vertauschte URLs).

Mit **LTI Dynamic Registration** (IMS LTI Dynamic Registration 1.0) gibt
der Moodle-Admin nur noch eine URL ein; Tool und Moodle tauschen alle
Werte selbst aus. Ziel ist weniger Handarbeit und weniger Fehler beim
Verknüpfen, **ohne** dass das Verknüpfen ohne Admins geschieht: Beide
Seiten sollen bewusst beteiligt sein.

## Ziele

- Ein Tool-Admin erzeugt im Web-Admin des Tools einen **Einmal-Link**
  und gibt ihn dem Moodle-Admin.
- Der Moodle-Admin trägt den Link in Moodle als Tool-URL ein
  („LTI Advantage“-Registrierung). Tool und Moodle registrieren sich
  gegenseitig; im Tool entsteht eine aktive `LtiPlatform` mit Issuer,
  Client-ID, Endpunkten und Deployment-ID. In Moodle aktiviert der
  Moodle-Admin das Tool wie gewohnt.
- Danach funktionieren Launch und Deep Linking (beide Tools) mit **einem**
  dokumentierten Nachschritt in Moodle: Startcontainer auf „Neues
  Fenster“ stellen (siehe „Startcontainer“). Ziel ist also „fast ohne
  Handarbeit“, nicht „ohne“.
- Der Mechanismus liegt in `basicbar-lti`; was ein Tool anmeldet (Name,
  Beschreibung, Nachrichtentypen, Icon), konfiguriert jedes Tool selbst.

## Nicht-Ziele

- **Stud.IP, ILIAS, Canvas:** Referenz ist Moodle. Andere LMS laufen
  weiter über die manuelle Registrierung; Stud.IP ggf. später als
  Feature-Request an Stud.IP.
- **planbar** bleibt außen vor (hat noch keine LTI-App).
- **Copier-Template:** enthält kein LTI; bleibt unverändert.
- **Ersetzen der manuellen Registrierung:** Sie bleibt vollständig
  erhalten (andere LMS, Sonderfälle, Korrekturen).
- **Umstieg bestehender, von Hand angelegter Plattformen** (User-
  Entscheidung 2026-11-25): Dynamic Registration ist nur für **neue**
  Verknüpfungen. An einer `LtiPlatform` hängen `LtiUserLink`
  (LTI-Nutzer → Konto) und die Kursverknüpfungen der Tools (abstimmbar
  `LtiContextLink` → Raum, ausleihbar `LtiCourseLink` → Pool); eine
  Neuregistrierung erzeugt eine neue Plattform mit neuer Client-ID, die
  alte zu deaktivieren würde diese Verknüpfungen verwaisen lassen und
  doppelte Konten erzeugen. Kein Datenumzug, kein Update bestehender
  Registrierungen per Dynamic Registration.
- **Eingebetteter Start ab Werk:** Den Start im Moodle-iframe ohne
  Zusatz-Einstellungen am Tool-Server lauffähig zu machen (dynamische
  `frame-ancestors` für die SPA, `SameSite` der Session-Cookies) ist ein
  eigenes Vorhaben (User-Entscheidung 2026-11-25).
- **Ein gemeinsames Admin-UI-Bauteil in `@basicbar/ui`:** Die beiden
  Admin-Seiten (abstimmbar `AdminPage`, ausleihbar `AdminLmsPage`) sind
  verschieden gebaut; jedes Tool bekommt seinen Button selbst.

## Anti-Ziele (wäre ein Fehlschlag, auch wenn es technisch läuft)

- Jemand ohne vom Tool-Admin ausgegebenen Link kann eine Plattform
  anlegen.
- Das Tool ruft auf Zuruf eines Unbekannten beliebige URLs ab
  (Server-Side Request Forgery).
- Ein Link lässt sich mehrfach verwenden, oder ein alter, vergessener
  Link funktioniert nach Monaten noch.
- Die bestehende Einbettungs-Policy (`frame-ancestors` nur für aktive
  Plattformen) wird für `/lti/` allgemein aufgeweicht.
- Ein Tool ändert ohne Konfiguration sein Verhalten (Paket-Konvention
  „aus per Default“).

## Rahmenbedingungen

- PyLTI1p3 2.0 kennt keine Dynamic Registration — der Ablauf wird im
  Paket selbst implementiert (HTTP-Client: stdlib `urllib` wie in
  `basicbar-integrations`, keine neue Abhängigkeit).
- Ein Schlüsselpaar für alle Plattformen (`LtiToolKey`), JWKS unter
  `lti-jwks` — bleibt so; Moodle bekommt die JWKS-URL.
- ausleihbar hat kein `FRONTEND_BASE_URL`; seine `LtiToolInfoView` baut
  die URLs per `reverse()` + `request.build_absolute_uri`. Die
  Registrierung macht es genauso (siehe unten).
- Paket-Konventionen (CLAUDE.md): Settings über `conf.py` mit Defaults,
  Constraint-Namen mit Präfix `basicbar_lti_`, CHANGELOG mit
  Migrationsschritten für die Tools, Tag erst nach dem Merge.
- Moodle öffnet die Registrierungs-URL in einem eingebetteten Fenster
  (iframe im Dialog); die Seite muss sich dort einbetten lassen, obwohl
  die Plattform noch nicht registriert ist.

## Ansätze

Wie wird der **Tool-Admin** beteiligt? (Moodle hat seinen Admin-Schritt
schon: ein dynamisch registriertes Tool muss dort aktiviert werden.)

- **A — Einmal-Link vom Tool-Admin (gewählt).** Der Tool-Admin erzeugt
  einen Link mit Einmal-Token und begrenzter Gültigkeit; der Link ist die
  Freigabe, die Plattform ist nach der Registrierung sofort aktiv. Ohne
  gültigen Token ruft das Tool nichts ab. Kosten: Der Link muss vom
  Tool-Admin zum Moodle-Admin gelangen.
- **B — Feste offene URL + Freigabe im Tool.** Keine Übergabe nötig, aber
  eine öffentliche URL, die Einträge anlegt und das Tool fremde URLs
  abrufen lässt; die Angriffsfläche bleibt trotz Eingrenzung.
- **C — Tool-Login im Registrierungsfenster.** Scheitert, wenn Moodle-
  und Tool-Admin verschiedene Personen sind, und an blockierten
  Third-Party-Cookies im iframe.

Entscheidungen des Users (2026-11-25): **A, Einmal-Link**. Referenz-LMS:
Moodle. Admins auf beiden Seiten beteiligt. Startcontainer: dokumentierter
Nachschritt „Neues Fenster“ in Moodle statt eingebettetem Start ab Werk.
Nur neue Verknüpfungen, kein Umstieg bestehender Plattformen (Warnung bei
bekanntem Issuer).

## Design

### Ablauf

1. **Link erzeugen.** Tool-Admin klickt im Web-Admin „Registrierungs-Link
   erzeugen“, optional mit einer Notiz („Moodle Uni Osnabrück, Test“).
   Das Tool legt ein `LtiRegistrationToken` an und zeigt die URL **einmal**
   an: `https://<tool>/lti/register/?token=<geheim>`.
2. **In Moodle eintragen.** Moodle-Admin: Website-Administration →
   Plugins → Externe Tools → Tools verwalten → Tool-URL einfügen →
   „LTI Advantage hinzufügen“. Moodle öffnet die URL mit den
   Spec-Parametern `openid_configuration` und `registration_token`.
3. **Token prüfen.** Das Tool prüft den Token (existiert, nicht
   abgelaufen, nicht verbraucht). Ungültig → Fehlerseite, **kein**
   ausgehender Request.
4. **Plattform-Konfiguration holen.** GET auf `openid_configuration`
   (mit `registration_token` als Bearer, falls vorhanden). Prüfungen:
   - nur `https` (Ausnahme: Setting für lokale Entwicklung, s. u.);
   - Timeout, Größenlimit der Antwort, keine Weiterleitung auf einen
     anderen Host;
   - Zieladresse: Loopback (`127.0.0.0/8`, `::1`), link-lokal
     (`169.254.0.0/16`, `fe80::/10`, u. a. Cloud-Metadaten) und
     unspezifizierte Adressen werden abgelehnt; private Netze (`10/8`,
     `172.16/12`, `192.168/16`) bleiben erlaubt, weil ein Campus-Moodle
     dort liegen kann. Geprüft wird die per DNS aufgelöste Adresse vor
     dem Request; kein Festnageln der IP gegen DNS-Rebinding — der Link
     ist geheim, einmalig und befristet (eigene Entscheidung,
     Builder-Check). Gilt für alle ausgehenden Requests (Schritte 4 und 5);
     `LTI_REGISTRATION_ALLOW_HTTP` hebt diese Sperre für lokale
     Entwicklung mit auf.
   - `issuer` aus der Antwort: Die `openid_configuration`-URL muss mit dem
     Issuer beginnen (Spec-Anforderung); `authorization_endpoint`,
     `token_endpoint`, `jwks_uri`, `registration_endpoint` auf demselben
     Host wie der Issuer (Härtung, eigene Entscheidung — bei Moodle
     erfüllt).
5. **Beim LMS registrieren.** POST auf `registration_endpoint` mit
   `Authorization: Bearer <registration_token>` und der
   Tool-Konfiguration (OIDC-Client-Metadaten + Block
   `https://purl.imsglobal.org/spec/lti-tool-configuration`):
   `application_type: web`, `response_types: [id_token]`,
   `grant_types: [implicit, client_credentials]`,
   `token_endpoint_auth_method: private_key_jwt`, `initiate_login_uri`
   (`lti-login`), `redirect_uris` (`lti-launch`), `jwks_uri`
   (`lti-jwks`), `client_name`, `logo_uri`, `scope`; im LTI-Block
   `domain`, `target_link_uri`, `claims`, `messages`, `description`.
6. **Plattform anlegen.** Aus Konfiguration + Antwort entsteht eine
   `LtiPlatform`: `issuer`, `client_id` (Antwort), `auth_login_url` =
   `authorization_endpoint`, `auth_token_url` = `token_endpoint`,
   `key_set_url` = `jwks_uri`, `deployment_ids` = `[deployment_id]` aus
   der Antwort, `name` = Notiz des Tokens oder `client_name`/Produkt aus
   der Plattform-Konfiguration, `is_active=True`, `link_by_email=False`
   (bleibt bewusste Admin-Entscheidung). Der Token wird **im selben
   Datenbank-Vorgang** als verbraucht markiert und mit der Plattform
   verknüpft.
   **Issuer schon bekannt:** Gibt es bereits eine aktive `LtiPlatform` mit
   demselben Issuer, fragt die Seite **vor** Schritt 5 nach: Hinweis, dass
   eine bestehende Verknüpfung nicht übernommen wird (Kursverknüpfungen
   und Konten hängen an der alten), mit „Trotzdem neu registrieren“ und
   „Abbrechen“. Abbrechen verbraucht den Token nicht.
7. **Abschluss.** Das Tool zeigt eine kurze Erfolgsseite und schickt per
   `postMessage({subject: "org.imsglobal.lti.close"}, "*")` an
   `window.opener || window.parent` das Schließen-Signal. Moodle zeigt
   das Tool danach als ausstehend; der Moodle-Admin aktiviert es. Die
   Erfolgsseite nennt den Nachschritt „Startcontainer auf Neues Fenster
   stellen“ ausdrücklich (siehe „Startcontainer“).

Schlägt Schritt 4 oder 5 fehl (Netz, LMS lehnt ab), bleibt der Token
**unverbraucht** (Wiederholung möglich, solange gültig); die Seite nennt
dem Moodle-Admin den Fehler im Klartext, das Tool loggt Details.

### Datenmodell (`basicbar-lti`, Migration `0002`)

`LtiRegistrationToken`:

- `token_hash` — SHA-256 des Tokens (der Klartext wird nur einmal
  angezeigt, nie gespeichert), eindeutig;
- `note` — Freitext des Admins (wird Plattformname);
- `created_by` — FK auf `AUTH_USER_MODEL`, `SET_NULL`;
- `created_at`, `expires_at`;
- `used_at` (null), `platform` — FK auf `LtiPlatform`, `SET_NULL`, null.

Gültigkeit per Setting `LTI_REGISTRATION_TOKEN_TTL` (Default 7 Tage).
Verbrauch per `select_for_update` — zwei gleichzeitige Versuche mit
demselben Token ergeben höchstens eine Plattform.

### Endpunkte (`basicbar-lti`)

- `lti_register` (View-Funktion, Tool verdrahtet sie unter
  `lti/register/`, Name `lti-register`) — Schritte 3–7, HTML-Antwort.
- `LtiRegistrationTokenViewSet` (Staff-API wie `LtiPlatformViewSet`,
  Tools überschreiben `permission_classes`): `create` liefert die URL
  einmalig zurück, `list` zeigt Notiz/Ersteller/Ablauf/Status (ohne
  Token), `destroy` widerruft einen offenen Token.
- Django-Admin: `LtiRegistrationToken` lesbar, Widerrufen möglich.

### URLs der Tool-Konfiguration

Alle Tool-URLs per `reverse()` der etablierten Namen (`lti-login`,
`lti-launch`, `lti-jwks`, `lti-register`) und
`request.build_absolute_uri` — wie in ausleihbar. Der Registrierungs-
Request kommt vom Browser des Moodle-Admins aufs Tool, die Basis-URL ist
also die öffentliche. Die erzeugte Einmal-URL entsteht in der Staff-API
genauso. (`LtiToolInfoView` im Paket bei der Gelegenheit ebenfalls auf
`reverse()` umstellen — offener Punkt aus dem Framework-Review.)

### Was ein Tool anmeldet (Setting `LTI_TOOL_REGISTRATION`)

Dict in `conf.py` mit Defaults; ein Tool setzt nur, was abweicht:

- `client_name` (Default: `"LTI Tool"`; Tools setzen ihren Namen),
  `description`, `logo_path` (z. B. `/lti/icon.svg`, wird absolut
  gemacht; leer → kein `logo_uri`);
- `messages`: Default nur `LtiResourceLinkRequest` auf `lti-launch`;
  abstimmbar und ausleihbar ergänzen `LtiDeepLinkingRequest` (Ziel
  ebenfalls `lti-launch`, beide unterscheiden dort per
  `is_deep_link_launch`), mit Label und Placement nach Moodle-Bedarf;
- `claims`: Default `["iss", "sub", "name", "given_name",
  "family_name", "email"]` (für E-Mail-Verknüpfung und Konto-Anlage);
- `scope`: Default leer (die Tools nutzen weder Noten- noch
  Teilnehmerdienste);
- `custom_parameters`: Default `{}`.

Ohne gesetzte Werte funktioniert die Registrierung mit dem Default; ohne
verdrahtete URL `lti/register/` und ohne erzeugten Token passiert gar
nichts („aus per Default“).

### Einbetten der Registrierungsseite

Die Seite liegt unter `/lti/`, wo die Middleware `frame-ancestors` auf
aktive Plattformen setzt — die neue Plattform ist dort noch nicht
dabei. Regel: Nur bei **gültigem Token** setzt `lti_register` selbst
`frame-ancestors 'self' <Origin der openid_configuration-URL>`; die
Middleware lässt eine von der View gesetzte `frame-ancestors`-Policy
stehen (statt sie zu überschreiben). Ohne gültigen Token bleibt es bei
der normalen Policy.

### Startcontainer

Moodle setzt bei jeder dynamischen Registrierung den Startcontainer auf
„Eingebettet, ohne Blöcke“ (`registration_helper.php`, MOODLE_405_STABLE:
`lti_launchcontainer = LTI_LAUNCH_CONTAINER_EMBED_NO_BLOCKS`); die
Tool-Konfiguration kann das nicht ändern. abstimmbar und ausleihbar
verlangen in ihrer Doku „Neues Fenster“ (eingebettet braucht
`SESSION_COOKIE_SAMESITE=None`, abstimmbar zusätzlich
`ABSTIMMBAR_FRAME_ANCESTORS`). Daher: Erfolgsseite, Admin-Dialog im Tool
und Tool-Doku nennen den Nachschritt in Moodle — Tool bearbeiten →
Standard-Startcontainer „Neues Fenster“.

### Lokale Entwicklung

`LTI_REGISTRATION_ALLOW_HTTP` (Default `False`) erlaubt `http://` für
`openid_configuration` und die Endpunkte sowie Loopback-Ziele — nur für eine lokale
Moodle-Instanz (Docker). Ein System-Check warnt, wenn es bei
`DEBUG=False` gesetzt ist.

### Admin-Oberfläche der Tools

abstimmbar (`AdminPage`) und ausleihbar (`AdminLmsPage`) bekommen neben
der Plattformliste:

- Button „Registrierungs-Link erzeugen“ → Dialog mit Notizfeld → zeigt
  die URL einmal mit Kopieren-Knopf und Hinweis „gilt 7 Tage, einmal
  verwendbar“ plus Kurzanleitung für den Moodle-Admin (inkl.
  Nachschritt „Neues Fenster“ und Hinweis: nur für neue Verknüpfungen);
- Liste offener/verbrauchter Links (Notiz, Ersteller, Ablauf, Status,
  verknüpfte Plattform), Widerrufen für offene.

Die manuelle Plattformerfassung bleibt daneben unverändert.

### Doku

- `basicbar-lti/README.md`: Ablauf, Settings, Sicherheitsmodell,
  Verdrahtung im Tool.
- Tool-Doku (abstimmbar `docs/lti.md`, ausleihbar entsprechend):
  Moodle-Anleitung „mit Registrierungs-Link“ als empfohlener Weg, die
  manuelle Anleitung bleibt für andere LMS.
- CHANGELOG: `lti/v0.2.0` mit Migrationsschritten (migrate, URL
  `lti/register/` verdrahten, `LTI_TOOL_REGISTRATION` setzen,
  Token-ViewSet mit Tool-Permission einbinden, Admin-UI).

### Tests

Paket: Token-Lebenszyklus (gültig/abgelaufen/verbraucht/widerrufen,
gleichzeitiger Verbrauch), Ablauf mit gemocktem LMS (Konfiguration +
Registrierung, Felder der entstandenen Plattform, gesendete
Tool-Konfiguration), alle Ablehnungsfälle ohne ausgehenden Request,
Issuer-/Host-/Adressprüfungen, Nachfrage bei bekanntem Issuer,
`frame-ancestors` mit und ohne gültigen Token,
Fehler des LMS lassen den Token unverbraucht. Tools: Verdrahtung, Rechte
der Token-API, Settings.

### Rollout

1. PR `basicbar-lti` 0.2.0 (Paket, Migration, README, CHANGELOG) → Merge
   → Tag `lti/v0.2.0`.
2. Konsumenten-PRs abstimmbar und ausleihbar (Bump, migrate, Verdrahtung,
   Settings, Admin-UI, Doku).
3. Abnahme gegen eine echte Moodle-Instanz (Test-Moodle; lokal per
   Docker möglich).

## Moodle-Verhalten

Im Moodle-Code geprüft (`mod/lti/classes/local/ltiopenid/registration_helper.php`,
MOODLE_405_STABLE):

- `deployment_id` kommt in der Registrierungsantwort (= Tool-Typ-ID);
- `LtiDeepLinkingRequest` im `messages`-Block schaltet Deep Linking ein
  (Ziel = dessen `target_link_uri`);
- `name`/`given_name`/`family_name` bzw. `email` in `claims` setzen
  Namens- bzw. E-Mail-Weitergabe auf „immer“, sonst „nie“;
- `token_endpoint_auth_method` muss `private_key_jwt` sein,
  `response_types` muss `id_token` enthalten;
- Startcontainer wird fest „Eingebettet, ohne Blöcke“ (s. o.).

Noch gegen ein echtes Moodle zu verifizieren, bevor die Tool-Doku final
wird:

- Moodle öffnet die URL im iframe (oder neuem Fenster) und reagiert auf
  `org.imsglobal.lti.close`;
- Moodle schickt `registration_token` mit;
- welche Moodle-Versionen der Uni im Einsatz sind (Dynamic Registration
  gibt es ab Moodle 3.10; das UI unterscheidet sich zwischen 4.x und 5.x).

## Dem Umsetzer überlassen

- Texte, Layout der Erfolgs-/Fehlerseite (schlicht, zweisprachig de/en
  wie die übrigen Tool-Seiten).
- Konkrete Timeouts und Größenlimits des HTTP-Clients.
- Aufteilung in Module (`registration.py` o. ä.) und Commits.
- Ob die Token-API eigene Serializer bekommt oder schlank in der View
  bleibt.
